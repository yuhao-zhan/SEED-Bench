"""
D-04: The Swing task evaluation module
Success: (1) Apex in zone — seat is in target zone with speed ≈ 0 (at highest point), OR
         (2) Vertical fall into zone — after an apex (speed ≈ 0), seat is in zone falling vertically (vy < 0, |vx| small).
Failure: did not satisfy either condition.
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

# Success: apex (v ≈ 0) in zone, or vertical fall into zone after apex
APEX_SPEED_THRESHOLD = 1.0       # m/s: consider "at rest" at apex (discrete steps may miss exact v=0)
VERTICAL_FALL_VX_THRESHOLD = 1.35  # m/s: max |vx| for "vertical fall" into zone


class Evaluator:
    def __init__(self, terrain_bounds, environment=None):
        self.terrain_bounds = terrain_bounds
        self.environment = environment
        self._target_y_min = terrain_bounds.get("target_y_min", 11.7)
        self._target_x_min = terrain_bounds.get("target_x_min", 9.35)
        self._target_x_max = terrain_bounds.get("target_x_max", 10.65)
        self._touched_target = False
        self._design_constraints_checked = False
        self._max_seat_y_reached = 0.0
        self._apex_reached = False  # True once we've seen speed < APEX_SPEED_THRESHOLD
        if environment is None:
            raise ValueError("Evaluator requires environment instance")
        self.MAX_STRUCTURE_MASS = getattr(environment, "MAX_STRUCTURE_MASS", 100.0)
        self.BUILD_ZONE_X_MIN = environment.BUILD_ZONE_X_MIN
        self.BUILD_ZONE_X_MAX = environment.BUILD_ZONE_X_MAX
        self.BUILD_ZONE_Y_MIN = environment.BUILD_ZONE_Y_MIN
        self.BUILD_ZONE_Y_MAX = environment.BUILD_ZONE_Y_MAX

    def evaluate(self, agent_body, step_count, max_steps):
        if self.environment is None:
            return True, 0.0, {"error": "Environment not available"}
        pos = self.environment.get_swing_seat_position()
        vel = self.environment.get_swing_seat_velocity()
        if pos is None:
            return True, 0.0, {"error": "Swing seat not found"}
        px, py = pos
        vx = vel[0] if vel else 0.0
        vy = vel[1] if vel else 0.0
        speed = (vx * vx + vy * vy) ** 0.5
        if py > self._max_seat_y_reached:
            self._max_seat_y_reached = py
        if speed < APEX_SPEED_THRESHOLD:
            self._apex_reached = True
        in_zone = py >= self._target_y_min and self._target_x_min <= px <= self._target_x_max
        # Success (1): apex in zone — in zone and at rest (apex)
        if in_zone and speed < APEX_SPEED_THRESHOLD:
            self._touched_target = True
        # Success (2): after apex, vertical fall into zone — in zone, falling (vy <= 0), nearly vertical (|vx| small)
        if self._apex_reached and in_zone and vy <= 0 and abs(vx) < VERTICAL_FALL_VX_THRESHOLD:
            self._touched_target = True
        if not self._design_constraints_checked and step_count == 0:
            violations = self._check_design_constraints()
            if violations:
                self._design_constraints_checked = True
                metrics = self._make_metrics(pos, vel, step_count, False, True,
                    "Design constraint violated: " + "; ".join(violations))
                return True, 0.0, metrics
            self._design_constraints_checked = True
        success = self._touched_target
        failed = False
        failure_reason = None
        if step_count >= max_steps - 1 and not self._touched_target:
            failed = True
            failure_reason = (
                f"Did not succeed: seat must (1) be at rest (speed < {APEX_SPEED_THRESHOLD} m/s) at apex inside "
                f"target zone (y >= {self._target_y_min} m, x in [{self._target_x_min}, {self._target_x_max}] m), "
                f"or (2) fall vertically (|vx| < {VERTICAL_FALL_VX_THRESHOLD} m/s, vy < 0) into the zone after an apex."
            )
        done = failed or success or step_count >= max_steps - 1
        score = 100.0 if success else (0.0 if failed else 0.0)
        metrics = self._make_metrics(pos, vel, step_count, success, failed, failure_reason)
        return done, score, metrics

    def _check_design_constraints(self):
        violations = []
        if self.environment is None:
            return ["Environment not available"]
        mass = self.environment.get_structure_mass()
        if mass > self.MAX_STRUCTURE_MASS:
            violations.append(f"Structure mass {mass:.2f} kg exceeds maximum {self.MAX_STRUCTURE_MASS} kg")
        for body in self.environment._bodies:
            x, y = body.position.x, body.position.y
            if not (self.BUILD_ZONE_X_MIN <= x <= self.BUILD_ZONE_X_MAX and
                    self.BUILD_ZONE_Y_MIN <= y <= self.BUILD_ZONE_Y_MAX):
                violations.append(
                    f"Beam at ({x:.2f}, {y:.2f}) is outside build zone "
                    f"x=[{self.BUILD_ZONE_X_MIN}, {self.BUILD_ZONE_X_MAX}], "
                    f"y=[{self.BUILD_ZONE_Y_MIN}, {self.BUILD_ZONE_Y_MAX}]"
                )
        return violations

    def _make_metrics(self, pos, vel, step_count, success=False, failed=False, failure_reason=None):
        px, py = pos if pos else (0, 0)
        vx, vy = (vel[0], vel[1]) if vel else (0, 0)
        speed = (vx * vx + vy * vy) ** 0.5
        # Pivot at (10, 10), rope L=4 -> angle from vertical: sin(angle) = (px-10)/4
        pivot_x = getattr(self.environment, "_pivot_x", 10.0)
        pivot_y = getattr(self.environment, "_pivot_y", 10.0)
        dx = px - pivot_x
        dy = py - pivot_y
        swing_angle_rad = math.atan2(dx, pivot_y - py) if (pivot_y - py) != 0 else 0.0
        swing_angle_deg = math.degrees(swing_angle_rad)
        height_gap_to_target = max(0.0, self._target_y_min - py)
        target_center_x = (self._target_x_min + self._target_x_max) / 2
        distance_to_target_x = abs(px - target_center_x) if not (self._target_x_min <= px <= self._target_x_max) else 0.0
        progress_pct = max(0.0, min(100.0, 100.0 * (py - 6.0) / (self._target_y_min - 6.0))) if self._target_y_min > 6 else (100.0 if py >= self._target_y_min else 0.0)
        return {
            "seat_x": px, "seat_y": py,
            "seat_vx": vx, "seat_vy": vy, "seat_speed": speed,
            "target_y_min": self._target_y_min,
            "target_x_min": self._target_x_min,
            "target_x_max": self._target_x_max,
            "success": success, "failed": failed, "failure_reason": failure_reason,
            "step_count": step_count,
            "structure_mass": self.environment.get_structure_mass(),
            "max_structure_mass": self.MAX_STRUCTURE_MASS,
            "touched_target": self._touched_target,
            "apex_reached": self._apex_reached,
            "max_seat_y_reached": self._max_seat_y_reached,
            "height_gap_to_target": height_gap_to_target,
            "swing_angle_deg": swing_angle_deg,
            "progress_pct": progress_pct,
            "distance_to_target_x": distance_to_target_x,
        }

    def get_task_description(self):
        return {
            "task": "D-04: The Swing",
            "description": "Pump swing so apex (v≈0) is in target zone or seat falls vertically into zone; wind/damping/force limit.",
            "success_criteria": {
                "primary": f"(1) Apex in zone: seat in zone (y>={self._target_y_min}, x in [{self._target_x_min},{self._target_x_max}]) with speed < {APEX_SPEED_THRESHOLD} m/s, OR (2) After apex, fall vertically (|vx|<{VERTICAL_FALL_VX_THRESHOLD}, vy<0) into zone",
                "failure": "Did not satisfy apex-in-zone or vertical-fall-into-zone",
            },
            "evaluation": {"score_range": "0-100", "success_score": 100, "failure_score": 0},
        }
