"""
E-05: The Magnet task evaluation module.
Success: body enters target zone. Failure: stuck in local minimum (never reach target).
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))
from common.simulator import TIME_STEP


class Evaluator:
    """
    Evaluation for E-05: The Magnet.
    Success: body center in target zone. Failure: timeout without reaching (stuck in local minimum).
    """

    def __init__(self, terrain_bounds, environment=None):
        self.terrain_bounds = terrain_bounds
        self.environment = environment
        tz = terrain_bounds.get("target_zone", {})
        self.target_x_min = float(tz.get("x_min", 28.0))
        self.target_x_max = float(tz.get("x_max", 32.0))
        self.target_y_min = float(tz.get("y_min", 6.0))
        self.target_y_max = float(tz.get("y_max", 9.0))
        self.body_start_x = float(terrain_bounds.get("body_start", {}).get("x", 8.0))
        self.body_start_y = float(terrain_bounds.get("body_start", {}).get("y", 5.0))
        self.reached_target = False
        if environment is None:
            raise ValueError("Evaluator requires environment instance")

    def evaluate(self, agent_body, step_count, max_steps):
        """
        Evaluate: success if body in target zone; fail if done and not reached.
        Returns: (done, score, metrics)
        """
        if not self.environment:
            return True, 0.0, {"error": "Environment not available"}

        pos = self.environment.get_body_position()
        if pos is None:
            return True, 0.0, {
                "success": False,
                "failed": True,
                "failure_reason": "Body not found",
                "step_count": step_count,
            }
        x, y = pos

        if (self.target_x_min <= x <= self.target_x_max and
                self.target_y_min <= y <= self.target_y_max):
            self.reached_target = True
        success = self.reached_target

        # Pit zone: instant fail if not yet reached target (includes corridor floor)
        in_pit = (16 <= x <= 24) and y < 5.5
        if in_pit and not success:
            failed = True
            failure_reason = "Fell into pit zone; body entered forbidden region"
        else:
            failed = step_count >= max_steps - 1 and not success
            failure_reason = ("Stuck in local minimum: did not reach target zone before time ran out" if failed else None)
        if success:
            score = 100.0
        elif failed:
            score = 0.0
        else:
            start_x = self.body_start_x
            max_dist = self.target_x_min - start_x
            dist_traveled = x - start_x
            progress = min(max(dist_traveled / max_dist, 0.0), 1.0) if max_dist > 0 else 0.0
            score = progress * 80.0

        vel = self.environment.get_body_velocity() or (0.0, 0.0)
        vx, vy = vel[0], vel[1]
        speed = (vx * vx + vy * vy) ** 0.5

        # Distance metrics for feedback
        start_x = self.body_start_x
        start_y = self.body_start_y
        # Distance to nearest point in target zone (0 if inside)
        closest_x = max(self.target_x_min, min(x, self.target_x_max))
        closest_y = max(self.target_y_min, min(y, self.target_y_max))
        dist_to_target = ((x - closest_x) ** 2 + (y - closest_y) ** 2) ** 0.5
        # Progress: fraction of horizontal distance traveled toward target (0 to 1)
        total_dist_x = self.target_x_min - start_x
        progress_x = (x - start_x) / total_dist_x if total_dist_x > 0 else 0.0
        progress_x = max(0.0, min(1.0, progress_x))
        in_target_x = self.target_x_min <= x <= self.target_x_max
        in_target_y = self.target_y_min <= y <= self.target_y_max

        metrics = {
            "step_count": step_count,
            "success": success,
            "failed": failed,
            "failure_reason": failure_reason,
            "body_x": x,
            "body_y": y,
            "target_x_min": self.target_x_min,
            "target_x_max": self.target_x_max,
            "target_y_min": self.target_y_min,
            "target_y_max": self.target_y_max,
            "reached_target": self.reached_target,
            "velocity_x": vx,
            "velocity_y": vy,
            "speed": speed,
            "progress_x": progress_x,
            "dist_to_target": dist_to_target,
            "in_target_x": in_target_x,
            "in_target_y": in_target_y,
            "start_x": start_x,
            "start_y": start_y,
        }
        done = failed or (step_count >= max_steps - 1)
        return done, score, metrics

    def get_task_description(self):
        return {
            "task": "E-05: The Magnet",
            "description": "Navigate body to target zone despite invisible repulsive/attractive force fields (avoid local minimum)",
            "terrain": self.terrain_bounds,
            "success_criteria": {
                "primary": f"Body center enters target zone (x in [{self.target_x_min:.1f}, {self.target_x_max:.1f}], y in [{self.target_y_min:.1f}, {self.target_y_max:.1f}])",
            },
            "evaluation": {
                "score_range": "0-100",
                "success_score": 100,
                "failure_score": 0,
            },
        }
