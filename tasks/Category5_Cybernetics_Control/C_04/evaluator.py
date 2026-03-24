"""
C-04: The Escaper task evaluation module
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from tasks.Category5_Cybernetics_Control.C_04.environment import (
    ACTIVATION_X_MAX,
    ACTIVATION_X_MIN,
    MAX_STEPS as TASK_MAX_STEPS,
    EXIT_X_MIN,
    EXIT_Y_MIN,
    EXIT_Y_MAX,
    HOLD_STEPS,
    LOCK_GATE_X_MAX,
    LOCK_GATE_X_MIN,
    ONEWAY_FORCE_RIGHT,
    ONEWAY_X,
)
from tasks.Category5_Cybernetics_Control.C_04 import prompt as c04_prompt
from tasks.Category5_Cybernetics_Control.C_04 import stages as c04_stages

# Fallback when metrics/environment omit runtime hold length (must match default unlock streak).
CONSECUTIVE_EXIT_STEPS_REQUIRED = HOLD_STEPS


def _exit_hold_steps_required(environment) -> int:
    """Exit-zone hold uses the same streak length as behavioral unlock (physics_config)."""
    if environment is not None and hasattr(environment, "_backward_steps_required"):
        return int(getattr(environment, "_backward_steps_required"))
    return int(HOLD_STEPS)


def _environment_max_steps(environment) -> int:
    if environment is not None and hasattr(environment, "MAX_STEPS"):
        return int(environment.MAX_STEPS)
    return int(TASK_MAX_STEPS)


def _oneway_params(environment):
    if environment is not None and hasattr(environment, "_oneway_x"):
        ox = float(environment._oneway_x)
        of = float(getattr(environment, "_oneway_force_right", ONEWAY_FORCE_RIGHT))
        return ox, of
    return float(ONEWAY_X), float(ONEWAY_FORCE_RIGHT)


def _lock_gate_bounds(environment):
    if environment is not None and hasattr(environment, "_lock_gate_x_min"):
        return float(environment._lock_gate_x_min), float(environment._lock_gate_x_max)
    return float(LOCK_GATE_X_MIN), float(LOCK_GATE_X_MAX)


def _activation_bounds(environment):
    if environment is not None and hasattr(environment, "_activation_x_min"):
        return float(environment._activation_x_min), float(environment._activation_x_max)
    return float(ACTIVATION_X_MIN), float(ACTIVATION_X_MAX)


class Evaluator:
    """
    C-04: Success = behavioral unlock achieved, then hold in exit zone for the configured
    consecutive-step streak (same as unlock streak from physics_config).
    Failure = timeout or structural failure.
    """

    def __init__(self, terrain_bounds, environment=None, task_description=None, **kwargs):
        self.terrain_bounds = terrain_bounds
        self.environment = environment
        self._exit_x_min = float(terrain_bounds.get("exit_x_min", EXIT_X_MIN))
        self._exit_y_min = float(terrain_bounds.get("exit_y_min", EXIT_Y_MIN))
        self._exit_y_max = float(terrain_bounds.get("exit_y_max", EXIT_Y_MAX))
        self._consecutive_in_exit = 0
        self._task_description_override = task_description
        
        # If not explicitly provided, check if it's injected in the environment's config
        if self._task_description_override is None and self.environment is not None:
            if hasattr(self.environment, "physics_config"):
                self._task_description_override = self.environment.physics_config.get("task_description")

    def evaluate(self, agent_body, step_count, max_steps):
        if not self.environment:
            # Configuration error: terminal stop (done=True) but explicitly not a physics/timeout outcome.
            return True, 0.0, {
                "error": "Environment not available",
                "success": False,
                "failed": True,
                "configuration_error": True,
                "failure_reason": (
                    "Evaluator configuration error: environment reference missing "
                    "(not a simulation timeout or structural failure)."
                ),
                "stop_reason": "evaluator_missing_environment",
            }

        reached_exit = self.environment.has_reached_exit()
        unlocked = bool(self.environment.get_metrics().get("unlocked", False))
        # Exit-hold counts only after unlock (aligns with prompt: unlock then reach + hold).
        if reached_exit and unlocked:
            self._consecutive_in_exit += 1
        else:
            self._consecutive_in_exit = 0

        x, y = self.environment.get_agent_position()
        vx, vy = self.environment.get_agent_velocity()
        whisker = self.environment.get_whisker_readings()

        exit_hold_need = _exit_hold_steps_required(self.environment)
        success = unlocked and self._consecutive_in_exit >= exit_hold_need
        failed = False
        failure_reason = None

        if self.environment and self.environment.is_destroyed():
            failed = True
            failure_reason = self.environment.get_destruction_reason()
        # step_count increments once per physics step in main loop; timeout after exactly max_steps steps
        elif max_steps > 0 and step_count >= max_steps and not success:
            failed = True
            if not unlocked:
                failure_reason = (
                    "Timeout: behavioral unlock not completed (required before exit hold counts toward success)"
                )
            else:
                failure_reason = (
                    f"Timeout: did not hold in exit zone for {exit_hold_need} "
                    "consecutive steps after unlock"
                )

        if success:
            score = 100.0
        elif failed:
            score = 0.0
        else:
            # Progress based on x-coordinate reaching the exit threshold
            progress_x = (x / self._exit_x_min) if self._exit_x_min > 0 else 0.0
            score = min(80.0, progress_x * 80.0)

        distance_to_exit_x = max(0.0, self._exit_x_min - x)
        progress_x = (x / self._exit_x_min) if self._exit_x_min > 0 else 0.0
        
        distance_y_to_band = 0.0
        if y < self._exit_y_min:
            distance_y_to_band = self._exit_y_min - y
        elif y > self._exit_y_max:
            distance_y_to_band = y - self._exit_y_max

        ox, _ = _oneway_params(self.environment)
        lock_lo, lock_hi = _lock_gate_bounds(self.environment)
        act_lo, act_hi = _activation_bounds(self.environment)
        metrics = {
            "agent_x": x,
            "agent_y": y,
            "agent_vx": vx,
            "agent_vy": vy,
            "whisker_front": whisker[0] if len(whisker) > 0 else 0.0,
            "whisker_up": whisker[1] if len(whisker) > 1 else 0.0,
            "whisker_down": whisker[2] if len(whisker) > 2 else 0.0,
            "unlocked": unlocked,
            "reached_exit": reached_exit,
            "consecutive_steps_in_exit": self._consecutive_in_exit,
            "step_count": step_count,
            "success": success,
            "failed": failed,
            "failure_reason": failure_reason,
            "distance_to_exit_x": distance_to_exit_x,
            "progress_x_pct": min(100.0, progress_x * 100.0),
            "distance_y_to_exit_band": distance_y_to_band,
            "exit_x_min": self._exit_x_min,
            "exit_y_min": self._exit_y_min,
            "exit_y_max": self._exit_y_max,
            # Zone thresholds for feedback (match runtime sandbox / curriculum)
            "oneway_x_threshold": ox,
            "lock_gate_x_min": lock_lo,
            "lock_gate_x_max": lock_hi,
            "activation_x_min": act_lo,
            "activation_x_max": act_hi,
            "consecutive_exit_steps_required": exit_hold_need,
        }

        done = success or failed
        return done, score, metrics

    def get_task_description(self):
        max_steps_meta = _environment_max_steps(self.environment)
        tc: dict = {}
        pc: dict = {}
        if self.environment is not None:
            tc = dict(getattr(self.environment, "terrain_config", None) or {})
            pc = dict(getattr(self.environment, "physics_config", None) or {})
            pc.pop("task_description", None)

        base_physics = c04_stages.get_source_base_physics_config()
        base_terrain = c04_stages.get_source_base_terrain_config()
        if self._task_description_override is not None:
            desc = self._task_description_override
        else:
            base_desc = c04_prompt.TASK_PROMPT["task_description"]
            desc = c04_stages.update_task_description_for_visible_changes(
                base_desc, tc, base_terrain, pc, base_physics
            )

        base_success = c04_prompt.TASK_PROMPT["success_criteria"]
        success_markdown = c04_stages.update_success_criteria_for_visible_changes(
            base_success, tc, base_terrain, pc, base_physics
        )

        hold_steps_meta = _exit_hold_steps_required(self.environment)
        return {
            "task": "C-04: The Escaper",
            "description": desc,
            "exit_x_min": self._exit_x_min,
            "exit_y_min": self._exit_y_min,
            "exit_y_max": self._exit_y_max,
            "time_limit_steps": max_steps_meta,
            "success_criteria": {
                "primary": (
                    f"Behavioral unlock, then hold in exit zone "
                    f"{hold_steps_meta} consecutive steps (exit hold counts only after unlock)"
                ),
                "failure": (
                    f"Timeout within {max_steps_meta:,} steps without success, or structural (impulse) failure"
                ),
                "detail_markdown": success_markdown.strip(),
            },
            "evaluation": {
                "score_range": "0-100",
                "success_score": 100,
                "failure_score": 0,
            },
        }
