"""
S-02: The Skyscraper task environment module
Defines physics world, terrain, API, etc.
"""
import Box2D
from Box2D.b2 import (world, polygonShape, staticBody, dynamicBody, revoluteJoint, weldJoint)
import math


class DaVinciSandbox:
    """DaVinci Sandbox environment wrapper for S-02: The Skyscraper"""
    
    def __init__(self, *, terrain_config=None, physics_config=None):
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
        self._springs = []  # Track spring-damper connections
        self._terrain_bodies = {}
        
        self.world = self._world
        self.bodies = self._bodies
        self.joints = self._joints
        
        self._create_terrain(terrain_config)
        self._setup_earthquake(terrain_config)
        self._setup_wind(terrain_config)

    def _create_terrain(self, terrain_config: dict):
        """Create foundation: Static ground x=[-2, 2], y=0"""
        foundation = self._world.CreateStaticBody(
            position=(0, 0.5),
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(2.0, 0.5)),
                friction=0.8,
            ),
        )
        self._terrain_bodies["foundation"] = foundation

    def _setup_earthquake(self, terrain_config: dict):
        """Setup earthquake: Horizontal oscillation x(t) = amplitude * sin(frequency * t) starting at t=start_time"""
        # Allow mutation via terrain_config
        self._earthquake_amplitude = float(terrain_config.get("earthquake_amplitude", 0.5))
        self._earthquake_frequency = float(terrain_config.get("earthquake_frequency", 2.0))
        self._earthquake_start_time = float(terrain_config.get("earthquake_start_time", 2.0))
        self._earthquake_active = False
        self._simulation_time = 0.0  # Track simulation time

    def _setup_wind(self, terrain_config: dict):
        """Setup wind: Constant lateral force applied to all blocks above height threshold"""
        # Allow mutation via terrain_config
        self._wind_force = float(terrain_config.get("wind_force", 100.0))
        self._wind_height_threshold = float(terrain_config.get("wind_height_threshold", 20.0))

    def step(self, time_step):
        """Physics step with earthquake and wind effects"""
        # Update simulation time
        self._simulation_time += time_step
        current_time = self._simulation_time
        if current_time >= self._earthquake_start_time:
            if not self._earthquake_active:
                self._earthquake_active = True
            if "foundation" in self._terrain_bodies:
                foundation = self._terrain_bodies["foundation"]
                earthquake_x = self._earthquake_amplitude * math.sin(self._earthquake_frequency * (current_time - self._earthquake_start_time))
                # Move foundation position (Box2D handles static body movement)
                foundation.position = (earthquake_x, foundation.position.y)
        
        # Apply wind force to bodies above threshold
        for body in self._bodies:
            if body.position.y > self._wind_height_threshold:
                body.ApplyForce((self._wind_force, 0), body.worldCenter, True)
        
        self._world.Step(time_step, 10, 10)

    # --- Physical constraint constants ---
    MIN_BEAM_SIZE = 0.1
    MAX_BEAM_SIZE = 10.0
    FOUNDATION_X_MIN = -2.0
    FOUNDATION_X_MAX = 2.0
    TARGET_HEIGHT = 30.0  # Topmost point must be > 30m
    MAX_WIDTH = 8.0  # Structure width cannot exceed 8m
    STABILITY_X_MIN = -4.0
    STABILITY_X_MAX = 4.0

    def add_beam(self, x, y, width, height, angle=0, density=1.0):
        """API: Add a beam"""
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

    def add_joint(self, body_a, body_b, anchor_point, type='rigid'):
        """API: Add a joint"""
        anchor_x, anchor_y = anchor_point[0], anchor_point[1]
        
        if type == 'rigid':
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

    def add_spring(self, body_a, body_b, anchor_a, anchor_b, stiffness, damping):
        """
        API: Creates a spring-damper connection
        Use this to build shock absorbers or tuned mass dampers
        Note: This is a simplified implementation using distance joint
        """
        # Convert local anchor points to world coordinates
        if isinstance(anchor_a, (tuple, list)) and len(anchor_a) >= 2:
            anchor_a_local = (anchor_a[0], anchor_a[1])
        else:
            anchor_a_local = (0, 0)
        
        if isinstance(anchor_b, (tuple, list)) and len(anchor_b) >= 2:
            anchor_b_local = (anchor_b[0], anchor_b[1])
        else:
            anchor_b_local = (0, 0)
        
        anchor_a_world = body_a.GetWorldPoint(anchor_a_local)
        anchor_b_world = body_b.GetWorldPoint(anchor_b_local)
        
        # Create distance joint (acts like a spring-damper)
        # Note: Box2D distance joints can simulate springs with frequency and damping
        joint_def = Box2D.b2DistanceJointDef()
        joint_def.bodyA = body_a
        joint_def.bodyB = body_b
        joint_def.localAnchorA = anchor_a_local
        joint_def.localAnchorB = anchor_b_local
        joint_def.length = math.sqrt((anchor_a_world.x - anchor_b_world.x)**2 + 
                                     (anchor_a_world.y - anchor_b_world.y)**2)
        joint_def.frequencyHz = float(stiffness)  # Spring frequency (stiffness)
        joint_def.dampingRatio = float(damping)  # Damping ratio (0-1)
        joint_def.collideConnected = False
        
        joint = self._world.CreateJoint(joint_def)
        self._springs.append(joint)
        return joint

    def get_structure_mass(self):
        """API: Returns total mass of created objects"""
        total_mass = 0.0
        for body in self._bodies:
            total_mass += body.mass
        return total_mass

    def get_structure_bounds(self):
        """Get structure bounds (for evaluation)"""
        if not self._bodies:
            return {"top": 0, "width": 0, "center_x": 0}
        
        # More accurate calculation: consider actual beam sizes
        min_x = float('inf')
        max_x = float('-inf')
        max_y = float('-inf')
        
        for body in self._bodies:
            # Get actual fixture bounds
            for fixture in body.fixtures:
                shape = fixture.shape
                if hasattr(shape, 'box'):
                    # Polygon shape with box attribute
                    box_width, box_height = shape.box
                    body_min_x = body.position.x - box_width
                    body_max_x = body.position.x + box_width
                    body_max_y = body.position.y + box_height
                    
                    min_x = min(min_x, body_min_x)
                    max_x = max(max_x, body_max_x)
                    max_y = max(max_y, body_max_y)
                else:
                    # Fallback to approximate
                    min_x = min(min_x, body.position.x - 1.0)
                    max_x = max(max_x, body.position.x + 1.0)
                    max_y = max(max_y, body.position.y + 1.0)
        
        if min_x == float('inf'):
            return {"top": 0, "width": 0, "center_x": 0}
        
        return {
            "top": max_y,
            "width": max_x - min_x,
            "center_x": (min_x + max_x) / 2.0,
            "min_x": min_x,
            "max_x": max_x
        }

    def get_terrain_bounds(self):
        """Get terrain bounds (for evaluation)"""
        return {
            "foundation": {"x": [self.FOUNDATION_X_MIN, self.FOUNDATION_X_MAX], "y": 0},
            "target_height": self.TARGET_HEIGHT,
            "max_width": self.MAX_WIDTH,
            "stability_zone": {"x": [self.STABILITY_X_MIN, self.STABILITY_X_MAX]}
        }
