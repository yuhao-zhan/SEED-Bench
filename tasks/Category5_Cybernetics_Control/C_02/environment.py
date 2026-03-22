"""
C-02: The Lander task environment module (hard variant)
Box lander, body-frame thrust, wind + gusts, limited fuel, narrow zone.
Actuation delay: thrust/torque commands take effect after a fixed number of steps (stated in prompt; overridable via physics_config).
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

# Landing success thresholds (stated in prompt success criteria; evaluator + terrain_bounds)
MAX_SAFE_VERTICAL_SPEED = 2.0
MAX_LANDING_ANGLE = math.radians(10.0)
# Total fuel impulse (N·s); thrust consumes fuel; exhaust = no thrust (higher for obstacle detour)
TOTAL_FUEL_IMPULSE = 5500.0
# Success also requires landing with at least this much fuel remaining (fuel-efficient trajectory)
MIN_FUEL_REMAINING_AT_LANDING = 450.0
# Random gusts: prob per step, amplitude (N)
GUST_PROB = 0.05
GUST_AMPLITUDE = 55.0
# Deterministic horizontal wind on the lander (superposition of two sinusoids; overridable via physics_config)
WIND_AMPLITUDE = 28.0
WIND_PERIOD1 = 3.0
WIND_PERIOD2 = 7.0
# Actuation delay: number of simulation steps before a thrust/torque command takes effect
THRUST_DELAY_STEPS = 3

# Moving platform: valid zone center oscillates (default params keep zone center x east of the barrier band).
PLATFORM_CENTER_BASE = 17.0
PLATFORM_AMPLITUDE = 1.8
PLATFORM_PERIOD = 6.0
PLATFORM_HALF_WIDTH = 2.0

# Vertical no-fly barrier: if any lander hull corner lies in x in [L,R] and
# (corner y < BARRIER_Y_TOP or corner y > BARRIER_Y_BOTTOM), episode fails.
# Forces trajectory: climb above barrier, then cross right, then descend and land.
BARRIER_X_LEFT = 10.5
BARRIER_X_RIGHT = 13.5
BARRIER_Y_TOP = 6.0
# In the barrier x-band: mission fails if any hull corner has y below this (obstacle top / corridor floor).
BARRIER_Y_BOTTOM = 20.0
# In the barrier x-band: mission fails if any hull corner has y above this (ceiling).

# Episode horizon (must match prompt and evaluation harness default for this task)
MAX_EPISODE_STEPS = 5000

# Integration step default (single source for Sandbox and prompt label)
DEFAULT_TIME_STEP = 1.0 / 60.0
# Human-readable timestep text in TASK_PROMPT (must correspond to DEFAULT_TIME_STEP)
DEFAULT_TIME_STEP_LABEL = "1/60"

# Touchdown: lander bottom within this distance of ground top counts as contact (evaluator + prompt)
LAND_TOLERANCE = 0.02

# Actuation limits (prompt-visible; stages.py imports for mutation baselines)
MAX_THRUST = 600.0
MAX_TORQUE = 120.0

# Spawn defaults (prompt-visible; mutable via terrain_config)
SPAWN_X = 6.0
SPAWN_Y = 12.0

# Ground surface and lander geometry defaults (prompt-visible; mutable via terrain_config)
GROUND_Y_TOP = 1.0
GROUND_LENGTH = 30.0
LANDER_HALF_WIDTH = 0.4
LANDER_HALF_HEIGHT = 0.3
LANDER_MASS = 50.0

# Contact / damping (used by Box2D; not spelled out in TASK_PROMPT — infer via interaction)
GROUND_FRICTION = 0.5
LANDER_FRICTION = 0.3
LANDER_RESTITUTION = 0.15
DEFAULT_LINEAR_DAMPING = 0.0
DEFAULT_ANGULAR_DAMPING = 0.1


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
        if "random_seed" in physics_config:
            random.seed(physics_config["random_seed"])

        gravity = tuple(physics_config.get("gravity", (0, -10)))
        self._default_linear_damping = float(
            physics_config.get("linear_damping", DEFAULT_LINEAR_DAMPING)
        )
        self._default_angular_damping = float(
            physics_config.get("angular_damping", DEFAULT_ANGULAR_DAMPING)
        )

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
        self._ground_y_top = float(terrain_config.get("ground_y_top", GROUND_Y_TOP))
        self._max_landing_angle = float(terrain_config.get("max_landing_angle", MAX_LANDING_ANGLE))
        self._platform_center_base = float(physics_config.get("platform_center_base", PLATFORM_CENTER_BASE))
        self._platform_amplitude = float(physics_config.get("platform_amplitude", PLATFORM_AMPLITUDE))
        self._platform_period = float(physics_config.get("platform_period", PLATFORM_PERIOD))
        self._platform_half_width = float(physics_config.get("platform_half_width", PLATFORM_HALF_WIDTH))
        self._time_step = float(physics_config.get("time_step", DEFAULT_TIME_STEP))
        self._land_tolerance = float(
            physics_config.get("land_tolerance", LAND_TOLERANCE)
        )
        # Box lander: full size 2*half_width × 2*half_height
        self._lander_half_width = float(terrain_config.get("lander_half_width", LANDER_HALF_WIDTH))
        self._lander_half_height = float(terrain_config.get("lander_half_height", LANDER_HALF_HEIGHT))
        self._lander_mass = float(terrain_config.get("lander_mass", LANDER_MASS))
        # Start offset from zone: agent must translate horizontally to reach landing zone
        self._spawn_x = float(terrain_config.get("spawn_x", SPAWN_X))
        self._spawn_y = float(terrain_config.get("spawn_y", SPAWN_Y))
        self._thrust_delay_steps = int(physics_config.get("thrust_delay_steps", THRUST_DELAY_STEPS))
        # Queue of (main_thrust, steering_torque); applied command is the oldest (issued delay_steps ago)
        qlen = max(1, self._thrust_delay_steps) + 1
        self._thrust_queue = deque([(0.0, 0.0)] * qlen, maxlen=qlen)
        self._step_count = 0
        self._wind_amplitude = float(physics_config.get("wind_amplitude", WIND_AMPLITUDE))
        self._wind_period1 = float(physics_config.get("wind_period1", WIND_PERIOD1))
        self._wind_period2 = float(physics_config.get("wind_period2", WIND_PERIOD2))
        self._gust_prob = float(physics_config.get("gust_prob", GUST_PROB))
        self._gust_amplitude = float(physics_config.get("gust_amplitude", GUST_AMPLITUDE))
        self._sim_time = 0.0
        self._total_fuel = float(physics_config.get("total_fuel_impulse", TOTAL_FUEL_IMPULSE))
        self._remaining_fuel = self._total_fuel
        self._min_fuel_remaining_at_landing = float(
            physics_config.get("min_fuel_remaining_at_landing", MIN_FUEL_REMAINING_AT_LANDING)
        )
        self._barrier_hit = False
        self._barrier_failure_kind = None  # "obstacle" | "ceiling" when _barrier_hit

        def _barrier_param(key: str, default: float) -> float:
            if key in physics_config and physics_config[key] is not None:
                return float(physics_config[key])
            if key in terrain_config and terrain_config[key] is not None:
                return float(terrain_config[key])
            return float(default)

        self._barrier_x_left = _barrier_param("barrier_x_left", BARRIER_X_LEFT)
        self._barrier_x_right = _barrier_param("barrier_x_right", BARRIER_X_RIGHT)
        self._barrier_y_top = _barrier_param("barrier_y_top", BARRIER_Y_TOP)
        self._barrier_y_bottom = _barrier_param("barrier_y_bottom", BARRIER_Y_BOTTOM)
        # Gravity mutation: {"at_step": N, "gravity_after": (gx, gy)} — applied once when step reaches N
        self._gravity_mutation = physics_config.get("gravity_mutation")

        self._create_ground(terrain_config)
        self._create_lander(terrain_config)

        self._main_thrust = 0.0
        self._steering_torque = 0.0
        self._max_thrust = float(physics_config.get("max_thrust", MAX_THRUST))
        self._max_torque = float(physics_config.get("max_torque", MAX_TORQUE))
        self._max_episode_steps = int(
            physics_config.get("max_episode_steps", MAX_EPISODE_STEPS)
        )

    def _create_ground(self, terrain_config: dict):
        """Create horizontal ground (static)."""
        ground_len = float(terrain_config.get("ground_length", GROUND_LENGTH))
        ground_h = 0.5
        center_y = self._ground_y_top - ground_h / 2
        ground = self._world.CreateStaticBody(
            position=(ground_len / 2, center_y),
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(ground_len / 2, ground_h / 2)),
                friction=GROUND_FRICTION,
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
                friction=LANDER_FRICTION,
                restitution=LANDER_RESTITUTION,
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
        """Return lander velocity (vx, vy) in m/s (internal)."""
        lander = self._terrain_bodies.get("lander")
        if lander is None:
            return (0.0, 0.0)
        return (lander.linearVelocity.x, lander.linearVelocity.y)

    def get_lander_velocity(self):
        """Return lander velocity (vx, vy) in m/s."""
        return self._get_lander_velocity()

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

    def get_thrust_delay_steps(self):
        """Simulation steps between issuing thrust/torque and their physical effect."""
        return self._thrust_delay_steps

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

        # Gravity mutation: after completing step `at_step`, subsequent steps use gravity_after
        # (i.e. steps 1..at_step use initial gravity; step at_step+1 onward use the new vector).
        if self._gravity_mutation:
            at_step = self._gravity_mutation.get("at_step")
            if at_step is not None and self._step_count >= int(at_step):
                gravity_after = tuple(self._gravity_mutation.get("gravity_after", (0, -10)))
                self._world.gravity = gravity_after
                self._gravity_mutation = None

        # Barrier (no-fly zone): any hull corner in x in [L,R] with y below corridor floor or above ceiling = fail
        if lander is not None and not self._barrier_hit:
            x, y = lander.position.x, lander.position.y
            a = lander.angle
            hw, hh = self._lander_half_width, self._lander_half_height
            for bx, by in ((-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)):
                wx = x + math.cos(a) * bx - math.sin(a) * by
                wy = y + math.sin(a) * bx + math.cos(a) * by
                if self._barrier_x_left <= wx <= self._barrier_x_right:
                    if wy < self._barrier_y_top:
                        self._barrier_hit = True
                        self._barrier_failure_kind = "obstacle"
                        break
                    if wy > self._barrier_y_bottom:
                        self._barrier_hit = True
                        self._barrier_failure_kind = "ceiling"
                        break

    def get_barrier_hit(self):
        """True if the lander breached the no-fly corridor (obstacle band below y=BARRIER_Y_TOP or ceiling above y=BARRIER_Y_BOTTOM)."""
        return getattr(self, "_barrier_hit", False)

    def get_barrier_failure_kind(self):
        """``\"obstacle\"`` | ``\"ceiling\"`` | ``None`` — set when barrier was breached."""
        return getattr(self, "_barrier_failure_kind", None)

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
            "thrust_delay_steps": self._thrust_delay_steps,
            "barrier_x_left": self._barrier_x_left,
            "barrier_x_right": self._barrier_x_right,
            "barrier_y_top": self._barrier_y_top,
            "barrier_y_bottom": self._barrier_y_bottom,
            "min_fuel_remaining_at_landing": self._min_fuel_remaining_at_landing,
            "max_episode_steps": self._max_episode_steps,
            "land_tolerance": self._land_tolerance,
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

    def get_lander_bottom_contact_x_span(self):
        """
        Horizontal extent (x_min, x_max) of corner(s) at minimum world y — i.e. ground contact footprint.
        Used so landing zone checks require the full craft width on the platform, not only center x.
        """
        lander = self._terrain_bodies.get("lander")
        if lander is None:
            return (0.0, 0.0)
        x, y = lander.position.x, lander.position.y
        a = lander.angle
        hw, hh = self._lander_half_width, self._lander_half_height
        corners = ((-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh))
        wx_list, wy_list = [], []
        for bx, by in corners:
            wx = x + math.cos(a) * bx - math.sin(a) * by
            wy = y + math.sin(a) * bx + math.cos(a) * by
            wx_list.append(wx)
            wy_list.append(wy)
        min_y = min(wy_list)
        eps = 1e-4
        xs_at_bottom = [wx_list[i] for i in range(4) if wy_list[i] <= min_y + eps]
        return (min(xs_at_bottom), max(xs_at_bottom))