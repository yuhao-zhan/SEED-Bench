"""
C-06: The Governor task evaluation module
Success: maintain wheel speed near target without stall. Failure: stall or speed too unstable.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from environment import (
    MEAN_SPEED_ERROR_THRESHOLD,
    REGULATION_START_STEP,
    STALL_SPEED_THRESHOLD,
    STALL_STEPS_THRESHOLD,
    TARGET_SPEED_RAD_S,
)


def _stall_steps_from_bounds(terrain_bounds):
    return int(terrain_bounds.get("stall_steps_threshold", STALL_STEPS_THRESHOLD))


class Evaluator:
    """
    Evaluation for C-06: The Governor (hard).
    Failure if stall OR if mean speed error (over regulation phase) exceeds threshold.
    Success = run to max_steps without stall AND mean |omega - target| <= mean threshold (inclusive).
    """

    def __init__(self, terrain_bounds, environment=None):
        self.terrain_bounds = terrain_bounds
        self.environment = environment
        self._target_speed_time_varying = bool(terrain_bounds.get("target_speed_time_varying", False))
        self._regulation_start = int(terrain_bounds.get("regulation_start_step", REGULATION_START_STEP))
        self._stall_threshold = float(terrain_bounds.get("stall_speed_threshold", STALL_SPEED_THRESHOLD))
        self._stall_steps_threshold = _stall_steps_from_bounds(terrain_bounds)
        self._mean_speed_error_threshold = float(terrain_bounds.get("mean_speed_error_threshold", MEAN_SPEED_ERROR_THRESHOLD))
        self._stall_count = 0
        self._speed_error_sum = 0.0
        self._speed_error_count = 0

    def evaluate(self, agent_body, step_count, max_steps):
        """
        Failure = stall (speed < threshold for STALL_STEPS_THRESHOLD steps)
                  OR (at end) mean speed error during regulation phase strictly exceeds threshold.
        Returns: (done, score, metrics)
        """
        if not self.environment:
            return True, 0.0, {"error": "Environment not available"}

        # Regulation and stall must use true ω only (never delayed readout used for control).
        omega = self.environment.get_wheel_angular_velocity_actual()
        target = self.environment.get_target_speed()
        speed_error = abs(omega - target)

        if step_count >= self._regulation_start:
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
        if (step_count >= max_steps - 1) and not failed:
            if max_steps <= self._regulation_start:
                failed = True
                failure_reason = (
                    f"Episode length {max_steps} steps does not exceed regulation start "
                    f"({self._regulation_start}); regulation phase was never scored."
                )
            elif self._speed_error_count == 0:
                failed = True
                failure_reason = (
                    "No regulation-phase samples recorded (internal evaluation error or "
                    "step indexing mismatch)."
                )
            elif mean_speed_error > self._mean_speed_error_threshold:
                failed = True
                failure_reason = (
                    f"Regulation too poor: mean speed error {mean_speed_error:.3f} rad/s "
                    f"exceeds {self._mean_speed_error_threshold} rad/s (must be <= threshold)"
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
        initial_target = float(self.terrain_bounds.get("target_speed_rad_s", TARGET_SPEED_RAD_S))
        target_note = (
            "time-varying setpoint from get_target_speed() each step"
            if self._target_speed_time_varying
            else f"near {initial_target} rad/s"
        )
        return {
            "task": "C-06: The Governor",
            "description": "Maintain wheel speed at the commanded target under load (load may vary with speed and time).",
            "target_speed_rad_s": initial_target,
            "target_speed_time_varying": self._target_speed_time_varying,
            "stall_speed_threshold": self._stall_threshold,
            "stall_steps_threshold": self._stall_steps_threshold,
            "mean_speed_error_threshold_rad_s": self._mean_speed_error_threshold,
            "regulation_start_step": self._regulation_start,
            "success_criteria": {
                "primary": (
                    f"Track the {target_note} without stall; mean |ω_true − target| over steps "
                    f">= {self._regulation_start} must be <= {self._mean_speed_error_threshold} rad/s "
                    f"(true instantaneous wheel speed, per task prompt)"
                ),
                "failure": (
                    f"Stall (ω < {self._stall_threshold} for >= {self._stall_steps_threshold} consecutive steps) "
                    f"or mean speed error strictly greater than {self._mean_speed_error_threshold} rad/s"
                ),
            },
            "evaluation": {
                "score_range": "0-100",
                "success_score": 100,
                "failure_score": 0,
            },
        }
