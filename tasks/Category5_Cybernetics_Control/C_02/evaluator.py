"""
C-02: The Lander task evaluation module (hard variant: moving platform)
Success: soft landing on the moving platform (zone at touchdown time), upright.
Failure: impact speed too high, out of zone (zone depends on when you land), capsized, or fuel exhausted.
The valid landing zone moves with time; the agent must infer this from feedback.
"""
import math
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

MAX_SAFE_VERTICAL_SPEED = 2.0
MIN_FUEL_REMAINING_AT_LANDING = 350.0


class Evaluator:
    """
    Evaluation for C-02: Box lander with moving platform.
    Zone at landing step = platform position at that time (time-dependent).
    """

    def __init__(self, terrain_bounds, environment=None):
        self.terrain_bounds = terrain_bounds
        self.environment = environment
        self.max_safe_vertical_speed = float(
            terrain_bounds.get("max_safe_vertical_speed", MAX_SAFE_VERTICAL_SPEED)
        )
        self._landed = False
        self._landing_vy = None
        self._landing_angle = None
        self._landing_x = None
        self._landing_step = None
        self._max_landing_angle = float(terrain_bounds.get("max_landing_angle", 0.25))
        self._min_fuel_remaining = float(
            terrain_bounds.get("min_fuel_remaining_at_landing", MIN_FUEL_REMAINING_AT_LANDING)
        )

    def evaluate(self, agent_body, step_count, max_steps):
        """
        Evaluate lander. Landing = first time bottom touches ground.
        Zone at touchdown = get_zone_x_bounds_at_step(landing_step) (moving platform).
        Success = landed AND x in zone(at landing time) AND |angle| <= limit AND |vy| <= limit.
        """
        if not self.environment:
            return True, 0.0, {"error": "Environment not available"}

        if getattr(self.environment, "get_barrier_hit", lambda: False)():
            x, y = self.environment.get_lander_position()
            return True, 0.0, {
                "failed": True,
                "failure_reason": "Entered forbidden zone (obstacle): you must go around it, e.g. above it",
                "success": False,
                "lander_x": x,
                "lander_y": y,
                "lander_vx": self.environment.get_lander_velocity()[0],
                "lander_vy": self.environment.get_lander_velocity()[1],
                "lander_angle": self.environment.get_lander_angle(),
                "step_count": step_count,
                "landed": False,
                "landing_vy": None,
                "landing_x": None,
                "landing_angle": None,
                "landing_step": None,
                "height_above_ground": y - self.environment.get_ground_y_top(),
                "zone_x_min": 0.0,
                "zone_x_max": 0.0,
                "remaining_fuel": self.environment.get_remaining_fuel() if hasattr(self.environment, "get_remaining_fuel") else None,
            }

        ground_y_top = self.environment.get_ground_y_top()
        bottom_y = self.environment.get_lander_bottom_y()
        x, y = self.environment.get_lander_position()
        vx, vy = self.environment.get_lander_velocity()
        angle = self.environment.get_lander_angle()

        LAND_TOLERANCE = 0.02
        landed_this_step = bottom_y <= ground_y_top + LAND_TOLERANCE

        if landed_this_step and not self._landed:
            self._landed = True
            self._landing_vy = vy
            self._landing_angle = angle
            self._landing_x = x
            self._landing_step = step_count

        failed = False
        failure_reason = None
        remaining_fuel = (
            self.environment.get_remaining_fuel()
            if hasattr(self.environment, "get_remaining_fuel")
            else None
        )
        if remaining_fuel is not None and remaining_fuel <= 0 and not self._landed:
            failed = True
            failure_reason = "Fuel exhausted before landing"
        elif self._landed and self._landing_vy is not None:
            if abs(self._landing_vy) > self.max_safe_vertical_speed:
                failed = True
                failure_reason = (
                    f"Impact speed too high: vertical speed {abs(self._landing_vy):.2f} m/s "
                    f"exceeds limit {self.max_safe_vertical_speed:.1f} m/s"
                )
            else:
                zone_x_min, zone_x_max = self.environment.get_zone_x_bounds_at_step(
                    self._landing_step
                )
                if self._landing_x is not None and (
                    self._landing_x < zone_x_min or self._landing_x > zone_x_max
                ):
                    failed = True
                    failure_reason = (
                        f"Out of landing zone: x={self._landing_x:.2f} m at step {self._landing_step} "
                        f"(valid zone at that time: x in [{zone_x_min:.2f}, {zone_x_max:.2f}] m)"
                    )
                elif self._landing_angle is not None and abs(
                    self._landing_angle
                ) > self._max_landing_angle:
                    failed = True
                    failure_reason = (
                        f"Capsized: landing angle {abs(self._landing_angle):.2f} rad "
                        f"exceeds limit {self._max_landing_angle:.2f} rad (must land upright)"
                    )
                elif remaining_fuel is not None and remaining_fuel < self._min_fuel_remaining:
                    failed = True
                    failure_reason = (
                        f"Insufficient fuel remaining: {remaining_fuel:.0f} N·s at landing; "
                        f"must land with at least {self._min_fuel_remaining:.0f} N·s (fuel-efficient trajectory required)"
                    )

        success = self._landed and not failed

        if success and not failed:
            score = 100.0
        elif failed:
            score = 0.0
        else:
            progress = step_count / max_steps if max_steps > 0 else 0.0
            score = progress * 80.0

        height_above_ground = bottom_y - ground_y_top
        speed = math.sqrt(vx * vx + vy * vy)
        zone_x_min, zone_x_max = (
            self.environment.get_zone_x_bounds_at_step(step_count)
            if hasattr(self.environment, "get_zone_x_bounds_at_step")
            else (12.0, 18.0)
        )

        metrics = {
            "lander_x": x,
            "lander_y": y,
            "lander_vx": vx,
            "lander_vy": vy,
            "lander_angle": angle,
            "lander_angular_velocity": self.environment.get_lander_angular_velocity()
                if self.environment else 0.0,
            "landed": self._landed,
            "landing_vy": self._landing_vy,
            "landing_angle": self._landing_angle,
            "landing_x": self._landing_x,
            "step_count": step_count,
            "success": success,
            "failed": failed,
            "failure_reason": failure_reason,
            "height_above_ground": height_above_ground,
            "speed": speed,
            "ground_y_top": ground_y_top,
            "max_safe_vertical_speed": self.max_safe_vertical_speed,
            "zone_x_min": zone_x_min,
            "zone_x_max": zone_x_max,
            "max_landing_angle": self._max_landing_angle,
            "remaining_fuel": remaining_fuel if remaining_fuel is not None else None,
            "min_fuel_remaining_at_landing": self._min_fuel_remaining,
            "landing_step": self._landing_step,
        }

        done = failed or self._landed
        return done, score, metrics

    def get_task_description(self):
        return {
            "task": "C-02: The Lander (obstacle + moving platform)",
            "description": "Avoid a no-fly zone (obstacle), then soft-land on the valid area, upright; valid area may depend on when you land",
            "max_safe_vertical_speed": self.max_safe_vertical_speed,
            "success_criteria": {
                "primary": "Land with vertical impact speed within limit, within the valid zone at touchdown time, upright, and with at least minimum fuel remaining",
                "failure": "Impact speed too high, out of zone, capsized, fuel exhausted, or insufficient fuel remaining at landing",
            },
            "evaluation": {
                "score_range": "0-100",
                "success_score": 100,
                "failure_score": 0,
            },
        }
