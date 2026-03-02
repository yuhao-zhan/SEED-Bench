"""
K-04: The Pusher task environment module
Defines physics world, terrain (high-friction ground), heavy object, pusher structure, API, etc.
"""
import Box2D
from Box2D.b2 import (world, polygonShape, circleShape, staticBody, dynamicBody, revoluteJoint, weldJoint)
import math


class Sandbox:
    """Sandbox environment wrapper for K-04: The Pusher
    
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

        gravity = tuple(physics_config.get("gravity", (0, -10)))
        self._default_linear_damping = float(physics_config.get("linear_damping", 0.0))
        self._default_angular_damping = float(physics_config.get("angular_damping", 0.0))

        # 1. Initialize physics world (private attributes, solver LLM should not directly access)
        # do_sleep: False prevents bodies from sleeping during sustained pushing (for pusher demo)
        self._world = world(gravity=gravity, doSleep=physics_config.get("do_sleep", True))
        self._bodies = []  # Private list, prevent direct manipulation
        self._joints = []  # Private list, prevent direct manipulation

        # Track terrain bodies so mutations can adjust fixture properties post-create.
        self._terrain_bodies = {}
        
        # Track pusher components
        self._pusher_bodies = {}
        self._pusher_joints = []
        
        # Track object to push
        self._object_to_push = None
        self._pusher_initial_velocity_applied = False  # demo: apply once from terrain_config
        
        # For backward compatibility, keep public attributes (but recommend using controlled API)
        self.world = self._world  # Reserved for renderer use
        self.bodies = self._bodies
        self.joints = self._joints
        
        # 2. Generate terrain (high-friction ground)
        self._create_terrain(terrain_config)
        
        # 3. Set build zone and constraints
        self.BUILD_ZONE_X_MIN = 0.0  # Build zone x start
        self.BUILD_ZONE_X_MAX = 15.0  # Build zone x end
        self.BUILD_ZONE_Y_MIN = 1.0  # Build zone y start (ground top at 1.0; allow sitting on ground)
        self.BUILD_ZONE_Y_MAX = 8.0  # Build zone y end
        self.MAX_STRUCTURE_MASS = float(terrain_config.get("max_structure_mass", 40.0))  # Maximum total structure mass (kg)
        
        # 4. Create object to push
        self._create_object(terrain_config)
        
        # 5. Create initial pusher structure (basic template - solver will build their own)
        # We create a simple placeholder to show the environment, but solver must build their own pusher
        self._create_initial_pusher_template(terrain_config)

    def _create_terrain(self, terrain_config: dict):
        """
        Create terrain: high-friction ground surface
        """
        ground_friction = float(terrain_config.get("ground_friction", 1.2))  # High friction
        ground_length = 50.0  # Long ground surface
        ground_height = 1.0
        
        ground = self._world.CreateStaticBody(
            position=(ground_length / 2, ground_height / 2),
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(ground_length / 2, ground_height / 2)),
                friction=ground_friction,
            ),
        )
        self._terrain_bodies["ground"] = ground
        self._ground_y = ground_height  # Ground top surface at y = 1.0m
        self._ground_friction = ground_friction

    def _create_object(self, terrain_config: dict):
        """
        Create heavy object to push
        """
        object_config = terrain_config.get("object", {})
        object_mass = float(object_config.get("mass", 50.0))  # Heavy object
        object_friction = float(object_config.get("friction", 0.8))
        
        # Object position (center y so bottom sits on ground: ground_top + height/2)
        object_x = 8.0
        width = 1.0
        height = 0.8
        object_y = self._ground_y + height / 2  # On ground
        density = object_mass / (width * height)
        obj = self._world.CreateDynamicBody(
            position=(object_x, object_y),
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(width/2, height/2)),
                density=density,
                friction=object_friction,
            )
        )
        obj.linearDamping = float(object_config.get("linear_damping", self._default_linear_damping))
        obj.angularDamping = float(object_config.get("angular_damping", self._default_angular_damping))
        # Optional: offset center of mass (in local coords) - makes object tend to rotate when pushed off-center
        com_offset = object_config.get("center_of_mass_offset")
        if com_offset is not None and len(com_offset) >= 2:
            md = obj.massData
            new_md = Box2D.b2MassData()
            new_md.mass = md.mass
            new_md.center = (float(com_offset[0]), float(com_offset[1]))
            new_md.I = md.I
            obj.massData = new_md
        self._object_to_push = obj
        self._terrain_bodies["object"] = obj

    def _create_initial_pusher_template(self, terrain_config: dict):
        """
        Create a simple placeholder pusher template to show the environment.
        This is just for visualization - the solver must build their own pusher.
        """
        spawn_x = 3.0  # Behind object
        spawn_y = 2.5  # Above ground
        
        # Simple body (small box) - just for visualization
        body_width = 0.4
        body_height = 0.4
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
        self._pusher_bodies["body_template"] = body
        
        # Note: This is just a placeholder. The solver must build their own pusher structure.

    def remove_initial_template(self):
        """
        Remove the initial pusher template body from the world (if present).
        Call this at the start of build_agent so the solver's structure is the only pusher.
        """
        if "body_template" in self._pusher_bodies:
            body = self._pusher_bodies.pop("body_template")
            if body and self._world:
                self._world.DestroyBody(body)

    # --- Physical constraint constants ---
    MIN_BEAM_SIZE = 0.05  # Minimum beam width/height (meters)
    MAX_BEAM_SIZE = 3.0  # Maximum beam width/height (meters)
    MIN_WHEEL_RADIUS = 0.05
    MAX_WHEEL_RADIUS = 0.8
    MIN_JOINT_LIMIT = -math.pi  # Minimum joint angle limit (radians)
    MAX_JOINT_LIMIT = math.pi  # Maximum joint angle limit (radians)
    # BUILD_ZONE_X_MIN, BUILD_ZONE_X_MAX, BUILD_ZONE_Y_MIN, BUILD_ZONE_Y_MAX, MAX_STRUCTURE_MASS
    # are set in __init__ based on terrain_config
    BUILD_ZONE_X_MIN = 0.0  # Default, will be updated in __init__
    BUILD_ZONE_X_MAX = 15.0  # Default, will be updated in __init__
    BUILD_ZONE_Y_MIN = 1.5  # Build zone y start
    BUILD_ZONE_Y_MAX = 8.0  # Build zone y end
    MAX_STRUCTURE_MASS = 40.0  # Default, will be updated in __init__

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

    def add_wheel(self, x, y, radius=0.2, density=0.6):
        """
        API: Add a wheel (circular rigid body). Attach with add_joint(..., type='pivot') and drive with set_motor.
        Constraint: 0.05 <= radius <= 0.8
        """
        radius = max(self.MIN_WHEEL_RADIUS, min(radius, self.MAX_WHEEL_RADIUS))
        body = self._world.CreateDynamicBody(
            position=(x, y),
            fixtures=Box2D.b2FixtureDef(
                shape=circleShape(radius=radius),
                density=density,
                friction=0.8,
            )
        )
        body.linearDamping = self._default_linear_damping
        body.angularDamping = self._default_angular_damping
        self._bodies.append(body)
        return body

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

    def set_fixed_rotation(self, body, fixed=True):
        """
        API: Set fixed rotation for a body
        """
        if body:
            body.fixedRotation = bool(fixed)

    def step(self, time_step):
        """Physics step"""
        # Demo only: apply initial pusher velocity once so GIF shows visible motion (test can pass pusher_initial_velocity_x in terrain_config)
        if not self._pusher_initial_velocity_applied and self._bodies:
            vx = self._terrain_config.get("pusher_initial_velocity_x")
            if vx is not None:
                v = (float(vx), 0.0)
                for b in self._bodies:
                    b.linearVelocity = v
                self._pusher_initial_velocity_applied = True
        self._world.Step(time_step, 10, 10)
    
    def get_terrain_bounds(self):
        """Get terrain bounds (for evaluation)"""
        return {
            "ground": {"y": self._ground_y, "friction": self._ground_friction},
            "build_zone": {
                "x": [self.BUILD_ZONE_X_MIN, self.BUILD_ZONE_X_MAX],
                "y": [self.BUILD_ZONE_Y_MIN, self.BUILD_ZONE_Y_MAX]
            }
        }
    
    def get_pusher_position(self):
        """Get pusher body position (for evaluation)"""
        # Find the first body in the build zone (likely the main body)
        if not self._bodies:
            return None
        
        # Return position of first body (solver should track their main body)
        if self._bodies:
            body = self._bodies[0]
            return (body.position.x, body.position.y)
        return None
    
    def get_object_position(self):
        """Get object position (for evaluation)"""
        if self._object_to_push:
            return (self._object_to_push.position.x, self._object_to_push.position.y)
        return None
