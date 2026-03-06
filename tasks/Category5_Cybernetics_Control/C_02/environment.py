"""
C-02: The Lander task environment module (hard variant)
Box lander, body-frame thrust, wind + gusts, limited fuel, narrow zone.
Actuation delay: thrust/torque commands take effect after a fixed number of steps (discoverable).
"""
import math
import random
from collections import deque
import Box2D
from Box2D.b2 import (
    world,
    polygonShape,
    circleShape,
    staticBody,
    dynamicBody,
)

# Stricter limits (discoverable via feedback only)
MAX_SAFE_VERTICAL_SPEED = 2.0
MAX_LANDING_ANGLE = 0.175  # ~10 degrees
# Total fuel impulse (N·s); thrust consumes fuel; exhaust = no thrust (higher for obstacle detour)
TOTAL_FUEL_IMPULSE = 5500.0
# Success also requires landing with at least this much fuel remaining (fuel-efficient trajectory)
MIN_FUEL_REMAINING_AT_LANDING = 450.0
# Random gusts: prob per step, amplitude (N)
GUST_PROB = 0.05
GUST_AMPLITUDE = 55.0
# Actuation delay: number of simulation steps before a thrust/torque command takes effect
THRUST_DELAY_STEPS = 3

# Moving platform: valid landing zone moves with time; always RIGHT of barrier (center - half_width >= BARRIER_X_RIGHT).
PLATFORM_CENTER_BASE = 17.0
PLATFORM_AMPLITUDE = 1.8
PLATFORM_PERIOD = 6.0
PLATFORM_HALF_WIDTH = 2.0

# Vertical no-fly barrier: if lander enters this box (x in [L,R], y < TOP), instant fail.
# Forces trajectory: climb above barrier, then cross right, then descend and land.
BARRIER_X_LEFT = 10.5
BARRIER_X_RIGHT = 13.5
BARRIER_Y_TOP = 6.0


