"""
F-05: The Boat task environment module
Defines physics world, water zone, boat (hull), cargo, wave excitation, API.
Mechanics: buoyancy, multi-mode wave/wind/current forcing, passive roll-restoring torque on the hull
(torque = -restoring_coeff * hull_angle; coefficient from terrain_config["restoring_coeff"], default 1600.0),
and (when configured) fragile welds. Failure: cargo center crosses the evaluator
loss plane (y < CARGO_WATER_Y, any x), boat exceeds peak roll limit, or structure joints break.
"""
import Box2D
from Box2D.b2 import (world, polygonShape, circleShape, staticBody, dynamicBody, weldJoint)
import math
import random


class Sandbox:
    """Sandbox environment wrapper for F-05: The Boat"""

    def __init__(self, *, terrain_config=None, physics_config=None):
        terrain_config = terrain_config or {}
        physics_config = physics_config or {}
        self._terrain_config = dict(terrain_config)
        self._physics_config = dict(physics_config)

        gravity = tuple(physics_config.get("gravity", (0, -10)))
        self._default_linear_damping = float(physics_config.get("linear_damping", 0.1))
        self._default_angular_damping = float(physics_config.get("angular_damping", 0.05))

        self._world = world(gravity=gravity, doSleep=True)
        self._bodies = []
        self._joints = []
        self._terrain_bodies = {}
        self._cargo = []

        self.world = self._world
        self.bodies = self._bodies
        self.joints = self._joints

        # Zones and params (set before _create_*) — HARD MODE: strict limits, rough seas, wind
        self.WATER_X_MIN = 5.0
        self.WATER_X_MAX = 25.0
        self.WATER_SURFACE_Y = 2.0
        self.CARGO_WATER_Y = float(terrain_config.get("cargo_water_y", 1.98))  # Retention: fail if cargo center y < this (loss plane)
        self.BOAT_MAX_ANGLE_RAD = math.radians(float(terrain_config.get("max_capsize_angle_deg", 18.0)))  # Extreme: 18°
        self.BUILD_ZONE_X_MIN = float(terrain_config.get("build_zone_x_min", 12.0))
        self.BUILD_ZONE_X_MAX = float(terrain_config.get("build_zone_x_max", 18.0))
        self.BUILD_ZONE_Y_MIN = float(terrain_config.get("build_zone_y_min", 2.0))
        self.BUILD_ZONE_Y_MAX = float(terrain_config.get("build_zone_y_max", 4.5))
        self.MAX_STRUCTURE_MASS = float(terrain_config.get("max_structure_mass", 60.0))
        # Multi-mode waves (primary + secondary + gusts)
        wave_amplitude = float(terrain_config.get("wave_amplitude", 10.0))
        wave_freq = float(terrain_config.get("wave_frequency", 0.5))
        self._wave_amplitude = wave_amplitude
        self._wave_omega = 2.0 * math.pi * wave_freq
        self._wave2_amplitude = float(terrain_config.get("wave2_amplitude", 5.0))
        self._wave2_omega = 2.0 * math.pi * float(terrain_config.get("wave2_frequency", 0.27))
        self._gust_amplitude = float(terrain_config.get("gust_amplitude", 4.0))
        self._gust_interval = int(terrain_config.get("gust_interval_steps", 80))
        # Lateral wind (creates roll torque)
        self._wind_amplitude = float(terrain_config.get("wind_amplitude", 5.0))
        self._wind_omega = 2.0 * math.pi * float(terrain_config.get("wind_frequency", 0.15))
        self._sim_time = 0.0
        self._restoring_coeff = float(terrain_config.get("restoring_coeff", 1600.0))  # Stronger for 18° limit
        # Water current (pushes boat away from center)
        self._current_strength = float(terrain_config.get("current_strength", 0.35))
        # Rogue wave (periodic large impulse, sometimes double-hit)
        self._rogue_amplitude = float(terrain_config.get("rogue_amplitude", 14.0))
        self._rogue_interval = int(terrain_config.get("rogue_interval_steps", 380))
        self._rogue_double_step = int(terrain_config.get("rogue_double_step", 5))  # second impulse N steps after first
        # Lateral impulse (sudden gust) — knocks boat sideways
        self._lateral_impulse_amplitude = float(terrain_config.get("lateral_impulse_amplitude", 68.0))
        self._lateral_impulse_interval = int(terrain_config.get("lateral_impulse_interval_steps", 200))
        # Confused-sea roll snaps: impulsive hull angular kicks (Stage-3+); default off.
        self._hull_roll_impulse_amplitude = float(terrain_config.get("hull_roll_impulse_amplitude", 0.0))
        self._hull_roll_impulse_interval = max(1, int(terrain_config.get("hull_roll_impulse_interval_steps", 90)))

        self._create_terrain(terrain_config)
        
        # New mechanics: fragile joints and slippery deck
        self.DECK_FRICTION = float(terrain_config.get("deck_friction", 0.5))
        self.JOINT_MAX_FORCE = float(terrain_config.get("joint_max_force", float('inf')))

        self._create_boat(terrain_config)
        self._create_cargo(terrain_config)

        # Episode-wide extrema for evaluation (any-time failure semantics)
        self._peak_abs_boat_angle_rad = 0.0
        self._cargo_ever_below_loss_plane = False
        self._physics_steps_done = 0
        # Ignore loss-plane crossings during early settle-in (contact resolution / spawn chatter).
        self._cargo_loss_grace_steps = int(terrain_config.get("cargo_loss_grace_steps", 120))

    def _create_terrain(self, terrain_config: dict):
        """Create floor, water zone, and floating obstacles (rocks) that boat can collide with."""
        floor_length = 30.0
        floor_height = 0.3
        floor = self._world.CreateStaticBody(
            position=(floor_length / 2, -floor_height / 2),
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(floor_length / 2, floor_height / 2)),
                friction=0.4,
            ),
        )
        self._terrain_bodies["floor"] = floor

        water_width = 20.0
        water_center_x = 15.0
        water_height = 3.0
        water = self._world.CreateStaticBody(
            position=(water_center_x, water_height / 2),
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(water_width / 2, water_height / 2)),
                friction=0.0,
                isSensor=True,
            ),
        )
        self._terrain_bodies["water"] = water

        # Floating obstacles (rocks) in water — boat/cargo collide and get impulses (4 rocks: extreme)
        rock_config = terrain_config.get("rocks", [])
        if not rock_config:
            rock_config = [
                {"x": 13.5, "y": 1.0, "r": 0.24}, {"x": 14.5, "y": 1.1, "r": 0.22},
                {"x": 15.5, "y": 1.05, "r": 0.23}, {"x": 16.5, "y": 1.08, "r": 0.22}
            ]
        self._rocks = []
        for r in rock_config:
            rx = float(r.get("x", 15.0))
            ry = float(r.get("y", 1.0))
            rr = float(r.get("radius", r.get("r", 0.2)))
            rock = self._world.CreateStaticBody(
                position=(rx, ry),
                fixtures=Box2D.b2FixtureDef(
                    shape=circleShape(radius=rr),
                    friction=0.6,
                    restitution=0.2,
                ),
            )
            self._rocks.append(rock)

    def _create_boat(self, terrain_config: dict):
        """Create boat hull (platform)."""
        boat_width = 3.0
        boat_height = 0.4
        boat_x = 15.0
        # Positive offset raises the hull (more keel clearance); negative sinks it toward hazards.
        boat_y = 2.5 + float(terrain_config.get("boat_y_offset", 0.0))
        hull = self._world.CreateDynamicBody(
            position=(boat_x, boat_y),
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(boat_width / 2, boat_height / 2)),
                density=80.0,
                friction=self.DECK_FRICTION,
            ),
        )
        hull.linearDamping = self._default_linear_damping
        hull.angularDamping = self._default_angular_damping
        self._terrain_bodies["boat"] = hull

    def _create_cargo(self, terrain_config: dict):
        """Create cargo (more, heavier, slipperier) on the boat."""
        cargo_config = terrain_config.get("cargo", {})
        n_cargo = int(cargo_config.get("count", 10))  # 10 cargo (hard but containable)
        radius = float(cargo_config.get("radius", 0.15))
        density = float(cargo_config.get("density", 260.0))  # Heavier
        friction = float(cargo_config.get("friction", 0.28))  # Slipperier (extreme)
        cargo_rest = cargo_config.get("restitution", terrain_config.get("cargo_restitution", None))
        restitution = float(cargo_rest if cargo_rest is not None else 0.12)
        # Harness stages inject terrain_config["target_rng_seed"] for reproducibility; cargo may override with cargo["seed"].
        seed = int(cargo_config.get("seed", terrain_config.get("target_rng_seed", 42)))
        random.seed(seed)
        boat = self._terrain_bodies["boat"]
        bx, by = boat.position.x, boat.position.y
        # Match hull half-width (boat fixture uses boat_width / 2 = 1.5 m).
        boat_half_w = 1.5
        boat_top_y = by + 0.2
        for i in range(n_cargo):
            ox = random.uniform(-boat_half_w + radius, boat_half_w - radius)
            oy = random.uniform(0.0, 0.55)
            x = bx + ox
            y = boat_top_y + oy + radius
            body = self._world.CreateDynamicBody(
                position=(x, y),
                fixtures=Box2D.b2FixtureDef(
                    shape=circleShape(radius=radius),
                    density=density,
                    friction=friction,
                    restitution=restitution,
                ),
            )
            ld = cargo_config.get("linear_damping", terrain_config.get("cargo_linear_damping", None))
            body.linearDamping = float(ld) if ld is not None else self._default_linear_damping
            ad = cargo_config.get("angular_damping", terrain_config.get("cargo_angular_damping", None))
            body.angularDamping = float(ad) if ad is not None else self._default_angular_damping
            self._cargo.append(body)
        self._initial_cargo_count = len(self._cargo)

    # --- Physical constraint constants (beam clamp only; build zone and mass are set in __init__ from terrain_config) ---
    MIN_BEAM_SIZE = 0.1
    MAX_BEAM_SIZE = 1.0

    @staticmethod
    def _beam_rect_corners_world(center_x, center_y, half_w, half_h, angle_rad):
        """World-space vertices of a centered rectangle (half extents) rotated by angle_rad."""
        ca, sa = math.cos(angle_rad), math.sin(angle_rad)
        corners = []
        for lx, ly in ((half_w, half_h), (-half_w, half_h), (-half_w, -half_h), (half_w, -half_h)):
            wx = center_x + lx * ca - ly * sa
            wy = center_y + lx * sa + ly * ca
            corners.append((wx, wy))
        return corners

    @staticmethod
    def _weld_reaction_force_torque(joint, inv_dt: float) -> tuple[float, float]:
        """Best-effort reaction force magnitude and |torque| (N, N·m) for weld break logic."""
        force = 0.0
        torque = 0.0
        try:
            rf = joint.GetReactionForce(inv_dt)
            if hasattr(rf, "length"):
                force = float(rf.length)
            elif hasattr(rf, "x") and hasattr(rf, "y"):
                force = math.hypot(float(rf.x), float(rf.y))
            else:
                force = math.hypot(float(rf[0]), float(rf[1]))
        except (AttributeError, TypeError, ValueError, IndexError):
            force = 0.0
        try:
            torque = abs(float(joint.GetReactionTorque(inv_dt)))
        except (AttributeError, TypeError, ValueError):
            torque = 0.0
        return force, torque

    def _beam_footprint_outside_build_zone(self, center_x, center_y, width, height, angle_rad):
        """True if any rectangle corner lies outside the inclusive build zone (matches design-check semantics)."""
        hw, hh = width / 2.0, height / 2.0
        for wx, wy in self._beam_rect_corners_world(center_x, center_y, hw, hh, angle_rad):
            if not (
                self.BUILD_ZONE_X_MIN <= wx <= self.BUILD_ZONE_X_MAX
                and self.BUILD_ZONE_Y_MIN <= wy <= self.BUILD_ZONE_Y_MAX
            ):
                return True, wx, wy
        return False, None, None

    def add_beam(self, x, y, width, height, angle=0, density=150.0):
        """API: Add a beam (e.g. rail, tie to secure cargo)."""
        if not (
            self.BUILD_ZONE_X_MIN <= x <= self.BUILD_ZONE_X_MAX
            and self.BUILD_ZONE_Y_MIN <= y <= self.BUILD_ZONE_Y_MAX
        ):
            raise ValueError(
                "add_beam: beam center must lie inside the build zone "
                f"x=[{self.BUILD_ZONE_X_MIN}, {self.BUILD_ZONE_X_MAX}], "
                f"y=[{self.BUILD_ZONE_Y_MIN}, {self.BUILD_ZONE_Y_MAX}] "
                f"(got ({x:.3f}, {y:.3f}))."
            )
        width = max(self.MIN_BEAM_SIZE, min(width, self.MAX_BEAM_SIZE))
        height = max(self.MIN_BEAM_SIZE, min(height, self.MAX_BEAM_SIZE))
        bad, vx, vy = self._beam_footprint_outside_build_zone(x, y, width, height, angle)
        if bad:
            raise ValueError(
                "add_beam: beam rectangle footprint extends outside the build zone "
                f"(e.g. corner at ({vx:.3f}, {vy:.3f})); "
                f"allowed x=[{self.BUILD_ZONE_X_MIN}, {self.BUILD_ZONE_X_MAX}], "
                f"y=[{self.BUILD_ZONE_Y_MIN}, {self.BUILD_ZONE_Y_MAX}] "
                f"(center ({x:.3f}, {y:.3f}), size {width:.3f}×{height:.3f} m, angle {angle:.3f} rad)."
            )
        body = self._world.CreateDynamicBody(
            position=(x, y),
            angle=angle,
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(width / 2, height / 2)),
                density=density,
                friction=self.DECK_FRICTION,
            ),
        )
        body.linearDamping = self._default_linear_damping
        body.angularDamping = self._default_angular_damping
        self._bodies.append(body)
        return body

    def add_joint(self, body_a, body_b, anchor_point, type='rigid'):
        """API: Add a joint. body_b can be None to weld body_a to the boat hull at anchor_point."""
        if body_a is None:
            raise ValueError("add_joint: body_a cannot be None.")
        anchor_x, anchor_y = anchor_point[0], anchor_point[1]
        if not (
            self.BUILD_ZONE_X_MIN <= anchor_x <= self.BUILD_ZONE_X_MAX
            and self.BUILD_ZONE_Y_MIN <= anchor_y <= self.BUILD_ZONE_Y_MAX
        ):
            raise ValueError(
                "add_joint: weld anchor must lie inside build zone "
                f"x=[{self.BUILD_ZONE_X_MIN}, {self.BUILD_ZONE_X_MAX}], "
                f"y=[{self.BUILD_ZONE_Y_MIN}, {self.BUILD_ZONE_Y_MAX}] "
                f"(got ({anchor_x:.3f}, {anchor_y:.3f}))."
            )
        if body_b is None:
            boat = self._terrain_bodies.get("boat")
            if not boat:
                raise ValueError("add_joint: boat not found for hull attachment.")
            body_b = boat
        if type != "rigid":
            raise ValueError("add_joint: only type='rigid' (weld) is supported for F-05.")
        joint = self._world.CreateWeldJoint(
            bodyA=body_a,
            bodyB=body_b,
            anchor=(anchor_x, anchor_y),
            collideConnected=False
        )
        # Declared world anchor for design checks (native anchors can disagree slightly before stepping).
        setattr(joint, "_f05_declared_anchor_world", (float(anchor_x), float(anchor_y)))
        self._joints.append(joint)
        return joint

    def get_structure_mass(self):
        """API: Total mass of added structure (beams)."""
        return sum(b.mass for b in self._bodies)

    def set_material_properties(self, body, restitution=0.1):
        """API: Set restitution for a body."""
        for fixture in body.fixtures:
            fixture.restitution = float(restitution)

    def step(self, time_step):
        """Physics step: buoyancy, multi-mode waves, gusts, lateral wind, hull roll-restoring torque."""
        boat = self._terrain_bodies.get("boat")
        if boat and boat.active:
            x, y = boat.position.x, boat.position.y
            if self.WATER_X_MIN <= x <= self.WATER_X_MAX and y <= self.WATER_SURFACE_Y + 1.0:
                g = abs(self._world.gravity[1]) if len(self._world.gravity) > 1 else 10.0
                effective_mass = boat.mass + sum(b.mass for b in self._bodies) + sum(c.mass for c in self._cargo if c.active)
                ref_y = self.WATER_SURFACE_Y + 0.5
                buoyancy = 1.5 * effective_mass * g * (ref_y - y)
                buoyancy = max(0.0, buoyancy)
                boat.ApplyForceToCenter((0, buoyancy), wake=True)
                # Multi-mode waves
                wave_fy = self._wave_amplitude * math.sin(self._wave_omega * self._sim_time)
                wave_fy += self._wave2_amplitude * math.sin(self._wave2_omega * self._sim_time + 0.7)
                step_int = int(self._sim_time / time_step + 0.5)
                if step_int > 0 and step_int % self._gust_interval == 0:
                    wave_fy += self._gust_amplitude * (1.0 if (step_int // self._gust_interval) % 2 == 0 else -1.0)
                boat.ApplyForceToCenter((0, wave_fy), wake=True)
                # Rogue wave: primary every rogue_interval steps; secondary rogue_double_step steps after each primary
                ri = self._rogue_interval
                rd = self._rogue_double_step
                if step_int > 0 and step_int % ri == 0:
                    boat.ApplyForceToCenter((0, self._rogue_amplitude), wake=True)
                if step_int > rd and (step_int - rd) % ri == 0:
                    boat.ApplyForceToCenter((0, self._rogue_amplitude * 0.6), wake=True)
                # Lateral impulse (sudden gust)
                if step_int > 0 and step_int % self._lateral_impulse_interval == 0:
                    sign = 1.0 if (step_int // self._lateral_impulse_interval) % 2 == 0 else -1.0
                    boat.ApplyForceToCenter((sign * self._lateral_impulse_amplitude, 0), wake=True)
                # Lateral wind
                wind_fx = self._wind_amplitude * math.sin(self._wind_omega * self._sim_time)
                boat.ApplyForceToCenter((wind_fx, 0), wake=True)
                # Water current: pushes boat away from x=15 (stronger when farther from center)
                current_fx = self._current_strength * (x - 15.0)
                boat.ApplyForceToCenter((current_fx, 0), wake=True)
                # Roll-restoring torque (−restoring_coeff·θ); coefficient from terrain_config
                boat.ApplyTorque(-self._restoring_coeff * boat.angle, wake=True)
                # Impulsive roll kicks (confused seas); discovered through sudden capsize / cargo chatter
                if self._hull_roll_impulse_amplitude > 0.0 and step_int > 0:
                    if step_int % self._hull_roll_impulse_interval == 0:
                        sign = 1.0 if (step_int // self._hull_roll_impulse_interval) % 2 == 0 else -1.0
                        boat.ApplyAngularImpulse(sign * self._hull_roll_impulse_amplitude, wake=True)
        for c in self._cargo:
            if c.active:
                cx, cy = c.position.x, c.position.y
                if self.WATER_X_MIN <= cx <= self.WATER_X_MAX and cy < self.WATER_SURFACE_Y:
                    g = abs(self._world.gravity[1]) if len(self._world.gravity) > 1 else 10.0
                    buoyancy = 0.5 * c.mass * g
                    c.ApplyForceToCenter((0, buoyancy), wake=True)
        self._sim_time += time_step
        self._world.Step(time_step, 10, 10)

        # Break joints if force/torque exceeds limit (fragile anchor points)
        if self.JOINT_MAX_FORCE < float('inf'):
            broken_joints = []
            inv_dt = 1.0 / time_step
            for j in list(self._joints):
                force, torque = self._weld_reaction_force_torque(j, inv_dt)
                if force > self.JOINT_MAX_FORCE or torque > self.JOINT_MAX_FORCE * 0.4:
                    broken_joints.append(j)
            for j in broken_joints:
                if j in self._joints:
                    self._world.DestroyJoint(j)
                    self._joints.remove(j)

        self._physics_steps_done += 1
        # After grace period, track worst roll and cargo loss-plane crossings (spawn/settle chatter).
        if self._physics_steps_done > self._cargo_loss_grace_steps:
            boat_after = self._terrain_bodies.get("boat")
            if boat_after and boat_after.active:
                self._peak_abs_boat_angle_rad = max(
                    self._peak_abs_boat_angle_rad, abs(float(boat_after.angle))
                )
            for c in self._cargo:
                if c.active and c.position.y < self.CARGO_WATER_Y:
                    self._cargo_ever_below_loss_plane = True

    def get_terrain_bounds(self):
        """Get terrain bounds for evaluation and rendering."""
        return {
            "water": {"x_min": self.WATER_X_MIN, "x_max": self.WATER_X_MAX, "surface_y": self.WATER_SURFACE_Y},
            "cargo_water_y": self.CARGO_WATER_Y,
            "boat_max_angle_rad": self.BOAT_MAX_ANGLE_RAD,
            "build_zone": {"x": [self.BUILD_ZONE_X_MIN, self.BUILD_ZONE_X_MAX],
                           "y": [self.BUILD_ZONE_Y_MIN, self.BUILD_ZONE_Y_MAX]},
        }

    def get_boat_body(self):
        return self._terrain_bodies.get("boat")

    def get_boat_position(self):
        """Boat center (x, y) for feedback and metrics."""
        boat = self.get_boat_body()
        if boat is None or not boat.active:
            return None
        return (boat.position.x, boat.position.y)

    def get_boat_angle(self):
        """Boat hull angle in radians (for capsize check)."""
        boat = self.get_boat_body()
        if boat is None or not boat.active:
            return None
        return boat.angle

    def get_initial_cargo_count(self):
        return self._initial_cargo_count

    def get_cargo_in_water_count(self):
        """Count cargo disks whose center is currently below the evaluator loss plane (y < CARGO_WATER_Y).

        Not "in water" in the visual sense: CARGO_WATER_Y may lie above the nominal free surface, so this
        can count particles that are still above y = WATER_SURFACE_Y. Name kept for API compatibility.
        """
        return sum(1 for c in self._cargo if c.active and c.position.y < self.CARGO_WATER_Y)

    def get_peak_abs_boat_angle_rad(self):
        """Largest |hull angle| observed so far this episode (radians)."""
        return float(self._peak_abs_boat_angle_rad)

    def get_cargo_ever_below_loss_plane(self) -> bool:
        """True if any cargo particle's center was ever below CARGO_WATER_Y this episode."""
        return bool(self._cargo_ever_below_loss_plane)
