"""
F-02: The Amphibian task environment module
Defines physics world, terrain (left bank, water zone, right bank), buoyancy, API.
Mechanics: buoyancy, paddling propulsion. Failure: sink, unable to reach shore.
"""
import Box2D
from Box2D.b2 import (world, polygonShape, circleShape, staticBody, dynamicBody, weldJoint)
import math


class Sandbox:
    """Sandbox environment wrapper for F-02: The Amphibian"""

    def __init__(self, *, terrain_config=None, physics_config=None):
        terrain_config = terrain_config or {}
        physics_config = physics_config or {}
        self._terrain_config = dict(terrain_config)
        self._physics_config = dict(physics_config)

        gravity = tuple(physics_config.get("gravity", (0, -10)))
        self._default_linear_damping = float(physics_config.get("linear_damping", 0.0))
        self._default_angular_damping = float(physics_config.get("angular_damping", 0.0))

        self._world = world(gravity=gravity, doSleep=True)
        self._bodies = []
        self._joints = []
        self._terrain_bodies = {}

        self.world = self._world
        self.bodies = self._bodies
        self.joints = self._joints

        self._create_terrain(terrain_config)

        # Water zone and targets (set before any agent build)
        self.WATER_X_LEFT = 10.0
        self.WATER_X_RIGHT = 24.0
        self.WATER_SURFACE_Y = 2.0
        self.WATER_BOTTOM_Y = 0.0
        self.TARGET_X = 26.0
        self.BUILD_ZONE_X_MIN = 2.0
        self.BUILD_ZONE_X_MAX = 8.0
        self.BUILD_ZONE_Y_MIN = 0.0
        self.BUILD_ZONE_Y_MAX = 4.0
        self.MAX_STRUCTURE_MASS = float(terrain_config.get("max_structure_mass", 600.0))
        self.LEFT_BANK_X_MAX = 10.0
        self.RIGHT_BANK_X_MIN = 24.0
        liquid_density = float(terrain_config.get("liquid_density", 1000.0))
        self._buoyancy_factor = min(1.5, (liquid_density / 1000.0) * 0.8)
        self._step_count = 0
        # Hard obstacles: strong opposing current, quadratic drag, lateral wind, deep channel
        self._current_per_kg = float(terrain_config.get("current_per_kg", 5.5))
        self._water_drag_coef = float(terrain_config.get("water_drag_coef", 115.0))
        self._wind_amplitude = float(terrain_config.get("wind_amplitude", 200.0))
        self._wind_period_steps = int(terrain_config.get("wind_period_steps", 90))
        self._wind_x_left = 12.0
        self._wind_x_right = 22.0
        self._deep_channel_x_left = 16.5
        self._deep_channel_x_right = 19.5
        self._deep_channel_buoyancy_scale = 0.35

    def _create_terrain(self, terrain_config: dict):
        """
        Create terrain: continuous floor, water zone (sensor for drawing and buoyancy region).
        Left bank: x < 10. Water: x in [10, 24], y in [0, 2]. Right bank: x > 24.
        """
        floor_length = 35.0
        floor_height = 0.3
        floor = self._world.CreateStaticBody(
            position=(floor_length / 2, -floor_height / 2),
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(floor_length / 2, floor_height / 2)),
                friction=0.6,
            ),
        )
        self._terrain_bodies["floor"] = floor

        water_width = 14.0
        water_center_x = 17.0
        water_height = 2.0
        water_body = self._world.CreateStaticBody(
            position=(water_center_x, water_height / 2),
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(water_width / 2, water_height / 2)),
                friction=0.0,
                isSensor=True,
            ),
        )
        self._terrain_bodies["water"] = water_body

        # Obstacles: three pillars in water (vehicle must steer around or rise over)
        pillar_radius = float(terrain_config.get("pillar_radius", 0.46))
        pillar_positions = [(14.0, 0.88), (17.0, 0.90), (20.0, 0.92)]
        for i, (px, py) in enumerate(pillar_positions):
            pillar = self._world.CreateStaticBody(
                position=(px, py),
                fixtures=Box2D.b2FixtureDef(
                    shape=circleShape(radius=pillar_radius),
                    friction=0.4,
                ),
            )
            self._terrain_bodies[f"pillar_{i}"] = pillar
        self._pillar_positions = pillar_positions
        self._pillar_radius = pillar_radius

        # Headwind burst: extra opposing force in mid-water (x 15-19) so crossing is harder
        self._headwind_burst_x_left = 15.0
        self._headwind_burst_x_right = 19.0
        self._headwind_burst_per_kg = float(terrain_config.get("headwind_burst_per_kg", 0.8))

        # Propulsion cooldown: each body can only apply thrust every N steps (paddle stroke)
        self._thrust_cooldown_steps = int(terrain_config.get("thrust_cooldown_steps", 3))
        self._last_thrust_step = {}  # body id -> last step that applied thrust
        self._current_step = 0  # set by main loop before agent_action for cooldown

    # --- Physical constraint constants ---
    MIN_BEAM_SIZE = 0.15
    MAX_BEAM_SIZE = 2.0
    BUILD_ZONE_X_MIN = 2.0
    BUILD_ZONE_X_MAX = 8.0
    BUILD_ZONE_Y_MIN = 0.0
    BUILD_ZONE_Y_MAX = 4.0
    MAX_STRUCTURE_MASS = 600.0

    def add_beam(self, x, y, width, height, angle=0, density=200.0):
        """API: Add a beam (rigid rectangular element for the amphibian vehicle)."""
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
            body_b = self._terrain_bodies.get("floor")
            if body_b is None:
                raise ValueError("add_joint: floor not found for anchor.")
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
        """API: Total mass of the vehicle (all created beams)."""
        total_mass = 0.0
        for body in self._bodies:
            total_mass += body.mass
        return total_mass

    def set_material_properties(self, body, restitution=0.1):
        """API: Set restitution for a body."""
        for fixture in body.fixtures:
            fixture.restitution = float(restitution)

    # Propulsion limit: max thrust per body per step (single paddle cannot overcome current)
    _MAX_THRUST_PER_BODY = 520.0

    def apply_force(self, body, force_x, force_y, step_count=None):
        """API: Apply a force to a body (e.g. for paddling). Capped per-body. Cooldown: each body can thrust only every _thrust_cooldown_steps steps (uses step_count or env._current_step)."""
        if body is not None and body.active:
            step = step_count if step_count is not None else getattr(self, '_current_step', 0)
            if self._thrust_cooldown_steps > 0:
                bid = id(body)
                last = self._last_thrust_step.get(bid, -999)
                if step - last < self._thrust_cooldown_steps:
                    return  # cooldown: skip this body this step
                self._last_thrust_step[bid] = step
            fx, fy = float(force_x), float(force_y)
            mag = math.sqrt(fx * fx + fy * fy)
            if mag > self._MAX_THRUST_PER_BODY:
                scale = self._MAX_THRUST_PER_BODY / mag
                fx, fy = fx * scale, fy * scale
            body.ApplyForceToCenter((fx, fy), wake=True)

    # Cap vehicle velocity to prevent tunneling / explosion (buoyancy can cause large impulses)
    _MAX_LINEAR_SPEED = 4.0

    def step(self, time_step):
        """Physics step: buoyancy, opposing current, drag, wind, deep channel."""
        self._step_count += 1
        # Clamp vehicle speeds before Step to avoid tunneling
        for body in self._bodies:
            if not body.active:
                continue
            vx, vy = body.linearVelocity.x, body.linearVelocity.y
            speed = math.sqrt(vx * vx + vy * vy)
            if speed > self._MAX_LINEAR_SPEED:
                scale = self._MAX_LINEAR_SPEED / speed
                body.linearVelocity = (vx * scale, vy * scale)
        for body in self._bodies:
            if not body.active:
                continue
            x, y = body.position.x, body.position.y
            vx, vy = body.linearVelocity.x, body.linearVelocity.y
            in_water = (self.WATER_X_LEFT <= x <= self.WATER_X_RIGHT and
                        self.WATER_BOTTOM_Y <= y <= self.WATER_SURFACE_Y)
            if in_water:
                submerged = self.WATER_SURFACE_Y - y
                g = abs(self._world.gravity[1]) if len(self._world.gravity) > 1 else 10.0
                bf = self._buoyancy_factor
                if self._deep_channel_x_left <= x <= self._deep_channel_x_right:
                    bf *= self._deep_channel_buoyancy_scale
                buoyancy_up = bf * submerged * body.mass * g
                body.ApplyForceToCenter((0, buoyancy_up), wake=True)
                # Opposing current (strong headwind in water)
                f_current = -self._current_per_kg * body.mass
                body.ApplyForceToCenter((f_current, 0), wake=True)
                # Quadratic drag in water (faster = much more resistance)
                speed = math.sqrt(vx * vx + vy * vy)
                if speed > 0.01:
                    drag_mag = self._water_drag_coef * speed * speed
                    drag_x = -drag_mag * (vx / speed)
                    drag_y = -drag_mag * (vy / speed)
                    body.ApplyForceToCenter((drag_x, drag_y), wake=True)
                # Lateral wind in mid-water (tips unstable rafts)
                if self._wind_x_left <= x <= self._wind_x_right:
                    phase = 2.0 * math.pi * self._step_count / self._wind_period_steps
                    f_wind_y = self._wind_amplitude * math.sin(phase)
                    body.ApplyForceToCenter((0, f_wind_y), wake=True)
                # Headwind burst: extra opposing force in mid-water (x 15-19)
                if self._headwind_burst_x_left <= x <= self._headwind_burst_x_right:
                    f_headwind = -self._headwind_burst_per_kg * body.mass
                    body.ApplyForceToCenter((f_headwind, 0), wake=True)
        self._world.Step(time_step, 10, 10)
        for body in self._bodies:
            if not body.active:
                continue
            vx, vy = body.linearVelocity.x, body.linearVelocity.y
            speed = math.sqrt(vx * vx + vy * vy)
            if speed > self._MAX_LINEAR_SPEED:
                scale = self._MAX_LINEAR_SPEED / speed
                body.linearVelocity = (vx * scale, vy * scale)

    def get_terrain_bounds(self):
        """Get terrain bounds for evaluation and rendering."""
        return {
            "left_bank": {"x_max": self.LEFT_BANK_X_MAX},
            "water": {"x_left": self.WATER_X_LEFT, "x_right": self.WATER_X_RIGHT,
                      "surface_y": self.WATER_SURFACE_Y, "bottom_y": self.WATER_BOTTOM_Y},
            "right_bank": {"x_min": self.RIGHT_BANK_X_MIN},
            "target_x": self.TARGET_X,
            "build_zone": {
                "x": [self.BUILD_ZONE_X_MIN, self.BUILD_ZONE_X_MAX],
                "y": [self.BUILD_ZONE_Y_MIN, self.BUILD_ZONE_Y_MAX],
            },
        }

    def get_vehicle_front_x(self):
        """Rightmost x among all vehicle bodies (front of amphibian)."""
        if not self._bodies:
            return None
        return max(b.position.x for b in self._bodies if b.active)

    def get_vehicle_lowest_y(self):
        """Lowest y among all vehicle bodies (for sink check)."""
        if not self._bodies:
            return None
        return min(b.position.y for b in self._bodies if b.active)

    def get_vehicle_velocity(self):
        """Velocity (vx, vy) of the front (rightmost) body for feedback."""
        if not self._bodies:
            return None
        front = max(self._bodies, key=lambda b: b.position.x if b.active else -1e9)
        if not front.active:
            return None
        return (front.linearVelocity.x, front.linearVelocity.y)
