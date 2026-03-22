import math
from collections import deque
import Box2D
from Box2D.b2 import (
    world,
    staticBody,
    dynamicBody,
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

# Episode length (single source of truth; prompt and main.py use this when max_steps is None)
MAX_STEPS = 20000

# Horizontal cart force clamp (N); keep in sync with prompt + primitives_api (patched from prompt loader)
CART_FORCE_LIMIT_NEWTONS = 450.0

class Sandbox:
    def __init__(self, terrain_config=None, physics_config=None, **kwargs):
        if kwargs:
            raise TypeError(f"Sandbox got unexpected keyword arguments: {sorted(kwargs.keys())}")
        # Retained for harness compatibility; C-01 does not read terrain keys (only physics_config).
        self.terrain_config = terrain_config or {}
        self.physics_config = physics_config or {}
        self.world = world(gravity=(0, -10.0), doSleep=True)
        self._terrain_bodies = {}
        self.TRACK_CENTER_X = TRACK_CENTER_X
        self.SAFE_HALF_RANGE = SAFE_HALF_RANGE
        self.MAX_STEPS = MAX_STEPS
        self._apply_configs()
        self._create_environment()
        self._step_count = 0
        self._last_applied_force = 0.0

        # Sensor delay buffers (filled after real physics warm-up so oldest samples match integrated dynamics)
        self._angle_buffer = deque(maxlen=max(1, self._sensor_delay_angle_steps + 1))
        self._omega_buffer = deque(maxlen=max(1, self._sensor_delay_omega_steps + 1))
        self._prime_sensor_delay_buffers()

    def _snapshot_cart_pole(self):
        snap = []
        for key in ("cart", "pole"):
            b = self._terrain_bodies[key]
            p, lv = b.position, b.linearVelocity
            snap.append(
                (
                    float(p.x),
                    float(p.y),
                    float(b.angle),
                    float(lv.x),
                    float(lv.y),
                    float(b.angularVelocity),
                )
            )
        return snap

    def _restore_cart_pole(self, snap):
        for key, state in zip(("cart", "pole"), snap):
            b = self._terrain_bodies[key]
            x, y, ang, vx, vy, av = state
            b.position = (x, y)
            b.angle = ang
            b.linearVelocity = (vx, vy)
            b.angularVelocity = av

    def _prime_sensor_delay_buffers(self):
        """Fill delay queues from a zero-force rollout, then restore bodies (episode step count unchanged)."""
        da = self._sensor_delay_angle_steps
        dw = self._sensor_delay_omega_steps
        n = max(da, dw, 0)
        if n == 0:
            self._angle_buffer.append(self.get_true_pole_angle())
            self._omega_buffer.append(self.get_true_pole_angular_velocity())
            return
        snap = self._snapshot_cart_pole()
        angles = []
        omegas = []
        for _ in range(n + 1):
            angles.append(self.get_true_pole_angle())
            omegas.append(self.get_true_pole_angular_velocity())
            cart = self._terrain_bodies["cart"]
            cart.ApplyForce((self._last_applied_force, 0), cart.position, True)
            self.world.Step(TIME_STEP, 8, 3)
        self._restore_cart_pole(snap)
        tail_a = angles[-(da + 1) :] if da > 0 else [self.get_true_pole_angle()]
        tail_w = omegas[-(dw + 1) :] if dw > 0 else [self.get_true_pole_angular_velocity()]
        for v in tail_a:
            self._angle_buffer.append(v)
        for v in tail_w:
            self._omega_buffer.append(v)

    def _apply_configs(self):
        pc = self.physics_config
        # gravity: config value is positive scalar (m/s^2), applied as (0, -g)
        if "gravity" in pc:
            self.world.gravity = (0, -float(pc["gravity"]))
        # Baseline: 0° upright; only use default 0.0 so prompt and env stay aligned when config is empty
        self._initial_angle = pc.get("pole_start_angle", 0.0)
        self._cart_mass = pc.get("cart_mass", CART_MASS)
        self._pole_length = pc.get("pole_length", POLE_LENGTH)
        self._pole_mass = pc.get("pole_mass", POLE_MASS)
        self._sensor_delay_angle_steps = pc.get("sensor_delay_angle_steps", 0)
        self._sensor_delay_omega_steps = pc.get("sensor_delay_omega_steps", 0)
        self.TRACK_CENTER_X = pc.get("track_center_x", TRACK_CENTER_X)
        self.SAFE_HALF_RANGE = pc.get("safe_half_range", SAFE_HALF_RANGE)
        self.MAX_STEPS = pc.get("max_steps", MAX_STEPS)


    def _create_environment(self):
        cart = self.world.CreateDynamicBody(position=(self.TRACK_CENTER_X, 2.0))
        cart.CreatePolygonFixture(box=(0.5, 0.25), density=self._cart_mass/0.5)
        self._terrain_bodies["cart"] = cart
        ground = self.world.CreateStaticBody(position=(0, 0))
        # Joint limits match graded safe half-range (no extra slack beyond evaluator threshold)
        self.world.CreatePrismaticJoint(
            bodyA=ground,
            bodyB=cart,
            anchor=cart.position,
            axis=(1, 0),
            lowerTranslation=-self.SAFE_HALF_RANGE,
            upperTranslation=self.SAFE_HALF_RANGE,
            enableLimit=True,
        )
        # Pole fixture: half-width POLE_WIDTH/2, half-height pole_length/2 → area = POLE_WIDTH * pole_length
        half_pw = POLE_WIDTH / 2.0
        pole_area = POLE_WIDTH * self._pole_length
        cx = self.TRACK_CENTER_X - (self._pole_length / 2) * math.sin(self._initial_angle)
        cy = 2.0 + (self._pole_length / 2) * math.cos(self._initial_angle)
        pole = self.world.CreateDynamicBody(position=(cx, cy), angle=self._initial_angle)
        pole.CreatePolygonFixture(box=(half_pw, self._pole_length / 2), density=self._pole_mass / pole_area)
        self._terrain_bodies["pole"] = pole
        self.world.CreateRevoluteJoint(bodyA=cart, bodyB=pole, anchor=(self.TRACK_CENTER_X, 2.0))

    def step(self, dt):
        # Update delay buffers BEFORE stepping to store current state
        true_angle = self.get_true_pole_angle()
        true_omega = self.get_true_pole_angular_velocity()
        self._angle_buffer.append(true_angle)
        self._omega_buffer.append(true_omega)

        self._step_count += 1
        cart = self._terrain_bodies["cart"]
        cart.ApplyForce((self._last_applied_force, 0), cart.position, True)
        self.world.Step(TIME_STEP, 8, 3)

    def get_true_pole_angle(self):
        p = self._terrain_bodies.get("pole")
        return math.atan2(math.sin(p.angle), math.cos(p.angle)) if p else 0.0

    def get_true_pole_angular_velocity(self):
        p = self._terrain_bodies.get("pole")
        return p.angularVelocity if p else 0.0

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
    def apply_cart_force(self, f):
        lim = CART_FORCE_LIMIT_NEWTONS
        self._last_applied_force = max(-lim, min(lim, float(f)))
    def get_terrain_bounds(self):
        return {"track_center_x": self.TRACK_CENTER_X, "safe_half_range": self.SAFE_HALF_RANGE}

    def get_cart_body(self): return self._terrain_bodies.get("cart")
    def get_pole_body(self): return self._terrain_bodies.get("pole")
