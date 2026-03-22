"""
C-02: The Lander task evaluation module (hard variant: moving platform)
Success: soft landing on the moving platform (full hull footprint in zone at touchdown), upright,
with vertical speed, angle, and remaining impulse within configured limits.

Failure modes: impact speed too high at touchdown; hull footprint outside the valid zone at
touchdown time; landing angle beyond limit; main-engine fuel exhausted before landing;
insufficient impulse remaining at landing; breach of the no-fly corridor; episode step horizon
reached without landing.

The valid landing zone moves with time; the agent must infer this from feedback.
"""
import math
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

try:
    from environment import (
        BARRIER_Y_BOTTOM,
        BARRIER_Y_TOP,
        LAND_TOLERANCE,
        MAX_EPISODE_STEPS,
        MAX_LANDING_ANGLE,
        MAX_SAFE_VERTICAL_SPEED,
        MIN_FUEL_REMAINING_AT_LANDING,
        PLATFORM_CENTER_BASE,
        PLATFORM_HALF_WIDTH,
    )
except ImportError:
    from tasks.Category5_Cybernetics_Control.C_02.environment import (
        BARRIER_Y_BOTTOM,
        BARRIER_Y_TOP,
        LAND_TOLERANCE,
        MAX_EPISODE_STEPS,
        MAX_LANDING_ANGLE,
        MAX_SAFE_VERTICAL_SPEED,
        MIN_FUEL_REMAINING_AT_LANDING,
        PLATFORM_CENTER_BASE,
        PLATFORM_HALF_WIDTH,
    )


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
        self._landing_x_lo = None
        self._landing_x_hi = None
        self._max_landing_angle = float(
            terrain_bounds.get("max_landing_angle", MAX_LANDING_ANGLE)
        )
        self._min_fuel_remaining = float(
            terrain_bounds.get("min_fuel_remaining_at_landing", MIN_FUEL_REMAINING_AT_LANDING)
        )
        self._barrier_y_top = float(terrain_bounds.get("barrier_y_top", BARRIER_Y_TOP))
        self._barrier_y_bottom = float(terrain_bounds.get("barrier_y_bottom", BARRIER_Y_BOTTOM))
        self._land_tolerance = float(terrain_bounds.get("land_tolerance", LAND_TOLERANCE))
        _ms = terrain_bounds.get("max_episode_steps")
        self._episode_step_limit = int(_ms) if _ms is not None else int(MAX_EPISODE_STEPS)

    def evaluate(self, agent_body, step_count, max_steps):
        """
        Evaluate lander. Landing = first time bottom touches ground.
        Zone at touchdown = get_zone_x_bounds_at_step(landing_step) (moving platform).
        Success = landed AND x in zone(at landing time) AND |angle| <= limit AND |vy| <= limit (|vy| at touchdown).
        """
        if not self.environment:
            return True, 0.0, {"error": "Environment not available"}

        # Align with sandbox/prompt: never exceed terrain max_episode_steps; honor caller max_steps when > 0.
        if max_steps > 0:
            horizon = min(max_steps, self._episode_step_limit)
        else:
            horizon = self._episode_step_limit

        if getattr(self.environment, "get_barrier_hit", lambda: False)():
            x, y = self.environment.get_lander_position()
            ground_y_top = self.environment.get_ground_y_top()
            bottom_y = self.environment.get_lander_bottom_y()
            kind = (
                self.environment.get_barrier_failure_kind()
                if hasattr(self.environment, "get_barrier_failure_kind")
                else getattr(self.environment, "_barrier_failure_kind", None)
            )
            if kind == "ceiling":
                reason = "Entered forbidden zone (atmospheric ceiling): you must fly lower within this region."
            elif kind == "obstacle":
                reason = "Entered forbidden zone (obstacle): you must fly higher within this region."
            else:
                # Defensive: env should always set kind; infer from altitude in corridor band
                bt = float(self.terrain_bounds.get("barrier_y_top", BARRIER_Y_TOP))
                bb = float(self.terrain_bounds.get("barrier_y_bottom", BARRIER_Y_BOTTOM))
                mid = 0.5 * (bt + bb)
                if y < mid:
                    reason = "Entered forbidden zone (obstacle): you must fly higher within this region."
                else:
                    reason = "Entered forbidden zone (atmospheric ceiling): you must fly lower within this region."

            if hasattr(self.environment, "get_zone_x_bounds_at_step"):
                zone_x_min, zone_x_max = self.environment.get_zone_x_bounds_at_step(step_count)
            else:
                _pc = float(getattr(self.environment, "_platform_center_base", PLATFORM_CENTER_BASE))
                _ph = float(getattr(self.environment, "_platform_half_width", PLATFORM_HALF_WIDTH))
                zone_x_min, zone_x_max = _pc - _ph, _pc + _ph

            rfuel = (
                self.environment.get_remaining_fuel()
                if hasattr(self.environment, "get_remaining_fuel")
                else None
            )
            return True, 0.0, {
                "failed": True,
                "failure_reason": reason,
                "success": False,
                "lander_x": x,
                "lander_y": y,
                "lander_vx": self.environment.get_lander_velocity()[0],
                "lander_vy": self.environment.get_lander_velocity()[1],
                "lander_angle": self.environment.get_lander_angle(),
                "lander_angular_velocity": self.environment.get_lander_angular_velocity()
                if hasattr(self.environment, "get_lander_angular_velocity")
                else 0.0,
                "step_count": step_count,
                "landed": False,
                "landing_vy": None,
                "landing_x": None,
                "landing_x_lo": None,
                "landing_x_hi": None,
                "landing_angle": None,
                "landing_step": None,
                "height_above_ground": bottom_y - ground_y_top,
                "zone_x_min": zone_x_min,
                "zone_x_max": zone_x_max,
                "max_safe_vertical_speed": self.max_safe_vertical_speed,
                "max_landing_angle": self._max_landing_angle,
                "min_fuel_remaining_at_landing": self._min_fuel_remaining,
                "remaining_fuel": rfuel,
                "ground_y_top": ground_y_top,
                "barrier_y_top": self._barrier_y_top,
                "barrier_y_bottom": float(
                    self.terrain_bounds.get("barrier_y_bottom", BARRIER_Y_BOTTOM)
                ),
            }

        ground_y_top = self.environment.get_ground_y_top()
        bottom_y = self.environment.get_lander_bottom_y()
        x, y = self.environment.get_lander_position()
        vx, vy = self.environment.get_lander_velocity()
        angle = self.environment.get_lander_angle()

        landed_this_step = bottom_y <= ground_y_top + self._land_tolerance

        if landed_this_step and not self._landed:
            self._landed = True
            self._landing_vy = vy
            self._landing_angle = angle
            self._landing_x = x
            self._landing_step = step_count
            if hasattr(self.environment, "get_lander_bottom_contact_x_span"):
                self._landing_x_lo, self._landing_x_hi = (
                    self.environment.get_lander_bottom_contact_x_span()
                )
            else:
                self._landing_x_lo = self._landing_x_hi = x

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
                    f"Impact speed too high: |vy|={abs(self._landing_vy):.2f} m/s "
                    f"exceeds limit {self.max_safe_vertical_speed:.1f} m/s (magnitude at touchdown)"
                )
            else:
                zone_x_min, zone_x_max = self.environment.get_zone_x_bounds_at_step(
                    self._landing_step
                )
                x_lo = self._landing_x_lo if self._landing_x_lo is not None else self._landing_x
                x_hi = self._landing_x_hi if self._landing_x_hi is not None else self._landing_x
                if x_lo is not None and x_hi is not None and (
                    x_lo < zone_x_min or x_hi > zone_x_max
                ):
                    failed = True
                    failure_reason = (
                        f"Out of landing zone: hull footprint x in [{x_lo:.2f}, {x_hi:.2f}] m at step "
                        f"{self._landing_step} (valid zone at that time: "
                        f"[{zone_x_min:.2f}, {zone_x_max:.2f}] m)"
                    )
                elif self._landing_angle is not None and abs(
                    self._landing_angle
                ) > self._max_landing_angle:
                    failed = True
                    limit_deg = math.degrees(self._max_landing_angle)
                    angle_deg = math.degrees(abs(self._landing_angle))
                    failure_reason = (
                        f"Capsized: landing angle {angle_deg:.2f}° "
                        f"exceeds limit {limit_deg:.2f}° (must land upright)"
                    )
                elif remaining_fuel is not None and remaining_fuel < self._min_fuel_remaining:
                    failed = True
                    failure_reason = (
                        f"Insufficient fuel remaining: {remaining_fuel:.0f} N·s at landing; "
                        f"must land with at least {self._min_fuel_remaining:.0f} N·s (fuel-efficient trajectory required)"
                    )
        elif horizon > 0 and step_count >= horizon and not self._landed:
            failed = True
            failure_reason = (
                f"Episode horizon reached ({horizon} simulation steps) without successful landing"
            )

        success = self._landed and not failed

        if success and not failed:
            score = 100.0
        elif failed:
            score = 0.0
        else:
            if horizon > 0:
                progress = step_count / horizon
            elif max_steps > 0:
                progress = step_count / max_steps
            else:
                progress = 0.0
            score = progress * 80.0

        height_above_ground = bottom_y - ground_y_top
        speed = math.sqrt(vx * vx + vy * vy)
        if hasattr(self.environment, "get_zone_x_bounds_at_step"):
            zone_x_min, zone_x_max = self.environment.get_zone_x_bounds_at_step(step_count)
        else:
            _pc = float(getattr(self.environment, "_platform_center_base", PLATFORM_CENTER_BASE))
            _ph = float(getattr(self.environment, "_platform_half_width", PLATFORM_HALF_WIDTH))
            zone_x_min, zone_x_max = _pc - _ph, _pc + _ph

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
            "landing_x_lo": self._landing_x_lo,
            "landing_x_hi": self._landing_x_hi,
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
            "barrier_y_top": self._barrier_y_top,
            "barrier_y_bottom": self._barrier_y_bottom,
        }

        done = failed or self._landed
        return done, score, metrics

    def get_task_description(self):
        return {
            "task": "C-02: The Lander (obstacle + moving platform)",
            "description": "Avoid a no-fly zone (obstacle), then soft-land on the valid area, upright; valid area may depend on when you land",
            "max_safe_vertical_speed": self.max_safe_vertical_speed,
            "max_landing_angle_rad": self._max_landing_angle,
            "min_fuel_remaining_at_landing": self._min_fuel_remaining,
            "success_criteria": {
                "primary": "Land with |vy| within limit at touchdown, footprint in zone at that time, |angle| within limit, min fuel remaining",
                "failure": "|vy| too high, out of zone, capsized, fuel exhausted, insufficient fuel at landing, barrier breach, or step horizon without landing",
            },
            "evaluation": {
                "score_range": "0-100",
                "success_score": 100,
                "failure_score": 0,
            },
        }