class Sandbox:
    """
    Sandbox for C-02: Box lander with rotation, body-frame thrust, wind.
    Lander is a rectangle; thrust is along body up; horizontal wind force applied.
    """

    def __init__(self, *, terrain_config=None, physics_config=None):
        terrain_config = terrain_config or {}
        physics_config = physics_config or {}
        self._terrain_config = dict(terrain_config)
        self._physics_config = dict(physics_config)

        gravity = tuple(physics_config.get("gravity", (0, -10)))
        self._default_linear_damping = float(physics_config.get("linear_damping", 0.0))
        self._default_angular_damping = float(physics_config.get("angular_damping", 0.1))

        self._world = world(gravity=gravity, doSleep=True)
        self._bodies = []
        self._joints = []
        self._terrain_bodies = {}

        self.world = self._world
        self.bodies = self._bodies
        self.joints = self._joints

        self._max_safe_vertical_speed = float(
            terrain_config.get("max_safe_vertical_speed", MAX_SAFE_VERTICAL_SPEED)
        )
        self._ground_y_top = float(terrain_config.get("ground_y_top", 1.0))
        self._max_landing_angle = float(terrain_config.get("max_landing_angle", MAX_LANDING_ANGLE))
        self._platform_center_base = float(physics_config.get("platform_center_base", PLATFORM_CENTER_BASE))
        self._platform_amplitude = float(physics_config.get("platform_amplitude", PLATFORM_AMPLITUDE))
        self._platform_period = float(physics_config.get("platform_period", PLATFORM_PERIOD))
        self._platform_half_width = float(physics_config.get("platform_half_width", PLATFORM_HALF_WIDTH))
        self._time_step = float(physics_config.get("time_step", 1.0 / 60.0))
        # Box lander: width 0.8 m, height 0.6 m
        self._lander_half_width = float(terrain_config.get("lander_half_width", 0.4))
        self._lander_half_height = float(terrain_config.get("lander_half_height", 0.3))
        self._lander_mass = float(terrain_config.get("lander_mass", 50.0))
        # Start offset from zone: agent must translate horizontally to reach landing zone
        self._spawn_x = float(terrain_config.get("spawn_x", 6.0))
        self._spawn_y = float(terrain_config.get("spawn_y", 12.0))
        self._thrust_delay_steps = int(physics_config.get("thrust_delay_steps", THRUST_DELAY_STEPS))
        # Queue of (main_thrust, steering_torque); applied command is the oldest (issued delay_steps ago)
        qlen = max(1, self._thrust_delay_steps) + 1
        self._thrust_queue = deque([(0.0, 0.0)] * qlen, maxlen=qlen)
        self._step_count = 0
        self._wind_amplitude = float(physics_config.get("wind_amplitude", 28.0))
        self._wind_period1 = float(physics_config.get("wind_period1", 3.0))
        self._wind_period2 = float(physics_config.get("wind_period2", 7.0))
        self._gust_prob = float(physics_config.get("gust_prob", GUST_PROB))
        self._gust_amplitude = float(physics_config.get("gust_amplitude", GUST_AMPLITUDE))
        self._sim_time = 0.0
        self._total_fuel = float(physics_config.get("total_fuel_impulse", TOTAL_FUEL_IMPULSE))
        self._remaining_fuel = self._total_fuel
        self._min_fuel_remaining_at_landing = float(
            physics_config.get("min_fuel_remaining_at_landing", MIN_FUEL_REMAINING_AT_LANDING)
        )
        self._barrier_hit = False
        self._barrier_x_left = float(physics_config.get("barrier_x_left", BARRIER_X_LEFT))
        self._barrier_x_right = float(physics_config.get("barrier_x_right", BARRIER_X_RIGHT))
        self._barrier_y_top = float(physics_config.get("barrier_y_top", BARRIER_Y_TOP))
        # Gravity mutation: {"at_step": N, "gravity_after": (gx, gy)} — applied once when step reaches N
        self._gravity_mutation = physics_config.get("gravity_mutation")

        self._create_ground(terrain_config)
        self._create_lander(terrain_config)

        self._main_thrust = 0.0
        self._steering_torque = 0.0
        self._max_thrust = 600.0
        self._max_torque = 120.0

    def _create_ground(self, terrain_config: dict):
        """Create horizontal ground (static)."""
        ground_len = 30.0
        ground_h = 0.5
        center_y = self._ground_y_top - ground_h / 2
        ground = self._world.CreateStaticBody(
            position=(ground_len / 2, center_y),
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(ground_len / 2, ground_h / 2)),
                friction=0.5,
                restitution=0.0,
            ),
        )
        self._terrain_bodies["ground"] = ground
        self._ground_length = ground_len

    def _create_lander(self, terrain_config: dict):
        """Create lander as box (rectangle) so rotation matters; body-frame thrust."""
        hw = self._lander_half_width
        hh = self._lander_half_height
        area = 4.0 * hw * hh
        density = self._lander_mass / area
        lander = self._world.CreateDynamicBody(
            position=(self._spawn_x, self._spawn_y),
            angle=0.0,
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(hw, hh)),
                density=density,
                friction=0.3,
                restitution=0.15,
            ),
        )
        lander.linearDamping = self._default_linear_damping
        lander.angularDamping = self._default_angular_damping
        self._terrain_bodies["lander"] = lander

    def get_lander_position(self):
        """Return lander center (x, y) in meters."""
        lander = self._terrain_bodies.get("lander")
        if lander is None:
            return (0.0, 0.0)
        return (lander.position.x, lander.position.y)

    def _get_lander_velocity(self):
        """Return lander velocity (vx, vy) in m/s."""
        lander = self._terrain_bodies.get("lander")
        if lander is None:
            return (0.0, 0.0)
        return (lander.linearVelocity.x, lander.linearVelocity.y)

    def get_lander_angle(self):
        """Return lander angle in radians (0 = upright)."""
        lander = self._terrain_bodies.get("lander")
        if lander is None:
            return 0.0
        return lander.angle

    def get_lander_angular_velocity(self):
        """Return angular velocity in rad/s."""
        lander = self._terrain_bodies.get("lander")
        if lander is None:
            return 0.0
        return lander.angularVelocity

    def apply_thrust(self, main_thrust, steering_torque):
        """
        Apply thrust along body up axis and steering torque.
        main_thrust: force in N along craft's up direction (positive = engine fire).
        steering_torque: torque in N·m (positive = counterclockwise).
        """
        self._main_thrust = max(-self._max_thrust, min(self._max_thrust, float(main_thrust)))
        self._steering_torque = max(
            -self._max_torque, min(self._max_torque, float(steering_torque))
        )

    def get_remaining_fuel(self):
        """Return remaining fuel impulse in N·s (0 = exhausted)."""
        return max(0.0, self._remaining_fuel)

    def step(self, time_step):
        """Physics step: wind + gusts, delayed thrust (body frame, consumes fuel), then step world."""
        lander = self._terrain_bodies.get("lander")
        if lander is not None:
            t = self._sim_time
            wind_fx = self._wind_amplitude * (
                math.sin(2.0 * math.pi * t / self._wind_period1) * 0.6
                + math.sin(2.0 * math.pi * t / self._wind_period2) * 0.4
            )
            if random.random() < self._gust_prob:
                wind_fx += (random.random() * 2 - 1) * self._gust_amplitude
            lander.ApplyForceToCenter((wind_fx, 0.0), True)

            # Apply the delayed command (the one issued delay_steps ago)
            thrust_to_use = self._thrust_queue[0][0]
            torque_to_use = self._thrust_queue[0][1]
            self._thrust_queue.popleft()
            self._thrust_queue.append((self._main_thrust, self._steering_torque))
            self._main_thrust = 0.0
            self._steering_torque = 0.0

            impulse_cost = abs(thrust_to_use) * time_step
            if self._remaining_fuel <= 0:
                thrust_to_use = 0.0
            elif impulse_cost > self._remaining_fuel:
                scale = self._remaining_fuel / impulse_cost
                thrust_to_use *= scale
                impulse_cost = self._remaining_fuel
            self._remaining_fuel -= impulse_cost

            if thrust_to_use != 0.0:
                a = lander.angle
                fx = -thrust_to_use * math.sin(a)
                fy = thrust_to_use * math.cos(a)
                lander.ApplyForceToCenter((fx, fy), True)
            if torque_to_use != 0.0:
                lander.ApplyTorque(torque_to_use, True)

        self._world.Step(time_step, 10, 10)
        self._sim_time += time_step
        self._step_count += 1

        # Gravity mutation: apply once when step reaches at_step (invisible physics change)
        if self._gravity_mutation:
            at_step = self._gravity_mutation.get("at_step")
            if self._step_count >= at_step:
                gravity_after = tuple(self._gravity_mutation.get("gravity_after", (0, -10)))
                self._world.gravity = gravity_after
                self._gravity_mutation = None

        # Barrier (no-fly zone): entering below BARRIER_Y_TOP with x in [L,R] = fail
        if lander is not None and not self._barrier_hit:
            lx, ly = lander.position.x, lander.position.y
            if (
                self._barrier_x_left <= lx <= self._barrier_x_right
                and ly < self._barrier_y_top
            ):
                self._barrier_hit = True

    def get_barrier_hit(self):
        """True if lander ever entered the no-fly barrier (obstacle)."""
        return getattr(self, "_barrier_hit", False)

    def get_terrain_bounds(self):
        """Return terrain bounds for evaluator/renderer. Zone is time-dependent; use get_zone_x_bounds_at_step."""
        return {
            "ground_y_top": self._ground_y_top,
            "ground_length": self._ground_length,
            "lander_half_width": self._lander_half_width,
            "lander_half_height": self._lander_half_height,
            "max_safe_vertical_speed": self._max_safe_vertical_speed,
            "max_landing_angle": self._max_landing_angle,
            "total_fuel_impulse": self._total_fuel,
            "time_step": self._time_step,
            "barrier_x_left": self._barrier_x_left,
            "barrier_x_right": self._barrier_x_right,
            "barrier_y_top": self._barrier_y_top,
            "min_fuel_remaining_at_landing": self._min_fuel_remaining_at_landing,
        }

    def get_platform_center_at_time(self, sim_time: float) -> float:
        """Return moving platform center x at given simulation time (seconds)."""
        return self._platform_center_base + self._platform_amplitude * math.sin(
            2.0 * math.pi * sim_time / self._platform_period
        )

    def get_zone_x_bounds_at_step(self, step: int):
        """Return (zone_x_min, zone_x_max) at the given step (for evaluator at landing)."""
        t = step * self._time_step
        center = self.get_platform_center_at_time(t)
        return (center - self._platform_half_width, center + self._platform_half_width)

    def get_lander_body(self):
        return self._terrain_bodies.get("lander")

    def get_ground_y_top(self):
        return self._ground_y_top

    def get_lander_size(self):
        """Return (half_width, half_height) in meters for height-above-ground computation."""
        return (self._lander_half_width, self._lander_half_height)

    def get_lander_radius(self):
        """No longer a circle; return half-diagonal for compatibility."""
        return math.sqrt(
            self._lander_half_width ** 2 + self._lander_half_height ** 2
        )

    def get_lander_bottom_y(self):
        """Lowest y of the box in world frame."""
        lander = self._terrain_bodies.get("lander")
        if lander is None:
            return 0.0
        x, y = lander.position.x, lander.position.y
        a = lander.angle
        hw, hh = self._lander_half_width, self._lander_half_height
        # Bottom = y + min over corners of (sin(a)*bx + cos(a)*by)
        # Corners (±hw, ±hh): by = -hh gives -cos(a)*hh; bx = ±hw gives ±sin(a)*hw
        bottom = y - abs(math.sin(a)) * hw - math.cos(a) * hh
        return bottom