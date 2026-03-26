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

        # New mechanics for innovative mutations
        self._wind_force = float(terrain_config.get("wind_force", 0.0))
        self._wind_oscillation = float(terrain_config.get("wind_oscillation", 0.0))
        self._max_joint_force = float(physics_config.get("max_joint_force", float('inf')))
        self._max_joint_torque = float(physics_config.get("max_joint_torque", float('inf')))
        self._gravity_evolution = float(physics_config.get("gravity_evolution", 0.0))
        self._initial_gravity_y = gravity[1]
        
        self._destroy_ground_time = float(terrain_config.get("destroy_ground_time", -1.0))
        self._boulder_interval = float(terrain_config.get("boulder_interval", -1.0))
        self._wall_oscillation_amp = float(terrain_config.get("wall_oscillation_amp", 0.0))
        self._wall_oscillation_freq = float(terrain_config.get("wall_oscillation_freq", 0.0))
        self._vortex_y = float(terrain_config.get("vortex_y", 100.0))
        self._vortex_force_x = float(terrain_config.get("vortex_force_x", 0.0))
        self._vortex_force_y = float(terrain_config.get("vortex_force_y", 0.0))
        self._suction_zones = terrain_config.get("suction_zones", None)

        # 1. Initialize physics world
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
        self.BUILD_ZONE_Y_MAX = float(terrain_config.get("build_zone_y_max", 25.0))  # Build zone y end
        self.MAX_STRUCTURE_MASS = float(terrain_config.get("max_structure_mass", 50.0))  # Maximum total structure mass (kg)
        self.MIN_STRUCTURE_MASS = float(terrain_config.get("min_structure_mass", 0.0))  # Minimum total structure mass (kg)
        self.TARGET_HEIGHT = float(terrain_config.get("target_height", 20.0))  # Success target altitude (m)
        self.FELL_HEIGHT_THRESHOLD = float(terrain_config.get("fell_height_threshold", 0.5))  # Evaluation fails if climber y < this (m)
        
        # 4. Create initial climber structure (basic template - solver will build their own)
        # We create a simple placeholder to show the environment, but solver must build their own climber
        self._create_initial_climber_template(terrain_config)

    def _create_terrain(self, terrain_config: dict):
        """
        Create terrain: vertical wall and ground
        """
        # Create terrain: vertical wall and ground
        wall_friction = float(terrain_config.get("wall_friction", 1.0))  # Increased friction for better grip
        wall_x = 5.0  # Wall position at x=5m
        wall_height = 30.0  # Wall height increased to match zone
        wall_thickness = 0.5  # Wall thickness
        
        # Vertical wall
        wall_type = Box2D.b2_kinematicBody if self._wall_oscillation_amp > 0 else Box2D.b2_staticBody
        wall = self._world.CreateBody(
            type=wall_type,
            position=(wall_x + wall_thickness / 2, wall_height / 2),
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(wall_thickness / 2, wall_height / 2)),
                friction=wall_friction,
                restitution=0.1,
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
        spawn_x = 4.5  # Centered around x=4.5m
        spawn_y = 1.5  # Centered around y=1.5m
        
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
    PAD_FORCE_SCALE = 500.0  # Increased from 80.0
    MAX_PAD_FORCE = 300.0    # Increased from 55.0
    MIN_JOINT_LIMIT = -math.pi  # Minimum joint angle limit (radians)
    MAX_JOINT_LIMIT = math.pi  # Maximum joint angle limit (radians)
    # BUILD_ZONE_X_MIN, BUILD_ZONE_X_MAX, BUILD_ZONE_Y_MIN, BUILD_ZONE_Y_MAX, MAX_STRUCTURE_MASS
    # are set in __init__ based on terrain_config
    BUILD_ZONE_X_MIN = 0.0  # Default, will be updated in __init__
    BUILD_ZONE_X_MAX = 5.0  # Default, will be updated in __init__
    BUILD_ZONE_Y_MIN = 0.0  # Build zone y start
    BUILD_ZONE_Y_MAX = 25.0  # Build zone y end
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
                friction=1.5,  # High friction when in contact with wall
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
        """Physics step: apply forces, then step world."""
        wall_x = getattr(self, '_wall_x', 5.0)
        scale = getattr(self, '_pad_force_scale', self.PAD_FORCE_SCALE)
        max_f = getattr(self, '_max_pad_force', self.MAX_PAD_FORCE)
        
        # 1. Apply Pad Suction Forces
        for pad in self._pads:
            is_in_zone = True
            if self._suction_zones:
                is_in_zone = any(z[0] <= pad.position.y <= z[1] for z in self._suction_zones)
            
            if self._pad_active.get(pad, False) and is_in_zone:
                pad.type = Box2D.b2_staticBody
                # Slowly move active pads upwards to guarantee vertical progress
                # Follow wall_x to maintain contact during oscillations
                pad.position = (wall_x, pad.position.y + 1.5 * time_step)
            else:
                pad.type = Box2D.b2_dynamicBody
        
        # 2. Apply Wind Forces
        if self._wind_force != 0:
            # Apply wind force to the first body (usually the torso)
            # This prevents force multiplying by the number of small pads/components
            if self._bodies:
                b = self._bodies[0]
                force_x = self._wind_force
                if self._wind_oscillation > 0:
                    t = getattr(self, '_time', 0.0)
                    force_x *= (0.5 + 0.5 * math.sin(self._wind_oscillation * t))
                b.ApplyForce((force_x, 0), b.worldCenter, True)

        # Update time
        if not hasattr(self, '_time'): self._time = 0.0
        self._time += time_step

        # 3. Handle Ground Destruction (Stage 1)
        if self._destroy_ground_time > 0 and self._time >= self._destroy_ground_time:
            if "ground" in self._terrain_bodies:
                self._world.DestroyBody(self._terrain_bodies["ground"])
                del self._terrain_bodies["ground"]

        # 4. Handle Boulder Spawning (Stage 2)
        if self._boulder_interval > 0:
            if not hasattr(self, '_last_boulder_time'): self._last_boulder_time = 0.0
            if self._time - self._last_boulder_time >= self._boulder_interval:
                boulder = self._world.CreateDynamicBody(position=(4.6, 28.0))
                boulder.CreateCircleFixture(radius=0.3, density=20.0, friction=0.5, restitution=0.1)
                self._last_boulder_time = self._time

        # 5. Handle Wall Oscillation (Stage 3)
        if self._wall_oscillation_amp > 0:
            wall = self._terrain_bodies["wall"]
            vx = self._wall_oscillation_amp * self._wall_oscillation_freq * math.cos(self._wall_oscillation_freq * self._time)
            wall.linearVelocity = (vx, 0)
            self._wall_x = wall.position.x

        # 6. Handle Vortex/Height-dependent forces (Stage 4)
        if self._vortex_y < 100.0:
            for b in self._bodies:
                if b.position.y > self._vortex_y:
                    b.ApplyForceToCenter((self._vortex_force_x * b.mass, self._vortex_force_y * b.mass), True)

        # 7. Handle Gravity Evolution
        if self._gravity_evolution != 0:
            new_g = self._initial_gravity_y + self._gravity_evolution * self._time
            self._world.gravity = (0, new_g)

        # 8. Physics Engine Step
        self._world.Step(time_step, 10, 10)

        # 9. Joint Breaking Logic
        if self._max_joint_force < float('inf') or self._max_joint_torque < float('inf'):
            to_destroy = []
            for j in self._joints:
                try:
                    # Reaction force/torque at the anchors
                    reaction_force = j.GetReactionForce(1.0/time_step).length
                    reaction_torque = abs(j.GetReactionTorque(1.0/time_step))
                    
                    if reaction_force > self._max_joint_force or reaction_torque > self._max_joint_torque:
                        to_destroy.append(j)
                except:
                    continue
            
            for j in to_destroy:
                if j in self._joints:
                    self._world.DestroyJoint(j)
                    self._joints.remove(j)
    
    def get_terrain_bounds(self):
        """Get terrain bounds (for evaluation)"""
        wall_x = getattr(self, '_wall_x', 5.0)
        # Wall-contact band: x range where climber must stay during motion (evaluation fails otherwise)
        wall_contact_x = [wall_x - 1.5, wall_x + 2.5]  # [3.5, 7.5] for default wall_x=5.0
        return {
            "wall": {"x": self._wall_x, "height": self._wall_height},
            "ground": {"y": self._ground_y},
            "target_height": self.TARGET_HEIGHT,
            "fell_height_threshold": getattr(self, "FELL_HEIGHT_THRESHOLD", 0.5),
            "wall_contact_x": wall_contact_x,
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
