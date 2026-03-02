"""
E-01: Inverted Gravity task environment module.
Gravity direction is inverted or time-varying (e.g. oscillating). Agents must adapt so that
nothing flies out of the bounded arena. Failure: any body leaves the boundary.
"""
import math
import Box2D
from Box2D.b2 import world, polygonShape, staticBody, dynamicBody, weldJoint, revoluteJoint


def default_gravity_function(t):
    """
    Default gravity vector for E-01: oscillates between downward (-10) and upward (+10).
    Period 5 seconds. Mutations can override via physics_config['gravity_function'].
    """
    # Oscillate: g_y = 10 * sin(2*pi*t/5) => period 5s, range [-10, +10]
    g_y = 10.0 * math.sin(2.0 * math.pi * t / 5.0)
    return (0.0, g_y)


class Sandbox:
    """
    Sandbox for E-01: Inverted Gravity.
    Bounded arena with time-varying gravity. All dynamic bodies must stay inside bounds.
    """

    # Arena bounds (meters). Out of bounds = failure.
    ARENA_X_MIN = 0.0
    ARENA_X_MAX = 40.0
    ARENA_Y_MIN = 0.0
    ARENA_Y_MAX = 20.0

    # Build zone for agent structures (narrower vertically: no single beam can span floor–ceiling)
    BUILD_ZONE_X_MIN = 12.0
    BUILD_ZONE_X_MAX = 28.0
    BUILD_ZONE_Y_MIN = 6.0
    BUILD_ZONE_Y_MAX = 18.0  # extended so top connector can sit above second forbidden band

    MAX_STRUCTURE_MASS = 200.0
    MAX_BEAM_COUNT = 12  # no more than this many beams; agent must infer from feedback

    # Obstacle 1: central horizontal bar (mid-height)
    OBSTACLE1_X_MIN = 18.0
    OBSTACLE1_X_MAX = 22.0
    OBSTACLE1_Y_CENTER = 10.0
    OBSTACLE1_HALF_W = 2.0
    OBSTACLE1_HALF_H = 0.25
    # Obstacle 2: full-width horizontal bar at upper mid — blocks naive bridge at y=13 and pillar at x=14
    OBSTACLE2_X_MIN = 14.0
    OBSTACLE2_X_MAX = 26.0
    OBSTACLE2_Y_CENTER = 13.0
    OBSTACLE2_HALF_W = 6.0
    OBSTACLE2_HALF_H = 0.25
    # Obstacle 3: small block at bridge level — forces split bridge + top connector (no single span)
    OBSTACLE3_X_MIN = 18.5
    OBSTACLE3_X_MAX = 19.5
    OBSTACLE3_Y_CENTER = 14.0
    OBSTACLE3_HALF_W = 0.5
    OBSTACLE3_HALF_H = 0.25
    # Forbidden zone 1: no beam center allowed (rule-only; agent must infer from feedback)
    FORBIDDEN_X_MIN = 19.0
    FORBIDDEN_X_MAX = 20.0
    FORBIDDEN_Y_MIN = 14.5
    FORBIDDEN_Y_MAX = 15.5
    # Forbidden zone 2: narrow band so naive top connector at y=16 fails; must step to y=17
    FORBIDDEN2_X_MIN = 18.0
    FORBIDDEN2_X_MAX = 21.0
    FORBIDDEN2_Y_MIN = 15.9
    FORBIDDEN2_Y_MAX = 16.1
    MIN_BEAM_SIZE = 0.1
    MAX_BEAM_SIZE = 5.0

    def __init__(self, *, terrain_config=None, physics_config=None):
        terrain_config = terrain_config or {}
        physics_config = physics_config or {}
        self._terrain_config = dict(terrain_config)
        self._physics_config = dict(physics_config)

        # Mutations can override arena and build zone via terrain_config
        if "arena_y_max" in terrain_config:
            self.ARENA_Y_MAX = float(terrain_config["arena_y_max"])
        if "build_zone_y_max" in terrain_config:
            self.BUILD_ZONE_Y_MAX = float(terrain_config["build_zone_y_max"])

        # Gravity: can be a fixed tuple or a callable (t) -> (gx, gy). Default for E-01: oscillating.
        gravity_spec = physics_config.get("gravity", default_gravity_function)
        if callable(gravity_spec):
            self._gravity_function = gravity_spec
            self._world = world(gravity=(0, -10), doSleep=True)  # initial value
        else:
            g = tuple(gravity_spec)
            self._gravity_function = lambda t: g
            self._world = world(gravity=g, doSleep=True)

        self._time = 0.0
        self._default_linear_damping = float(physics_config.get("linear_damping", 0.0))
        self._default_angular_damping = float(physics_config.get("angular_damping", 0.0))
        self._beam_density_scale = float(physics_config.get("beam_density_scale", 1.0))

        self._bodies = []
        self._joints = []
        self._terrain_bodies = {}

        self.world = self._world
        self.bodies = self._bodies
        self.joints = self._joints

        self._create_terrain(terrain_config)
        self._create_demonstrator_bodies(terrain_config)

    def _create_terrain(self, terrain_config: dict):
        """Create bounded arena: floor, ceiling, left and right walls."""
        w = self.ARENA_X_MAX - self.ARENA_X_MIN
        h_half = 0.5

        # Floor at y = 0
        floor = self._world.CreateStaticBody(
            position=(self.ARENA_X_MIN + w / 2, h_half / 2),
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(w / 2, h_half / 2)),
                friction=0.6,
            ),
        )
        self._terrain_bodies["floor"] = floor

        # Ceiling at y = ARENA_Y_MAX
        ceiling_y = self.ARENA_Y_MAX
        ceiling = self._world.CreateStaticBody(
            position=(self.ARENA_X_MIN + w / 2, ceiling_y + h_half / 2),
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(w / 2, h_half / 2)),
                friction=0.6,
            ),
        )
        self._terrain_bodies["ceiling"] = ceiling

        # Left wall
        wall_h = self.ARENA_Y_MAX
        left_wall = self._world.CreateStaticBody(
            position=(h_half / 2, wall_h / 2),
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(h_half / 2, wall_h / 2)),
                friction=0.6,
            ),
        )
        self._terrain_bodies["left_wall"] = left_wall

        # Right wall
        right_x = self.ARENA_X_MAX
        right_wall = self._world.CreateStaticBody(
            position=(right_x - h_half / 2, wall_h / 2),
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(h_half / 2, wall_h / 2)),
                friction=0.6,
            ),
        )
        self._terrain_bodies["right_wall"] = right_wall

        # Obstacle 1: central horizontal bar (mid-height)
        obs1_cx = (self.OBSTACLE1_X_MIN + self.OBSTACLE1_X_MAX) / 2
        obs1_cy = self.OBSTACLE1_Y_CENTER
        obstacle1 = self._world.CreateStaticBody(
            position=(obs1_cx, obs1_cy),
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(self.OBSTACLE1_HALF_W, self.OBSTACLE1_HALF_H)),
                friction=0.4,
            ),
        )
        self._terrain_bodies["obstacle_1"] = obstacle1
        # Obstacle 2: full-width bar at upper mid (blocks bridge at y=13 and pillar at x=14)
        obs2_cx = (self.OBSTACLE2_X_MIN + self.OBSTACLE2_X_MAX) / 2
        obs2_cy = self.OBSTACLE2_Y_CENTER
        obstacle2 = self._world.CreateStaticBody(
            position=(obs2_cx, obs2_cy),
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(self.OBSTACLE2_HALF_W, self.OBSTACLE2_HALF_H)),
                friction=0.4,
            ),
        )
        self._terrain_bodies["obstacle_2"] = obstacle2
        # Obstacle 3: small block at bridge level (center)
        obs3_cx = (self.OBSTACLE3_X_MIN + self.OBSTACLE3_X_MAX) / 2
        obs3_cy = self.OBSTACLE3_Y_CENTER
        obstacle3 = self._world.CreateStaticBody(
            position=(obs3_cx, obs3_cy),
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(self.OBSTACLE3_HALF_W, self.OBSTACLE3_HALF_H)),
                friction=0.4,
            ),
        )
        self._terrain_bodies["obstacle_3"] = obstacle3

    def _create_demonstrator_bodies(self, terrain_config: dict):
        """Create a few dynamic bodies to visualize gravity effect (no agent solution)."""
        # Skip if disabled (e.g. when agent has built)
        if terrain_config.get("no_demonstrators", False):
            return
        cx = (self.BUILD_ZONE_X_MIN + self.BUILD_ZONE_X_MAX) / 2
        cy = (self.BUILD_ZONE_Y_MIN + self.BUILD_ZONE_Y_MAX) / 2
        for i, (dx, dy) in enumerate([(-3, 0), (0, 0), (3, 0)]):
            body = self._world.CreateDynamicBody(
                position=(cx + dx, cy + dy),
                fixtures=Box2D.b2FixtureDef(
                    shape=polygonShape(box=(0.5, 0.5)),
                    density=2.0,
                    friction=0.4,
                    restitution=0.2,
                ),
            )
            body.linearDamping = self._default_linear_damping
            body.angularDamping = self._default_angular_damping
            self._terrain_bodies[f"demonstrator_{i}"] = body

    def step(self, time_step):
        """Advance physics: update gravity from function then step world."""
        self._time += time_step
        gx, gy = self._gravity_function(self._time)
        self._world.gravity = (float(gx), float(gy))
        self._world.Step(time_step, 10, 10)

    def add_beam(self, x, y, width, height, angle=0, density=1.0):
        """Add a beam (rigid rectangular body). Constrained to MIN/MAX size."""
        width = max(self.MIN_BEAM_SIZE, min(width, self.MAX_BEAM_SIZE))
        height = max(self.MIN_BEAM_SIZE, min(height, self.MAX_BEAM_SIZE))
        density = density * self._beam_density_scale
        body = self._world.CreateDynamicBody(
            position=(x, y),
            angle=angle,
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(width / 2, height / 2)),
                density=density,
                friction=0.5,
            ),
        )
        body.linearDamping = self._default_linear_damping
        body.angularDamping = self._default_angular_damping
        self._bodies.append(body)
        return body

    def add_joint(self, body_a, body_b, anchor_point, type="rigid"):
        """
        Add a joint between two bodies. If body_b is None, anchor to terrain by anchor x,y:
        - to floor (y near 0), ceiling (y near ARENA_Y_MAX), or walls by position.
        """
        if body_a is None:
            raise ValueError("add_joint: body_a cannot be None.")
        anchor_x, anchor_y = anchor_point[0], anchor_point[1]

        if body_b is None:
            # Anchor to nearest terrain: floor, ceiling, or walls
            if anchor_y < self.ARENA_Y_MAX * 0.25:
                body_b = self._terrain_bodies.get("floor")
            elif anchor_y > self.ARENA_Y_MAX * 0.75:
                body_b = self._terrain_bodies.get("ceiling")
            elif anchor_x < self.ARENA_X_MAX * 0.25:
                body_b = self._terrain_bodies.get("left_wall")
            else:
                body_b = self._terrain_bodies.get("right_wall")
            if body_b is None:
                body_b = self._terrain_bodies.get("floor")

        if type == "rigid":
            joint = self._world.CreateWeldJoint(
                bodyA=body_a, bodyB=body_b,
                anchor=(anchor_x, anchor_y), collideConnected=False,
            )
        elif type == "pivot":
            joint = self._world.CreateRevoluteJoint(
                bodyA=body_a, bodyB=body_b,
                anchor=(anchor_x, anchor_y), collideConnected=False,
            )
        else:
            raise ValueError(f"Unknown joint type: {type}")
        self._joints.append(joint)
        return joint

    def get_structure_mass(self):
        """Total mass of all agent-created bodies (beams)."""
        total = 0.0
        for body in self._bodies:
            total += body.mass
        return total

    def set_material_properties(self, body, restitution=0.2):
        """Set restitution (bounciness) for a body."""
        for fixture in body.fixtures:
            fixture.restitution = float(restitution)

    def get_arena_bounds(self):
        """Return (x_min, x_max, y_min, y_max) for arena. Use y_min/y_max for floor/ceiling anchor points."""
        return (self.ARENA_X_MIN, self.ARENA_X_MAX, self.ARENA_Y_MIN, self.ARENA_Y_MAX)

    def get_build_zone(self):
        """Return (x_min, x_max, y_min, y_max) for build zone."""
        return (self.BUILD_ZONE_X_MIN, self.BUILD_ZONE_X_MAX, self.BUILD_ZONE_Y_MIN, self.BUILD_ZONE_Y_MAX)

    def get_terrain_bounds(self):
        """Return arena, build zone, and obstacle region for evaluator/renderer."""
        return {
            "arena": {
                "x_min": self.ARENA_X_MIN,
                "x_max": self.ARENA_X_MAX,
                "y_min": self.ARENA_Y_MIN,
                "y_max": self.ARENA_Y_MAX,
            },
            "build_zone": {
                "x": [self.BUILD_ZONE_X_MIN, self.BUILD_ZONE_X_MAX],
                "y": [self.BUILD_ZONE_Y_MIN, self.BUILD_ZONE_Y_MAX],
            },
            "max_beam_count": getattr(self, "MAX_BEAM_COUNT", 99),
            "obstacles": [
                {
                    "x_min": self.OBSTACLE1_X_MIN,
                    "x_max": self.OBSTACLE1_X_MAX,
                    "y_min": self.OBSTACLE1_Y_CENTER - self.OBSTACLE1_HALF_H,
                    "y_max": self.OBSTACLE1_Y_CENTER + self.OBSTACLE1_HALF_H,
                },
                {
                    "x_min": self.OBSTACLE2_X_MIN,
                    "x_max": self.OBSTACLE2_X_MAX,
                    "y_min": self.OBSTACLE2_Y_CENTER - self.OBSTACLE2_HALF_H,
                    "y_max": self.OBSTACLE2_Y_CENTER + self.OBSTACLE2_HALF_H,
                },
                {
                    "x_min": self.OBSTACLE3_X_MIN,
                    "x_max": self.OBSTACLE3_X_MAX,
                    "y_min": self.OBSTACLE3_Y_CENTER - self.OBSTACLE3_HALF_H,
                    "y_max": self.OBSTACLE3_Y_CENTER + self.OBSTACLE3_HALF_H,
                },
            ],
            "forbidden_zones": [
                {
                    "x_min": self.FORBIDDEN_X_MIN,
                    "x_max": self.FORBIDDEN_X_MAX,
                    "y_min": self.FORBIDDEN_Y_MIN,
                    "y_max": self.FORBIDDEN_Y_MAX,
                },
                {
                    "x_min": self.FORBIDDEN2_X_MIN,
                    "x_max": self.FORBIDDEN2_X_MAX,
                    "y_min": self.FORBIDDEN2_Y_MIN,
                    "y_max": self.FORBIDDEN2_Y_MAX,
                },
            ],
        }

    def get_gravity_at_time(self, t=None):
        """Current or specified-time gravity vector (for feedback/display)."""
        t = t if t is not None else self._time
        return self._gravity_function(t)
