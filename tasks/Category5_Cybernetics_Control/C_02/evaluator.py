"""
C-02: The Lander task evaluation module (hard variant: moving platform)
Success: soft landing on the moving platform (full hull footprint in zone at touchdown), upright,
with vertical speed, angle, and remaining impulse within configured limits.

Failure modes: impact speed too high at touchdown; hull footprint outside the valid zone at
touchdown time; landing angle beyond limit; main-engine fuel exhausted before landing;
insufficient impulse remaining at landing; breach of the no-fly corridor; episode step horizon
reached without landing.

The valid landing zone moves in time; the task text states the platform center law (base,
amplitude, period) so the x-window at touchdown can be computed from the landing time. Closed-loop
feedback remains useful to synchronize with the simulator clock and handle unmodeled effects.

Note: The authoritative task text for agents is ``prompt.TASK_PROMPT`` plus any curriculum
``update_*`` edits and suffixes; ``get_task_description()`` mirrors the main quantitative limits
when ``terrain_bounds`` is populated from the environment (defaults match ``environment.py``).
"""
import math
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

try:
    from environment import (
        BARRIER_X_LEFT,
        BARRIER_X_RIGHT,
        BARRIER_Y_BOTTOM,
        BARRIER_Y_TOP,
        DEFAULT_TIME_STEP,
        GROUND_LENGTH,
        GROUND_SLAB_HEIGHT,
        GROUND_Y_TOP,
        LAND_TOLERANCE,
        LANDER_HALF_HEIGHT,
        LANDER_HALF_WIDTH,
        LANDER_MASS,
        MAX_EPISODE_STEPS,
        MAX_LANDING_ANGLE,
        MAX_SAFE_VERTICAL_SPEED,
        MAX_THRUST,
        MAX_TORQUE,
        MIN_FUEL_REMAINING_AT_LANDING,
        PLATFORM_AMPLITUDE,
        PLATFORM_CENTER_BASE,
        PLATFORM_HALF_WIDTH,
        PLATFORM_PERIOD,
        SPAWN_X,
        SPAWN_Y,
        THRUST_DELAY_STEPS,
        TOTAL_FUEL_IMPULSE,
    )
