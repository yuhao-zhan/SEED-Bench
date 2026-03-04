"""
C-04: The Escaper (Counterintuitive behavioral unlock)
Exit LOCKED until the agent has applied backward force (fx < -30) while speed < 1.0 for 20 consecutive steps.
Unlock is behavioral and counterintuitive (must go backward slowly); discover via interaction and feedback.
One-way barrier and hold-60-steps-in-exit remain. Velocity sensor returns (0,0).
"""
import math
import Box2D
from Box2D.b2 import (
    world,
    polygonShape,
    circleShape,
    staticBody,
    dynamicBody,
)

WHISKER_MAX_RANGE = 3.0
EXIT_X_MIN = 18.0
EXIT_Y_MIN = 1.25
EXIT_Y_MAX = 1.45

# Obstacles
MOMENTUM_DRAIN_X_MIN = 7.0
MOMENTUM_DRAIN_X_MAX = 9.5
MOMENTUM_DRAIN_DAMPING = 12.0
CURRENT_X_MIN = 12.0
CURRENT_X_MAX = 15.0
CURRENT_FORCE_BACK = 24.0
WIND_X_MIN = 15.5
WIND_X_MAX = 18.0
WIND_BASE_DOWN = 8.0
WIND_OSCILLATION_AMP = 10.0
WIND_OSCILLATION_OMEGA = 0.08

# Behavioral unlock (not in prompt): apply backward force (fx < threshold) while speed below max, for N consecutive steps
BACKWARD_FX_THRESHOLD = -30.0
BACKWARD_SPEED_MAX = 1.0  # must stay below this while applying backward force (counterintuitive: go backward slowly)
BACKWARD_STEPS_REQUIRED = 25
# Spatial activation zone for unlock (required by prompt)
ACTIVATION_X_MIN = 6.0
ACTIVATION_X_MAX = 8.0

# Slip zone default friction (configurable for maze "complexity")
SLIP_FRICTION = 0.03
# Exit barrier
EXIT_BARRIER_X_LO, EXIT_BARRIER_X_HI = 17.0, 18.5
EXIT_BARRIER_FORCE = 120.0
# One-way: past x=10.2 cannot go back
ONEWAY_X = 10.2
ONEWAY_FORCE_RIGHT = 100.0
ONEWAY_VX_THRESHOLD = -0.3


class _RayCastClosestCallback(Box2D.b2.rayCastCallback):
    def __init__(self, exclude_body=None):
        Box2D.b2.rayCastCallback.__init__(self)
        self.fraction = 1.0
        self.exclude_body = exclude_body

    def ReportFixture(self, fixture, point, normal, fraction):
        if self.exclude_body is not None and fixture.body == self.exclude_body:
            return -1
        if fraction < self.fraction:
            self.fraction = fraction
        return fraction


