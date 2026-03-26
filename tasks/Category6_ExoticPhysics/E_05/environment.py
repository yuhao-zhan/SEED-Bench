"""
E-05: The Magnet task environment module.
Invisible repulsive/attractive force fields act on a body. Agent must navigate using thrust;
failure: stuck in local minimum (never reach target).

Hard mode: dense repulsive wall, oscillating fields, narrow passage, attractive traps.
Magnets can be static (x, y, strength) or oscillating (x, y, base, amplitude, omega).
"""
import math
import Box2D
from Box2D.b2 import world, polygonShape, staticBody, dynamicBody


def default_magnets():
    """
    Very hard: two phase-offset oscillating gates (pass gate1, wait, pass gate2),
    then oscillating keyhole. Format: (x,y,s) static; (x,y,base,amp,omega) or
    (x,y,base,amp,omega,phase) oscillating.
    """
    return [
        # Wall
        (12.0, 4.0, -300.0),
        (12.0, 5.0, -300.0),
        (12.0, 6.0, -300.0),
        (12.0, 7.0, -300.0),
        (12.0, 8.0, -280.0),
        (12.0, 8.3, -260.0),
        # Ceiling
        (11.0, 9.7, -200.0),
        (13.0, 9.7, -200.0),
        (15.0, 9.7, -200.0),
        (17.0, 9.7, -200.0),
        (19.0, 9.7, -200.0),
        (21.0, 9.7, -180.0),
        # Gate 1: weak steps 8–20 (period 52)
        (15.0, 9.0, -250.0, 230.0, 0.12),
        # Gate 2: phase π, faster omega — weak window ~5 steps every 42
        (20.0, 9.0, -350.0, 330.0, 0.15, 3.14159),
        # Attractive trap
        (19.0, 3.0, 160.0),
        (21.0, 3.5, 130.0),
        # Keyhole sides (static)
        (24.0, 5.0, -190.0),
        (24.0, 8.2, -180.0),
        # Oscillating keyhole center — weak ~steps 5–15 in 38-step cycle
        (24.0, 6.6, -180.0, 160.0, 0.165),
        # Repulsive near target
        (26.0, 5.5, -130.0),
        (27.0, 9.5, -120.0),
        (29.5, 7.5, 95.0),
    ]


