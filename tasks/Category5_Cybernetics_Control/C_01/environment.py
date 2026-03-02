"""
C-01: Cart-Pole Swing-up then Balance (fundamentally hard).
Pole starts hanging downward at rest. Agent must swing it up to upright and then keep it balanced.
Requires two-phase strategy (energy pumping / swing-up then balance); simple PD cannot solve it.
Sensor delay, actuator delay, and safe zone still apply; agent infers from feedback.
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
)

# Balance threshold: once pole enters this band, it must stay (radians)
BALANCE_ANGLE_RAD = math.radians(45.0)
FAILURE_ANGLE_RAD = BALANCE_ANGLE_RAD

# Default delays and limits (overridable via physics_config for mutated tasks)
SENSOR_DELAY_ANGLE_STEPS = 2
SENSOR_DELAY_OMEGA_STEPS = 3
ACTUATOR_DELAY_STEPS = 1
ACTUATOR_RATE_LIMIT = 80.0
ACTUATOR_DROPOUT_PROB = 0.02
TRACK_CENTER_X = 10.0
SAFE_HALF_RANGE = 8.5   # cart [1.5, 18.5] m so swing-up has room; prompt does not give exact value

# No speed zones or position-dependent force for this task (swing-up needs full authority)
RANDOM_TORQUE_PROB = 0.008
RANDOM_TORQUE_MAG = 1.0
SENSOR_NOISE_ANGLE_STD = 0.015
SENSOR_NOISE_OMEGA_STD = 0.03
SENSOR_ANGLE_BIAS = 0.018
FORCE_MAX_RIGHT = 450.0
FORCE_MAX_LEFT = 450.0
SENSOR_DROPOUT_PROB = 0.02
BASE_OSCILLATION_AMP = 0.08
BASE_OSCILLATION_FREQ = 0.25


class Sandbox:
    """
    Sandbox for C-01: Cart-Pole (hard).
    Pre-built cart on track, pole on cart. Agent applies horizontal force.
    Sensor delay: reported state is delayed. Actuator delay: commanded force applies later.
    Cart must stay within safe zone; random disturbances act on the pole.
    """

    def __init__(self, *, terrain_config=None, physics_config=None):
        terrain_config = terrain_config or {}
        physics_config = physics_config or {}
        self._terrain_config = dict(terrain_config)
        self._physics_config = dict(physics_config)

        gravity = tuple(physics_config.get("gravity", (0, -10)))
        self._default_linear_damping = float(physics_config.get("linear_damping", 0.0))
        self._default_angular_damping = float(physics_config.get("angular_damping", 0.1))
        self._sensor_delay_angle_steps = int(physics_config.get("sensor_delay_angle_steps", SENSOR_DELAY_ANGLE_STEPS))
        self._sensor_delay_omega_steps = int(physics_config.get("sensor_delay_omega_steps", SENSOR_DELAY_OMEGA_STEPS))
        self._actuator_delay_steps = int(physics_config.get("actuator_delay_steps", ACTUATOR_DELAY_STEPS))
        self._actuator_rate_limit = float(physics_config.get("actuator_rate_limit", ACTUATOR_RATE_LIMIT))

        self._world = world(gravity=gravity, doSleep=True)
        self._bodies = []
        self._joints = []
        self._terrain_bodies = {}

        self.world = self._world
        self.bodies = self._bodies
        self.joints = self._joints

        self._pole_length = float(terrain_config.get("pole_length", 2.0))
        self._pole_mass = float(terrain_config.get("pole_mass", 1.0))
        self._cart_mass = float(terrain_config.get("cart_mass", 10.0))
        self._track_length = float(terrain_config.get("track_length", 20.0))
        # Pole starts hanging downward (pi); swing-up then balance task
        self._initial_pole_angle = float(terrain_config.get("initial_pole_angle", math.pi))

        self._create_track(terrain_config)
        self._create_cart_pole(terrain_config)

        # Actuator delay: queue of forces to apply (oldest applied each step)
        self._force_queue = deque([0.0] * self._actuator_delay_steps, maxlen=self._actuator_delay_steps + 10)
        self._cart_force_x = 0.0  # commanded this step (will be queued)
        self._last_applied_force = 0.0  # for rate limiting

        # Sensor delay: buffer of (angle, omega); angle and omega have different delay lengths
        _max_delay = max(self._sensor_delay_angle_steps, self._sensor_delay_omega_steps) + 2
        self._sensor_buffer = deque(maxlen=_max_delay)
        self._sensor_buffer.append((self._get_true_pole_angle(), self._get_true_pole_omega()))
        self._step_count = 0
        self._dropout_this_step = False

    def _create_track(self, terrain_config: dict):
        track_y = 2.0
        track_length = self._track_length
        track_height = 0.2
        track_center_x = track_length / 2
        track = self._world.CreateStaticBody(
            position=(track_center_x, track_y),
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(track_length / 2, track_height / 2)),
                friction=0.1,
            ),
        )
        self._terrain_bodies["track"] = track
        self._track_y = track_y
        self._track_height = track_height
        self._track_length = track_length

    def _create_cart_pole(self, terrain_config: dict):
        track = self._terrain_bodies["track"]
        track_y = self._track_y
        track_height = self._track_height
        pole_length = self._pole_length
        cart_mass = self._cart_mass
        pole_mass = self._pole_mass
        initial_angle = self._initial_pole_angle

        cart_width = 1.0
        cart_height = 0.4
        cart_center_x = self._track_length / 2
        cart_center_y = track_y + track_height / 2 + cart_height / 2
        cart_density = cart_mass / (cart_width * cart_height)

        cart = self._world.CreateDynamicBody(
            position=(cart_center_x, cart_center_y),
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(cart_width / 2, cart_height / 2)),
                density=cart_density,
                friction=0.2,
            ),
        )
        cart.linearDamping = self._default_linear_damping
        cart.angularDamping = self._default_angular_damping
        cart.fixedRotation = True
        self._terrain_bodies["cart"] = cart

        anchor = (cart_center_x, cart_center_y)
        axis = (1.0, 0.0)
        half_range = (self._track_length / 2) - (cart_width / 2) - 0.5
        prismatic = self._world.CreatePrismaticJoint(
            bodyA=track,
            bodyB=cart,
            anchor=anchor,
            axis=axis,
            lowerTranslation=-half_range,
            upperTranslation=half_range,
            enableLimit=True,
            enableMotor=False,
        )
        self._joints.append(prismatic)

        pole_width = 0.08
        pole_density = pole_mass / (pole_width * pole_length)
        pivot_x = cart_center_x
        pivot_y = cart_center_y + cart_height / 2
        pole_center_x = pivot_x + (pole_length / 2) * math.sin(initial_angle)
        pole_center_y = pivot_y + (pole_length / 2) * math.cos(initial_angle)

        pole = self._world.CreateDynamicBody(
            position=(pole_center_x, pole_center_y),
            angle=initial_angle,
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(pole_width / 2, pole_length / 2)),
                density=pole_density,
                friction=0.0,
                restitution=0.0,
            ),
        )
        pole.linearDamping = self._default_linear_damping
        pole.angularDamping = self._default_angular_damping
        self._terrain_bodies["pole"] = pole

        rev = self._world.CreateRevoluteJoint(
            bodyA=cart,
            bodyB=pole,
            anchor=(pivot_x, pivot_y),
            collideConnected=False,
        )
        self._joints.append(rev)

    def _get_true_pole_angle(self):
        pole = self._terrain_bodies.get("pole")
        if pole is None:
            return 0.0
        angle = pole.angle
        return (angle + math.pi) % (2 * math.pi) - math.pi

    def _get_true_pole_omega(self):
        pole = self._terrain_bodies.get("pole")
        if pole is None:
            return 0.0
        return pole.angularVelocity

    # --- Agent API (delayed, noisy, with intermittent dropout) ---

    def get_pole_angle(self):
        """Return pole angle (radians). Delayed; may have bias, noise, or dropout."""
        if random.random() < SENSOR_DROPOUT_PROB:
            self._dropout_this_step = True
        if getattr(self, "_dropout_this_step", False):
            return 0.0
        idx_angle = -(1 + self._sensor_delay_angle_steps)
        if len(self._sensor_buffer) + idx_angle < 0:
            raw = self._sensor_buffer[0][0] if self._sensor_buffer else 0.0
        else:
            raw = self._sensor_buffer[idx_angle][0]
        return raw + SENSOR_ANGLE_BIAS + random.gauss(0.0, SENSOR_NOISE_ANGLE_STD)

    def get_pole_angular_velocity(self):
        """Return pole angular velocity (rad/s). Delayed by different amount; may be noisy or dropout."""
        if getattr(self, "_dropout_this_step", False):
            return 0.0
        idx_omega = -(1 + self._sensor_delay_omega_steps)
        if len(self._sensor_buffer) + idx_omega < 0:
            raw = self._sensor_buffer[0][1] if self._sensor_buffer else 0.0
        else:
            raw = self._sensor_buffer[idx_omega][1]
        return raw + random.gauss(0.0, SENSOR_NOISE_OMEGA_STD)

    def get_cart_position(self):
        """Return cart x position (m). No delay."""
        cart = self._terrain_bodies.get("cart")
        if cart is None:
            return 0.0
        return cart.position.x

    def get_cart_velocity(self):
        """Return cart x velocity (m/s). No delay."""
        cart = self._terrain_bodies.get("cart")
        if cart is None:
            return 0.0
        return cart.linearVelocity.x

    def apply_cart_force(self, force_x):
        """Command horizontal force (N). Applied after actuator delay."""
        fx = float(force_x)
        fx = max(-FORCE_MAX_LEFT, min(FORCE_MAX_RIGHT, fx))
        self._cart_force_x = fx

    def step(self, time_step):
        # 1) Queue commanded force (actuator delay: apply oldest)
        self._force_queue.append(self._cart_force_x)
        self._cart_force_x = 0.0
        force_from_queue = self._force_queue.popleft() if self._force_queue else 0.0
        # Rate limit: max change per step
        delta = max(-self._actuator_rate_limit, min(self._actuator_rate_limit, force_from_queue - self._last_applied_force))
        force_to_apply = self._last_applied_force + delta
        # Intermittent actuator dropout: sometimes force not applied
        if random.random() < ACTUATOR_DROPOUT_PROB:
            force_to_apply = 0.0
        self._last_applied_force = force_to_apply

        # 2) Random disturbance on pole (not told in prompt)
        pole = self._terrain_bodies.get("pole")
        if pole is not None and random.random() < RANDOM_TORQUE_PROB:
            torque = (random.random() * 2 - 1) * RANDOM_TORQUE_MAG
            pole.ApplyTorque(torque, wake=True)

        # 3) Apply (rate-limited, possibly dropped) force to cart
        cart = self._terrain_bodies.get("cart")
        if cart is not None and force_to_apply != 0.0:
            cart.ApplyForce((force_to_apply, 0.0), cart.position, True)

        # 3b) Oscillating base: inertial force on cart (simulates moving track)
        if cart is not None:
            t = self._step_count * time_step
            omega = 2.0 * math.pi * BASE_OSCILLATION_FREQ
            a_base = -BASE_OSCILLATION_AMP * (omega ** 2) * math.sin(omega * t)
            cart.ApplyForce((self._cart_mass * a_base, 0.0), cart.position, True)

        # 4) Physics step
        self._world.Step(time_step, 10, 10)

        # 5) Push current state to sensor buffer (for delay)
        self._sensor_buffer.append((self._get_true_pole_angle(), self._get_true_pole_omega()))
        self._step_count += 1
        self._dropout_this_step = False

    def get_true_pole_angle(self):
        """True pole angle (radians) for evaluator; not delayed/noisy."""
        return self._get_true_pole_angle()

    def get_terrain_bounds(self):
        return {
            "track_y": self._track_y,
            "track_length": self._track_length,
            "track_height": self._track_height,
            "pole_length": self._pole_length,
            "failure_angle_deg": math.degrees(FAILURE_ANGLE_RAD),
            "track_center_x": TRACK_CENTER_X,
            "safe_half_range": SAFE_HALF_RANGE,
        }

    def get_cart_body(self):
        return self._terrain_bodies.get("cart")

    def get_pole_body(self):
        return self._terrain_bodies.get("pole")
