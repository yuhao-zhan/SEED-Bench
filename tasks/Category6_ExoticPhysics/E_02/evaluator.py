"""
E-02: Thick Air task evaluation module.
Success: craft enters target zone without overheating. Failure: cannot move or overheat.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))
from common.simulator import TIME_STEP


class Evaluator:
    """
    Evaluation for E-02: Thick Air.
    Success: craft center in target zone. Failure: overheat or timeout without reaching target.
    """

    def __init__(self, terrain_bounds, environment=None):
        self.terrain_bounds = terrain_bounds
        self.environment = environment
        tz = terrain_bounds.get("target_zone", {})
        self.target_x_min = float(tz.get("x_min", 28.0))
        self.target_x_max = float(tz.get("x_max", 32.0))
        self.target_y_min = float(tz.get("y_min", 2.0))
        self.target_y_max = float(tz.get("y_max", 5.0))
        self.reached_target = False
        if environment is None:
            raise ValueError("Evaluator requires environment instance")
        self.OVERHEAT_LIMIT = (
            environment.get_overheat_limit()
            if hasattr(environment, "get_overheat_limit") and callable(getattr(environment, "get_overheat_limit"))
            else getattr(type(environment), "OVERHEAT_LIMIT", 72000.0)
        )

    def evaluate(self, agent_body, step_count, max_steps):
        """
        Evaluate: success if craft in target zone; fail if overheated or (done and not reached).
        Returns: (done, score, metrics)
        """
        if not self.environment:
            return True, 0.0, {"error": "Environment not available"}

        pos = self.environment.get_craft_position()
        if pos is None:
            return True, 0.0, {
                "success": False,
                "failed": True,
                "failure_reason": "Craft not found",
                "step_count": step_count,
            }
        x, y = pos
        heat = self.environment.get_heat()
        overheated = self.environment.is_overheated()

        if (self.target_x_min <= x <= self.target_x_max and
                self.target_y_min <= y <= self.target_y_max):
            self.reached_target = True

        failed = overheated or (step_count >= max_steps - 1 and not self.reached_target)
        success = self.reached_target and not overheated

        if overheated:
            failure_reason = f"Overheat: cumulative thrust usage exceeded {self.OVERHEAT_LIMIT:.0f} N·s"
        elif step_count >= max_steps - 1 and not self.reached_target:
            failure_reason = "Cannot move: craft did not reach the target zone before time ran out"
        else:
            failure_reason = None

        if success:
            score = 100.0
        elif failed:
            score = 0.0
        else:
            # Partial: progress toward target (x distance)
            start_x = type(self.environment).CRAFT_START_X
            max_dist = self.target_x_min - start_x
            dist_traveled = x - start_x
            progress = min(max(dist_traveled / max_dist, 0.0), 1.0) if max_dist > 0 else 0.0
            score = progress * 80.0

        vel = self.environment.get_craft_velocity() or (0.0, 0.0)
        vx, vy = vel[0], vel[1]
        speed = (vx * vx + vy * vy) ** 0.5
        start_x = type(self.environment).CRAFT_START_X
        dist_traveled_x = x - start_x
        max_dist_x = self.target_x_min - start_x
        progress_x = (dist_traveled_x / max_dist_x * 100.0) if max_dist_x > 0 else 0.0
        # Distance from craft to target zone center (30, 3.5)
        dx_center = 30.0 - x
        dy_center = 3.5 - y
        distance_to_target = (dx_center * dx_center + dy_center * dy_center) ** 0.5
        heat_remaining = max(0.0, self.OVERHEAT_LIMIT - heat)
        metrics = {
            "step_count": step_count,
            "success": success,
            "failed": failed,
            "failure_reason": failure_reason,
            "craft_x": x,
            "craft_y": y,
            "target_x_min": self.target_x_min,
            "target_x_max": self.target_x_max,
            "target_y_min": self.target_y_min,
            "target_y_max": self.target_y_max,
            "reached_target": self.reached_target,
            "heat": heat,
            "overheated": overheated,
            "overheat_limit": self.OVERHEAT_LIMIT,
            "heat_remaining": heat_remaining,
            "velocity_x": vx,
            "velocity_y": vy,
            "speed": speed,
            "progress_x": progress_x,
            "distance_to_target": distance_to_target,
            "dist_traveled_x": dist_traveled_x,
        }
        return failed or (step_count >= max_steps - 1), score, metrics

    def get_task_description(self):
        return {
            "task": "E-02: Thick Air",
            "description": "Move craft to target zone in high-drag environment without overheating",
            "terrain": self.terrain_bounds,
            "success_criteria": {
                "primary": "Craft center enters target zone (x in [28, 32], y in [2, 5])",
                "secondary": f"Heat stays below {self.OVERHEAT_LIMIT:.0f} N·s",
            },
            "evaluation": {
                "score_range": "0-100",
                "success_score": 100,
                "failure_score": 0,
            },
        }
