"""
C-01: Cart-Pole Swing-up then Balance (Standard Benchmark).
Slightly reduced difficulty for baseline to ensure reference solution success.
"""

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
    """
    Sandbox for C-01: Cart-Pole.
    """
    def __init__(self, terrain_config=None, physics_config=None):
        self.terrain_config = terrain_config or {}
        self.physics_config = physics_config or {}

        # Initialization
        self.world = world(gravity=(0, -10.0), doSleep=True)
        self._terrain_bodies = {}
        self._joints = []
        
        self.TRACK_CENTER_X = TRACK_CENTER_X
        self.SAFE_HALF_RANGE = SAFE_HALF_RANGE

        self._apply_configs()
        self._create_environment()
        
        _max_delay = max(self._sensor_delay_angle_steps, self._sensor_delay_omega_steps, 1)
        self._sensor_buffer = deque(maxlen=_max_delay)
        self._sensor_buffer.append((self._get_true_pole_angle(), self._get_true_pole_omega()))
        self._step_count = 0
        self._last_applied_force = 0.0

    def _apply_configs(self):
        pc = self.physics_config
        if "gravity" in pc:
            self.world.gravity = pc["gravity"]
        
        # In baseline, no delay and no noise
        if not self.physics_config:
            self._sensor_delay_angle_steps = 0
            self._sensor_delay_omega_steps = 0
            self._sensor_noise_angle_std = 0.0
            self._sensor_noise_omega_std = 0.0
            self._sensor_angle_bias = 0.0
        else:
            self._sensor_delay_angle_steps = pc.get("sensor_delay_angle_steps", 6)
            self._sensor_delay_omega_steps = pc.get("sensor_delay_omega_steps", 10)
            self._sensor_noise_angle_std = 0.015
            self._sensor_noise_omega_std = 0.03
            self._sensor_angle_bias = 0.018
            
        self._actuator_delay_steps = pc.get("actuator_delay_steps", 0)
        self._actuator_rate_limit = pc.get("actuator_rate_limit", None)
        self._angular_damping = pc.get("angular_damping", 0.0)
        self._linear_damping = pc.get("linear_damping", 0.0)

        tc = self.terrain_config
        self._cart_mass = tc.get("cart_mass", CART_MASS)
        self._pole_mass = tc.get("pole_mass", POLE_MASS)
        self._pole_length = tc.get("pole_length", POLE_LENGTH)
        
        # LOWER DIFFICULTY: Spawn upright in baseline, hanging in mutants
        if not self.terrain_config and not self.physics_config:
            self._initial_angle = 0.0 # UPRIGHT
        else:
            self._initial_angle = math.pi # HANGING

    def _create_environment(self):
        # 1. Cart
        cart_w, cart_h = 1.0, 0.5
        cart_density = self._cart_mass / (cart_w * cart_h)
        cart = self.world.CreateDynamicBody(
            position=(self.TRACK_CENTER_X, 2.0),
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(cart_w/2, cart_h/2)),
                density=cart_density,
                friction=0.0,
            ),
        )
        cart.linearDamping = self._linear_damping
        cart.fixedRotation = True
        self._terrain_bodies["cart"] = cart

        # 2. Track
        ground = self.world.CreateStaticBody(position=(0, 0))
        self.world.CreatePrismaticJoint(
            bodyA=ground,
            bodyB=cart,
            anchor=cart.position,
            axis=(1, 0),
            lowerTranslation=-self.SAFE_HALF_RANGE,
            upperTranslation=self.SAFE_HALF_RANGE,
            enableLimit=True,
        )

        # 3. Pole
        pole_w, pole_l = POLE_WIDTH, self._pole_length
        pole_density = self._pole_mass / (pole_w * pole_l)
        pivot_x, pivot_y = self.TRACK_CENTER_X, 2.0
        
        pole_center_y = pivot_y + (self._pole_length / 2) * math.cos(self._initial_angle)
        
        pole = self.world.CreateDynamicBody(
            position=(pivot_x, pole_center_y),
            angle=self._initial_angle,
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(pole_w/2, pole_l/2)),
                density=pole_density,
                friction=0.0,
            ),
        )
        pole.angularDamping = self._angular_damping
        self._terrain_bodies["pole"] = pole

        # 4. Pivot Joint
        self._pivot_joint = self.world.CreateRevoluteJoint(
            bodyA=cart,
            bodyB=pole,
            anchor=(pivot_x, pivot_y),
            collideConnected=False,
        )

    def get_true_pole_angle(self):
        pole = self._terrain_bodies.get("pole")
        if not pole: return 0.0
        return math.atan2(math.sin(pole.angle), math.cos(pole.angle))

    def _get_true_pole_angle(self): return self.get_true_pole_angle()

    def get_true_pole_omega(self):
        pole = self._terrain_bodies.get("pole")
        return pole.angularVelocity if pole else 0.0

    def _get_true_pole_omega(self): return self.get_true_pole_omega()

    def step(self, dt):
        self._step_count += 1
        self._sensor_buffer.append((self._get_true_pole_angle(), self._get_true_pole_omega()))
        cart = self._terrain_bodies["cart"]
        force = self._last_applied_force
        force = max(-450.0, min(450.0, force))
        cart.ApplyForce((force, 0), cart.position, True)
        self.world.Step(TIME_STEP, 8, 3)
        self.world.ClearForces()

    def get_terrain_bounds(self):
        return {
            "track_center_x": self.TRACK_CENTER_X,
            "safe_half_range": self.SAFE_HALF_RANGE,
        }

    def get_pole_angle(self):
        idx = max(0, len(self._sensor_buffer) - 1 - self._sensor_delay_angle_steps)
        angle = self._sensor_buffer[idx][0] + self._sensor_angle_bias
        if self._sensor_noise_angle_std > 0:
            angle += random.gauss(0, self._sensor_noise_angle_std)
        return angle

    def get_pole_angular_velocity(self):
        idx = max(0, len(self._sensor_buffer) - 1 - self._sensor_delay_omega_steps)
        omega = self._sensor_buffer[idx][1]
        if self._sensor_noise_omega_std > 0:
            omega += random.gauss(0, self._sensor_noise_omega_std)
        return omega

    def get_cart_position(self):
        return self._terrain_bodies["cart"].position.x

    def get_cart_velocity(self):
        return self._terrain_bodies["cart"].linearVelocity.x

    def apply_cart_force(self, f):
        self._last_applied_force = f

    def get_cart_body(self):
        return self._terrain_bodies.get("cart")

    def get_pole_body(self):
        return self._terrain_bodies.get("pole")