class Sandbox:
    """
    Sandbox for E-05: The Magnet.
    A body is subject to invisible force fields (magnets); agent applies thrust to reach target.
    """

    BODY_START_X = 8.0
    BODY_START_Y = 5.0
    TARGET_X_MIN = 28.0
    TARGET_X_MAX = 32.0
    TARGET_Y_MIN = 6.0   # Unified with evaluator/prompt
    TARGET_Y_MAX = 9.0

    # Pit zone (forbidden region) constants
    PIT_X_MIN = 16.0
    PIT_X_MAX = 24.0
    PIT_Y_MAX = 5.5

    # Single source of truth for step limit; prompt time budget should match (see main.py when max_steps is None).
    MAX_STEPS = 10000

    # Minimum distance for force computation (avoid singularity)
    MAGNET_R_MIN = 0.5

    def __init__(self, *, terrain_config=None, physics_config=None):
        terrain_config = terrain_config or {}
        physics_config = physics_config or {}
        self._terrain_config = dict(terrain_config)
        self._physics_config = dict(physics_config)
        gravity = tuple(physics_config.get("gravity", (0, -10)))
        self._linear_damping = float(physics_config.get("linear_damping", 0.28))
        self._angular_damping = float(physics_config.get("angular_damping", 0.15))

        self._world = world(gravity=gravity, doSleep=True)
        self._terrain_bodies = {}
        self._pending_thrust = (0.0, 0.0)
        self._magnets = list(terrain_config.get("magnets", default_magnets()))
        self._step_count = 0
        self._max_thrust_magnitude = float(terrain_config.get("max_thrust", 165.0))
        self._body_start_x = float(terrain_config.get("body_start_x", self.BODY_START_X))
        self._body_start_y = float(terrain_config.get("body_start_y", self.BODY_START_Y))

        self.world = self._world
        self.bodies = []
        self.joints = []

        self._create_terrain(terrain_config)
        self._create_body(terrain_config)

    def _create_terrain(self, terrain_config: dict):
        """Ground."""
        ground_length = 45.0
        ground_height = 1.0
        ground = self._world.CreateStaticBody(
            position=(ground_length / 2, ground_height / 2),
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(ground_length / 2, ground_height / 2)),
                friction=0.4,
            ),
        )
        self._terrain_bodies["ground"] = ground
        self._ground_y = ground_height

    def _create_body(self, terrain_config: dict):
        """Body that will be pushed by magnets and thrust."""
        sx, sy = self._body_start_x, self._body_start_y
        w, h = 0.8, 0.4
        body = self._world.CreateDynamicBody(
            position=(sx, sy),
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(w / 2, h / 2)),
                density=30.0,
                friction=0.3,
                restitution=0.1,
            ),
        )
        body.linearDamping = self._linear_damping
        body.angularDamping = self._angular_damping
        self._terrain_bodies["body"] = body

    def step(self, time_step):
        """Apply magnet forces, then pending thrust (clamped), then step physics."""
        self._step_count += 1
        body = self._terrain_bodies.get("body")
        if body:
            bx, by = body.position.x, body.position.y
            for m in self._magnets:
                if len(m) == 3:
                    mx, my, strength = m[0], m[1], m[2]
                else:
                    mx, my, base, amp, omega = m[0], m[1], m[2], m[3], m[4]
                    phase = m[5] if len(m) >= 6 else 0.0
                    strength = base + amp * math.sin(self._step_count * omega + phase)
                dx = mx - bx
                dy = my - by
                r = math.sqrt(dx * dx + dy * dy) + 1e-6
                r = max(r, self.MAGNET_R_MIN)
                scale = strength / (r * r * r)
                fx = scale * dx
                fy = scale * dy
                body.ApplyForceToCenter((fx, fy), wake=True)
            tx, ty = self._pending_thrust
            thrust_mag = math.sqrt(tx * tx + ty * ty)
            if thrust_mag > self._max_thrust_magnitude:
                scale = self._max_thrust_magnitude / thrust_mag
                tx, ty = tx * scale, ty * scale
            body.ApplyForceToCenter((tx, ty), wake=True)
        self._pending_thrust = (0.0, 0.0)
        self._world.Step(time_step, 10, 10)

    def apply_thrust(self, fx, fy):
        """Apply thrust to the body for the next physics step."""
        self._pending_thrust = (float(fx), float(fy))

    def get_body_position(self):
        """Body center position (x, y)."""
        body = self._terrain_bodies.get("body")
        if body:
            return (body.position.x, body.position.y)
        return None

    def get_body_velocity(self):
        """Body velocity (vx, vy)."""
        body = self._terrain_bodies.get("body")
        if body:
            return (body.linearVelocity.x, body.linearVelocity.y)
        return None

    def get_step_count(self):
        """Current simulation step (for agents that need timing)."""
        return self._step_count

    def get_terrain_bounds(self):
        """For evaluator/renderer: start, target zone, pit, and thrust limit. Magnets are not exposed (invisible)."""
        return {
            "ground_y": self._ground_y,
            "body_start": {"x": self._body_start_x, "y": self._body_start_y},
            "target_zone": {
                "x_min": self.TARGET_X_MIN,
                "x_max": self.TARGET_X_MAX,
                "y_min": self.TARGET_Y_MIN,
                "y_max": self.TARGET_Y_MAX,
            },
            "pit_zone": {
                "x_min": self.PIT_X_MIN,
                "x_max": self.PIT_X_MAX,
                "y_max": self.PIT_Y_MAX,
            },
            "max_thrust": self._max_thrust_magnitude,
        }
