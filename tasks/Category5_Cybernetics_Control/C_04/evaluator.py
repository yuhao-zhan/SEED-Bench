"""
C-04: The Escaper task evaluation module
Success: hold in exit zone for 60 consecutive steps. Failure: timeout without doing so.
"""
import math
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))
from common.simulator import TIME_STEP

CONSECUTIVE_EXIT_STEPS_REQUIRED = 60


class Evaluator:
    """
    C-04: Success = agent has been in exit zone for 60 consecutive steps (reach + hold).
    Failure = timeout without achieving that.
    """

    def __init__(self, terrain_bounds, environment=None):
        self.terrain_bounds = terrain_bounds
        self.environment = environment
        self._exit_x_min = float(terrain_bounds.get("exit_x_min", 18.0))
        self._exit_y_min = float(terrain_bounds.get("exit_y_min", 1.25))
        self._exit_y_max = float(terrain_bounds.get("exit_y_max", 1.45))
        self._consecutive_in_exit = 0

    def evaluate(self, agent_body, step_count, max_steps):
        """
        Success = 60 consecutive steps in exit zone (reach and hold). Failure = timeout.
        Returns: (done, score, metrics)
        """
        if not self.environment:
            return True, 0.0, {"error": "Environment not available"}

        reached_exit = self.environment.has_reached_exit()
        if reached_exit:
            self._consecutive_in_exit += 1
        else:
            self._consecutive_in_exit = 0

        x, y = self.environment.get_agent_position()
        vx, vy = self.environment.get_agent_velocity()
        whisker = self.environment.get_whisker_readings()

        success = self._consecutive_in_exit >= CONSECUTIVE_EXIT_STEPS_REQUIRED
        failed = False
        failure_reason = None
        if step_count >= max_steps - 1 and not success:
            failed = True
            failure_reason = (
                f"Timeout: did not hold in exit zone (x >= {self._exit_x_min}, "
                f"y in [{self._exit_y_min}, {self._exit_y_max}]) for {CONSECUTIVE_EXIT_STEPS_REQUIRED} consecutive steps"
            )

        if success:
            score = 100.0
        elif failed:
            score = 0.0
        else:
            progress = step_count / max_steps if max_steps > 0 else 0.0
            score = progress * 80.0

        # Progress: fraction of x to exit (0 to 1+); distance to exit zone
        distance_to_exit_x = max(0.0, self._exit_x_min - x)
        progress_x = (x / self._exit_x_min) if self._exit_x_min > 0 else 0.0
        # Vertical: how far y is from exit band [exit_y_min, exit_y_max]
        if y < self._exit_y_min:
            distance_y_to_band = self._exit_y_min - y
        elif y > self._exit_y_max:
            distance_y_to_band = y - self._exit_y_max
        else:
            distance_y_to_band = 0.0

        metrics = {
            "agent_x": x,
            "agent_y": y,
            "agent_vx": vx,
            "agent_vy": vy,
            "whisker_front": whisker[0] if len(whisker) > 0 else 0.0,
            "whisker_left": whisker[1] if len(whisker) > 1 else 0.0,
            "whisker_right": whisker[2] if len(whisker) > 2 else 0.0,
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
        }

        done = success or failed
        return done, score, metrics

    def get_task_description(self):
        """Return task description dict for feedback."""
        return {
            "task": "C-04: The Escaper",
            "description": "Escape the maze using whisker sensors",
            "exit_x_min": self._exit_x_min,
            "exit_y_min": self._exit_y_min,
            "exit_y_max": self._exit_y_max,
            "success_criteria": {
                "primary": f"Hold in exit zone (x >= {self._exit_x_min}, y in [{self._exit_y_min}, {self._exit_y_max}]) for 60 consecutive steps",
                "failure": "Timeout without holding in exit for 60 consecutive steps",
            },
            "evaluation": {
                "score_range": "0-100",
                "success_score": 100,
                "failure_score": 0,
            },
        }
