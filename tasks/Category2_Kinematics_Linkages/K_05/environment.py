"""
K-05: The Lifter task environment module
Defines physics world, terrain, object to lift, lifter structure, API, etc.

Design alignment (keep consistent with evaluator.py, prompt.py):
- Object must start at ground y=1.8m and be lifted by the mechanism (no placing on a pre-built high platform).
- After build, enforce_object_at_ground() is called so the object is at (4, 1.8) when simulation starts.
- Target y=9m (8m above ground y=1.0m); build zone x=[0, 8], y=[1, 12]; max structure mass 60kg.
"""
# Object start height (must match evaluator OBJECT_START_Y)
OBJECT_START_Y = 1.8
OBJECT_START_X = 4.0
# Minimum height gain (m) above initial object y to count as "lifting started" (align with evaluator, prompt)
LIFTING_THRESHOLD_M = 0.5
import Box2D
from Box2D.b2 import (world, polygonShape, circleShape, staticBody, dynamicBody, revoluteJoint, weldJoint)
import math


class Sandbox:
    """Sandbox environment wrapper for K-05: The Lifter
    
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
        
        # Track lifter components
        self._lifter_bodies = {}
        self._lifter_joints = []
        
        # Track object to lift
        self._object_to_lift = None
        
        # For backward compatibility, keep public attributes (but recommend using controlled API)
        self.world = self._world  # Reserved for renderer use
        self.bodies = self._bodies
        self.joints = self._joints
        
        # 2. Generate terrain (ground surface)
        self._create_terrain(terrain_config)
        
        # 3. Set build zone and constraints
        self.BUILD_ZONE_X_MIN = float(terrain_config.get("BUILD_ZONE_X_MIN", 0.0))
        self.BUILD_ZONE_X_MAX = float(terrain_config.get("BUILD_ZONE_X_MAX", 8.0))
        self.BUILD_ZONE_Y_MIN = float(terrain_config.get("BUILD_ZONE_Y_MIN", 1.0))
        self.BUILD_ZONE_Y_MAX = float(terrain_config.get("BUILD_ZONE_Y_MAX", 12.0))
        self.MAX_STRUCTURE_MASS = float(terrain_config.get("max_structure_mass", 60.0))  # Maximum total structure mass (kg)
        
        # Start position and lifting threshold (sync with evaluator, prompt)
        self.OBJECT_START_X = float(terrain_config.get("OBJECT_START_X", 4.0))
        self.OBJECT_START_Y = float(terrain_config.get("OBJECT_START_Y", 1.8))
        self.LIFTING_THRESHOLD_M = float(terrain_config.get("LIFTING_THRESHOLD_M", 0.5))

        # Mutated tasks: optional target height and sustain time (evaluator reads these)
        self.target_object_y = float(terrain_config.get("target_object_y", 9.0))
        self.min_sustain_s = float(terrain_config.get("min_sustain_s", 3.0))

        # 4. Create object to lift
        self._create_object(terrain_config)
        
        # 5. Create initial lifter structure (basic template - solver will build their own)
        # We create a simple placeholder to show the environment, but solver must build their own lifter
        self._create_initial_lifter_template(terrain_config)

    def _create_terrain(self, terrain_config: dict):
        """
        Create terrain: flat ground surface
        """
        ground_friction = float(terrain_config.get("ground_friction", 0.8))
        ground_length = 20.0  # Ground surface
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

        # Add ceiling if configured
        ceiling_config = terrain_config.get("ceiling_gap", None)
        if ceiling_config:
            c_y = ceiling_config.get("y", 6.0)
            c_x_min = ceiling_config.get("x_min", 3.0)
            c_x_max = ceiling_config.get("x_max", 5.0)
            thickness = 0.5
            
            # Left ceiling
            left_width = c_x_min
            if left_width > 0:
                self._world.CreateStaticBody(
                    position=(left_width / 2, c_y + thickness / 2),
                    fixtures=Box2D.b2FixtureDef(
                        shape=polygonShape(box=(left_width / 2, thickness / 2)),
                        friction=ground_friction,
                    ),
                )
            
            # Right ceiling
            right_width = ground_length - c_x_max
            if right_width > 0:
                self._world.CreateStaticBody(
                    position=(c_x_max + right_width / 2, c_y + thickness / 2),
                    fixtures=Box2D.b2FixtureDef(
                        shape=polygonShape(box=(right_width / 2, thickness / 2)),
                        friction=ground_friction,
                    ),
                )


    def _create_object(self, terrain_config: dict):
        """
        Create object to lift. Supports optional com_offset (center of mass offset in body-local coordinates).
        """
        object_config = terrain_config.get("object", {})
        object_mass = float(object_config.get("mass", 20.0))  # Object to lift
        object_friction = float(object_config.get("friction", 0.6))
        com_offset = object_config.get("com_offset")
        if com_offset is not None:
            com_offset = (float(com_offset[0]), float(com_offset[1]))
        
        # Object position
        object_x = self.OBJECT_START_X
        object_y = self.OBJECT_START_Y
        
        # Rectangular object
        width, height = 0.6, 0.4
        hw, hh = width / 2.0, height / 2.0
        density = object_mass / (width * height)
        obj = self._world.CreateDynamicBody(
            position=(object_x, object_y),
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(hw, hh)),
                density=density,
                friction=object_friction,
            )
        )
        obj.linearDamping = self._default_linear_damping
        obj.angularDamping = self._default_angular_damping
        if com_offset is not None and (com_offset[0] != 0.0 or com_offset[1] != 0.0):
            # Set center of mass offset (Box2D: center is in local coordinates)
            try:
                mass_data = obj.GetMassData()
                ox, oy = com_offset[0], com_offset[1]
                # b2MassData: mass, center (b2Vec2), I (inertia)
                mass_data.center = (ox, oy)
                # Parallel-axis: I_new = I_cm + m * (ox^2 + oy^2) so inertia stays valid
                mass_data.I = mass_data.I + object_mass * (ox * ox + oy * oy)
                if mass_data.I <= 0:
                    mass_data.I = 0.01
                obj.SetMassData(mass_data)
            except Exception:
                pass
        self._object_to_lift = obj
        self._terrain_bodies["object"] = obj

    def _create_initial_lifter_template(self, terrain_config: dict):
        """
        Create a simple placeholder lifter template to show the environment.
        This is just for visualization - the solver must build their own lifter.
        """
        spawn_x = self.OBJECT_START_X
        spawn_y = self.OBJECT_START_Y + 0.2  # Above object
        
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
        self._lifter_bodies["body_template"] = body

        # Note: This is just a placeholder. The solver must build their own lifter structure.

    def remove_initial_template(self):
        """Remove the initial lifter template body from the world (if present)."""
        if "body_template" in self._lifter_bodies:
            body = self._lifter_bodies.pop("body_template")
            if body and self._world:
                self._world.DestroyBody(body)

    # --- Physical constraint constants ---
    MIN_BEAM_SIZE = 0.05  # Minimum beam width/height (meters)
    MAX_BEAM_SIZE = 4.0  # Maximum beam width/height (meters)
    MIN_JOINT_LIMIT = -math.pi  # Minimum joint angle limit (radians)
    MAX_JOINT_LIMIT = math.pi  # Maximum joint angle limit (radians)

    # --- Below are Primitives API open to LLM (with physical constraints) ---

    def add_beam(self, x, y, width, height, angle=0, density=1.0):
        """
        API: Add a beam (rigid rectangular structural element)
        Constraint: 0.05 <= width, height <= 4.0
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

    def add_joint(self, body_a, body_b, anchor_point, type='pivot', lower_limit=None, upper_limit=None,
                  axis=None, lower_translation=None, upper_translation=None):
        """
        API: Add a joint between two bodies
        - type='rigid': Locks relative rotation (Weld)
        - type='pivot': Allows free rotation (Revolute) - use for motor-driven joints
        - type='slider': Prismatic joint (linear motion)
        - lower_limit, upper_limit: Joint angle limits in radians (for pivot joints)
        - axis: (dx, dy) direction of motion for slider (e.g. (0,1) for vertical)
        - lower_translation, upper_translation: limits in meters for slider
        """
        # Validate body_a (must not be None)
        if body_a is None:
            raise ValueError("add_joint: body_a cannot be None. You must provide a valid body object (e.g., from add_beam).")
        
        if body_b is None:
            body_b = self._terrain_bodies.get("ground")
        
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
        elif type == 'slider':
            # Prismatic joint
            ax = axis if axis is not None else (0, 1)
            lo = float(lower_translation) if lower_translation is not None else -10.0
            hi = float(upper_translation) if upper_translation is not None else 10.0
            joint = self._world.CreatePrismaticJoint(
                bodyA=body_a,
                bodyB=body_b,
                anchor=(anchor_x, anchor_y),
                axis=ax,
                lowerTranslation=lo,
                upperTranslation=hi,
                enableLimit=True,
                collideConnected=False
            )
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

    def set_slider_motor(self, joint, motor_speed, max_force=100.0):
        """
        API: Set motor properties for a prismatic (slider) joint
        - joint: Joint object (must be a slider/prismatic joint)
        - motor_speed: Target linear velocity (m/s)
        - max_force: Maximum motor force (N)
        """
        if type(joint).__name__ != 'b2PrismaticJoint':
            raise ValueError("set_slider_motor: joint must be a slider/prismatic joint")
        
        joint.enableMotor = True
        joint.motorSpeed = float(motor_speed)
        joint.maxMotorForce = float(max_force)

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

    def apply_force(self, body, force_vector):
        """
        API: Apply a world-space force to the center of a body.
        """
        if body and force_vector:
            body.ApplyForceToCenter(tuple(force_vector), True)

    def step(self, time_step):
        """Physics step"""
        # Apply wind force to all dynamic bodies
        wind_force = self._physics_config.get("wind_force", (0.0, 0.0))
        if wind_force != (0.0, 0.0):
            for body in self._bodies:
                if body.type == Box2D.b2_dynamicBody:
                    body.ApplyForceToCenter(wind_force, True)
            if self._object_to_lift:
                self._object_to_lift.ApplyForceToCenter(wind_force, True)
                
        self._world.Step(time_step, 10, 10)
        
        # Check fragile joints
        max_joint_force = self._physics_config.get("max_joint_force", float('inf'))
        if max_joint_force < float('inf'):
            joints_to_destroy = []
            inv_dt = 1.0 / time_step if time_step > 0 else 0.0
            for joint in self._joints:
                # b2Joint.GetReactionForce(inv_dt) returns b2Vec2
                force = joint.GetReactionForce(inv_dt)
                force_mag = (force.x**2 + force.y**2)**0.5
                if force_mag > max_joint_force:
                    joints_to_destroy.append(joint)
            
            for joint in joints_to_destroy:
                if joint in self._joints:
                    self._joints.remove(joint)
                    try:
                        self._world.DestroyJoint(joint)
                    except Exception:
                        pass

    
    def get_terrain_bounds(self):
        """Get terrain bounds (for evaluation)"""
        return {
            "ground": {"y": self._ground_y},
            "build_zone": {
                "x": [self.BUILD_ZONE_X_MIN, self.BUILD_ZONE_X_MAX],
                "y": [self.BUILD_ZONE_Y_MIN, self.BUILD_ZONE_Y_MAX]
            }
        }
    
    def get_lifter_position(self):
        """Get lifter body position (for evaluation)"""
        # Find the highest body in the build zone (likely the platform)
        if not self._bodies:
            return None
        
        # Return position of first body (solver should track their platform)
        if self._bodies:
            body = self._bodies[0]
            return (body.position.x, body.position.y)
        return None
    
    def get_object_position(self):
        """Get object position (for evaluation)"""
        if self._object_to_lift:
            return (self._object_to_lift.position.x, self._object_to_lift.position.y)
        return None

    def set_object_position(self, x, y):
        """Set object position. For K-05 the object must start at ground; after build, enforce_object_at_ground() overrides this."""
        if self._object_to_lift:
            self._object_to_lift.position = (float(x), float(y))
            self._object_to_lift.linearVelocity = (0, 0)
            self._object_to_lift.angularVelocity = 0

    def enforce_object_at_ground(self):
        """Enforce object at ground at simulation start. Call after build so the object must be lifted by the mechanism.
        Set terrain_config['skip_enforce_object_at_ground']=True to skip (e.g. reference agent test)."""
        if self._terrain_config.get('skip_enforce_object_at_ground'):
            return
        if self._object_to_lift:
            self._object_to_lift.position = (self.OBJECT_START_X, self.OBJECT_START_Y)
            self._object_to_lift.linearVelocity = (0, 0)
            self._object_to_lift.angularVelocity = 0

    def set_object_damping(self, linear_damping=0.0, angular_damping=0.0):
        """Set object linear/angular damping (reduces oscillation on platform)."""
        if self._object_to_lift:
            self._object_to_lift.linearDamping = float(linear_damping)
            self._object_to_lift.angularDamping = float(angular_damping)

    def weld_to_ground(self, body, anchor_point):
        """Weld a body to the ground at the given anchor (for stabilizing lifter base)."""
        ground = self._terrain_bodies.get("ground")
        if ground is None or body is None:
            return
        ax, ay = float(anchor_point[0]), float(anchor_point[1])
        joint = self._world.CreateWeldJoint(
            bodyA=ground,
            bodyB=body,
            anchor=(ax, ay),
            collideConnected=False
        )
        self._joints.append(joint)

    def get_target_height(self):
        """Get target height (y-axis) for renderer and evaluator."""
        return self.target_object_y

    def get_target_x(self):
        """Deprecated: use get_target_height(). Returns target height (y) for backward compatibility."""
        return self.get_target_height()
