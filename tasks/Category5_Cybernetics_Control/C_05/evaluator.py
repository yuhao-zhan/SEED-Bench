"""
C-05: Logic Lock — temporal chain, timed barrier, dwell + speed/force caps, C high-path rule.
Success: A then B then C in order. Failure: wrong order, or episode step budget exhausted.
"""
import math

# Partial credit: one milestone per required switch, scaled to 0–80 before success/timeout.
_PARTIAL_SCORE_MAX = 80.0
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from tasks.Category5_Cybernetics_Control.C_05.environment import (
    BARRIER_DELAY_STEPS as _SOURCE_BARRIER_DELAY_STEPS,
    FORCE_LIMIT_INSIDE as _SOURCE_FORCE_LIMIT_INSIDE,
    RECENT_A_FOR_B as _SOURCE_RECENT_A_FOR_B,
    REPULSION_STRONG_THRESHOLD as _SOURCE_REPULSION_STRONG_THRESHOLD,
)


def _distance_point_to_switch_zone(x: float, y: float, cx: float, cy: float, hw: float, hh: float) -> float:
    """Shortest distance from (x,y) to the axis-aligned switch zone rectangle (same predicate as the environment)."""
    closest_x = min(max(x, cx - hw), cx + hw)
    closest_y = min(max(y, cy - hh), cy + hh)
    return math.hypot(x - closest_x, y - closest_y)


def _agent_center_in_zone(x: float, y: float, cx: float, cy: float, hw: float, hh: float) -> bool:
    """True iff agent center (x,y) lies inside the switch zone AABB (same test as environment._point_in_zone)."""
    return (cx - hw <= x <= cx + hw) and (cy - hh <= y <= cy + hh)


class Evaluator:
    """
    C-05: sequence A→B→C with dwell steps per zone, speed/force limits in zones,
    cooldown between triggers, barrier opening after A with delay, A→B and B→C
    recency windows, and C requiring recent max y above a threshold.
    """

    def __init__(self, terrain_bounds, environment=None):
        self.terrain_bounds = terrain_bounds
        self.environment = environment
        self._required_order = list(terrain_bounds.get("required_order", ["A", "B", "C"]))

    def evaluate(self, agent_body, step_count, max_steps):
        """
        Success = A→B→C complete. Failure = wrong order, or step_count >= max_steps without success.
        Returns: (done, score, metrics). Partial score only before failure/timeout.
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
        timed_out = False
        if wrong_order:
            failed = True
            failure_reason = (
                "Wrong order: switches must be triggered in order A -> B -> C. "
                f"Triggered so far: {triggered}"
            )
        elif max_steps > 0 and step_count >= max_steps and not sequence_correct:
            failed = True
            timed_out = True
            failure_reason = (
                f"Timeout: sequence A→B→C not completed within {max_steps} simulation steps "
                f"(triggered so far: {triggered})."
            )

        success = sequence_correct and not failed

        n_milestones = max(1, len(self._required_order))
        milestone_weight = _PARTIAL_SCORE_MAX / float(n_milestones)

        if success:
            score = 100.0
        elif failed:
            score = 0.0
        else:
            score = (
                len(triggered) * milestone_weight
                if self._required_order
                else 0.0
            )

        # Physical metrics for feedback: distance to next switch rectangle (not just its center), speed, progress
        zones = self.terrain_bounds.get("zones", {})
        tb_fn = getattr(self.environment, "get_terrain_bounds", None)
        if callable(tb_fn):
            live_tb = tb_fn()
            if isinstance(live_tb, dict) and live_tb.get("zones"):
                zones = live_tb["zones"]
        distance_to_next = None
        inside_next_required_zone = False
        if next_req and next_req in zones:
            cx, cy, hw, hh = zones[next_req]
            distance_to_next = _distance_point_to_switch_zone(x, y, cx, cy, hw, hh)
            inside_next_required_zone = _agent_center_in_zone(x, y, cx, cy, hw, hh)
        speed = math.sqrt(vx * vx + vy * vy)
        progress_percent = (
            (len(triggered) / float(n_milestones) * 100.0) if self._required_order else 0.0
        )

        metrics = {
            "max_steps": max_steps,
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
            "inside_next_required_zone": inside_next_required_zone,
            "speed": speed,
            "progress_percent": progress_percent,
            "steps_in_current_zone": steps_in_current_zone,
            "steps_required_to_trigger": steps_required_to_trigger,
            "cooldown_remaining": cooldown_remaining,
            "timed_out": timed_out,
        }

        # Agent-facing: live zone speed cap (numeric) for feedback; curriculum booleans for other axes.
        if self.environment is not None:
            env = self.environment
            metrics["env_speed_cap_inside"] = getattr(env, "_speed_cap_inside", None)

            rab = getattr(env, "_recent_a_for_b", None)
            if rab is not None:
                metrics["env_flag_tight_a_to_b"] = rab < _SOURCE_RECENT_A_FOR_B
                metrics["env_flag_loose_a_to_b_recency"] = rab > _SOURCE_RECENT_A_FOR_B
            else:
                metrics["env_flag_tight_a_to_b"] = False
                metrics["env_flag_loose_a_to_b_recency"] = False

            bdelay = getattr(env, "_barrier_delay_steps", None)
            if bdelay is not None:
                metrics["env_flag_long_barrier_delay"] = (
                    bdelay > _SOURCE_BARRIER_DELAY_STEPS
                )

            rm = getattr(env, "_repulsion_mag", None)
            if rm is not None:
                metrics["env_flag_strong_repulsion"] = (
                    rm >= _SOURCE_REPULSION_STRONG_THRESHOLD
                )

            fl = getattr(env, "_force_limit_inside", None)
            if fl is not None:
                metrics["env_flag_sensitive_trigger"] = fl < _SOURCE_FORCE_LIMIT_INSIDE

        done = failed or sequence_correct
        return done, score, metrics

    def get_task_description(self):
        """High-level tooling summary only.

        Per-step metrics may include the live zone speed cap and boolean curriculum flags;
        canonical prose is ``prompt.py`` TASK_PROMPT plus ``stages.py`` updates.
        """
        desc = (
            "Trigger switches A, then B, then C in order. Rules for dwell time, speed/force limits "
            "inside zones, cooldowns, barrier timing after A, temporal windows (A→B, B→C), C altitude "
            "over a sliding history window, repulsion near B/C until prior triggers, and fatal "
            "wrong-order entry are defined in the task prompt (including any stage-specific updates)."
        )
        primary = (
            "Complete A→B→C in order within the episode step budget; respect all constraints "
            "stated in the task prompt and success criteria."
        )
        return {
            "task": "C-05: The Logic Lock",
            "description": desc,
            "required_order": self._required_order,
            "success_criteria": {
                "primary": primary,
                "failure": (
                    "Wrong order (e.g. B before A) — irreversible; or time limit exceeded "
                    "without completing A→B→C."
                ),
            },
            "evaluation": {
                "score_range": "0-100",
                "success_score": 100,
                "failure_score": 0,
            },
        }
