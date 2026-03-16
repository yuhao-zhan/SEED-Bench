"""
D-02: The Jumper task evaluation module
Success: jumper reaches right platform (x >= right_platform_start_x, y >= safe). Failure: fall into pit.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))


class Evaluator:
    """
    Evaluation for D-02: The Jumper.
    Success: jumper center reaches right platform (x >= right_platform_start_x, y >= landing_min_y).
    Failure: fall into pit (y < pit_fail_y) or never reach right platform.
    """

    def __init__(self, terrain_bounds, environment=None):
        self.terrain_bounds = terrain_bounds
        self.environment = environment
        self._right_platform_start_x = terrain_bounds.get("right_platform_start_x", 26.0)
        self._pit_bottom_y = terrain_bounds.get("pit_bottom_y", 0.0)
        self._landing_min_y = float(terrain_bounds.get("landing_min_y", 1.0))  # Jumper center must be at least this y when on right side
        self._pit_fail_y = self._pit_bottom_y  # Below this y = in pit (fail); use env value
        spawn = terrain_bounds.get("jumper_spawn", (5.0, 5.0))
        self._jumper_spawn_x = float(spawn[0]) if len(spawn) >= 1 else 5.0
        jw = float(terrain_bounds.get("jumper_width", 0.8))
        jh = float(terrain_bounds.get("jumper_height", 0.6))
        self._jumper_half_w = jw / 2.0
        self._jumper_half_h = jh / 2.0
        self._landed = False
        self._design_constraints_checked = False
        # Slots in pit: each slot (x_min, x_max, floor_y, ceil_y); jumper center must stay inside (floor+margin, ceil-margin) when in x-range
        self._slots = list(terrain_bounds.get("slots", []))
        self._barrier_x_min = terrain_bounds.get("barrier_x_min")
        self._barrier_x_max = terrain_bounds.get("barrier_x_max")
        self._barrier_y_max = terrain_bounds.get("barrier_y_max")
        self._barrier2_x_min = terrain_bounds.get("barrier2_x_min")
        self._barrier2_x_max = terrain_bounds.get("barrier2_x_max")
        self._barrier2_y_max = terrain_bounds.get("barrier2_y_max")
        self._barrier3_x_min = terrain_bounds.get("barrier3_x_min")
        self._barrier3_x_max = terrain_bounds.get("barrier3_x_max")
        self._barrier3_y_max = terrain_bounds.get("barrier3_y_max")

        if environment is None:
            raise ValueError("Evaluator requires environment instance")
        self.MAX_STRUCTURE_MASS = getattr(environment, "MAX_STRUCTURE_MASS", 180.0)
        self.BUILD_ZONE_X_MIN = environment.BUILD_ZONE_X_MIN
        self.BUILD_ZONE_X_MAX = environment.BUILD_ZONE_X_MAX
        self.BUILD_ZONE_Y_MIN = environment.BUILD_ZONE_Y_MIN
        self.BUILD_ZONE_Y_MAX = environment.BUILD_ZONE_Y_MAX

    def evaluate(self, agent_body, step_count, max_steps):
        """Returns: (done, score, metrics)."""
        if self.environment is None:
            return True, 0.0, {"error": "Environment not available"}

        pos = self.environment.get_jumper_position()
        vel = self.environment.get_jumper_velocity()
        if pos is None:
            return True, 0.0, {"error": "Jumper not found"}

        px, py = pos
        vx = vel[0] if vel else 0.0
        vy = vel[1] if vel else 0.0

        # Reached right platform?
        if px >= self._right_platform_start_x and py >= self._landing_min_y:
            self._landed = True

        # Design constraints on first evaluation (main loop first eval is at step_count=1)
        if not self._design_constraints_checked and step_count <= 1:
            violations = self._check_design_constraints()
            if violations:
                self._design_constraints_checked = True
                metrics = self._make_metrics(
                    pos, vel, step_count, success=False, failed=True,
                    failure_reason="Design constraint violated: " + "; ".join(violations),
                )
                return True, 0.0, metrics
            self._design_constraints_checked = True

        success = self._landed
        failed = False
        failure_reason = None

        # Must pass through each slot: when in slot x-range, jumper center must be inside (floor+margin, ceiling-margin)
        SLOT_MARGIN = 0.05  # m; clearance from floor and ceiling (minimal for discrete step passability)
        for i, slot in enumerate(self._slots):
            if len(slot) != 4:
                continue
            bx_min, bx_max, floor_y, ceil_y = slot
            if bx_min is None or bx_max is None or floor_y is None or ceil_y is None:
                continue
            # Slot rule applies when jumper center x is within 0.5 m of slot center (match prompt)
            in_x_range = bx_min <= px <= bx_max
            if not in_x_range:
                continue
            # In this slot: center must be in (floor+margin, ceil-margin); also avoid touching (bottom/top vs floor/ceiling)
            slot_num = i + 1
            if py - self._jumper_half_h <= floor_y + SLOT_MARGIN:
                failed = True
                failure_reason = f"Hit lower red bar in slot {slot_num}: trajectory must pass through the gap between lower and upper red bars"
                break
            if py + self._jumper_half_h >= ceil_y - SLOT_MARGIN:
                failed = True
                failure_reason = f"Hit upper red bar in slot {slot_num}: trajectory must pass through the gap between lower and upper red bars"
                break

        # Fall into pit: y below threshold
        if py < self._pit_fail_y:
            failed = True
            failure_reason = f"Fall into pit: jumper fell into the pit (y < {self._pit_fail_y} m)"

        done = False
        if failed:
            done = True
            score = 0.0
        elif success:
            done = True
            score = 100.0
        elif step_count >= max_steps - 1:
            done = True
            if self._landed:
                score = 100.0
                success = True
            else:
                failed = True
                failure_reason = "Jumper did not reach the right platform (fell into pit or insufficient jump)"
                score = 0.0
        else:
            score = 100.0 if self._landed else 0.0

        metrics = self._make_metrics(
            pos, vel, step_count, success=success, failed=failed,
            failure_reason=failure_reason,
        )
        return done, score, metrics

    def _check_design_constraints(self):
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
        progress = max(0.0, (px - self._jumper_spawn_x) / (self._right_platform_start_x - self._jumper_spawn_x)) * 100.0
        progress = min(100.0, progress)

        # Jumper body for angular state (if available)
        jumper_body = self.environment._terrain_bodies.get("jumper")
        angular_velocity = float(jumper_body.angularVelocity) if jumper_body else 0.0
        angle = float(jumper_body.angle) if jumper_body else 0.0
        distance_from_platform = max(0.0, self._right_platform_start_x - px)

        return {
            "jumper_x": px,
            "jumper_y": py,
            "jumper_vx": vx,
            "jumper_vy": vy,
            "jumper_speed": speed,
            "right_platform_start_x": self._right_platform_start_x,
            "progress": progress,
            "success": success,
            "failed": failed,
            "failure_reason": failure_reason,
            "step_count": step_count,
            "structure_mass": self.environment.get_structure_mass(),
            "max_structure_mass": self.MAX_STRUCTURE_MASS,
            "landed": self._landed,
            "angular_velocity": angular_velocity,
            "angle": angle,
            "distance_from_platform": distance_from_platform,
            "pit_fail_y": self._pit_fail_y,
            "landing_min_y": self._landing_min_y,
        }

    def get_task_description(self):
        return {
            "task": "D-02: The Jumper",
            "description": "Launch a jumper across a pit with an obstacle; trajectory must go OVER the barrier to the right platform",
            "success_criteria": {
                "primary": f"Jumper reaches right platform (x >= {self._right_platform_start_x} m, y >= {self._landing_min_y} m)",
                "failure": "Fall into pit or insufficient jump",
            },
            "evaluation": {"score_range": "0-100", "success_score": 100, "failure_score": 0},
        }
