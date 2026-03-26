"""
K-01: The Walker task environment module
Defines physics world, terrain, walker structure, API, etc.
"""
import Box2D
from Box2D.b2 import (world, polygonShape, circleShape, staticBody, dynamicBody, revoluteJoint, weldJoint)
import math


class Sandbox:
    """Sandbox environment wrapper for K-01: The Walker
    
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
        self._world = world(gravity=gravity, doSleep=True)
        self._bodies = []  # Private list, prevent direct manipulation
        self._joints = []  # Private list, prevent direct manipulation

        # Track terrain bodies so mutations can adjust fixture properties post-create.
        self._terrain_bodies = {}
        
        # Track walker components
        self._walker_bodies = {}
        self._walker_joints = []
        self._broken_joints = []
        self._peak_joint_force = 0.0
        
        # For backward compatibility, keep public attributes (but recommend using controlled API)
        self.world = self._world  # Reserved for renderer use
        self.bodies = self._bodies
        self.joints = self._joints
        
        # 2. Generate terrain (ground surface)
        self._create_terrain(terrain_config)
        
        # 3. Set build zone and constraints
        self.BUILD_ZONE_X_MIN = 0.0  # Build zone x start
        self.BUILD_ZONE_X_MAX = 50.0  # Build zone x end
        self.BUILD_ZONE_Y_MIN = 2.0  # Build zone y start (above ground)
        self.BUILD_ZONE_Y_MAX = 10.0  # Build zone y end
        self.MAX_STRUCTURE_MASS = float(terrain_config.get("max_structure_mass", 100.0))  # Maximum total structure mass (kg)
        
        # 4. Create initial walker structure (basic template - solver will build their own)
        # We create a simple placeholder to show the environment, but solver must build their own walker
        self._create_initial_walker_template(terrain_config)

    def _create_terrain(self, terrain_config: dict):
        """
        Create terrain: flat ground surface
        """
        ground_friction = float(terrain_config.get("ground_friction", 0.8))
        ground_length = 100.0  # Long ground surface
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

    def _create_initial_walker_template(self, terrain_config: dict):
        """
        Create a simple placeholder walker template to show the environment.
        This is just for visualization - the solver must build their own walker.
        """
        spawn_x = 10.0
        spawn_y = 2.0  # Match prompt: "Starting Position ... y=2.0m"
        
        # Simple torso (small box) - just for visualization
        torso_width = 0.5
        torso_height = 0.3
        torso = self._world.CreateDynamicBody(
            position=(spawn_x, spawn_y),
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(torso_width/2, torso_height/2)),
                density=1.0,
                friction=0.5,
            )
        )
        torso.linearDamping = self._default_linear_damping
        torso.angularDamping = self._default_angular_damping
        self._walker_bodies["torso_template"] = torso
        
        # Note: This is just a placeholder. The solver must build their own walker structure.

    # --- Physical constraint constants ---
    MIN_BEAM_SIZE = 0.05  # Minimum beam width/height (meters)
    MAX_BEAM_SIZE = 5.0  # Maximum beam width/height (meters)
    MIN_WHEEL_RADIUS = 0.05
    MAX_WHEEL_RADIUS = 0.8
    MIN_JOINT_LIMIT = -math.pi  # Minimum joint angle limit (radians)
    MAX_JOINT_LIMIT = math.pi  # Maximum joint angle limit (radians)
    # BUILD_ZONE_X_MIN, BUILD_ZONE_X_MAX, BUILD_ZONE_Y_MIN, BUILD_ZONE_Y_MAX, MAX_STRUCTURE_MASS
    # are set in __init__ based on terrain_config
    BUILD_ZONE_X_MIN = 0.0  # Default, will be updated in __init__
    BUILD_ZONE_X_MAX = 50.0  # Default, will be updated in __init__
    BUILD_ZONE_Y_MIN = 2.0  # Build zone y start
    BUILD_ZONE_Y_MAX = 10.0  # Build zone y end
    MAX_STRUCTURE_MASS = 100.0  # Default, will be updated in __init__

    # --- Below are Primitives API open to LLM (with physical constraints) ---

    def add_beam(self, x, y, width, height, angle=0, density=1.0):
        """
        API: Add a beam (rigid rectangular structural element)
        Constraint: 0.05 <= width, height <= 5.0; position must be within build zone x=[0, 50], y=[2, 10].
        """
        # Validate build zone (placement constraint)
        if not (self.BUILD_ZONE_X_MIN <= x <= self.BUILD_ZONE_X_MAX and self.BUILD_ZONE_Y_MIN <= y <= self.BUILD_ZONE_Y_MAX):
            raise ValueError(
                f"add_beam: position ({x}, {y}) is outside the build zone "
                f"x=[{self.BUILD_ZONE_X_MIN}, {self.BUILD_ZONE_X_MAX}], y=[{self.BUILD_ZONE_Y_MIN}, {self.BUILD_ZONE_Y_MAX}]. "
                "All components must be placed within this zone."
            )
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
        Constraint: 0.05 <= radius <= 0.8; position must be within build zone x=[0, 50], y=[2, 10].
        """
        # Validate build zone (placement constraint)
        if not (self.BUILD_ZONE_X_MIN <= x <= self.BUILD_ZONE_X_MAX and self.BUILD_ZONE_Y_MIN <= y <= self.BUILD_ZONE_Y_MAX):
            raise ValueError(
                f"add_wheel: position ({x}, {y}) is outside the build zone "
                f"x=[{self.BUILD_ZONE_X_MIN}, {self.BUILD_ZONE_X_MAX}], y=[{self.BUILD_ZONE_Y_MIN}, {self.BUILD_ZONE_Y_MAX}]. "
                "All components must be placed within this zone."
            )
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
        
        # Mutated tasks: apply default joint limits from physics_config when agent doesn't specify
        if type == 'pivot' and lower_limit is None and upper_limit is None:
            def_lo = self._physics_config.get("default_joint_lower_limit")
            def_hi = self._physics_config.get("default_joint_upper_limit")
            if def_lo is not None and def_hi is not None:
                lower_limit = float(def_lo)
                upper_limit = float(def_hi)
        
        if type == 'rigid':
            # Weld joint (no relative rotation)
            joint = self._world.CreateWeldJoint(
                bodyA=body_a,
                bodyB=body_b,
                anchor=(anchor_x, anchor_y),
                collideConnected=False
            )
        elif type == 'pivot':
            if lower_limit is None and upper_limit is None:
                if def_lo is not None and def_hi is not None:
                    lower_limit = float(def_lo)
                    upper_limit = float(def_hi)
            else:
                # If agent provides limits, they must be within environment limits
                if def_lo is not None:
                    lower_limit = max(float(lower_limit), float(def_lo))
                if def_hi is not None:
                    upper_limit = min(float(upper_limit), float(def_hi))

            # Revolute joint (allows rotation) - can be motor-driven
            joint_kwargs = {
                'bodyA': body_a,
                'bodyB': body_b,
                'anchor': (anchor_x, anchor_y),
                'collideConnected': False
            }
            
            # Set joint limits if provided
            if lower_limit is not None and upper_limit is not None:
                joint_kwargs['lowerAngle'] = max(self.MIN_JOINT_LIMIT, min(float(lower_limit), self.MAX_JOINT_LIMIT))
                joint_kwargs['upperAngle'] = min(self.MAX_JOINT_LIMIT, max(float(upper_limit), self.MIN_JOINT_LIMIT))
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
        # Mutated tasks: cap friction to max_body_friction if set (simulates slippery contact)
        max_friction = self._physics_config.get("max_body_friction")
        for fixture in body.fixtures:
            fixture.restitution = float(restitution)
            if friction is not None:
                f = float(friction)
                if max_friction is not None:
                    f = min(f, float(max_friction))
                fixture.friction = f

    def set_fixed_rotation(self, body, fixed=True):
        """
        API: Set fixed rotation for a body
        """
        if body:
            body.fixedRotation = bool(fixed)

    def step(self, time_step):
        """Physics step, tracking joint stress"""
        self._world.Step(time_step, 10, 10)
        
        # Track joint stresses
        for joint in self._joints:
            try:
                # Get reaction force
                force = joint.GetReactionForce(1.0 / time_step).length
                if force > self._peak_joint_force:
                    self._peak_joint_force = force
            except:
                pass
    
    def get_joint_stress(self):
        """API: Returns peak joint stress and broken count"""
        return {
            "peak_joint_force": self._peak_joint_force,
            "broken_joints": len(self._broken_joints)
        }
    
    def get_terrain_bounds(self):
        """Get terrain bounds (for evaluation and renderer). Includes target_distance and initial_x."""
        initial_x = float(self._terrain_config.get("initial_x", 10.0))
        target_distance = float(self._terrain_config.get("target_distance", 15.0))
        return {
            "ground": {"y": self._ground_y},
            "build_zone": {
                "x": [self.BUILD_ZONE_X_MIN, self.BUILD_ZONE_X_MAX],
                "y": [self.BUILD_ZONE_Y_MIN, self.BUILD_ZONE_Y_MAX]
            },
            "target_distance": target_distance,
            "initial_x": initial_x,
            "target_x": initial_x + target_distance,
        }
    
    def get_walker_position(self):
        """Get walker torso position (for evaluation)"""
        # Find the lowest body in the build zone (likely the torso)
        if not self._bodies:
            return None
        
        # Return position of first body (solver should track their torso)
        if self._bodies:
            body = self._bodies[0]
            return (body.position.x, body.position.y)
        return None
