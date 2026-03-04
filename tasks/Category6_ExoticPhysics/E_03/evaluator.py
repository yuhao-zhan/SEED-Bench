"""
E-03: Slippery World task evaluation module.
Success: sled enters target zone. Failure: cannot get traction (never reach target).
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))
from common.simulator import TIME_STEP


class Evaluator:
    """
    Evaluation for E-03: Slippery World.
    Success: sled center in target zone. Failure: timeout without reaching target.
    """

    def __init__(self, terrain_bounds, environment=None):
        self.terrain_bounds = terrain_bounds
        self.environment = environment
        tz = terrain_bounds.get("target_zone", {})
        self.target_x_min = float(tz.get("x_min", 28.0))
        self.target_x_max = float(tz.get("x_max", 32.0))
        self.target_y_min = float(tz.get("y_min", 2.2))
        self.target_y_max = float(tz.get("y_max", 2.8))
        self.sled_start_x = float(terrain_bounds.get("sled_start", {}).get("x", 8.0))
        self.sled_start_y = float(terrain_bounds.get("sled_start", {}).get("y", 2.0))
        self.reached_target = False
        if environment is None:
            raise ValueError("Evaluator requires environment instance")

    def evaluate(self, agent_body, step_count, max_steps):
        """
        Evaluate: success only if checkpoint was reached AND sled is in final target zone.
        Returns: (done, score, metrics)
        """
        if not self.environment:
            return True, 0.0, {"error": "Environment not available"}

        pos = self.environment.get_sled_position()
        if pos is None:
            return True, 0.0, {
                "success": False,
                "failed": True,
                "failure_reason": "Sled not found",
                "step_count": step_count,
            }
        x, y = pos
        checkpoint_a = self.environment.get_checkpoint_a_reached()
        checkpoint_b = self.environment.get_checkpoint_b_reached()
        checkpoint_reached = self.environment.get_checkpoint_reached()

        if (self.target_x_min <= x <= self.target_x_max and
                self.target_y_min <= y <= self.target_y_max):
            self.reached_target = True

        # Success requires both checkpoint and final zone (sequence constraint)
        success = checkpoint_reached and self.reached_target
        failed = step_count >= max_steps - 1 and not success

        if failed:
            if not checkpoint_a:
                failure_reason = "First checkpoint (A) not reached: sled did not pass through the required intermediate zone before time ran out (sequence constraint)"
            elif not checkpoint_b:
                failure_reason = "Second checkpoint (B) not reached: sled must pass through both intermediate zones in order before final target"
            else:
                failure_reason = "Sled did not reach the final target zone before time ran out"
        else:
            failure_reason = None

        if success:
            score = 100.0
        elif failed:
            score = 0.0
        else:
            start_x = self.sled_start_x
            max_dist = self.target_x_min - start_x
            dist_traveled = x - start_x
            progress = min(max(dist_traveled / max_dist, 0.0), 1.0) if max_dist > 0 else 0.0
            # Partial credit: checkpoint matters for sequence; progress for distance
            score = (40.0 if checkpoint_reached else 0.0) + progress * 50.0

        vel = self.environment.get_sled_velocity() or (0.0, 0.0)
        vx, vy = vel[0], vel[1]
        velocity_magnitude = (vx * vx + vy * vy) ** 0.5
        # Distance from sled center to target zone (to nearest point of rectangle)
        dx_lo = max(0, self.target_x_min - x)
        dx_hi = max(0, x - self.target_x_max)
        dy_lo = max(0, self.target_y_min - y)
        dy_hi = max(0, y - self.target_y_max)
        dist_x = dx_lo if x < self.target_x_min else (dx_hi if x > self.target_x_max else 0)
        dist_y = dy_lo if y < self.target_y_min else (dy_hi if y > self.target_y_max else 0)
        distance_to_target = (dist_x * dist_x + dist_y * dist_y) ** 0.5
        start_x = self.sled_start_x
        max_dist_x = self.target_x_min - start_x
        progress_pct = min(100.0, max(0.0, (x - start_x) / max_dist_x * 100.0)) if max_dist_x > 0 else 0.0
        metrics = {
            "step_count": step_count,
            "success": success,
            "failed": failed,
            "failure_reason": failure_reason,
            "checkpoint_reached": checkpoint_reached,
            "checkpoint_a_reached": checkpoint_a,
            "checkpoint_b_reached": checkpoint_b,
            "sled_x": x,
            "sled_y": y,
            "target_x_min": self.target_x_min,
            "target_x_max": self.target_x_max,
            "target_y_min": self.target_y_min,
            "target_y_max": self.target_y_max,
            "reached_target": self.reached_target,
            "velocity_x": vx,
            "velocity_y": vy,
            "velocity_magnitude": velocity_magnitude,
            "distance_to_target": distance_to_target,
            "progress_pct": progress_pct,
            "sled_start_x": self.sled_start_x,
        }
        return failed or (step_count >= max_steps - 1), score, metrics

    def get_task_description(self):
        return {
            "task": "E-03: Slippery World",
            "description": "Move sled to target zone using reaction-force thrust; must pass through a required intermediate zone first (sequence); path has region-specific effects discoverable via feedback",
            "terrain": self.terrain_bounds,
            "success_criteria": {
                "primary": "Sled must first pass through a checkpoint zone, then enter the final target zone (exact bounds in feedback; checkpoint_reached and target zone reported in metrics)",
            },
            "evaluation": {
                "score_range": "0-100",
                "success_score": 100,
                "failure_score": 0,
            },
        }
