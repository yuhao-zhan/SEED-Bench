"""
K-06: The Wiper task environment module
Defines physics world, terrain (glass surface), particles, wiper structure, API, etc.
"""
import Box2D
from Box2D.b2 import (world, polygonShape, circleShape, staticBody, dynamicBody, revoluteJoint, weldJoint)
import math
import random


class Sandbox:
    """Sandbox environment wrapper for K-06: The Wiper
    
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
        
        # Track wiper components
        self._wiper_bodies = {}
        self._wiper_joints = []
        
        # Track particles to clean
        self._particles = []
        
        # For backward compatibility, keep public attributes (but recommend using controlled API)
        self.world = self._world  # Reserved for renderer use
        self.bodies = self._bodies
        self.joints = self._joints
        
        # 2. Generate terrain (glass surface)
        self._create_terrain(terrain_config)
        
        # 3. Set build zone and constraints
        self.BUILD_ZONE_X_MIN = 0.0  # Build zone x start
        self.BUILD_ZONE_X_MAX = 12.0  # Build zone x end
        self.BUILD_ZONE_Y_MIN = 2.0  # Build zone y start (above glass)
        self.BUILD_ZONE_Y_MAX = 10.0  # Build zone y end
        self.MAX_STRUCTURE_MASS = float(terrain_config.get("max_structure_mass", 15.0))  # Hard: 15kg limit (was 25)
        # Reference test: use 3-segment bar when smooth glass so bar can oscillate
        self._reference_wiper_short_bar = bool(terrain_config.get("reference_short_bar", False))
        
        # 4. Create particles to clean
        self._create_particles(terrain_config)
        
        # 5. Create initial wiper structure (basic template - solver will build their own)
        # We create a simple placeholder to show the environment, but solver must build their own wiper
        self._create_initial_wiper_template(terrain_config)

    # Collision filter bits: wiper does not collide with glass so it can swing freely
    _CATEGORY_GLASS = 0x0001
    _CATEGORY_WIPER = 0x0002
    _CATEGORY_PARTICLE = 0x0004

    def _create_terrain(self, terrain_config: dict):
        """
        Create terrain: glass surface
        """
        glass_friction = float(terrain_config.get("glass_friction", 0.25))
        glass_length = 12.0  # Glass surface length
        glass_height = 0.1  # Thin glass surface
        glass_y = 2.0  # Glass top surface at y=2.0m
        
        fd = Box2D.b2FixtureDef(
            shape=polygonShape(box=(glass_length / 2, glass_height / 2)),
            friction=glass_friction,
        )
        if terrain_config.get("wiper_ignore_glass_collision", True):  # Hard: default True so wiper can swing
            fd.filter.categoryBits = self._CATEGORY_GLASS
            fd.filter.maskBits = self._CATEGORY_GLASS | self._CATEGORY_PARTICLE  # no wiper
        glass = self._world.CreateStaticBody(
            position=(glass_length / 2, glass_y - glass_height / 2),
            fixtures=fd,
        )
        self._terrain_bodies["glass"] = glass
        self._glass_y = glass_y  # Glass top surface at y = 2.0m
        self._glass_length = glass_length
        self._glass_friction = glass_friction

    def _create_particles(self, terrain_config: dict):
        """
        Create particles to clean (small circular objects on glass)
        """
        particle_config = terrain_config.get("particles", {})
        num_particles = int(particle_config.get("count", 45))  # Hard: 45 particles, 100% must be cleared
        particle_friction = float(particle_config.get("friction", 0.35))
        particle_mass = float(particle_config.get("mass", 0.15))
        particle_radius = float(particle_config.get("radius", 0.08))
        
        particle_seed = int(particle_config.get("seed", 42))
        random.seed(particle_seed)
        glass_start_x = 1.0
        glass_end_x = 11.0
        
        use_filter = terrain_config.get("wiper_ignore_glass_collision", True)
        for i in range(num_particles):
            # Random position on glass
            x = random.uniform(glass_start_x, glass_end_x)
            y = self._glass_y + particle_radius  # On top of glass
            
            density = particle_mass / (math.pi * particle_radius * particle_radius)
            pfd = Box2D.b2FixtureDef(
                shape=circleShape(radius=particle_radius),
                density=density,
                friction=particle_friction,
            )
            if use_filter:
                pfd.filter.categoryBits = self._CATEGORY_PARTICLE
                pfd.filter.maskBits = self._CATEGORY_GLASS | self._CATEGORY_WIPER | self._CATEGORY_PARTICLE
            particle = self._world.CreateDynamicBody(
                position=(x, y),
                fixtures=pfd,
            )
            particle.linearDamping = self._default_linear_damping
            particle.angularDamping = self._default_angular_damping
            self._particles.append(particle)
        
        self._initial_particle_count = len(self._particles)

    def _create_initial_wiper_template(self, terrain_config: dict):
        """
        Create a simple placeholder wiper template to show the environment.
        This is just for visualization - the solver must build their own wiper.
        """
        spawn_x = 6.0  # Center of glass
        spawn_y = 4.0  # Above glass
        
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
        self._wiper_bodies["body_template"] = body
        
        # Note: This is just a placeholder. The solver must build their own wiper structure.

    def remove_initial_template(self):
        """Remove the initial wiper template body from the world (if present)."""
        if "body_template" in self._wiper_bodies:
            body = self._wiper_bodies.pop("body_template")
            if body and self._world:
                self._world.DestroyBody(body)

    def weld_to_glass(self, body, anchor_point):
        """Weld a body to the glass surface at the given anchor (keeps wiper base fixed)."""
        glass = self._terrain_bodies.get("glass")
        if glass is None or body is None:
            return
        ax, ay = float(anchor_point[0]), float(anchor_point[1])
        joint = self._world.CreateWeldJoint(
            bodyA=glass,
            bodyB=body,
            anchor=(ax, ay),
            collideConnected=False
        )
        self._joints.append(joint)

    # --- Physical constraint constants ---
    MIN_BEAM_SIZE = 0.05  # Minimum beam width/height (meters)
    MAX_BEAM_SIZE = 2.0  # Maximum beam width/height (meters)
    MIN_JOINT_LIMIT = -math.pi  # Minimum joint angle limit (radians)
    MAX_JOINT_LIMIT = math.pi  # Maximum joint angle limit (radians)
    # BUILD_ZONE_X_MIN, BUILD_ZONE_X_MAX, BUILD_ZONE_Y_MIN, BUILD_ZONE_Y_MAX, MAX_STRUCTURE_MASS
    # are set in __init__ based on terrain_config
    BUILD_ZONE_X_MIN = 0.0  # Default, will be updated in __init__
    BUILD_ZONE_X_MAX = 12.0  # Default, will be updated in __init__
    BUILD_ZONE_Y_MIN = 2.0  # Build zone y start
    BUILD_ZONE_Y_MAX = 10.0  # Build zone y end
    MAX_STRUCTURE_MASS = 15.0  # Hard default; overridden in __init__ from terrain_config

    # --- Below are Primitives API open to LLM (with physical constraints) ---

    def add_beam(self, x, y, width, height, angle=0, density=1.0):
        """
        API: Add a beam (rigid rectangular structural element)
        Constraint: 0.05 <= width, height <= 2.0
        """
        # Validate constraints
        width = max(self.MIN_BEAM_SIZE, min(width, self.MAX_BEAM_SIZE))
        height = max(self.MIN_BEAM_SIZE, min(height, self.MAX_BEAM_SIZE))
        
        beam_fd = Box2D.b2FixtureDef(
            shape=polygonShape(box=(width/2, height/2)),
            density=density,
            friction=0.5,
        )
        if self._terrain_config.get("wiper_ignore_glass_collision"):
            beam_fd.filter.categoryBits = self._CATEGORY_WIPER
            beam_fd.filter.maskBits = self._CATEGORY_WIPER | self._CATEGORY_PARTICLE
        body = self._world.CreateDynamicBody(
            position=(x, y),
            angle=angle,
            fixtures=beam_fd,
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
        # PyBox2D uses motorEnabled (not enableMotor)
        joint.motorEnabled = True
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
        """Physics step"""
        self._world.Step(time_step, 10, 10)
    
    def get_terrain_bounds(self):
        """Get terrain bounds (for evaluation)"""
        return {
            "glass": {"y": self._glass_y, "length": self._glass_length, "friction": self._glass_friction},
            "build_zone": {
                "x": [self.BUILD_ZONE_X_MIN, self.BUILD_ZONE_X_MAX],
                "y": [self.BUILD_ZONE_Y_MIN, self.BUILD_ZONE_Y_MAX]
            }
        }
    
    def get_wiper_position(self):
        """Get wiper body position (for evaluation)"""
        # Find the first body in the build zone (likely the main body)
        if not self._bodies:
            return None
        
        # Return position of first body (solver should track their main body)
        if self._bodies:
            body = self._bodies[0]
            return (body.position.x, body.position.y)
        return None
    
    def get_particle_count(self):
        """Get number of particles remaining on glass (for evaluation).
        Remaining = still on the glass: 0.5 <= x <= 11.5 and |y - glass_y| < 0.5.
        Removed = pushed off the glass: x < 0.5 or x > 11.5 or |y - glass_y| >= 0.5.
        Task failure: residual > 20% (i.e. must remove at least 80% of particles).
        """
        remaining = 0
        for particle in self._particles:
            if abs(particle.position.y - self._glass_y) < 0.5 and \
               0.5 <= particle.position.x <= 11.5:
                remaining += 1
        return remaining
    
    def get_initial_particle_count(self):
        """Get initial particle count"""
        return self._initial_particle_count
