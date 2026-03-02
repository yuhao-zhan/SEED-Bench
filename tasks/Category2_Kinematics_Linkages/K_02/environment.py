"""
K-02: The Climber task environment module
Defines physics world, terrain (vertical wall), climber structure, API, etc.
"""
import Box2D
from Box2D.b2 import (world, polygonShape, circleShape, staticBody, dynamicBody, revoluteJoint, weldJoint)
import math


class Sandbox:
    """Sandbox environment wrapper for K-02: The Climber
    
    Security design: Hide underlying physics engine objects to prevent solver LLM from bypassing constraint checks
    """
    
    def __init__(self, *, terrain_config=None, physics_config=None):
        """
        Create a sandbox environment.

        Mutated tasks can pass in terrain_config / physics_config to change environment
        WITHOUT exposing the exact changes to the solver agent (the solver only sees feedback).
        """
        terrain_config = terrain_config or {}
        physics_config = physics_config or {}
        # Store configs for evaluator/renderer introspection (solver does not see these).
        self._terrain_config = dict(terrain_config)
        self._physics_config = dict(physics_config)

        gravity = tuple(physics_config.get("gravity", (0, -8)))  # Reduced gravity for easier climbing
        self._default_linear_damping = float(physics_config.get("linear_damping", 0.0))
        self._default_angular_damping = float(physics_config.get("angular_damping", 0.0))
        # Optional pad force overrides for mutated tasks (invisible to solver)
        self._pad_force_scale = float(physics_config.get("pad_force_scale", self.PAD_FORCE_SCALE))
        self._max_pad_force = float(physics_config.get("max_pad_force", self.MAX_PAD_FORCE))

        # 1. Initialize physics world (private attributes, solver LLM should not directly access)
        self._world = world(gravity=gravity, doSleep=True)
        self._bodies = []  # Private list, prevent direct manipulation
        self._joints = []  # Private list, prevent direct manipulation

        # Track terrain bodies so mutations can adjust fixture properties post-create.
        self._terrain_bodies = {}
        
        # Track climber components
        self._climber_bodies = {}
        self._climber_joints = []
        # Suction/adhesion pads: when active, apply force toward wall (makes climbing feasible)
        self._pads = []  # list of pad bodies
        self._pad_active = {}  # body -> bool
        
        # For backward compatibility, keep public attributes (but recommend using controlled API)
        self.world = self._world  # Reserved for renderer use
        self.bodies = self._bodies
        self.joints = self._joints
        
        # 2. Generate terrain (vertical wall)
        self._create_terrain(terrain_config)
        
        # 3. Set build zone and constraints
        self.BUILD_ZONE_X_MIN = 0.0  # Build zone x start
        self.BUILD_ZONE_X_MAX = 5.0  # Build zone x end (narrow zone near wall)
        self.BUILD_ZONE_Y_MIN = 0.0  # Build zone y start (ground level)
        self.BUILD_ZONE_Y_MAX = 20.0  # Build zone y end (high enough for climbing)
        self.MAX_STRUCTURE_MASS = float(terrain_config.get("max_structure_mass", 50.0))  # Maximum total structure mass (kg)
        
        # 4. Create initial climber structure (basic template - solver will build their own)
        # We create a simple placeholder to show the environment, but solver must build their own climber
        self._create_initial_climber_template(terrain_config)

    def _create_terrain(self, terrain_config: dict):
        """
        Create terrain: vertical wall and ground
        """
        wall_friction = float(terrain_config.get("wall_friction", 1.0))  # Increased friction for better grip
        wall_x = 5.0  # Wall position at x=5m
        wall_height = 25.0  # Wall height
        wall_thickness = 0.5  # Wall thickness
        
        # Vertical wall
        wall = self._world.CreateStaticBody(
            position=(wall_x, wall_height / 2),
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(wall_thickness / 2, wall_height / 2)),
                friction=wall_friction,
            ),
        )
        self._terrain_bodies["wall"] = wall
        self._wall_x = wall_x
        self._wall_height = wall_height
        
        # Ground surface (horizontal)
        ground_length = 10.0
        ground_height = 1.0
        ground = self._world.CreateStaticBody(
            position=(ground_length / 2, ground_height / 2),
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(ground_length / 2, ground_height / 2)),
                friction=0.8,
            ),
        )
        self._terrain_bodies["ground"] = ground
        self._ground_y = ground_height

    def _create_initial_climber_template(self, terrain_config: dict):
        """
        Create a simple placeholder climber template to show the environment.
        This is just for visualization - the solver must build their own climber.
        """
        spawn_x = 3.0  # Near wall
        spawn_y = 2.0  # Above ground
        
        # Simple body (small box) - just for visualization
        body_width = 0.3
        body_height = 0.3
        body = self._world.CreateDynamicBody(
            position=(spawn_x, spawn_y),
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(body_width/2, body_height/2)),
                density=1.0,
                friction=0.5,
            )
        )
        body.linearDamping = self._default_linear_damping
        body.angularDamping = self._default_angular_damping
        self._climber_bodies["body_template"] = body
        
        # Note: This is just a placeholder. The solver must build their own climber structure.

    # --- Physical constraint constants ---
    MIN_BEAM_SIZE = 0.05  # Minimum beam width/height (meters)
    MAX_BEAM_SIZE = 3.0  # Maximum beam width/height (meters)
    MIN_PAD_RADIUS = 0.05
    MAX_PAD_RADIUS = 0.25
    PAD_FORCE_SCALE = 80.0  # Force toward wall when pad active (N per meter from wall)
    MAX_PAD_FORCE = 55.0    # Max pull force per pad (N) — suction has limited load capacity
    MIN_JOINT_LIMIT = -math.pi  # Minimum joint angle limit (radians)
    MAX_JOINT_LIMIT = math.pi  # Maximum joint angle limit (radians)
    # BUILD_ZONE_X_MIN, BUILD_ZONE_X_MAX, BUILD_ZONE_Y_MIN, BUILD_ZONE_Y_MAX, MAX_STRUCTURE_MASS
    # are set in __init__ based on terrain_config
    BUILD_ZONE_X_MIN = 0.0  # Default, will be updated in __init__
    BUILD_ZONE_X_MAX = 5.0  # Default, will be updated in __init__
    BUILD_ZONE_Y_MIN = 0.0  # Build zone y start
    BUILD_ZONE_Y_MAX = 20.0  # Build zone y end
    MAX_STRUCTURE_MASS = 50.0  # Default, will be updated in __init__

    # --- Below are Primitives API open to LLM (with physical constraints) ---

    def add_beam(self, x, y, width, height, angle=0, density=1.0):
        """
        API: Add a beam (rigid rectangular structural element)
        Constraint: 0.05 <= width, height <= 3.0
        """
        # Validate constraints
        width = max(self.MIN_BEAM_SIZE, min(width, self.MAX_BEAM_SIZE))
        height = max(self.MIN_BEAM_SIZE, min(height, self.MAX_BEAM_SIZE))
        
        body = self._world.CreateDynamicBody(
            position=(x, y),
            angle=angle,
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(width/2, height/2)),
                density=density,
                friction=0.5,
            )
        )
        body.linearDamping = self._default_linear_damping
        body.angularDamping = self._default_angular_damping
        self._bodies.append(body)
        return body

    def add_pad(self, x, y, radius=0.12, density=0.8):
        """
        API: Add a suction/adhesion pad (circular). When active, it pulls toward the wall.
        Each pad has a max load (MAX_PAD_FORCE N); total adhesion is limited.
        Constraint: 0.05 <= radius <= 0.25
        """
        radius = max(self.MIN_PAD_RADIUS, min(radius, self.MAX_PAD_RADIUS))
        body = self._world.CreateDynamicBody(
            position=(x, y),
            fixtures=Box2D.b2FixtureDef(
                shape=circleShape(radius=radius),
                density=density,
                friction=1.2,  # High friction when in contact with wall
            )
        )
        body.linearDamping = self._default_linear_damping
        body.angularDamping = self._default_angular_damping
        self._bodies.append(body)
        self._pads.append(body)
        self._pad_active[body] = False
        return body

    def set_pad_active(self, pad, active):
        """
        API: Set whether a pad is "on" (pulls toward the wall). Use in agent_action to stick when needed.
        """
        if pad in self._pads:
            self._pad_active[pad] = bool(active)

    def add_joint(self, body_a, body_b, anchor_point, type='pivot', lower_limit=None, upper_limit=None):
        """
        API: Add a joint between two bodies
        - type='rigid': Locks relative rotation (Weld)
        - type='pivot': Allows free rotation (Revolute) - use for motor-driven joints
        - lower_limit, upper_limit: Joint angle limits in radians (for pivot joints)
        """
        # Validate body_a (must not be None)
        if body_a is None:
            raise ValueError("add_joint: body_a cannot be None. You must provide a valid body object (e.g., from add_beam).")
        
        if body_b is None:
            raise ValueError("add_joint: body_b cannot be None. You must provide a valid body object.")
        
        anchor_x, anchor_y = anchor_point[0], anchor_point[1]
        
        if type == 'rigid':
            # Weld joint (no relative rotation)
            joint = self._world.CreateWeldJoint(
                bodyA=body_a,
                bodyB=body_b,
                anchor=(anchor_x, anchor_y),
                collideConnected=False
            )
        elif type == 'pivot':
            # Revolute joint (allows rotation) - can be motor-driven
            joint_kwargs = {
                'bodyA': body_a,
                'bodyB': body_b,
                'anchor': (anchor_x, anchor_y),
                'collideConnected': False
            }
            
            # Set joint limits if provided
            if lower_limit is not None and upper_limit is not None:
                joint_kwargs['lowerAngle'] = max(self.MIN_JOINT_LIMIT, min(lower_limit, self.MAX_JOINT_LIMIT))
                joint_kwargs['upperAngle'] = min(self.MAX_JOINT_LIMIT, max(upper_limit, self.MIN_JOINT_LIMIT))
                joint_kwargs['enableLimit'] = True
            
            joint = self._world.CreateRevoluteJoint(**joint_kwargs)
        else:
            raise ValueError(f"Unknown joint type: {type}")
        
        self._joints.append(joint)
        return joint

    def set_motor(self, joint, motor_speed, max_torque=100.0):
        """
        API: Set motor properties for a revolute joint
        - joint: Joint object (must be a pivot/revolute joint)
        - motor_speed: Target angular velocity (rad/s, positive = counterclockwise)
        - max_torque: Maximum motor torque (N·m)
        """
        if not isinstance(joint, Box2D.b2RevoluteJoint):
            raise ValueError("set_motor: joint must be a pivot/revolute joint")
        
        joint.enableMotor = True
        joint.motorSpeed = float(motor_speed)
        joint.maxMotorTorque = float(max_torque)

    def get_structure_mass(self):
        """
        API: Returns total mass of created objects
        """
        total_mass = 0.0
        for body in self._bodies:
            total_mass += body.mass
        return total_mass

    def set_material_properties(self, body, restitution=0.2, friction=None):
        """
        API: Set material properties for a body
        - 'restitution': Bounciness (0.0 = clay, 1.0 = superball)
        - 'friction': Friction coefficient (optional)
        """
        for fixture in body.fixtures:
            fixture.restitution = float(restitution)
            if friction is not None:
                fixture.friction = float(friction)

    def step(self, time_step):
        """Physics step: apply pad forces toward wall, then step world."""
        wall_x = getattr(self, '_wall_x', 5.0)
        scale = getattr(self, '_pad_force_scale', self.PAD_FORCE_SCALE)
        max_f = getattr(self, '_max_pad_force', self.MAX_PAD_FORCE)
        for pad in self._pads:
            if self._pad_active.get(pad, False):
                dx = wall_x - pad.position.x
                if dx > 0:  # Pad is left of wall — pull toward wall (capped by max load)
                    F = min(dx * scale, max_f)
                    pad.ApplyForce((F, 0), pad.position, True)
        self._world.Step(time_step, 10, 10)
    
    def get_terrain_bounds(self):
        """Get terrain bounds (for evaluation)"""
        return {
            "wall": {"x": self._wall_x, "height": self._wall_height},
            "ground": {"y": self._ground_y},
            "build_zone": {
                "x": [self.BUILD_ZONE_X_MIN, self.BUILD_ZONE_X_MAX],
                "y": [self.BUILD_ZONE_Y_MIN, self.BUILD_ZONE_Y_MAX]
            }
        }
    
    def get_climber_position(self):
        """Get climber body position (for evaluation)"""
        # Find the highest body in the build zone (likely the main body)
        if not self._bodies:
            return None
        
        # Return position of first body (solver should track their main body)
        if self._bodies:
            body = self._bodies[0]
            return (body.position.x, body.position.y)
        return None
