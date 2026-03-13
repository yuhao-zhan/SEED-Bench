"""
D-04: The Swing task environment module
Pivot, swing (rope + seat), target zone, build zone.
Mechanics: parametric resonance, swing period. External disturbance: wind (periodic + gusts).
"""
import math
import random
import Box2D
from Box2D.b2 import (
    world,
    polygonShape,
    circleShape,
    staticBody,
    dynamicBody,
    revoluteJoint,
    weldJoint,
    distanceJointDef,
)


class Sandbox:
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
        self._create_swing(terrain_config)
        self._define_target(terrain_config)
        self.BUILD_ZONE_X_MIN = float(terrain_config.get("build_zone_x_min", 6.0))
        self.BUILD_ZONE_X_MAX = float(terrain_config.get("build_zone_x_max", 14.0))
        self.BUILD_ZONE_Y_MIN = float(terrain_config.get("build_zone_y_min", 4.0))
        self.BUILD_ZONE_Y_MAX = float(terrain_config.get("build_zone_y_max", 10.0))
        self.MAX_STRUCTURE_MASS = float(terrain_config.get("max_structure_mass", 100.0))
        self.MAX_PUMP_FORCE = float(terrain_config.get("max_pump_force", 42.0))
        # Wind: periodic + random gusts (applied to swing seat each step)
        self._wind_strength = float(terrain_config.get("wind_strength", 12.0))  # N
        self._wind_period = float(terrain_config.get("wind_period", 2.8))
        self._gust_prob = float(terrain_config.get("gust_prob", 0.04))
        self._gust_force = float(terrain_config.get("gust_force", 20.0))
        self._sim_time = 0.0
        self._wind_enabled = terrain_config.get("wind_enabled", True)

    def _create_terrain(self, terrain_config: dict):
        ground_len = 30.0
        ground_h = 0.5
        ground = self._world.CreateStaticBody(
            position=(ground_len / 2, ground_h / 2),
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(ground_len / 2, ground_h / 2)),
                friction=0.6,
            ),
        )
        self._terrain_bodies["ground"] = ground
        self._ground_y = ground_h
        pivot_x = float(terrain_config.get("pivot_x", 10.0))
        pivot_y = float(terrain_config.get("pivot_y", 10.0))
        pivot = self._world.CreateStaticBody(position=(pivot_x, pivot_y))
        pivot.CreateFixture(shape=circleShape(radius=0.2), density=0, friction=0)
        self._terrain_bodies["pivot"] = pivot
        self._pivot_x = pivot_x
        self._pivot_y = pivot_y

    def _create_swing(self, terrain_config: dict):
        pivot_x = self._pivot_x
        pivot_y = self._pivot_y
        rope_length = float(terrain_config.get("rope_length", 4.0))
        seat_x = pivot_x
        seat_y = pivot_y - rope_length
        seat_radius = 0.3
        seat_density = float(terrain_config.get("seat_density", 35.0))
        seat_linear_damping = float(terrain_config.get("seat_linear_damping", 0.1))
        seat_angular_damping = float(terrain_config.get("seat_angular_damping", 0.1))
        seat = self._world.CreateDynamicBody(
            position=(seat_x, seat_y),
            fixtures=Box2D.b2FixtureDef(
                shape=circleShape(radius=seat_radius),
                density=seat_density,
                friction=0.3,
                restitution=0.1,
            ),
        )
        seat.linearDamping = seat_linear_damping
        seat.angularDamping = seat_angular_damping
        self._terrain_bodies["swing_seat"] = seat
        pivot_body = self._terrain_bodies["pivot"]
        defn = distanceJointDef()
        defn.bodyA = pivot_body
        defn.bodyB = seat
        defn.localAnchorA = pivot_body.GetLocalPoint((pivot_x, pivot_y))
        defn.localAnchorB = seat.GetLocalPoint((seat_x, seat_y))
        defn.length = rope_length
        defn.collideConnected = False
        self._world.CreateJoint(defn)

    def _define_target(self, terrain_config: dict):
        self._target_y_min = float(terrain_config.get("target_y_min", 11.7))
        self._target_x_min = float(terrain_config.get("target_x_min", 9.35))
        self._target_x_max = float(terrain_config.get("target_x_max", 10.65))

    MIN_BEAM_SIZE = 0.1
    MAX_BEAM_SIZE = 3.0

    def add_beam(self, x, y, width, height, angle=0, density=1.0):
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

    def add_joint(self, body_a, body_b, anchor_point, type="rigid"):
        if body_a is None:
            raise ValueError("add_joint: body_a cannot be None.")
        anchor_x, anchor_y = anchor_point[0], anchor_point[1]
        if body_b is None:
            body_b = self._terrain_bodies.get("ground")
            if body_b is None:
                raise ValueError("add_joint: Cannot anchor to ground.")
        if type == "rigid":
            joint = self._world.CreateWeldJoint(
                bodyA=body_a, bodyB=body_b,
                anchor=(anchor_x, anchor_y), collideConnected=False,
            )
        elif type == "pivot":
            joint = self._world.CreateRevoluteJoint(
                bodyA=body_a, bodyB=body_b,
                anchor=(anchor_x, anchor_y), collideConnected=False,
            )
        else:
            raise ValueError(f"Unknown joint type: {type}")
        self._joints.append(joint)
        return joint

    def get_structure_mass(self):
        return sum(b.mass for b in self._bodies)

    def set_material_properties(self, body, restitution=0.2):
        for fixture in body.fixtures:
            fixture.restitution = float(restitution)

    def step(self, time_step):
        # Apply wind to swing seat before physics step (external disturbance)
        seat = self._terrain_bodies.get("swing_seat")
        if self._wind_enabled and seat is not None:
            # Periodic wind: F_x = wind_strength * sin(2*pi*t/T)
            if self._wind_period == 0:
                wind_fx = self._wind_strength
            else:
                wind_fx = self._wind_strength * math.sin(2.0 * math.pi * self._sim_time / self._wind_period)
            
            # Random gust (impulse-like)
            if random.random() < self._gust_prob:
                wind_fx += self._gust_force * (1 if random.random() > 0.5 else -1)
            try:
                seat.ApplyForceToCenter((wind_fx, 0.0), True)
            except TypeError:
                seat.ApplyForceToCenter((wind_fx, 0.0), wake=True)

        # Apply quadratic damping if configured
        qd = self._terrain_config.get("quadratic_damping", 0.0)
        if qd > 0.0 and seat is not None:
            vx, vy = seat.linearVelocity.x, seat.linearVelocity.y
            speed_sq = vx**2 + vy**2
            speed = math.sqrt(speed_sq)
            if speed > 0:
                drag_mag = qd * speed_sq
                drag_fx = -drag_mag * (vx / speed)
                drag_fy = -drag_mag * (vy / speed)
                try:
                    seat.ApplyForceToCenter((drag_fx, drag_fy), True)
                except TypeError:
                    seat.ApplyForceToCenter((drag_fx, drag_fy), wake=True)

        self._sim_time += time_step
        self._world.Step(time_step, 10, 10)

    def get_terrain_bounds(self):
        return {
            "ground_y": self._ground_y,
            "pivot_x": self._pivot_x,
            "pivot_y": self._pivot_y,
            "target_y_min": self._target_y_min,
            "target_x_min": self._target_x_min,
            "target_x_max": self._target_x_max,
            "max_pump_force": getattr(self, "MAX_PUMP_FORCE", 42.0),
            "build_zone": {
                "x": [self.BUILD_ZONE_X_MIN, self.BUILD_ZONE_X_MAX],
                "y": [self.BUILD_ZONE_Y_MIN, self.BUILD_ZONE_Y_MAX],
            },
        }

    def get_swing_seat_position(self):
        s = self._terrain_bodies.get("swing_seat")
        return (s.position.x, s.position.y) if s else None

    def get_swing_seat_velocity(self):
        s = self._terrain_bodies.get("swing_seat")
        return (s.linearVelocity.x, s.linearVelocity.y) if s else None

    def get_wind_force_at_time(self, sim_time):
        """Return horizontal wind force (N) that would be applied at given sim_time (no gust). For wind-aware control."""
        if not self._wind_enabled:
            return 0.0
        if self._wind_period == 0:
            return self._wind_strength
        return self._wind_strength * math.sin(2.0 * math.pi * sim_time / self._wind_period)

    def get_swing_seat(self):
        """Return swing seat body for control."""
        return self._terrain_bodies.get("swing_seat")

    def apply_force_to_seat(self, fx, fy):
        """Apply force (N) to swing seat. Call in agent_action for pumping. |fx| <= MAX_PUMP_FORCE."""
        seat = self._terrain_bodies.get("swing_seat")
        if seat is not None:
            # Clamp force to MAX_PUMP_FORCE
            max_f = getattr(self, "MAX_PUMP_FORCE", 42.0)
            fx = max(-max_f, min(max_f, float(fx)))
            fy = max(-max_f, min(max_f, float(fy)))
            
            # Apply task-specific mutations
            fault = self._terrain_config.get("actuator_fault")
            if fault == "right_only" and fx < 0: fx = 0.0
            if fault == "left_only" and fx > 0: fx = 0.0

            dead_zone = self._terrain_config.get("dead_zone")
            if dead_zone:
                if dead_zone[0] <= seat.position.x <= dead_zone[1]:
                    fx = 0.0
                    fy = 0.0

            try:
                seat.ApplyForceToCenter((fx, fy), True)
            except TypeError:
                seat.ApplyForceToCenter((fx, fy), wake=True)

    def apply_impulse_to_seat(self, ix, iy):
        """Apply impulse (N·s) to swing seat. Call in agent_action for initial kick."""
        seat = self._terrain_bodies.get("swing_seat")
        if seat is not None:
            max_i = getattr(self, "MAX_PUMP_FORCE", 42.0) * 0.1 # Very small to prevent impulse exploit
            ix = max(-max_i, min(max_i, float(ix)))
            iy = max(-max_i, min(max_i, float(iy)))
            
            # Apply task-specific mutations
            fault = self._terrain_config.get("actuator_fault")
            if fault == "right_only" and ix < 0: ix = 0.0
            if fault == "left_only" and ix > 0: ix = 0.0

            dead_zone = self._terrain_config.get("dead_zone")
            if dead_zone:
                if dead_zone[0] <= seat.position.x <= dead_zone[1]:
                    ix = 0.0
                    iy = 0.0

            try:
                seat.ApplyLinearImpulse((ix, iy), seat.worldCenter, True)
            except TypeError:
                seat.ApplyLinearImpulse((ix, iy), seat.worldCenter, wake=True)

    def get_sim_time(self):
        """Return current simulation time in seconds."""
        return self._sim_time
