"""
D-01: The Launcher task evaluation module
Defines success (projectile hits target zone) and failure (miss, insufficient distance).
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))
from common.simulator import TIME_STEP


def _segment_intersects_rect(x0, y0, x1, y1, rx_min, ry_min, rx_max, ry_max):
    """True if segment (x0,y0)-(x1,y1) intersects axis-aligned rectangle [rx_min,rx_max] x [ry_min,ry_max]."""
    # Either endpoint inside
    if rx_min <= x0 <= rx_max and ry_min <= y0 <= ry_max:
        return True
    if rx_min <= x1 <= rx_max and ry_min <= y1 <= ry_max:
        return True
    # Segment parametrization: (x0 + t*(x1-x0), y0 + t*(y1-y0)), t in [0,1]
    dx, dy = x1 - x0, y1 - y0
    for edge in ("left", "right", "bottom", "top"):
        if edge == "left" and dx != 0:
            t = (rx_min - x0) / dx
            if 0 <= t <= 1 and ry_min <= y0 + t * dy <= ry_max:
                return True
        if edge == "right" and dx != 0:
            t = (rx_max - x0) / dx
            if 0 <= t <= 1 and ry_min <= y0 + t * dy <= ry_max:
                return True
        if edge == "bottom" and dy != 0:
            t = (ry_min - y0) / dy
            if 0 <= t <= 1 and rx_min <= x0 + t * dx <= rx_max:
                return True
        if edge == "top" and dy != 0:
            t = (ry_max - y0) / dy
            if 0 <= t <= 1 and rx_min <= x0 + t * dx <= rx_max:
                return True
    return False


class Evaluator:
    """
    Evaluation for D-01: The Launcher.
    Success: projectile center enters target zone (x in [target_x_min, target_x_max],
    y in [target_y_min, target_y_max]). Failure: miss or insufficient distance.
    """

    def __init__(self, terrain_bounds, environment=None):
        self.terrain_bounds = terrain_bounds
        self.environment = environment
        tz = terrain_bounds.get("target_zone", {})
        self.target_x_min = tz.get("x_min", 40.0)
        self.target_x_max = tz.get("x_max", 45.0)
        self.target_y_min = tz.get("y_min", 2.0)
        self.target_y_max = tz.get("y_max", 5.0)
        # Strict: success only when projectile center is inside the red zone [40,45] x [2,5] (no tolerance).
        self._eff_y_min = self.target_y_min
        self._eff_y_max = self.target_y_max

        self._hit_occurred = False  # True once projectile has entered target zone
        self._design_constraints_checked = False
        self._last_pos = None  # For trajectory segment hit detection
        self._max_y_in_target_x = None  # Max y when x in [target_x_min, target_x_max]

        if environment is None:
            raise ValueError("Evaluator requires environment instance")
        self.MAX_STRUCTURE_MASS = getattr(
            type(environment), "MAX_STRUCTURE_MASS", 500.0
        )
        self.BUILD_ZONE_X_MIN = environment.BUILD_ZONE_X_MIN
        self.BUILD_ZONE_X_MAX = environment.BUILD_ZONE_X_MAX
        self.BUILD_ZONE_Y_MIN = environment.BUILD_ZONE_Y_MIN
        self.BUILD_ZONE_Y_MAX = environment.BUILD_ZONE_Y_MAX

    def evaluate(self, agent_body, step_count, max_steps):
        """
        Evaluate launcher outcome.
        Returns: (done, score, metrics)
        done: True when we can stop (success or clear failure or max_steps).
        """
        if self.environment is None:
            return True, 0.0, {"error": "Environment not available"}

        pos = self.environment.get_projectile_position()
        vel = self.environment.get_projectile_velocity()
        if pos is None:
            return True, 0.0, {"error": "Projectile not found"}

        px, py = pos
        vx = vel[0] if vel else 0.0
        vy = vel[1] if vel else 0.0

        # Check if projectile is inside target zone (point-in-box)
        in_zone = (
            self.target_x_min <= px <= self.target_x_max
            and self._eff_y_min <= py <= self._eff_y_max
        )
        if in_zone:
            self._hit_occurred = True
        if self.target_x_min <= px <= self.target_x_max:
            if self._max_y_in_target_x is None or py > self._max_y_in_target_x:
                self._max_y_in_target_x = py
        # Also check if trajectory segment (last_pos -> current) crossed the zone (avoids missing due to discrete steps)
        if not self._hit_occurred and self._last_pos is not None:
            x0, y0 = self._last_pos
            if _segment_intersects_rect(x0, y0, px, py,
                    self.target_x_min, self._eff_y_min, self.target_x_max, self._eff_y_max):
                self._hit_occurred = True
        self._last_pos = (px, py)

        # Design constraints (only at step 0)
        if not self._design_constraints_checked and step_count == 0:
            violations = self._check_design_constraints()
            if violations:
                self._design_constraints_checked = True
                metrics = self._make_metrics(
                    pos, vel, step_count, success=False, failed=True,
                    failure_reason="Design constraint violated: " + "; ".join(violations),
                )
                return True, 0.0, metrics
            self._design_constraints_checked = True

        success = self._hit_occurred
        failed = False
        failure_reason = None

        # Out of bounds: only fail if we have not already hit the target zone
        if not self._hit_occurred and (py < -5.0 or px < -10.0 or px > 60.0):
            failed = True
            failure_reason = "Projectile left simulation bounds"

        # Decide when we are "done" and assign final success/failure
        done = False
        if failed:
            done = True
            score = 0.0
        elif success:
            done = True
            score = 100.0
        elif step_count >= max_steps - 1:
            done = True
            if self._hit_occurred:
                score = 100.0
                success = True
            else:
                # Final verdict: miss or insufficient distance
                if px < self.target_x_min:
                    failed = True
                    failure_reason = "Insufficient distance: projectile did not reach target zone"
                else:
                    failed = True
                    failure_reason = "Miss: projectile did not land inside target zone (wrong y or overshoot)"
                score = 0.0
        else:
            score = 0.0 if failed else (100.0 if self._hit_occurred else 0.0)

        metrics = self._make_metrics(
            pos, vel, step_count, success=success, failed=failed,
            failure_reason=failure_reason,
        )
        return done, score, metrics

    def _check_design_constraints(self):
        """Return list of design constraint violation messages."""
        violations = []
        if self.environment is None:
            return ["Environment not available"]
        mass = self.environment.get_structure_mass()
        if mass > self.MAX_STRUCTURE_MASS:
            violations.append(
                f"Structure mass {mass:.2f} kg exceeds maximum {self.MAX_STRUCTURE_MASS} kg"
            )
        for body in self.environment._bodies:
            x, y = body.position.x, body.position.y
            if not (
                self.BUILD_ZONE_X_MIN <= x <= self.BUILD_ZONE_X_MAX
                and self.BUILD_ZONE_Y_MIN <= y <= self.BUILD_ZONE_Y_MAX
            ):
                violations.append(
                    f"Beam at ({x:.2f}, {y:.2f}) is outside build zone "
                    f"x=[{self.BUILD_ZONE_X_MIN}, {self.BUILD_ZONE_X_MAX}], "
                    f"y=[{self.BUILD_ZONE_Y_MIN}, {self.BUILD_ZONE_Y_MAX}]"
                )
        return violations

    def _make_metrics(
        self, pos, vel, step_count, success=False, failed=False, failure_reason=None
    ):
        px, py = pos if pos else (0, 0)
        vx, vy = (vel[0], vel[1]) if vel else (0, 0)
        speed = (vx * vx + vy * vy) ** 0.5
        # Progress: how far toward target (x) the projectile has gone
        progress = max(
            0.0,
            (px - 10.0) / (self.target_x_min - 10.0),
        ) if (self.target_x_min - 10.0) > 0 else 0.0
        progress = min(1.0, progress) * 100.0

        return {
            "projectile_x": px,
            "projectile_y": py,
            "projectile_vx": vx,
            "projectile_vy": vy,
            "projectile_speed": speed,
            "target_x_min": self.target_x_min,
            "target_x_max": self.target_x_max,
            "target_y_min": self.target_y_min,
            "target_y_max": self.target_y_max,
            "progress": progress,
            "success": success,
            "failed": failed,
            "failure_reason": failure_reason,
            "step_count": step_count,
            "structure_mass": self.environment.get_structure_mass(),
            "max_structure_mass": self.MAX_STRUCTURE_MASS,
            "hit_occurred": self._hit_occurred,
            "max_y_in_target_x": self._max_y_in_target_x,
        }

    def get_task_description(self):
        """Return task description for logging/UI."""
        return {
            "task": "D-01: The Launcher",
            "description": "Design a launcher to propel a projectile into a distant target zone",
            "target_zone": {
                "x": [self.target_x_min, self.target_x_max],
                "y": [self.target_y_min, self.target_y_max],
            },
            "success_criteria": {
                "primary": f"Projectile center enters target zone (x in [{self.target_x_min}, {self.target_x_max}] m, y in [{self.target_y_min}, {self.target_y_max}] m)",
                "failure_miss": "Projectile does not land inside target zone",
                "failure_insufficient_distance": "Projectile does not reach target x range",
            },
            "evaluation": {
                "score_range": "0-100",
                "success_score": 100,
                "failure_score": 0,
            },
        }
