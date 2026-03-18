"""
E-03: Slippery World task environment module (hard variant v2).
Friction is near zero; movement requires thrust. The path contains:
- Momentum drain, reversed horizontal thrust, oscillating crosswind (discoverable).
- A checkpoint zone: sled must enter it before the final target counts (sequence constraint).
- A speed-penalty zone: excessive speed is heavily damped (discoverable).
- A vertical-thrust-reverse zone: vertical thrust effect is negated near the final target (discoverable).
Checkpoint and target zone bounds are stated in the task prompt; path effects (momentum drain, thrust scale, etc.) are discoverable from feedback.
"""
import math
import Box2D
from Box2D.b2 import world, polygonShape, staticBody, dynamicBody


class Sandbox:
    """
    Sandbox for E-03: Slippery World (hard v2).
    - Checkpoint zone: must pass through (x in [17.5, 19], y in [3.8, 4.5]) before final target counts.
    - Speed-penalty zone [22, 26]: if speed > 4.0 m/s, velocity scaled down each step.
    - Vertical-reverse zone [26.5, 28.5]: fy_actual = -fy (discoverable when approaching final band).
    Plus existing: momentum drain, reverse horizontal thrust, wind zone.
    """

    SLED_START_X = 8.0
    SLED_START_Y = 2.0
    TARGET_X_MIN = 28.0
    TARGET_X_MAX = 32.0
    TARGET_Y_MIN = 2.2
    TARGET_Y_MAX = 2.8

    DEFAULT_GROUND_FRICTION = 0.02
    DEFAULT_SLED_FRICTION = 0.02

    # Checkpoint A (first): must enter before B and final count
    CHECKPOINT_X_LO = 17.5
    CHECKPOINT_X_HI = 19.0
    CHECKPOINT_Y_LO = 3.8
    CHECKPOINT_Y_HI = 4.5
    # Checkpoint B (second): must enter after A, before final
    CHECKPOINT_B_X_LO = 23.0
    CHECKPOINT_B_X_HI = 24.5
    CHECKPOINT_B_Y_LO = 2.5
    CHECKPOINT_B_Y_HI = 3.2

    # Thrust scaling zone: applied thrust is scaled down (discoverable: "thrust barely moves")
    THRUST_SCALE_X_LO = 19.5
    THRUST_SCALE_X_HI = 21.0
    THRUST_SCALE_FACTOR = 0.5
    # Oscillating horizontal force zone (discoverable from velocity/position)
    OSCILLATING_FX_X_LO = 21.0
    OSCILLATING_FX_X_HI = 27.0
    OSCILLATING_FX_AMP = 30.0
    OSCILLATING_FX_OMEGA = 0.04

    MOMENTUM_DRAIN_X_LO = 11.0
    MOMENTUM_DRAIN_X_HI = 17.0
    MOMENTUM_DRAIN_FACTOR = 0.85
    REVERSE_THRUST_X_LO = 20.0
    REVERSE_THRUST_X_HI = 25.0
    WIND_ZONE_X_LO = 14.0
    WIND_ZONE_X_HI = 28.0
    WIND_FY_BASE = 20.0
    WIND_FY_AMP = 35.0
    WIND_OMEGA = 0.06

    # Speed penalty: if in zone and speed > threshold, velocity heavily damped
    SPEED_PENALTY_X_LO = 22.0
    SPEED_PENALTY_X_HI = 26.0
    SPEED_PENALTY_THRESHOLD = 4.0
    SPEED_PENALTY_FACTOR = 0.35

    # Vertical thrust reversed in this x-range (e.g. "thrust up" pushes down)
    VERT_REVERSE_X_LO = 26.5
    VERT_REVERSE_X_HI = 28.5

    def __init__(self, *, terrain_config=None, physics_config=None):
        terrain_config = terrain_config or {}
        physics_config = physics_config or {}
        self._terrain_config = dict(terrain_config)
        self._physics_config = dict(physics_config)

        gravity = physics_config.get("gravity", (0, -10))
        if callable(gravity):
            gravity = gravity(0.0)
        self._gravity = tuple(gravity)
        self._ground_friction = float(terrain_config.get("ground_friction", self.DEFAULT_GROUND_FRICTION))
        self._sled_friction = float(terrain_config.get("sled_friction", self.DEFAULT_SLED_FRICTION))
        self._linear_damping = float(physics_config.get("linear_damping", 0.0))
        self._angular_damping = float(physics_config.get("angular_damping", 0.0))
        # Optional zone overrides (invisible to agent; for mutated stages)
        self._momentum_drain_factor = float(physics_config.get("momentum_drain_factor", self.MOMENTUM_DRAIN_FACTOR))
        self._thrust_scale_factor = float(physics_config.get("thrust_scale_factor", self.THRUST_SCALE_FACTOR))
        self._speed_penalty_factor = float(physics_config.get("speed_penalty_factor", self.SPEED_PENALTY_FACTOR))
        self._speed_penalty_threshold = float(physics_config.get("speed_penalty_threshold", self.SPEED_PENALTY_THRESHOLD))

        self._world = world(gravity=self._gravity, doSleep=True)
        self._terrain_bodies = {}
        self._pending_thrust = (0.0, 0.0)
        self._step_count = 0
        self._checkpoint_a_reached = False
        self._checkpoint_b_reached = False

        self.world = self._world
        self.bodies = []
        self.joints = []

        self._sled_start_x = float(terrain_config.get("sled_start_x", self.SLED_START_X))
        self._sled_start_y = float(terrain_config.get("sled_start_y", self.SLED_START_Y))
        self._create_terrain(terrain_config)
        self._create_sled(terrain_config)

    def _create_terrain(self, terrain_config: dict):
        ground_length = 50.0
        ground_height = 1.0
        ground = self._world.CreateStaticBody(
            position=(ground_length / 2, ground_height / 2),
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(ground_length / 2, ground_height / 2)),
                friction=self._ground_friction,
            ),
        )
        self._terrain_bodies["ground"] = ground
        self._ground_y = ground_height

    def _create_sled(self, terrain_config: dict):
        sx, sy = self._sled_start_x, self._sled_start_y
        w, h = 1.0, 0.5
        sled = self._world.CreateDynamicBody(
            position=(sx, sy),
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(w / 2, h / 2)),
                density=50.0,
                friction=self._sled_friction,
                restitution=0.1,
            ),
        )
        sled.linearDamping = self._linear_damping
        sled.angularDamping = self._angular_damping
        self._terrain_bodies["sled"] = sled

    def step(self, time_step):
        sled = self._terrain_bodies.get("sled")
        if not sled:
            self._pending_thrust = (0.0, 0.0)
            self._world.Step(time_step, 10, 10)
            self._step_count += 1
            return

        fx, fy = self._pending_thrust
        self._pending_thrust = (0.0, 0.0)
        sx, sy = sled.position.x, sled.position.y

        # Checkpoint A
        if (self.CHECKPOINT_X_LO <= sx <= self.CHECKPOINT_X_HI and
                self.CHECKPOINT_Y_LO <= sy <= self.CHECKPOINT_Y_HI):
            self._checkpoint_a_reached = True
        # Checkpoint B (must pass A first; order enforced in evaluator)
        if (self.CHECKPOINT_B_X_LO <= sx <= self.CHECKPOINT_B_X_HI and
                self.CHECKPOINT_B_Y_LO <= sy <= self.CHECKPOINT_B_Y_HI):
            self._checkpoint_b_reached = True

        # Thrust scaling zone: applied thrust reduced (discoverable: "barely moves here")
        if self.THRUST_SCALE_X_LO <= sx <= self.THRUST_SCALE_X_HI:
            fx *= self._thrust_scale_factor
            fy *= self._thrust_scale_factor

        # Reverse horizontal thrust zone
        if self.REVERSE_THRUST_X_LO <= sx <= self.REVERSE_THRUST_X_HI:
            fx = -fx

        # Vertical thrust reverse zone: fy is negated (discoverable near final target)
        if self.VERT_REVERSE_X_LO <= sx <= self.VERT_REVERSE_X_HI:
            fy = -fy

        # Wind zone
        if self.WIND_ZONE_X_LO <= sx <= self.WIND_ZONE_X_HI:
            fy += self.WIND_FY_BASE + self.WIND_FY_AMP * math.sin(self._step_count * self.WIND_OMEGA)

        # Oscillating horizontal force zone (discoverable from feedback)
        if self.OSCILLATING_FX_X_LO <= sx <= self.OSCILLATING_FX_X_HI:
            fx += self.OSCILLATING_FX_AMP * math.sin(self._step_count * self.OSCILLATING_FX_OMEGA)

        sled.ApplyForceToCenter((fx, fy), wake=True)
        self._world.Step(time_step, 10, 10)

        # Momentum drain
        if self.MOMENTUM_DRAIN_X_LO <= sled.position.x <= self.MOMENTUM_DRAIN_X_HI:
            vx, vy = sled.linearVelocity.x, sled.linearVelocity.y
            sled.linearVelocity = (vx * self._momentum_drain_factor, vy * self._momentum_drain_factor)

        # Speed penalty: in zone, if speed > threshold, heavily damp velocity
        if self.SPEED_PENALTY_X_LO <= sled.position.x <= self.SPEED_PENALTY_X_HI:
            vx, vy = sled.linearVelocity.x, sled.linearVelocity.y
            speed = math.sqrt(vx * vx + vy * vy)
            if speed > self._speed_penalty_threshold:
                sled.linearVelocity = (vx * self._speed_penalty_factor, vy * self._speed_penalty_factor)

        self._step_count += 1

    def apply_thrust(self, fx, fy):
        self._pending_thrust = (float(fx), float(fy))

    def get_sled_position(self):
        sled = self._terrain_bodies.get("sled")
        if sled:
            return (sled.position.x, sled.position.y)
        return None

    def get_sled_velocity(self):
        sled = self._terrain_bodies.get("sled")
        if sled:
            return (sled.linearVelocity.x, sled.linearVelocity.y)
        return None

    def get_checkpoint_a_reached(self):
        return getattr(self, "_checkpoint_a_reached", False)

    def get_checkpoint_b_reached(self):
        return getattr(self, "_checkpoint_b_reached", False)

    def get_checkpoint_reached(self):
        """True only if both checkpoint A and B have been reached (sequence)."""
        return self.get_checkpoint_a_reached() and self.get_checkpoint_b_reached()

    def get_terrain_bounds(self):
        return {
            "ground_y": self._ground_y,
            "sled_start": {"x": self._sled_start_x, "y": self._sled_start_y},
            "target_zone": {
                "x_min": self.TARGET_X_MIN,
                "x_max": self.TARGET_X_MAX,
                "y_min": self.TARGET_Y_MIN,
                "y_max": self.TARGET_Y_MAX,
            },
            "checkpoint_zone": {
                "x_min": self.CHECKPOINT_X_LO,
                "x_max": self.CHECKPOINT_X_HI,
                "y_min": self.CHECKPOINT_Y_LO,
                "y_max": self.CHECKPOINT_Y_HI,
            },
            "checkpoint_b_zone": {
                "x_min": self.CHECKPOINT_B_X_LO,
                "x_max": self.CHECKPOINT_B_X_HI,
                "y_min": self.CHECKPOINT_B_Y_LO,
                "y_max": self.CHECKPOINT_B_Y_HI,
            },
        }