except ImportError:
    from tasks.Category5_Cybernetics_Control.C_02.environment import (
        BARRIER_X_LEFT,
        BARRIER_X_RIGHT,
        BARRIER_Y_BOTTOM,
        BARRIER_Y_TOP,
        DEFAULT_TIME_STEP,
        GROUND_LENGTH,
        GROUND_SLAB_HEIGHT,
        GROUND_Y_TOP,
        LAND_TOLERANCE,
        LANDER_HALF_HEIGHT,
        LANDER_HALF_WIDTH,
        LANDER_MASS,
        MAX_EPISODE_STEPS,
        MAX_LANDING_ANGLE,
        MAX_SAFE_VERTICAL_SPEED,
        MAX_THRUST,
        MAX_TORQUE,
        MIN_FUEL_REMAINING_AT_LANDING,
        PLATFORM_AMPLITUDE,
        PLATFORM_CENTER_BASE,
        PLATFORM_HALF_WIDTH,
        PLATFORM_PERIOD,
        SPAWN_X,
        SPAWN_Y,
        THRUST_DELAY_STEPS,
        TOTAL_FUEL_IMPULSE,
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
        self._barrier_x_left = float(terrain_bounds.get("barrier_x_left", BARRIER_X_LEFT))
        self._barrier_x_right = float(terrain_bounds.get("barrier_x_right", BARRIER_X_RIGHT))
        self._barrier_y_top = float(terrain_bounds.get("barrier_y_top", BARRIER_Y_TOP))
        self._barrier_y_bottom = float(terrain_bounds.get("barrier_y_bottom", BARRIER_Y_BOTTOM))
        self._land_tolerance = float(terrain_bounds.get("land_tolerance", LAND_TOLERANCE))
        _ms = terrain_bounds.get("max_episode_steps")
        self._episode_step_limit = int(_ms) if _ms is not None else int(MAX_EPISODE_STEPS)

    def evaluate(self, agent_body, step_count, max_steps):
        """
        Evaluate lander each step.

        Landing is detected the first time the craft's lowest point is within ``land_tolerance``
        of the ground surface. Success additionally requires, at that instant: touchdown
        ``|vy|`` within limit; **full** ground-contact x-span inside
        ``get_zone_x_bounds_at_step(landing_step)`` (moving platform); ``|angle|`` within limit;
        remaining impulse at least ``min_fuel_remaining_at_landing``. Early failures: no-fly
        corridor breach, fuel exhausted before landing, or step horizon without landing.
        """
        if not self.environment:
            hz = (
                min(max_steps, self._episode_step_limit)
                if max_steps > 0
                else self._episode_step_limit
            )
            td = int(self.terrain_bounds.get("thrust_delay_steps", THRUST_DELAY_STEPS))
            return False, 0.0, {
                "error": "Environment not available",
                "failed": True,
                "success": False,
                "landed": False,
                "max_episode_steps": self._episode_step_limit,
                "episode_horizon": hz,
                "thrust_delay_steps": td,
            }

        # Align with sandbox/prompt: never exceed terrain max_episode_steps; honor caller max_steps when > 0.
        if max_steps > 0:
            horizon = min(max_steps, self._episode_step_limit)
        else:
            horizon = self._episode_step_limit

        thrust_delay_steps = int(self.terrain_bounds.get("thrust_delay_steps", THRUST_DELAY_STEPS))
        if hasattr(self.environment, "get_thrust_delay_steps"):
            thrust_delay_steps = int(self.environment.get_thrust_delay_steps())

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
                "barrier_x_left": self._barrier_x_left,
                "barrier_x_right": self._barrier_x_right,
                "barrier_y_top": self._barrier_y_top,
                "barrier_y_bottom": float(
                    self.terrain_bounds.get("barrier_y_bottom", BARRIER_Y_BOTTOM)
                ),
                "max_episode_steps": self._episode_step_limit,
                "episode_horizon": horizon,
                "thrust_delay_steps": thrust_delay_steps,
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
            zone_x_min, zone_x_max = self.environment.get_zone_x_bounds_at_step(
                self._landing_step
            )
            x_lo = self._landing_x_lo if self._landing_x_lo is not None else self._landing_x
            x_hi = self._landing_x_hi if self._landing_x_hi is not None else self._landing_x
            landing_reasons = []
            if abs(self._landing_vy) > self.max_safe_vertical_speed:
                landing_reasons.append(
                    f"Impact speed too high: |vy|={abs(self._landing_vy):.2f} m/s "
                    f"exceeds limit {self.max_safe_vertical_speed:.1f} m/s (magnitude at touchdown)"
                )
            if x_lo is not None and x_hi is not None and (
                x_lo < zone_x_min or x_hi > zone_x_max
            ):
                landing_reasons.append(
                    f"Out of landing zone: hull footprint x in [{x_lo:.2f}, {x_hi:.2f}] m at step "
                    f"{self._landing_step} (valid zone at that time: "
                    f"[{zone_x_min:.2f}, {zone_x_max:.2f}] m)"
                )
            if self._landing_angle is not None and abs(self._landing_angle) > self._max_landing_angle:
                limit_deg = math.degrees(self._max_landing_angle)
                angle_deg = math.degrees(abs(self._landing_angle))
                landing_reasons.append(
                    f"Capsized: landing angle {angle_deg:.2f}° "
                    f"exceeds limit {limit_deg:.2f}° (must land upright)"
                )
            if remaining_fuel is not None and remaining_fuel < self._min_fuel_remaining:
                landing_reasons.append(
                    f"Insufficient fuel remaining: {remaining_fuel:.0f} N·s at landing; "
                    f"must land with at least {self._min_fuel_remaining:.0f} N·s (fuel-efficient trajectory required)"
                )
            if landing_reasons:
                failed = True
                failure_reason = " | ".join(landing_reasons)
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
            "barrier_x_left": self._barrier_x_left,
            "barrier_x_right": self._barrier_x_right,
            "barrier_y_top": self._barrier_y_top,
            "barrier_y_bottom": self._barrier_y_bottom,
            "max_episode_steps": self._episode_step_limit,
            "episode_horizon": horizon,
            "thrust_delay_steps": thrust_delay_steps,
        }

        done = failed or self._landed
        return done, score, metrics

    def get_task_description(self):
        """Quantitative summary; prefer ``TASK_PROMPT`` for agents. Uses ``terrain_bounds`` + live env when set."""
        tb = self.terrain_bounds
        e = self.environment

        def _from_env(attr: str, default):
            if e is not None and hasattr(e, attr):
                return getattr(e, attr)
            return default

        spawn_x = float(tb.get("spawn_x", _from_env("_spawn_x", SPAWN_X)))
        spawn_y = float(tb.get("spawn_y", _from_env("_spawn_y", SPAWN_Y)))
        lander_mass = float(tb.get("lander_mass", _from_env("_lander_mass", LANDER_MASS)))
        pc = float(tb.get("platform_center_base", _from_env("_platform_center_base", PLATFORM_CENTER_BASE)))
        pa = float(tb.get("platform_amplitude", _from_env("_platform_amplitude", PLATFORM_AMPLITUDE)))
        pp = float(tb.get("platform_period", _from_env("_platform_period", PLATFORM_PERIOD)))
        phw = float(tb.get("platform_half_width", _from_env("_platform_half_width", PLATFORM_HALF_WIDTH)))
        max_thrust = float(tb.get("max_thrust", _from_env("_max_thrust", MAX_THRUST)))
        max_torque = float(tb.get("max_torque", _from_env("_max_torque", MAX_TORQUE)))

        return {
            "task": "C-02: The Lander (obstacle + moving platform)",
            "description": (
                "Avoid the no-fly corridor, then soft-land with the full hull footprint inside the "
                "x-window at touchdown (window moves in time per the stated platform law), upright, "
                "within |vy|/angle/fuel limits."
            ),
            "spawn_m": {"x": spawn_x, "y": spawn_y},
            "lander": {
                "mass_kg": lander_mass,
                "half_width_m": float(tb.get("lander_half_width", LANDER_HALF_WIDTH)),
                "half_height_m": float(tb.get("lander_half_height", LANDER_HALF_HEIGHT)),
            },
            "ground": {
                "surface_y_m": float(tb.get("ground_y_top", GROUND_Y_TOP)),
                "slab_thickness_m": float(tb.get("ground_slab_height", GROUND_SLAB_HEIGHT)),
                "length_m": float(tb.get("ground_length", GROUND_LENGTH)),
            },
            "simulation": {
                "time_step_s": float(tb.get("time_step", DEFAULT_TIME_STEP)),
                "max_episode_steps": int(tb.get("max_episode_steps", MAX_EPISODE_STEPS)),
                "thrust_delay_steps": int(tb.get("thrust_delay_steps", THRUST_DELAY_STEPS)),
            },
            "no_fly_corridor": {
                "x_left_m": float(tb.get("barrier_x_left", BARRIER_X_LEFT)),
                "x_right_m": float(tb.get("barrier_x_right", BARRIER_X_RIGHT)),
                "y_obstacle_top_m": float(tb.get("barrier_y_top", BARRIER_Y_TOP)),
                "y_ceiling_m": float(tb.get("barrier_y_bottom", BARRIER_Y_BOTTOM)),
            },
            "landing_platform": {
                "center_x_m": pc,
                "half_width_m": phw,
                "amplitude_m": pa,
                "period_s": pp,
            },
            "actuation_limits": {"max_thrust_n": max_thrust, "max_torque_nm": max_torque},
            "fuel_impulse": {
                "total_budget_ns": float(tb.get("total_fuel_impulse", TOTAL_FUEL_IMPULSE)),
                "min_remaining_at_landing_ns": float(
                    tb.get("min_fuel_remaining_at_landing", MIN_FUEL_REMAINING_AT_LANDING)
                ),
            },
            "touchdown": {
                "land_tolerance_m": float(tb.get("land_tolerance", LAND_TOLERANCE)),
                "max_safe_vertical_speed_m_s": self.max_safe_vertical_speed,
                "max_landing_angle_rad": self._max_landing_angle,
            },
            "max_safe_vertical_speed": self.max_safe_vertical_speed,
            "max_landing_angle_rad": self._max_landing_angle,
            "min_fuel_remaining_at_landing": self._min_fuel_remaining,
            "success_criteria": {
                "primary": (
                    "Land with |vy| within limit at touchdown, full footprint in zone at that time, "
                    "|angle| within limit, min fuel remaining"
                ),
                "failure": (
                    "|vy| too high, out of zone, capsized, fuel exhausted, insufficient fuel at landing, "
                    "barrier breach, or step horizon without landing"
                ),
            },
            "evaluation": {
                "score_range": "0-100",
                "success_score": 100,
                "failure_score": 0,
            },
        }
