import math
import random
from collections import deque
import Box2D
from Box2D.b2 import (
    world,
    polygonShape,
    staticBody,
    dynamicBody,
    revoluteJointDef,
    prismaticJointDef,
)

# --- Configuration & Constants ---
FPS = 60
TIME_STEP = 1.0 / FPS

# Baseline Physical Params
CART_MASS = 10.0
POLE_MASS = 1.0
POLE_LENGTH = 2.0
POLE_WIDTH = 0.2

TRACK_CENTER_X = 10.0
SAFE_HALF_RANGE = 8.5 

BALANCE_ANGLE_RAD = 0.785 

class Sandbox:
    def __init__(self, terrain_config=None, physics_config=None, **kwargs):
        self.terrain_config = terrain_config or {}
        self.physics_config = physics_config or {}
        self.world = world(gravity=(0, -10.0), doSleep=True)
        self._terrain_bodies = {}
        self.TRACK_CENTER_X = TRACK_CENTER_X
        self.SAFE_HALF_RANGE = SAFE_HALF_RANGE
        self._apply_configs()
        self._create_environment()
        self._step_count = 0
        self._last_applied_force = 0.0
        
        # Sensor delay buffers
        self._angle_buffer = deque([self._initial_angle] * (self._sensor_delay_angle + 1), maxlen=self._sensor_delay_angle + 1)
        self._omega_buffer = deque([0.0] * (self._sensor_delay_omega + 1), maxlen=self._sensor_delay_omega + 1)

    def _apply_configs(self):
        pc = self.physics_config
        if "gravity" in pc: self.world.gravity = (0, -pc["gravity"])
        self._initial_angle = pc.get("pole_start_angle", 0.0 if not self.physics_config else math.pi)
        self._cart_mass = pc.get("cart_mass", CART_MASS)
        self._pole_length = pc.get("pole_length", POLE_LENGTH)
        self._sensor_delay_angle = pc.get("sensor_delay_angle_steps", 0)
        self._sensor_delay_omega = pc.get("sensor_delay_omega_steps", 0)

    def _create_environment(self):
        cart = self.world.CreateDynamicBody(position=(self.TRACK_CENTER_X, 2.0))
        cart.CreatePolygonFixture(box=(0.5, 0.25), density=self._cart_mass/0.5)
        self._terrain_bodies["cart"] = cart
        ground = self.world.CreateStaticBody(position=(0, 0))
        self.world.CreatePrismaticJoint(bodyA=ground, bodyB=cart, anchor=cart.position, axis=(1, 0), lowerTranslation=-self.SAFE_HALF_RANGE, upperTranslation=self.SAFE_HALF_RANGE, enableLimit=True)
        pole = self.world.CreateDynamicBody(position=(self.TRACK_CENTER_X, 2.0 + self._pole_length/2), angle=self._initial_angle)
        pole.CreatePolygonFixture(box=(0.1, self._pole_length/2), density=1.0)
        self._terrain_bodies["pole"] = pole
        self.world.CreateRevoluteJoint(bodyA=cart, bodyB=pole, anchor=(self.TRACK_CENTER_X, 2.0))

    def step(self, dt):
        # Update delay buffers BEFORE stepping to store current state
        true_angle = self.get_true_pole_angle()
        true_omega = self._terrain_bodies["pole"].angularVelocity if "pole" in self._terrain_bodies else 0.0
        self._angle_buffer.append(true_angle)
        self._omega_buffer.append(true_omega)

        self._step_count += 1
        cart = self._terrain_bodies["cart"]
        cart.ApplyForce((self._last_applied_force, 0), cart.position, True)
        self.world.Step(TIME_STEP, 8, 3)

    def get_true_pole_angle(self):
        p = self._terrain_bodies.get("pole")
        return math.atan2(math.sin(p.angle), math.cos(p.angle)) if p else 0.0

    def get_pole_angle(self):
        if not self._angle_buffer:
            return self.get_true_pole_angle()
        return self._angle_buffer[0] # The oldest in buffer (which is limited by maxlen)

    def get_pole_angular_velocity(self):
        if not self._omega_buffer:
            return self._terrain_bodies["pole"].angularVelocity if "pole" in self._terrain_bodies else 0.0
        return self._omega_buffer[0]
    def get_cart_position(self): return self._terrain_bodies["cart"].position.x
    def get_cart_velocity(self): return self._terrain_bodies["cart"].linearVelocity.x
    def apply_cart_force(self, f): self._last_applied_force = f
    def get_terrain_bounds(self):
        return {"track_center_x": self.TRACK_CENTER_X, "safe_half_range": self.SAFE_HALF_RANGE}

    def get_cart_body(self): return self._terrain_bodies.get("cart")
    def get_pole_body(self): return self._terrain_bodies.get("pole")
