"""
S-04: The Balancer task environment module
"""
import Box2D
from Box2D.b2 import (world, polygonShape, circleShape, staticBody, dynamicBody, revoluteJoint, weldJoint)
import math


class DaVinciSandbox:
    """DaVinci Sandbox environment wrapper for S-04: The Balancer"""
    
    # --- Physical constraint constants (can be overridden by terrain_config) ---
    MIN_BEAM_SIZE = 0.1
    MAX_BEAM_SIZE = 10.0
    MAX_BEAM_WIDTH = 7.0   # Task-specific: limit solution space (reference solution within)
    MAX_BEAM_HEIGHT = 2.0
    PIVOT_POSITION = (0.0, 0.0)
    LOAD_POSITION = (3.0, 0.0)
    LOAD_MASS = 200.0
    MAX_ANGLE_DEVIATION = 10.0 * math.pi / 180.0  # ±10 degrees
    BALANCE_TIME = 15.0  # seconds
    
    def __init__(self, *, terrain_config=None, physics_config=None):
        terrain_config = terrain_config or {}
        physics_config = physics_config or {}
        self._terrain_config = dict(terrain_config)
        self._physics_config = dict(physics_config)

        gravity = tuple(physics_config.get("gravity", (0, -10)))
        self._default_linear_damping = float(physics_config.get("linear_damping", 0.0))
        self._default_angular_damping = float(physics_config.get("angular_damping", 0.0))
        self._default_friction = float(physics_config.get("friction", 0.5))  # Default friction for all beams
        self._default_restitution = float(physics_config.get("restitution", 0.0))  # Default restitution (bounciness)

        self._world = world(gravity=gravity, doSleep=True)
        self._bodies = []
        self._joints = []
        self._terrain_bodies = {}
        
        # Override constants from terrain_config if provided
        self.MAX_ANGLE_DEVIATION = terrain_config.get("max_angle_deviation_deg", 10.0) * math.pi / 180.0
        self.BALANCE_TIME = float(terrain_config.get("balance_time", 15.0))
        
        self.world = self._world
        self.bodies = self._bodies
        self.joints = self._joints
        
        # Mutated constraints
        self._obstacle_active = terrain_config.get("obstacle_active", False)
        self._obstacle_rect = terrain_config.get("obstacle_rect", [-2.5, -0.1, -1.5, 1.5])
        
        self._drop_load = terrain_config.get("drop_load", False)
        
        self._wind_active = terrain_config.get("wind_active", False)
        self._wind_force_multiplier = float(terrain_config.get("wind_force_multiplier", 5.0))
        
        self._create_terrain(terrain_config)
        self._setup_load(terrain_config)

    def _create_terrain(self, terrain_config: dict):
        """Create pivot at (0,0) - shape configurable (sharp triangle or rounded dome)"""
        pivot_shape = terrain_config.get("pivot_shape", "sharp")  # "sharp" or "rounded"
        pivot_friction = float(terrain_config.get("pivot_friction", self._default_friction * 1.6))  # Default 0.8 if friction=0.5
        
        if pivot_shape == "rounded":
            # Rounded dome pivot (circle) - less stable contact
            pivot = self._world.CreateStaticBody(
                position=(0, 0),
                fixtures=Box2D.b2FixtureDef(
                    shape=circleShape(radius=0.05),
                    friction=pivot_friction,
                ),
            )
            self._terrain_bodies["pivot"] = pivot
        else:
            # Default: sharp triangle pivot
            # Ensure pivot is created and added to _terrain_bodies
            pivot = self._world.CreateStaticBody(
                position=(0, 0),
                fixtures=Box2D.b2FixtureDef(
                    shape=polygonShape(vertices=[(0, 0.05), (-0.05, 0), (0.05, 0)]),
                    friction=pivot_friction,
                ),
            )
            self._terrain_bodies["pivot"] = pivot        
        if self._obstacle_active:
            xmin, ymin, xmax, ymax = self._obstacle_rect
            cx, cy = (xmin + xmax) / 2.0, (ymin + ymax) / 2.0
            hw, hh = (xmax - xmin) / 2.0, (ymax - ymin) / 2.0
            self._terrain_bodies["obstacle"] = self._world.CreateStaticBody(
                position=(cx, cy),
                fixtures=Box2D.b2FixtureDef(
                    shape=polygonShape(box=(hw, hh)),
                    friction=0.5,
                ),
            )

    def _setup_load(self, terrain_config: dict):
        """Setup load at (3, 0) that auto-attaches - mass configurable"""
        self._load_mass = float(terrain_config.get("load_mass", 200.0))
        self._load_position = (3.0, 0.0)
        self._load_body = None
        self._load_attached = False
        self._initial_disturbance_applied = False
        self._initial_disturbance = terrain_config.get("initial_disturbance", None)  # dict with "angular_velocity" or None

        if self._drop_load:
            # Spawn dynamic load immediately above the structure
            self._load_position = (3.0, 4.0)
            self._load_body = self._world.CreateDynamicBody(
                position=self._load_position,
                fixtures=Box2D.b2FixtureDef(
                    shape=polygonShape(box=(0.5, 0.5)),
                    density=self._load_mass / (1.0 * 1.0),
                    friction=0.8,
                    restitution=0.1
                )
            )
            self._load_attached = True # Marked as attached since it exists in the world
            self._terrain_bodies["load"] = self._load_body

    def step(self, time_step):
        """Physics step with load attachment and initial disturbance"""
        # Apply initial disturbance once (after first body is created)
        if not self._initial_disturbance_applied and self._bodies and self._initial_disturbance:
            main_beam = self._bodies[0]  # First beam is main beam
            if "angular_velocity" in self._initial_disturbance:
                main_beam.angularVelocity = float(self._initial_disturbance["angular_velocity"])
            if "linear_velocity" in self._initial_disturbance:
                vx = float(self._initial_disturbance["linear_velocity"][0])
                vy = float(self._initial_disturbance["linear_velocity"][1])
                main_beam.linearVelocity = (vx, vy)
            self._initial_disturbance_applied = True
            
        if self._wind_active:
            for body in self._bodies:
                body.ApplyForceToCenter((body.mass * self._wind_force_multiplier, 0), wake=True)
            if self._load_body:
                self._load_body.ApplyForceToCenter((self._load_body.mass * self._wind_force_multiplier, 0), wake=True)
        
        # Auto-attach load if structure present at (3,0)
        if not self._load_attached and not self._drop_load and self._bodies:
            # Check if any body is near (3, 0)
            for body in self._bodies:
                dist = math.sqrt((body.position.x - 3.0)**2 + (body.position.y - 0.0)**2)
                if dist < 0.5:  # Within 0.5m
                    # Create and attach load
                    self._load_body = self._world.CreateDynamicBody(
                        position=(3.0, 0.5),
                        fixtures=Box2D.b2FixtureDef(
                            shape=polygonShape(box=(0.5, 0.5)),
                            density=self._load_mass / (1.0 * 1.0),
                        )
                    )
                    # Attach to nearest body
                    joint = self._world.CreateWeldJoint(
                        bodyA=body,
                        bodyB=self._load_body,
                        anchor=(3.0, 0.0),
                        collideConnected=False
                    )
                    self._load_attached = True
                    self._terrain_bodies["load"] = self._load_body
                    break
        
        self._world.Step(time_step, 10, 10)

    def add_beam(self, x, y, width, height, angle=0, density=1.0):
        """API: Add a beam"""
        width = max(self.MIN_BEAM_SIZE, min(width, self.MAX_BEAM_WIDTH))
        height = max(self.MIN_BEAM_SIZE, min(height, self.MAX_BEAM_HEIGHT))
        
        body = self._world.CreateDynamicBody(
            position=(x, y),
            angle=angle,
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(width/2, height/2)),
                density=density,
                friction=self._default_friction,
                restitution=self._default_restitution,
            )
        )
        body.linearDamping = self._default_linear_damping
        body.angularDamping = self._default_angular_damping
        self._bodies.append(body)
        return body

    def add_joint(self, body_a, body_b, anchor_point, type='rigid'):
        """API: Add a joint"""
        anchor_x, anchor_y = anchor_point[0], anchor_point[1]
        
        # Check if connecting to pivot
        pivot = self._terrain_bodies.get("pivot")
        if pivot and (body_a == pivot or body_b == pivot):
            # NOTE: allow either order (pivot can be body_a or body_b).
            other = body_b if body_a == pivot else body_a
            
            # Check if forced to use pivot joint (for mutated tasks)
            force_pivot = self._terrain_config.get("force_pivot_joint", False)
            if force_pivot:
                # Force revolute joint regardless of requested type
                joint = self._world.CreateRevoluteJoint(
                    bodyA=other,
                    bodyB=pivot,
                    anchor=(0, 0),
                    collideConnected=False
                )
            elif type == 'pivot':
                joint = self._world.CreateRevoluteJoint(
                    bodyA=other,
                    bodyB=pivot,
                    anchor=(0, 0),
                    collideConnected=False
                )
            elif type == 'rigid':
                joint = self._world.CreateWeldJoint(
                    bodyA=other,
                    bodyB=pivot,
                    anchor=(0, 0),
                    collideConnected=False
                )
            else:
                raise ValueError(f"Unknown joint type: {type}")
        elif type == 'rigid':
            joint = self._world.CreateWeldJoint(
                bodyA=body_a,
                bodyB=body_b,
                anchor=(anchor_x, anchor_y),
                collideConnected=False
            )
        elif type == 'pivot':
            joint = self._world.CreateRevoluteJoint(
                bodyA=body_a,
                bodyB=body_b,
                anchor=(anchor_x, anchor_y),
                collideConnected=False
            )
        else:
            raise ValueError(f"Unknown joint type: {type}")
        
        self._joints.append(joint)
        return joint

    def get_structure_mass(self):
        """API: Returns total mass"""
        total_mass = 0.0
        for body in self._bodies:
            total_mass += body.mass
        return total_mass

    def get_main_beam_angle(self):
        """Get angle of main beam (first beam)"""
        if self._bodies:
            return self._bodies[0].angle
        return 0.0

    def get_terrain_bounds(self):
        """Get terrain bounds (includes beam limits for consistency with prompt/feedback)."""
        return {
            "pivot": self.PIVOT_POSITION,
            "load_position": self.LOAD_POSITION,
            "max_angle_deviation": self.MAX_ANGLE_DEVIATION * 180 / math.pi,
            "max_beam_width": self.MAX_BEAM_WIDTH,
            "max_beam_height": self.MAX_BEAM_HEIGHT,
        }
