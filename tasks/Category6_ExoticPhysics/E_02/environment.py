"""
E-02: Thick Air (Hard) — environment module.
Craft in viscous fluid; path has physical gates (gaps), momentum-drain, slippery,
and oscillating-wind zones. Heat limit constrains total thrust. Phenomena are
discoverable via interaction and feedback; exact zone boundaries are not given in prompt.
"""
import math
import Box2D
from Box2D.b2 import world, polygonShape, staticBody, dynamicBody


class Sandbox:
    """
    Hard E-02: Gates + momentum-drain + slippery + oscillating wind.
    Craft must pass through narrow gaps, overcome drain/slip/wind, reach target without overheating.
    """

    CRAFT_START_X = 8.0
    CRAFT_START_Y = 2.0
    TARGET_X_MIN = 28.0
    TARGET_X_MAX = 32.0
    TARGET_Y_MIN = 2.0
    TARGET_Y_MAX = 5.0

    OVERHEAT_LIMIT = 72000.0  # Hard but solvable with efficient trajectory

    DEFAULT_LINEAR_DAMPING = 4.0
    DEFAULT_ANGULAR_DAMPING = 3.0

    # Gate definitions (for internal use / reference agent; not exposed in prompt)
    GATE1_X_LO, GATE1_X_HI = 12.0, 14.0
    GATE1_Y_LO, GATE1_Y_HI = 1.0, 2.8   # gap: craft center y in [1.0, 2.8] (bottom bar y<1.0)
    GATE2_X_LO, GATE2_X_HI = 22.0, 24.0
    GATE2_Y_LO, GATE2_Y_HI = 1.8, 3.0

    # Zone x-ranges (momentum drain, slippery, wind) — discoverable
    DRAIN_X_LO, DRAIN_X_HI = 14.5, 17.0   # after gate 1 so craft can reach gate first
    SLIP_X_LO, SLIP_X_HI = 17.5, 20.0     # after drain
    WIND_X_LO, WIND_X_HI = 20.5, 28.0

    DRAIN_VELOCITY_FACTOR = 0.5    # velocity *= this each step in drain zone (default)
    SLIP_BACKWARD_FORCE = -28.0    # extra Fx in slippery zone (default)
    WIND_AMPLITUDE = 20.0
    WIND_OMEGA = 0.055

    def __init__(self, *, terrain_config=None, physics_config=None):
        terrain_config = terrain_config or {}
        physics_config = physics_config or {}
        self._terrain_config = dict(terrain_config)
        self._physics_config = dict(physics_config)
        gravity = tuple(physics_config.get("gravity", (0, -3)))  # lighter so craft can lift off ground
        self._linear_damping = float(physics_config.get("linear_damping", self.DEFAULT_LINEAR_DAMPING))
        self._angular_damping = float(physics_config.get("angular_damping", self.DEFAULT_ANGULAR_DAMPING))
        self._drain_velocity_factor = float(physics_config.get("drain_velocity_factor", self.DRAIN_VELOCITY_FACTOR))
        self._slip_backward_force = float(physics_config.get("slip_backward_force", self.SLIP_BACKWARD_FORCE))
        self._wind_amplitude = float(physics_config.get("wind_amplitude", self.WIND_AMPLITUDE))
        self._wind_omega = float(physics_config.get("wind_omega", self.WIND_OMEGA))
        self._overheat_limit = float(physics_config.get("overheat_limit", self.OVERHEAT_LIMIT))
        self._world = world(gravity=gravity, doSleep=True)
        self._terrain_bodies = {}
        self._heat = 0.0
        self._overheated = False
        self._pending_thrust = (0.0, 0.0)
        self._step_count = 0
        self.world = self._world
        self.bodies = []
        self.joints = []
        self._craft_start_x = float(terrain_config.get("craft_start_x", self.CRAFT_START_X))
        self._craft_start_y = float(terrain_config.get("craft_start_y", self.CRAFT_START_Y))
        self._create_terrain(terrain_config)
        self._create_craft(terrain_config)

    def _create_terrain(self, terrain_config: dict):
        """Ground + two gates (vertical walls with gaps)."""
        ground_length = 50.0
        ground_height = 1.0
        ground = self._world.CreateStaticBody(
            position=(ground_length / 2, ground_height / 2),
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(ground_length / 2, ground_height / 2)),
                friction=0.5,
            ),
        )
        self._terrain_bodies["ground"] = ground
        self._ground_y = ground_height

        # Gates: vertical walls with gaps (optional — set E02_USE_GATES=True to enable)
        bar_w = 0.25
        if terrain_config.get("use_gates", True):
            # Gate 1: gap y in [1.0, 2.8]; bottom bar y 0 to 1.0
            for (px, py, hw, hh) in [
                (self.GATE1_X_LO - bar_w / 2, 0.5, bar_w / 2, 0.5),
                (self.GATE1_X_LO - bar_w / 2, 4.4, bar_w / 2, 1.6),
                (self.GATE1_X_HI + bar_w / 2, 0.5, bar_w / 2, 0.5),
                (self.GATE1_X_HI + bar_w / 2, 4.4, bar_w / 2, 1.6),
            ]:
                self._world.CreateStaticBody(
                    position=(px, py),
                    fixtures=Box2D.b2FixtureDef(
                        shape=polygonShape(box=(hw, hh)),
                        friction=0.4,
                    ),
                )
            # Gate 2: gap y in [1.8, 3.0], x in [22, 24]
            for (px, py, hw, hh) in [
                (self.GATE2_X_LO - bar_w / 2, 0.9, bar_w / 2, 0.9),
                (self.GATE2_X_LO - bar_w / 2, 3.9, bar_w / 2, 0.9),
                (self.GATE2_X_HI + bar_w / 2, 0.9, bar_w / 2, 0.9),
                (self.GATE2_X_HI + bar_w / 2, 3.9, bar_w / 2, 0.9),
            ]:
                self._world.CreateStaticBody(
                    position=(px, py),
                    fixtures=Box2D.b2FixtureDef(
                        shape=polygonShape(box=(hw, hh)),
                        friction=0.4,
                    ),
                )

    def _create_craft(self, terrain_config: dict):
        sx, sy = self._craft_start_x, self._craft_start_y
        w, h = 1.0, 0.5
        craft = self._world.CreateDynamicBody(
            position=(sx, sy),
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(w / 2, h / 2)),
                density=50.0,
                friction=0.3,
                restitution=0.1,
            ),
        )
        craft.linearDamping = self._linear_damping
        craft.angularDamping = self._angular_damping
        self._terrain_bodies["craft"] = craft

    def step(self, time_step):
        """Apply thrust, zone effects (drain/slip/wind), accumulate heat, then physics step."""
        craft = self._terrain_bodies.get("craft")
        if not craft:
            self._pending_thrust = (0.0, 0.0)
            self._world.Step(time_step, 10, 10)
            self._step_count += 1
            return

        x, y = craft.position.x, craft.position.y

        if not self._overheated:
            fx, fy = self._pending_thrust
            craft.ApplyForceToCenter((fx, fy), wake=True)
            thrust_mag = math.sqrt(fx * fx + fy * fy)
            self._heat += thrust_mag * time_step
            if self._heat >= self._overheat_limit:
                self._overheated = True
        self._pending_thrust = (0.0, 0.0)

        # Momentum-drain zone: velocity heavily reduced each step
        if self.DRAIN_X_LO <= x <= self.DRAIN_X_HI:
            vx, vy = craft.linearVelocity.x, craft.linearVelocity.y
            craft.linearVelocity = (vx * self._drain_velocity_factor, vy * self._drain_velocity_factor)
            craft.angularVelocity *= self._drain_velocity_factor

        # Slippery zone: backward force (simulates slip)
        if self.SLIP_X_LO <= x <= self.SLIP_X_HI:
            craft.ApplyForceToCenter((self._slip_backward_force, 0), wake=True)

        # Oscillating wind zone
        if self.WIND_X_LO <= x <= self.WIND_X_HI:
            wind_fy = self._wind_amplitude * math.sin(self._wind_omega * self._step_count)
            craft.ApplyForceToCenter((0, wind_fy), wake=True)

        self._world.Step(time_step, 10, 10)
        self._step_count += 1

    def apply_thrust(self, fx, fy):
        if self._overheated:
            return
        self._pending_thrust = (float(fx), float(fy))

    def get_craft_position(self):
        craft = self._terrain_bodies.get("craft")
        if craft:
            return (craft.position.x, craft.position.y)
        return None

    def get_craft_velocity(self):
        craft = self._terrain_bodies.get("craft")
        if craft:
            return (craft.linearVelocity.x, craft.linearVelocity.y)
        return None

    def get_heat(self):
        return self._heat

    def is_overheated(self):
        return self._overheated

    def get_step_count(self):
        """Current simulation step (for compensating time-varying disturbances)."""
        return self._step_count

    def get_overheat_limit(self):
        """Overheat limit (N·s) for this run; may differ in mutated environments."""
        return self._overheat_limit

    def get_terrain_bounds(self):
        return {
            "ground_y": self._ground_y,
            "craft_start": {"x": self._craft_start_x, "y": self._craft_start_y},
            "target_zone": {
                "x_min": self.TARGET_X_MIN,
                "x_max": self.TARGET_X_MAX,
                "y_min": self.TARGET_Y_MIN,
                "y_max": self.TARGET_Y_MAX,
            },
        }