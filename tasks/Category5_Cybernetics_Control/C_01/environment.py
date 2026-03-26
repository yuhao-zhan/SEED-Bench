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

# Box2D Step(iterations) — single source for prompt + all Step() calls in this sandbox
WORLD_VELOCITY_ITERATIONS = 8
WORLD_POSITION_ITERATIONS = 3

# Grading thresholds (degrees / steps) — shared with evaluator.py and prompt.py via imports
BALANCE_ANGLE_DEG = 45.0
FAILURE_ANGLE_DEG = 90.0
BALANCE_HOLD_STEPS_REQUIRED = 200
BALANCE_LOCK_ANGLE_RAD = math.radians(BALANCE_ANGLE_DEG)

# Baseline Physical Params
CART_MASS = 10.0
POLE_MASS = 1.0
POLE_LENGTH = 2.0
POLE_WIDTH = 0.2

# Defaults applied when physics_config omits keys (single source of truth for stages.py baselines)
DEFAULT_POLE_START_ANGLE = 0.0
DEFAULT_SENSOR_DELAY_ANGLE_STEPS = 0
DEFAULT_SENSOR_DELAY_OMEGA_STEPS = 0

TRACK_CENTER_X = 10.0
SAFE_HALF_RANGE = 8.5

# World y of cart center (prismatic rail height); renderer reads via get_terrain_bounds
CART_RAIL_CENTER_Y = 2.0

# Episode length (single source of truth; prompt and main.py use this when max_steps is None)
MAX_STEPS = 20000

# Horizontal cart force clamp (N); keep in sync with prompt + primitives_api (patched from prompt loader)
CART_FORCE_LIMIT_NEWTONS = 450.0

# Default world gravity (+y up); stages/prompt use the same tuple when physics_config omits "gravity"
DEFAULT_GRAVITY_XY = (0.0, -10.0)


def gravity_from_config(g) -> tuple:
    """Support scalar g>0 as downward magnitude (0,-g) or a (gx, gy) tuple like other tasks."""
    if isinstance(g, (list, tuple)) and len(g) >= 2:
        return (float(g[0]), float(g[1]))
    return (0.0, -float(g))


