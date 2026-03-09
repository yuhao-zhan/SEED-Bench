"""
F-05: The Boat task environment module
Defines physics world, water zone, boat (hull), cargo, wave excitation, API.
Mechanics: metacentric height, anti-capsize. Failure: cargo in water, boat capsizes.
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
        self.CARGO_WATER_Y = float(terrain_config.get("cargo_water_y", 1.98))  # Extreme: cargo lost if y < 1.98m
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

        self._create_terrain(terrain_config)
        
        # New mechanics: fragile joints and slippery deck
        self.DECK_FRICTION = float(terrain_config.get("deck_friction", 0.5))
        self.JOINT_MAX_FORCE = float(terrain_config.get("joint_max_force", float('inf')))

        self._create_boat(terrain_config)
        self._create_cargo(terrain_config)

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
        boat_y = 2.5
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
        seed = int(cargo_config.get("seed", 42))
        random.seed(seed)
        boat = self._terrain_bodies["boat"]
        bx, by = boat.position.x, boat.position.y
        boat_half_w = 1.2
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
                    restitution=0.12,
                ),
            )
            body.linearDamping = self._default_linear_damping
            body.angularDamping = self._default_angular_damping
            self._cargo.append(body)
        self._initial_cargo_count = len(self._cargo)

    # --- Physical constraint constants ---
    MIN_BEAM_SIZE = 0.1
    MAX_BEAM_SIZE = 1.0
    BUILD_ZONE_X_MIN = 12.0
    BUILD_ZONE_X_MAX = 18.0
    BUILD_ZONE_Y_MIN = 2.0
    BUILD_ZONE_Y_MAX = 4.5
    MAX_STRUCTURE_MASS = 60.0

    def add_beam(self, x, y, width, height, angle=0, density=150.0):
        """API: Add a beam (e.g. rail, tie to secure cargo)."""
        width = max(self.MIN_BEAM_SIZE, min(width, self.MAX_BEAM_SIZE))
        height = max(self.MIN_BEAM_SIZE, min(height, self.MAX_BEAM_SIZE))
        body = self._world.CreateDynamicBody(
            position=(x, y),
            angle=angle,
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(width / 2, height / 2)),
                density=density,
                friction=0.5,
            ),
        )
        body.linearDamping = self._default_linear_damping
        body.angularDamping = self._default_angular_damping
        self._bodies.append(body)
        return body

    def add_joint(self, body_a, body_b, anchor_point, type='rigid'):
        """API: Add a joint. body_b can be None to anchor to the floor."""
        if body_a is None:
            raise ValueError("add_joint: body_a cannot be None.")
        anchor_x, anchor_y = anchor_point[0], anchor_point[1]
        if body_b is None:
            boat = self._terrain_bodies.get("boat")
            if boat and self.BUILD_ZONE_X_MIN <= anchor_x <= self.BUILD_ZONE_X_MAX and self.BUILD_ZONE_Y_MIN <= anchor_y <= self.BUILD_ZONE_Y_MAX:
                body_b = boat
            else:
                body_b = self._terrain_bodies.get("floor")
            if body_b is None:
                raise ValueError("add_joint: floor or boat not found.")
        if type != 'rigid':
            type = 'rigid'
        joint = self._world.CreateWeldJoint(
            bodyA=body_a,
            bodyB=body_b,
            anchor=(anchor_x, anchor_y),
            collideConnected=False
        )
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
        """Physics step: buoyancy, multi-mode waves, gusts, lateral wind, weak restoring torque."""
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
                # Rogue wave: periodic large vertical impulse + second hit a few steps later
                if step_int > 0 and step_int % self._rogue_interval == 0:
                    boat.ApplyForceToCenter((0, self._rogue_amplitude), wake=True)
                if step_int > 0 and step_int % self._rogue_interval == self._rogue_double_step:
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
                # Weak restoring torque: design must provide stability
                boat.ApplyTorque(-self._restoring_coeff * boat.angle, wake=True)
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
            for j in list(self._joints):
                try:
                    # Get reaction force/torque at the end of the step
                    force = j.GetReactionForce(1.0 / time_step).length
                    torque = abs(j.GetReactionTorque(1.0 / time_step))
                    # Threshold for torque is scaled
                    if force > self.JOINT_MAX_FORCE or torque > self.JOINT_MAX_FORCE * 0.4:
                        broken_joints.append(j)
                except Exception:
                    continue
            for j in broken_joints:
                if j in self._joints:
                    self._world.DestroyJoint(j)
                    self._joints.remove(j)

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
        """Cargo with y < CARGO_WATER_Y counts as in water (lost)."""
        return sum(1 for c in self._cargo if c.active and c.position.y < self.CARGO_WATER_Y)
