"""
K-03: The Gripper task environment module
Defines physics world, terrain, objects to grasp, gripper structure, API, etc.
"""
import Box2D
from Box2D.b2 import (world, polygonShape, circleShape, staticBody, dynamicBody, revoluteJoint, weldJoint)
import math


class Sandbox:
    """Sandbox environment wrapper for K-03: The Gripper
    
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
        
        # Track gripper components
        self._gripper_bodies = {}
        self._gripper_joints = []
        
        # Track objects to grasp
        self._objects_to_grasp = []
        
        # For backward compatibility, keep public attributes (but recommend using controlled API)
        self.world = self._world  # Reserved for renderer use
        self.bodies = self._bodies
        self.joints = self._joints
        
        # 2. Generate terrain (ground surface)
        self._create_terrain(terrain_config)
        
        # 3. Set build zone and constraints
        self.BUILD_ZONE_X_MIN = 0.0  # Build zone x start
        self.BUILD_ZONE_X_MAX = 10.0  # Build zone x end
        self.BUILD_ZONE_Y_MIN = 5.0  # Build zone y start (above objects)
        self.BUILD_ZONE_Y_MAX = 15.0  # Build zone y end
        self.MAX_STRUCTURE_MASS = float(terrain_config.get("max_structure_mass", 30.0))  # Maximum total structure mass (kg)
        # Evaluation targets (single source of truth; evaluator reads these when present)
        self.TARGET_OBJECT_Y = float(terrain_config.get("target_object_y", 3.5))
        self.MIN_OBJECT_HEIGHT = float(terrain_config.get("min_object_height", 2.0))
        self.MIN_SIMULATION_TIME = float(terrain_config.get("min_simulation_time", 1.34))
        
        # 4. Create objects to grasp
        self._create_objects(terrain_config)
        
        # 5. Create initial gripper structure (basic template - solver will build their own)
        # We create a simple placeholder to show the environment, but solver must build their own gripper
        self._create_initial_gripper_template(terrain_config)

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

        # Gantry: static horizontal support for gripper base (embodied primitive: fixed anchor)
        gantry_y = 10.0
        gantry_length = 4.0
        gantry = self._world.CreateStaticBody(
            position=(5.0, gantry_y),
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(gantry_length / 2, 0.15)),
                friction=0.6,
            ),
        )
        self._terrain_bodies["gantry"] = gantry
        self._gantry_y = gantry_y

        # Platform (table) so object rests at config height (e.g. y=2.0) instead of on ground
        object_config = terrain_config.get("objects", {})
        obj_x = float(object_config.get("x", 5.0))
        obj_y = float(object_config.get("y", 2.0))
        obj_h = 0.4  # object height (box half-extent * 2)
        platform_top = obj_y - obj_h / 2  # 1.8 for obj_y=2
        platform_h = 0.4
        platform = self._world.CreateStaticBody(
            position=(obj_x, platform_top - platform_h / 2),
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(0.6, platform_h / 2)),
                friction=0.25,
            ),
        )
        self._terrain_bodies["platform"] = platform

    def _create_objects(self, terrain_config: dict):
        """
        Create objects to grasp (different shapes)
        """
        object_config = terrain_config.get("objects", {})
        object_shape = object_config.get("shape", "box")  # "box", "circle", "triangle"
        object_friction = float(object_config.get("friction", 0.6))
        object_mass = float(object_config.get("mass", 1.0))
        
        # Object position (allow override for mutations/reference test)
        object_x = float(object_config.get("x", 5.0))
        object_y = float(object_config.get("y", 2.0))
        
        if object_shape == "box":
            # Rectangular box
            width = 0.4
            height = 0.4
            density = object_mass / (width * height)
            obj = self._world.CreateDynamicBody(
                position=(object_x, object_y),
                fixtures=Box2D.b2FixtureDef(
                    shape=polygonShape(box=(width/2, height/2)),
                    density=density,
                    friction=object_friction,
                )
            )
        elif object_shape == "circle":
            # Circular object
            radius = 0.25
            density = object_mass / (math.pi * radius * radius)
            obj = self._world.CreateDynamicBody(
                position=(object_x, object_y),
                fixtures=Box2D.b2FixtureDef(
                    shape=circleShape(radius=radius),
                    density=density,
                    friction=object_friction,
                )
            )
        else:  # triangle or default
            # Triangular object (approximated as polygon)
            vertices = [(-0.2, -0.2), (0.2, -0.2), (0.0, 0.2)]
            # Calculate approximate area for density
            area = 0.5 * 0.4 * 0.4  # Approximate triangle area
            density = object_mass / area
            obj = self._world.CreateDynamicBody(
                position=(object_x, object_y),
                fixtures=Box2D.b2FixtureDef(
                    shape=polygonShape(vertices=vertices),
                    density=density,
                    friction=object_friction,
                )
            )
        
        obj.linearDamping = self._default_linear_damping
        obj.angularDamping = self._default_angular_damping
        self._objects_to_grasp.append(obj)
        self._terrain_bodies["object"] = obj

    def _create_initial_gripper_template(self, terrain_config: dict):
        """
        Create a simple placeholder gripper template to show the environment.
        This is just for visualization - the solver must build their own gripper.
        """
        spawn_x = 5.0
        spawn_y = 8.0  # Above objects
        
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
        self._gripper_bodies["body_template"] = body
        
        # Note: This is just a placeholder. The solver must build their own gripper structure.

    def remove_initial_template(self):
        """
        Remove the initial gripper template body from the world (if present).
        Call this at the start of build_agent so the solver's structure is the only gripper.
        """
        if "body_template" in self._gripper_bodies:
            body = self._gripper_bodies.pop("body_template")
            if body and self._world:
                self._world.DestroyBody(body)

    # --- Physical constraint constants ---
    MIN_BEAM_SIZE = 0.05  # Minimum beam width/height (meters)
    MAX_BEAM_SIZE = 2.0  # Maximum beam width/height (meters)
    MIN_JOINT_LIMIT = -math.pi  # Minimum joint angle limit (radians)
    MAX_JOINT_LIMIT = math.pi  # Maximum joint angle limit (radians)
    # BUILD_ZONE_X_MIN, BUILD_ZONE_X_MAX, BUILD_ZONE_Y_MIN, BUILD_ZONE_Y_MAX, MAX_STRUCTURE_MASS
    # are set in __init__ based on terrain_config
    BUILD_ZONE_X_MIN = 0.0  # Default, will be updated in __init__
    BUILD_ZONE_X_MAX = 10.0  # Default, will be updated in __init__
    BUILD_ZONE_Y_MIN = 5.0  # Build zone y start
    BUILD_ZONE_Y_MAX = 15.0  # Build zone y end
    MAX_STRUCTURE_MASS = 30.0  # Default, will be updated in __init__

    # --- Below are Primitives API open to LLM (with physical constraints) ---

    def add_beam(self, x, y, width, height, angle=0, density=1.0):
        """
        API: Add a beam (rigid rectangular structural element)
        Constraint: 0.05 <= width, height <= 2.0
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

    def add_joint(self, body_a, body_b, anchor_point, type='pivot', lower_limit=None, upper_limit=None, enable_motor=False, motor_speed=0.0, max_motor_torque=0.0,
                  axis=None, lower_translation=None, upper_translation=None, max_motor_force=0.0):
        """
        API: Add a joint between two bodies
        - type='rigid': Locks relative rotation (Weld)
        - type='pivot': Revolute joint (rotation), use for finger open/close
        - type='slider': Prismatic joint (linear), use for vertical up/down — no rotation
        - For slider: axis=(0,-1) = vertical, lower_translation/upper_translation in meters, max_motor_force in N
        """
        if body_a is None or body_b is None:
            raise ValueError("add_joint: body_a and body_b cannot be None.")
        anchor_x, anchor_y = anchor_point[0], anchor_point[1]

        if type == 'rigid':
            joint = self._world.CreateWeldJoint(
                bodyA=body_a, bodyB=body_b, anchor=(anchor_x, anchor_y), collideConnected=False
            )
        elif type == 'slider':
            # Prismatic: vertical motion only (axis (0,-1) = positive translation = down)
            ax = axis if axis is not None else (0, -1)
            lo = float(lower_translation) if lower_translation is not None else 0.0
            hi = float(upper_translation) if upper_translation is not None else 8.0
            joint = self._world.CreatePrismaticJoint(
                bodyA=body_a,
                bodyB=body_b,
                anchor=(anchor_x, anchor_y),
                axis=ax,
                lowerTranslation=lo,
                upperTranslation=hi,
                enableLimit=True,
                enableMotor=bool(enable_motor),
                motorSpeed=float(motor_speed),
                maxMotorForce=float(max_motor_force) if max_motor_force else 5000.0,
            )
        elif type == 'pivot':
            joint_kwargs = {
                'bodyA': body_a, 'bodyB': body_b, 'anchor': (anchor_x, anchor_y),
                'collideConnected': False,
                'enableMotor': bool(enable_motor),
                'motorSpeed': float(motor_speed),
                'maxMotorTorque': float(max_motor_torque),
            }
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
        """Set motor for revolute (pivot) joint: motor_speed in rad/s, max_torque in N·m."""
        if isinstance(joint, Box2D.b2RevoluteJoint):
            joint.enableMotor = True
            joint.motorSpeed = float(motor_speed)
            joint.maxMotorTorque = float(max_torque)
            return
        raise ValueError("set_motor: joint must be a pivot/revolute joint")

    def set_slider_motor(self, joint, speed, max_force=5000.0):
        """
        API: Set motor for prismatic (slider) joint — vertical伸缩
        - speed: linear velocity (m/s). Positive = extend down, negative = retract up
        - max_force: max motor force (N)
        """
        if type(joint).__name__ != 'b2PrismaticJoint':
            raise ValueError("set_slider_motor: joint must be a prismatic/slider joint")
        joint.enableMotor = True
        joint.motorSpeed = float(speed)
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

    def step(self, time_step):
        """Physics step"""
        self._world.Step(time_step, 10, 10)
    
    def get_terrain_bounds(self):
        """Get terrain bounds (for evaluation)"""
        return {
            "ground": {"y": self._ground_y},
            "build_zone": {
                "x": [self.BUILD_ZONE_X_MIN, self.BUILD_ZONE_X_MAX],
                "y": [self.BUILD_ZONE_Y_MIN, self.BUILD_ZONE_Y_MAX]
            }
        }
    
    def get_gripper_position(self):
        """Get gripper body position (for evaluation)"""
        # Find the highest body in the build zone (likely the main body)
        if not self._bodies:
            return None
        
        # Return position of first body (solver should track their main body)
        if self._bodies:
            body = self._bodies[0]
            return (body.position.x, body.position.y)
        return None
    
    def get_object_position(self):
        """Get object position (for evaluation)"""
        if "object" in self._terrain_bodies:
            obj = self._terrain_bodies["object"]
            return (obj.position.x, obj.position.y)
        return None

    def get_anchor_for_gripper(self):
        """
        Physical primitive: returns the static gantry body for attaching the gripper base.
        Weld your gripper base to this body so the gripper does not fall; then control arm and fingers.
        Returns None if gantry is not present.
        """
        return self._terrain_bodies.get("gantry")

    def get_object_contact_count(self):
        """
        Physical primitive: returns (num_contact_points, num_gripper_bodies_touching_object).
        Use this to know if the object is being grasped (contact_count > 0).
        Call after physics step; counts contacts between object and any body in _bodies (gripper).
        """
        obj = self._terrain_bodies.get("object")
        if not obj or not self._bodies:
            return 0, 0
        gripper_set = set(self._bodies)
        num_points = 0
        bodies_touching = set()
        try:
            edges = []
            contact_list = getattr(obj, 'contacts', None) or getattr(obj, 'contactList', None)
            if contact_list is not None:
                if hasattr(contact_list, '__iter__') and not hasattr(contact_list, 'next'):
                    edges = list(contact_list)
                else:
                    ce = contact_list
                    while ce:
                        edges.append(ce)
                        ce = getattr(ce, 'next', None)
            for contact_edge in edges:
                contact = getattr(contact_edge, 'contact', contact_edge)
                if getattr(contact, 'touching', False):
                    other = getattr(contact_edge, 'other', None)
                    if other is None and hasattr(contact, 'bodyA'):
                        other = contact.bodyB if contact.bodyA == obj else contact.bodyA
                    if other is not None and other in gripper_set:
                        bodies_touching.add(other)
                        num_points += getattr(getattr(contact, 'manifold', None), 'pointCount', 1)
            if not edges and hasattr(self._world, 'contactList'):
                for contact in self._world.contactList:
                    if not getattr(contact, 'touching', contact.IsTouching() if hasattr(contact, 'IsTouching') else False):
                        continue
                    a, b = contact.bodyA, contact.bodyB
                    if a == obj and b in gripper_set:
                        bodies_touching.add(b)
                        num_points += 1
                    elif b == obj and a in gripper_set:
                        bodies_touching.add(a)
                        num_points += 1
        except Exception:
            pass
        return num_points, len(bodies_touching)
