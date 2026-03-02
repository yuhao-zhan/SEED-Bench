"""
D-01: The Launcher task environment module
Defines physics world, terrain, projectile, target zone, and launcher build API.
Mechanics: lever principle, whip effect, spring energy storage.
"""
import Box2D
from Box2D.b2 import (
    world,
    polygonShape,
    circleShape,
    staticBody,
    dynamicBody,
    revoluteJoint,
    weldJoint,
    distanceJointDef,
)
import math


class Sandbox:
    """Sandbox environment wrapper for D-01: The Launcher

    Security design: Hide underlying physics engine objects to prevent solver LLM
    from bypassing constraint checks.
    """

    def __init__(self, *, terrain_config=None, physics_config=None):
        """
        Create a sandbox environment.

        Mutated tasks can pass in terrain_config / physics_config to change
        environment WITHOUT exposing the exact changes to the solver agent.
        """
        terrain_config = terrain_config or {}
        physics_config = physics_config or {}
        self._terrain_config = dict(terrain_config)
        self._physics_config = dict(physics_config)

        gravity = tuple(physics_config.get("gravity", (0, -10)))
        self._default_linear_damping = float(physics_config.get("linear_damping", 0.0))
        self._default_angular_damping = float(physics_config.get("angular_damping", 0.0))

        self._world = world(gravity=gravity, doSleep=True)
        self._bodies = []
        self._joints = []
        self._springs = []  # Distance joints used as springs
        self._terrain_bodies = {}

        self.world = self._world
        self.bodies = self._bodies
        self.joints = self._joints
        self.springs = self._springs

        self._create_terrain(terrain_config)
        self._create_projectile(terrain_config)
        self._create_target_zone(terrain_config)

        # Build zone: where the agent may place launcher parts
        self.BUILD_ZONE_X_MIN = float(terrain_config.get("build_zone_x_min", 5.0))
        self.BUILD_ZONE_X_MAX = float(terrain_config.get("build_zone_x_max", 15.0))
        self.BUILD_ZONE_Y_MIN = float(terrain_config.get("build_zone_y_min", 1.5))
        self.BUILD_ZONE_Y_MAX = float(terrain_config.get("build_zone_y_max", 8.0))
        self.MAX_STRUCTURE_MASS = float(terrain_config.get("max_structure_mass", 500.0))

    def _create_terrain(self, terrain_config: dict):
        """Create ground: long flat static surface."""
        ground_friction = float(terrain_config.get("ground_friction", 0.6))
        ground_length = 60.0
        ground_height = 1.0

        ground = self._world.CreateStaticBody(
            position=(ground_length / 2, ground_height / 2),
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(ground_length / 2, ground_height / 2)),
                friction=ground_friction,
            ),
        )
        self._terrain_bodies["ground"] = ground
        self._ground_y = ground_height

    def _create_projectile(self, terrain_config: dict):
        """Create the projectile (ball) that the launcher must propel toward the target."""
        spawn_x = float(terrain_config.get("projectile_spawn_x", 10.0))
        spawn_y = float(terrain_config.get("projectile_spawn_y", 3.0))
        radius = float(terrain_config.get("projectile_radius", 0.25))
        density = float(terrain_config.get("projectile_density", 1.0))

        projectile = self._world.CreateDynamicBody(
            position=(spawn_x, spawn_y),
            fixtures=Box2D.b2FixtureDef(
                shape=circleShape(radius=radius),
                density=density,
                friction=0.3,
                restitution=0.2,
            ),
        )
        projectile.linearDamping = self._default_linear_damping
        projectile.angularDamping = self._default_angular_damping
        self._terrain_bodies["projectile"] = projectile

    def _create_target_zone(self, terrain_config: dict):
        """Define target zone bounds (no physical body; used for evaluation).
        y in [2, 5]: projectile must reach at least 2 m height in the x-band (non-trivial arc).
        """
        self._target_x_min = float(terrain_config.get("target_x_min", 40.0))
        self._target_x_max = float(terrain_config.get("target_x_max", 45.0))
        self._target_y_min = float(terrain_config.get("target_y_min", 2.0))
        self._target_y_max = float(terrain_config.get("target_y_max", 5.0))

    # --- Physical constraint constants ---
    MIN_BEAM_SIZE = 0.1
    MAX_BEAM_SIZE = 5.0
    MIN_SPRING_STIFFNESS = 10.0
    MAX_SPRING_STIFFNESS = 3000.0  # Allow stronger springs so arc can reach y in [2,5] in band

    # --- Primitives API ---

    def add_beam(self, x, y, width, height, angle=0, density=1.0):
        """
        API: Add a beam (rigid rectangular structural element) for launcher construction.
        Constraint: 0.1 <= width, height <= 5.0 (meters).
        """
        width = max(self.MIN_BEAM_SIZE, min(width, self.MAX_BEAM_SIZE))
        height = max(self.MIN_BEAM_SIZE, min(height, self.MAX_BEAM_SIZE))

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
        API: Add a joint between two bodies.
        - type='rigid': Weld (no relative rotation).
        - type='pivot': Revolute (hinge).
        - body_b can be None to anchor to the ground at anchor_point.
        """
        if body_a is None:
            raise ValueError("add_joint: body_a cannot be None.")

        anchor_x, anchor_y = anchor_point[0], anchor_point[1]
        if body_b is None:
            body_b = self._terrain_bodies.get("ground")
            if body_b is None:
                raise ValueError("add_joint: Cannot anchor to ground; ground body not found.")

        if type == "rigid":
            joint = self._world.CreateWeldJoint(
                bodyA=body_a,
                bodyB=body_b,
                anchor=(anchor_x, anchor_y),
                collideConnected=False,
            )
        elif type == "pivot":
            joint = self._world.CreateRevoluteJoint(
                bodyA=body_a,
                bodyB=body_b,
                anchor=(anchor_x, anchor_y),
                collideConnected=False,
            )
        else:
            raise ValueError(f"Unknown joint type: {type}")

        self._joints.append(joint)
        return joint

    def add_spring(
        self,
        body_a,
        body_b,
        anchor_a,
        anchor_b,
        rest_length=None,
        stiffness=500.0,
        damping_ratio=0.5,
    ):
        """
        API: Add a spring (distance joint with stiffness) between two bodies.
        Used for spring energy storage (e.g. pre-tension and release to launch).
        - rest_length: natural length (meters). If None, uses current distance.
        - stiffness: spring stiffness (N/m). frequencyHz is derived from stiffness and masses.
        - damping_ratio: 0 = no damping, ~0.5 = critical damping.
        """
        stiffness = max(
            self.MIN_SPRING_STIFFNESS,
            min(stiffness, self.MAX_SPRING_STIFFNESS),
        )
        ax, ay = anchor_a[0], anchor_a[1]
        bx, by = anchor_b[0], anchor_b[1]
        if rest_length is None:
            rest_length = math.sqrt((bx - ax) ** 2 + (by - ay) ** 2)
            rest_length = max(0.1, rest_length)

        defn = distanceJointDef()
        defn.bodyA = body_a
        defn.bodyB = body_b
        defn.localAnchorA = body_a.GetLocalPoint((ax, ay))
        defn.localAnchorB = body_b.GetLocalPoint((bx, by))
        defn.length = rest_length
        defn.collideConnected = False
        # Spring: frequencyHz and dampingRatio (Box2D 2.4 style)
        # Approximate: frequencyHz ~ sqrt(stiffness / effective_mass) / (2*pi)
        try:
            defn.frequencyHz = min(10.0, math.sqrt(stiffness / 10.0) / (2 * math.pi))
        except Exception:
            defn.frequencyHz = 4.0
        defn.dampingRatio = max(0.0, min(1.0, damping_ratio))

        joint = self._world.CreateJoint(defn)
        self._springs.append(joint)
        return joint

    def get_structure_mass(self):
        """API: Return total mass of all launcher bodies (beams) created by the agent."""
        total = 0.0
        for body in self._bodies:
            total += body.mass
        return total

    def set_material_properties(self, body, restitution=0.2):
        """API: Set restitution (bounciness) for a body."""
        for fixture in body.fixtures:
            fixture.restitution = float(restitution)

    def step(self, time_step):
        """Advance physics by one time step."""
        self._world.Step(time_step, 10, 10)

    def get_terrain_bounds(self):
        """Return terrain and target zone bounds for evaluation and rendering."""
        return {
            "ground_y": self._ground_y,
            "target_zone": {
                "x_min": self._target_x_min,
                "x_max": self._target_x_max,
                "y_min": self._target_y_min,
                "y_max": self._target_y_max,
            },
            "build_zone": {
                "x": [self.BUILD_ZONE_X_MIN, self.BUILD_ZONE_X_MAX],
                "y": [self.BUILD_ZONE_Y_MIN, self.BUILD_ZONE_Y_MAX],
            },
            "projectile_spawn": (
                self._terrain_config.get("projectile_spawn_x", 10.0),
                self._terrain_config.get("projectile_spawn_y", 3.0),
            ),
        }

    def get_projectile_position(self):
        """Return (x, y) of projectile center, or None if not found."""
        proj = self._terrain_bodies.get("projectile")
        if proj is None:
            return None
        return (proj.position.x, proj.position.y)

    def get_projectile_velocity(self):
        """Return (vx, vy) of projectile, or None if not found."""
        proj = self._terrain_bodies.get("projectile")
        if proj is None:
            return None
        return (proj.linearVelocity.x, proj.linearVelocity.y)

    def get_ground(self):
        """Return ground body for anchoring or spring attachment."""
        return self._terrain_bodies.get("ground")

    def get_projectile(self):
        """Return projectile body (ball to be launched)."""
        return self._terrain_bodies.get("projectile")