class Sandbox:
    """
    C-04: Exit locked until a counterintuitive behavioral condition is met (backward force + low speed for N steps).
    Unlock is behavioral; discover via trying.
    """

    def __init__(self, *, terrain_config=None, physics_config=None):
        terrain_config = terrain_config or {}
        physics_config = physics_config or {}

        self._terrain_config = dict(terrain_config)
        self._physics_config = dict(physics_config)
        gravity = tuple(physics_config.get("gravity", (0, -10)))
        self._default_linear_damping = float(physics_config.get("linear_damping", 0.3))
        self._default_angular_damping = float(physics_config.get("angular_damping", 0.3))

        self._world = world(gravity=gravity, doSleep=True)
        self._bodies = []
        self._joints = []
        self._terrain_bodies = {}
        self._wall_bodies = []

        self.world = self._world
        self.bodies = self._bodies
        self.joints = self._joints

        self._whisker_max_range = float(
            terrain_config.get("whisker_max_range", WHISKER_MAX_RANGE)
        )
        self._exit_x_min = float(terrain_config.get("exit_x_min", EXIT_X_MIN))
        self._exit_y_min = float(terrain_config.get("exit_y_min", EXIT_Y_MIN))
        self._exit_y_max = float(terrain_config.get("exit_y_max", EXIT_Y_MAX))
        self._agent_radius = float(terrain_config.get("agent_radius", 0.25))
        self._agent_mass = float(terrain_config.get("agent_mass", 5.0))
        self._spawn_x = float(terrain_config.get("spawn_x", 2.0))
        self._spawn_y = float(terrain_config.get("spawn_y", 2.0))
        self._current_step = 0

        # Physics config (mutations)
        self._momentum_drain_damping = float(
            physics_config.get("momentum_drain_damping", MOMENTUM_DRAIN_DAMPING)
        )
        self._current_force_back = float(
            physics_config.get("current_force_back", CURRENT_FORCE_BACK)
        )
        self._wind_base_down = float(physics_config.get("wind_base_down", WIND_BASE_DOWN))
        self._wind_oscillation_amp = float(
            physics_config.get("wind_oscillation_amp", WIND_OSCILLATION_AMP)
        )
        self._wind_oscillation_omega = float(
            physics_config.get("wind_oscillation_omega", WIND_OSCILLATION_OMEGA)
        )
        self._backward_fx_threshold = float(
            physics_config.get("backward_fx_threshold", BACKWARD_FX_THRESHOLD)
        )
        self._backward_speed_max = float(
            physics_config.get("backward_speed_max", BACKWARD_SPEED_MAX)
        )
        self._backward_steps_required = int(
            physics_config.get("backward_steps_required", BACKWARD_STEPS_REQUIRED)
        )
        self._exit_barrier_force = float(
            physics_config.get("exit_barrier_force", EXIT_BARRIER_FORCE)
        )

        # Sensor mutations (terrain_config)
        self._whisker_delay_steps = int(
            terrain_config.get("whisker_delay_steps", 0)
        )
        self._whisker_blind_front_x_lo = float(
            terrain_config.get("whisker_blind_front_x_lo", -999.0)
        )
        self._whisker_blind_front_x_hi = float(
            terrain_config.get("whisker_blind_front_x_hi", -999.0)
        )
        self._whisker_readings_history = []  # [(front, left, right), ...]

        self._behavioral_unlock = False
        self._backward_steps = 0

        self._create_maze(terrain_config)
        self._create_agent(terrain_config)

        self._force_x = 0.0
        self._force_y = 0.0

    def _create_maze(self, terrain_config: dict):
        """Maze: outer walls, three obstacles (up, middle-slit, down). No visible trigger markers."""
        walls = [
            (10.0, 0.25, 10.0, 0.25),
            (10.0, 2.75, 10.0, 0.25),
            (0.25, 1.5, 0.25, 1.5),
            (19.75, 0.625, 0.25, 0.625),
            (19.75, 2.225, 0.25, 0.775),
            (5.0, 0.625, 0.2, 0.625),
            (9.0, 0.5, 0.2, 0.5),
            (9.0, 2.3, 0.2, 0.7),
            (14.0, 2.225, 0.2, 0.775),
        ]
        for cx, cy, hw, hh in walls:
            body = self._world.CreateStaticBody(
                position=(cx, cy),
                fixtures=Box2D.b2FixtureDef(
                    shape=polygonShape(box=(hw, hh)),
                    friction=0.5,
                    restitution=0.0,
                ),
            )
            self._wall_bodies.append(body)

        slip_friction = float(terrain_config.get("slip_friction", SLIP_FRICTION))
        slip_body = self._world.CreateStaticBody(
            position=(11.5, 1.0),
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(1.5, 0.08)),
                friction=slip_friction,
                restitution=0.0,
            ),
        )
        self._wall_bodies.append(slip_body)

        self._maze_x_max = 20.0
        self._maze_y_min = 0.0
        self._maze_y_max = 3.0

    def _create_agent(self, terrain_config: dict):
        r = self._agent_radius
        density = self._agent_mass / (math.pi * r * r)
        agent = self._world.CreateDynamicBody(
            position=(self._spawn_x, self._spawn_y),
            fixtures=Box2D.b2FixtureDef(
                shape=circleShape(radius=r),
                density=density,
                friction=0.4,
                restitution=0.0,
            ),
        )
        agent.linearDamping = self._default_linear_damping
        agent.angularDamping = self._default_angular_damping
        self._terrain_bodies["agent"] = agent

    def _raycast(self, p1, p2, exclude_body):
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        length = math.sqrt(dx * dx + dy * dy)
        if length < 1e-6:
            return 1.0
        callback = _RayCastClosestCallback(exclude_body=exclude_body)
        self._world.RayCast(callback, p1, p2)
        return callback.fraction

    def get_agent_position(self):
        agent = self._terrain_bodies.get("agent")
        if agent is None:
            return (0.0, 0.0)
        return (agent.position.x, agent.position.y)

    def get_agent_velocity(self):
        """Returns (0, 0) always — velocity sensor is hidden/unreliable; agent must infer from position over time."""
        return (0.0, 0.0)

    def get_whisker_readings(self):
        agent = self._terrain_bodies.get("agent")
        if agent is None:
            return [self._whisker_max_range] * 3
        x, y = agent.position.x, agent.position.y
        r = self._whisker_max_range
        directions = [(1, 0), (0, 1), (0, -1)]
        out = []
        for dx, dy in directions:
            p2 = (x + dx * r, y + dy * r)
            frac = self._raycast((x, y), p2, agent)
            out.append(frac * r)
        # Sensor blind zone: when x in [lo, hi], front whisker returns max (blind)
        if (
            self._whisker_blind_front_x_lo <= x <= self._whisker_blind_front_x_hi
            and self._whisker_blind_front_x_hi > self._whisker_blind_front_x_lo
        ):
            out[0] = r
        # Sensor delay: return readings from N steps ago
        delay = max(0, self._whisker_delay_steps)
        self._whisker_readings_history.append(tuple(out))
        max_history = delay + 5
        if len(self._whisker_readings_history) > max_history:
            self._whisker_readings_history = self._whisker_readings_history[-max_history:]
        if delay > 0 and len(self._whisker_readings_history) > delay:
            return list(self._whisker_readings_history[-(delay + 1)])
        return out

    def apply_agent_force(self, force_x, force_y):
        max_f = 80.0
        self._force_x = max(-max_f, min(max_f, float(force_x)))
        self._force_y = max(-max_f, min(max_f, float(force_y)))

    def step(self, time_step):
        agent = self._terrain_bodies.get("agent")
        if agent is not None:
            x, y = agent.position.x, agent.position.y
            vx, vy = agent.linearVelocity.x, agent.linearVelocity.y
            speed = math.sqrt(vx * vx + vy * vy)
            # Check for behavioral unlock: must be in activation zone, applying backward force at low speed
            in_activation_zone = ACTIVATION_X_MIN <= x <= ACTIVATION_X_MAX
            if (in_activation_zone and self._force_x < self._backward_fx_threshold and speed < self._backward_speed_max):
                self._backward_steps += 1
                if self._backward_steps >= self._backward_steps_required:
                    self._behavioral_unlock = True
            else:
                self._backward_steps = 0

            # Apply user force first
            if self._force_x != 0.0 or self._force_y != 0.0:
                agent.ApplyForceToCenter((self._force_x, self._force_y), True)
                self._force_x = 0.0
                self._force_y = 0.0

            # Momentum-drain
            if MOMENTUM_DRAIN_X_MIN <= x <= MOMENTUM_DRAIN_X_MAX:
                vx_, vy_ = agent.linearVelocity.x, agent.linearVelocity.y
                d = self._momentum_drain_damping
                agent.ApplyForceToCenter(
                    (vx_ * (-d), vy_ * (-d)), True
                )

            # Current zone
            if CURRENT_X_MIN <= x <= CURRENT_X_MAX:
                agent.ApplyForceToCenter((-self._current_force_back, 0), True)

            # Wind
            if WIND_X_MIN <= x <= WIND_X_MAX:
                step = getattr(self, '_current_step', 0)
                wind_y = -(
                    self._wind_base_down
                    + self._wind_oscillation_amp
                    * math.sin(step * self._wind_oscillation_omega)
                )
                agent.ApplyForceToCenter((0, wind_y), True)

            # Exit barrier: until behavioral condition met (no spatial triggers)
            if EXIT_BARRIER_X_LO <= x <= EXIT_BARRIER_X_HI and not self._behavioral_unlock:
                agent.ApplyForceToCenter((-self._exit_barrier_force, 0), True)

            # One-way: past x=10.2 cannot go left
            vx = agent.linearVelocity.x
            if x > ONEWAY_X and vx < ONEWAY_VX_THRESHOLD:
                agent.ApplyForceToCenter((ONEWAY_FORCE_RIGHT, 0), True)

        self._world.Step(time_step, 10, 10)
        self._current_step += 1

    def has_reached_exit(self):
        x, y = self.get_agent_position()
        return (
            x >= self._exit_x_min
            and self._exit_y_min <= y <= self._exit_y_max
        )

    def get_terrain_bounds(self):
        return {
            "maze_x_max": self._maze_x_max,
            "maze_y_min": self._maze_y_min,
            "maze_y_max": self._maze_y_max,
            "exit_x_min": self._exit_x_min,
            "exit_y_min": self._exit_y_min,
            "exit_y_max": self._exit_y_max,
            "whisker_max_range": self._whisker_max_range,
        }

    def get_agent_body(self):
        return self._terrain_bodies.get("agent")