class Sandbox:
    def __init__(self, terrain_config=None, physics_config=None, **kwargs):
        if kwargs:
            raise TypeError(f"Sandbox got unexpected keyword arguments: {sorted(kwargs.keys())}")
        # Retained for harness compatibility; C-01 does not read terrain keys (only physics_config).
        self.terrain_config = terrain_config or {}
        self.physics_config = physics_config or {}
        self.world = world(gravity=DEFAULT_GRAVITY_XY, doSleep=True)
        self._terrain_bodies = {}
        self.TRACK_CENTER_X = TRACK_CENTER_X
        self.SAFE_HALF_RANGE = SAFE_HALF_RANGE
        self.MAX_STEPS = MAX_STEPS
        self.cart_rail_center_y = CART_RAIL_CENTER_Y
        self._apply_configs()
        self._create_environment()
        self._step_count = 0
        self._last_applied_force = 0.0

        # Sensor delay buffers (filled after real physics warm-up so oldest samples match integrated dynamics)
        self._angle_buffer = deque(maxlen=max(1, self._sensor_delay_angle_steps + 1))
        self._omega_buffer = deque(maxlen=max(1, self._sensor_delay_omega_steps + 1))
        self._prime_sensor_delay_buffers()
        # Consecutive completed physics steps with |true pole angle| in upright band (evaluator lock-in)
        self._consecutive_upright_sim_steps = 0
        self._peak_abs_pole_angle = 0.0

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
        """Fill delay queues with the initial state to ensure correct delay from step 0."""
        da = self._sensor_delay_angle_steps
        dw = self._sensor_delay_omega_steps
        n_a = da + 1
        n_w = dw + 1
        
        initial_a = self.get_true_pole_angle()
        initial_w = self.get_true_pole_angular_velocity()
        
        for _ in range(n_a):
            self._angle_buffer.append(initial_a)
        for _ in range(n_w):
            self._omega_buffer.append(initial_w)

    def _apply_configs(self):
        pc = self.physics_config
        if "gravity" in pc:
            self.world.gravity = gravity_from_config(pc["gravity"])
        self.cart_force_limit_newtons = float(pc.get("cart_force_limit_newtons", CART_FORCE_LIMIT_NEWTONS))
        # Baseline: 0° upright; only use default 0.0 so prompt and env stay aligned when config is empty
        self._initial_angle = pc.get("pole_start_angle", DEFAULT_POLE_START_ANGLE)
        self._cart_mass = pc.get("cart_mass", CART_MASS)
        self._pole_length = pc.get("pole_length", POLE_LENGTH)
        self._pole_mass = pc.get("pole_mass", POLE_MASS)
        self._sensor_delay_angle_steps = int(pc.get(
            "sensor_delay_angle_steps", DEFAULT_SENSOR_DELAY_ANGLE_STEPS
        ))
        self._sensor_delay_omega_steps = int(pc.get(
            "sensor_delay_omega_steps", DEFAULT_SENSOR_DELAY_OMEGA_STEPS
        ))
        self.TRACK_CENTER_X = pc.get("track_center_x", TRACK_CENTER_X)
        self.SAFE_HALF_RANGE = pc.get("safe_half_range", SAFE_HALF_RANGE)
        self.MAX_STEPS = pc.get("max_steps", MAX_STEPS)
        self.cart_rail_center_y = float(pc.get("cart_rail_center_y", CART_RAIL_CENTER_Y))
        self.balance_angle_deg = float(pc.get("balance_angle_deg", BALANCE_ANGLE_DEG))
        self.failure_angle_deg = float(pc.get("failure_angle_deg", FAILURE_ANGLE_DEG))
        self.balance_hold_steps_required = int(
            pc.get("balance_hold_steps_required", BALANCE_HOLD_STEPS_REQUIRED)
        )
        self._balance_lock_angle_rad = math.radians(self.balance_angle_deg)


    def _create_environment(self):
        cart = self.world.CreateDynamicBody(position=(self.TRACK_CENTER_X, self.cart_rail_center_y))
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
        cy = self.cart_rail_center_y + (self._pole_length / 2) * math.cos(self._initial_angle)
        pole = self.world.CreateDynamicBody(position=(cx, cy), angle=self._initial_angle)
        pole.CreatePolygonFixture(box=(half_pw, self._pole_length / 2), density=self._pole_mass / pole_area)
        self._terrain_bodies["pole"] = pole
        self.world.CreateRevoluteJoint(
            bodyA=cart, bodyB=pole, anchor=(self.TRACK_CENTER_X, self.cart_rail_center_y)
        )

    def step(self, dt):
        """Advance one fixed 1/60 s integration substep. *dt* must equal TIME_STEP (see TASK_PROMPT)."""
        if not math.isclose(float(dt), TIME_STEP, rel_tol=0.0, abs_tol=1e-12):
            raise ValueError(
                f"C-01 Sandbox.step(dt) requires dt == TIME_STEP ({TIME_STEP}); got {dt!r}."
            )

        self._step_count += 1
        cart = self._terrain_bodies["cart"]
        cart.ApplyForce((self._last_applied_force, 0), cart.position, True)
        self.world.Step(TIME_STEP, WORLD_VELOCITY_ITERATIONS, WORLD_POSITION_ITERATIONS)
        
        # Update delay buffers AFTER stepping so buffer[0] is state from da steps ago.
        # da=0 means maxlen=1, buffer[0] will be current state after this append.
        self._angle_buffer.append(self.get_true_pole_angle())
        self._omega_buffer.append(self.get_true_pole_angular_velocity())

        if abs(self.get_true_pole_angle()) <= self._balance_lock_angle_rad:
            self._consecutive_upright_sim_steps += 1
        else:
            self._consecutive_upright_sim_steps = 0
            
        current_abs_pole_angle = abs(self.get_true_pole_angle())
        if current_abs_pole_angle > self._peak_abs_pole_angle:
            self._peak_abs_pole_angle = current_abs_pole_angle

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
        lim = self.cart_force_limit_newtons
        self._last_applied_force = max(-lim, min(lim, float(f)))
    def get_terrain_bounds(self):
        return {
            "track_center_x": self.TRACK_CENTER_X,
            "safe_half_range": self.SAFE_HALF_RANGE,
            "cart_rail_center_y": self.cart_rail_center_y,
        }

    def get_cart_body(self): return self._terrain_bodies.get("cart")
    def get_pole_body(self): return self._terrain_bodies.get("pole")

    def get_consecutive_upright_sim_steps(self) -> int:
        """Completed physics steps in a row within the upright band (see module BALANCE_ANGLE_DEG)."""
        return int(self._consecutive_upright_sim_steps)

    def get_peak_pole_angle(self) -> float:
        """Get the peak absolute pole angle observed so far."""
        return float(self._peak_abs_pole_angle)
