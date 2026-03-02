"""
C-05: The Logic Lock task evaluation module
Success: trigger switches A then B then C in order. Failure: wrong order (e.g. B before A).
"""
import math
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))
from common.simulator import TIME_STEP


class Evaluator:
    """
    Evaluation for C-05: The Logic Lock.
    Success if A, B, C triggered in that order. Failure if wrong order.
    """

    def __init__(self, terrain_bounds, environment=None):
        self.terrain_bounds = terrain_bounds
        self.environment = environment
        self._required_order = list(terrain_bounds.get("required_order", ["A", "B", "C"]))

    def evaluate(self, agent_body, step_count, max_steps):
        """
        Evaluate logic lock. Success = sequence A->B->C correct; failure = wrong order.
        Returns: (done, score, metrics)
        """
        if not self.environment:
            return True, 0.0, {"error": "Environment not available"}

        sequence_correct = self.environment.get_sequence_correct()
        wrong_order = self.environment.get_wrong_order()
        triggered = self.environment.get_triggered_switches()
        next_req = self.environment.get_next_required_switch()
        x, y = self.environment.get_agent_position()
        vx, vy = self.environment.get_agent_velocity()
        steps_in_current_zone = getattr(
            self.environment, "get_steps_in_current_zone", lambda: 0
        )()
        steps_required_to_trigger = getattr(
            self.environment, "get_steps_required_to_trigger", lambda: 1
        )()
        cooldown_remaining = getattr(
            self.environment, "get_cooldown_remaining", lambda: 0
        )()

        failed = False
        failure_reason = None
        if wrong_order:
            failed = True
            failure_reason = (
                "Wrong order: switches must be triggered in order A -> B -> C. "
                f"Triggered so far: {triggered}"
            )

        success = sequence_correct and not failed

        if success:
            score = 100.0
        elif failed:
            score = 0.0
        else:
            progress = len(triggered) / 3.0 * 80.0 if self._required_order else 0.0
            score = progress

        # Physical metrics for feedback: distance to next zone, speed, progress (B is elevated)
        zone_centers = {"A": (2.0, 2.0), "B": (4.95, 3.2), "C": (8.0, 2.0)}
        distance_to_next = None
        if next_req and next_req in zone_centers:
            tx, ty = zone_centers[next_req]
            distance_to_next = math.sqrt((tx - x) ** 2 + (ty - y) ** 2)
        speed = math.sqrt(vx * vx + vy * vy)
        progress_percent = (len(triggered) / 3.0 * 100.0) if self._required_order else 0.0

        metrics = {
            "agent_x": x,
            "agent_y": y,
            "agent_vx": vx,
            "agent_vy": vy,
            "triggered_switches": list(triggered),
            "next_required": next_req,
            "sequence_correct": sequence_correct,
            "wrong_order": wrong_order,
            "step_count": step_count,
            "success": success,
            "failed": failed,
            "failure_reason": failure_reason,
            "distance_to_next_zone": distance_to_next,
            "speed": speed,
            "progress_percent": progress_percent,
            "steps_in_current_zone": steps_in_current_zone,
            "steps_required_to_trigger": steps_required_to_trigger,
            "cooldown_remaining": cooldown_remaining,
        }

        # Include environment (stage) hidden parameter diagnostics when available
        if self.environment is not None:
            env = self.environment
            # safe access with getattr fallbacks
            metrics.update(
                {
                    "env_trigger_stay_steps": getattr(env, "_trigger_stay_steps", None),
                    "env_speed_cap_inside": getattr(env, "_speed_cap_inside", None),
                    "env_repulsion_mag": getattr(env, "_repulsion_mag", None),
                    "env_repulsion_range": getattr(env, "_repulsion_range", None),
                    "env_c_required_max_y": getattr(env, "_c_required_max_y", None),
                    "env_c_high_history": getattr(env, "_c_high_history", None),
                    "env_barrier_delay_steps": getattr(env, "_barrier_delay_steps", None),
                    "env_cooldown_steps": getattr(env, "_cooldown_steps", None),
                    "env_recent_a_for_b": getattr(env, "_recent_a_for_b", None),
                    "env_recent_b_for_c": getattr(env, "_recent_b_for_c", None),
                    "env_wind_amp": getattr(env, "_wind_amp", None),
                    "env_wind_period": getattr(env, "_wind_period", None),
                }
            )

            # Add a few convenience flags to help feedback formulation
            try:
                if metrics.get("env_recent_a_for_b") is not None:
                    metrics["env_flag_tight_a_to_b"] = metrics["env_recent_a_for_b"] < 80
                if metrics.get("env_barrier_delay_steps") is not None:
                    metrics["env_flag_long_barrier_delay"] = metrics["env_barrier_delay_steps"] > 100
                if metrics.get("env_repulsion_mag") is not None:
                    metrics["env_flag_strong_repulsion"] = metrics["env_repulsion_mag"] > 30.0
            except Exception:
                pass

        done = failed or sequence_correct
        return done, score, metrics

    def get_task_description(self):
        """Return task description dict for feedback."""
        return {
            "task": "C-05: The Logic Lock",
            "description": "Trigger switches A -> B -> C in order",
            "required_order": self._required_order,
            "success_criteria": {
                "primary": "Trigger A, then B, then C in that order",
                "failure": "Wrong order (e.g. B before A)",
            },
            "evaluation": {
                "score_range": "0-100",
                "success_score": 100,
                "failure_score": 0,
            },
        }
