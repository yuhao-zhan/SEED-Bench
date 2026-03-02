"""
C-06: The Governor task evaluation module
Success: maintain wheel speed near target without stall. Failure: stall or speed too unstable.
"""
import math
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))
from common.simulator import TIME_STEP

TARGET_SPEED_RAD_S = 3.0
STALL_SPEED_THRESHOLD = 0.3
STALL_STEPS_THRESHOLD = 60  # consecutive steps below threshold = stall
# Regulation: success also requires mean speed error below this (cogging + deadzone + delay make this harder)
MEAN_SPEED_ERROR_THRESHOLD = 0.23
# Only count speed error after this step (allow transient)
REGULATION_START_STEP = 1000


class Evaluator:
    """
    Evaluation for C-06: The Governor (hard).
    Failure if stall OR if mean speed error (over regulation phase) exceeds threshold.
    Success = run to max_steps without stall AND mean |omega - target| < MEAN_SPEED_ERROR_THRESHOLD.
    """

    def __init__(self, terrain_bounds, environment=None):
        self.terrain_bounds = terrain_bounds
        self.environment = environment
        self._target_speed = float(terrain_bounds.get("target_speed_rad_s", TARGET_SPEED_RAD_S))
        self._stall_threshold = float(terrain_bounds.get("stall_speed_threshold", STALL_SPEED_THRESHOLD))
        self._stall_steps_threshold = STALL_STEPS_THRESHOLD
        self._stall_count = 0
        self._speed_error_sum = 0.0
        self._speed_error_count = 0

    def evaluate(self, agent_body, step_count, max_steps):
        """
        Failure = stall (speed < threshold for STALL_STEPS_THRESHOLD steps)
                  OR (at end) mean speed error during regulation phase >= threshold.
        Returns: (done, score, metrics)
        """
        if not self.environment:
            return True, 0.0, {"error": "Environment not available"}

        # Use actual omega for evaluation (not delayed measurement seen by agent)
        omega = (
            self.environment.get_wheel_angular_velocity_actual()
            if hasattr(self.environment, "get_wheel_angular_velocity_actual")
            else self.environment.get_wheel_angular_velocity()
        )
        target = self.environment.get_target_speed()
        speed_error = abs(omega - target)

        if step_count >= REGULATION_START_STEP:
            self._speed_error_sum += speed_error
            self._speed_error_count += 1

        if abs(omega) < self._stall_threshold:
            self._stall_count += 1
        else:
            self._stall_count = 0

        failed = False
        failure_reason = None
        if self._stall_count >= self._stall_steps_threshold:
            failed = True
            failure_reason = (
                f"Stall: wheel speed {omega:.2f} rad/s below threshold "
                f"{self._stall_threshold:.1f} rad/s for {self._stall_count} consecutive steps"
            )

        mean_speed_error = (
            self._speed_error_sum / self._speed_error_count
            if self._speed_error_count > 0
            else 0.0
        )
        if (step_count >= max_steps - 1) and not failed and self._speed_error_count > 0:
            if mean_speed_error >= MEAN_SPEED_ERROR_THRESHOLD:
                failed = True
                failure_reason = (
                    f"Regulation too poor: mean speed error {mean_speed_error:.3f} rad/s "
                    f">= {MEAN_SPEED_ERROR_THRESHOLD} rad/s (wheel not kept near target)"
                )

        success = (step_count >= max_steps - 1) and not failed

        if success and not failed:
            score = 100.0
        elif failed:
            score = 0.0
        else:
            progress = step_count / max_steps if max_steps > 0 else 0.0
            score = progress * 80.0

        metrics = {
            "wheel_angular_velocity": omega,
            "target_speed": target,
            "speed_error": speed_error,
            "mean_speed_error": mean_speed_error,
            "stall_count": self._stall_count,
            "stall_speed_threshold": self._stall_threshold,
            "step_count": step_count,
            "success": success,
            "failed": failed,
            "failure_reason": failure_reason,
        }

        done = failed or (step_count >= max_steps - 1)
        return done, score, metrics

    def get_task_description(self):
        """Return task description dict for feedback. No spoilers for load or disturbance details."""
        return {
            "task": "C-06: The Governor",
            "description": "Maintain constant wheel speed under load (load may vary with speed and time)",
            "target_speed_rad_s": self._target_speed,
            "stall_speed_threshold": self._stall_threshold,
            "success_criteria": {
                "primary": f"Keep wheel speed near {self._target_speed} rad/s without stall; regulation quality (mean speed error) must meet threshold",
                "failure": "Stall (speed below threshold for too long) or regulation too poor (mean speed error above threshold)",
            },
            "evaluation": {
                "score_range": "0-100",
                "success_score": 100,
                "failure_score": 0,
            },
        }
