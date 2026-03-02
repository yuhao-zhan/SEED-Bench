"""
S-06: The Overhang task environment module
"""
import Box2D
from Box2D.b2 import (world, polygonShape, staticBody, dynamicBody)
import math


class DaVinciSandbox:
    """DaVinci Sandbox environment wrapper for S-06: The Overhang"""
    
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
        self._joints = []  # Disabled for this task
        self._terrain_bodies = {}
        
        self.world = self._world
        self.bodies = self._bodies
        self.joints = self._joints
        
        self._create_terrain(terrain_config)

    def _create_terrain(self, terrain_config: dict):
        """Create table: Static surface x=[-10, 0]. Edge at x=0"""
        # Get configurable friction (default 0.5)
        table_friction = float(terrain_config.get("table_friction", 0.5))
        self.TABLE_FRICTION = table_friction
        
        table = self._world.CreateStaticBody(
            position=(-5, 0.5),
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(5.0, 0.5)),
                friction=table_friction,
            ),
        )
        self._terrain_bodies["table"] = table

    # --- Physical constraint constants ---
    MIN_BLOCK_SIZE = 0.1
    MAX_BLOCK_LENGTH = 1.0  # Maximum beam length = 1.0m
    MAX_BLOCK_HEIGHT = 0.5  # Maximum beam height = 0.5m
    START_ZONE_X_MAX = 0.0  # All blocks must spawn at x < 0
    MAX_BLOCK_COUNT = 20
    TABLE_FRICTION = 0.5  # Default, can be overridden by terrain_config
    BLOCK_FRICTION = 0.5  # Default, can be overridden by terrain_config

    def step(self, time_step):
        """Physics step"""
        self._world.Step(time_step, 10, 10)
    
    def add_block(self, x, y, width, height):
        """
        API: Add a block (no joints allowed)
        Constraint: width <= 1.0, height <= 0.5
        """
        # Validate constraints
        if x >= self.START_ZONE_X_MAX:
            raise ValueError(f"Blocks must spawn at x < {self.START_ZONE_X_MAX}")
        
        if len(self._bodies) >= self.MAX_BLOCK_COUNT:
            raise ValueError(f"Maximum {self.MAX_BLOCK_COUNT} blocks allowed")
        
        width = max(self.MIN_BLOCK_SIZE, min(width, self.MAX_BLOCK_LENGTH))
        height = max(self.MIN_BLOCK_SIZE, min(height, self.MAX_BLOCK_HEIGHT))
        
        # Get configurable material properties (defaults)
        block_density = float(self._terrain_config.get("block_density", 1.0))
        block_friction = float(self._terrain_config.get("block_friction", 0.5))
        self.BLOCK_FRICTION = block_friction  # Update for consistency
        
        body = self._world.CreateDynamicBody(
            position=(x, y),
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(width/2, height/2)),
                density=block_density,
                friction=block_friction,
            )
        )
        body.linearDamping = self._default_linear_damping
        body.angularDamping = self._default_angular_damping
        self._bodies.append(body)
        return body

    def add_joint(self, body_a, body_b, anchor_point, type='rigid'):
        """
        API: DISABLED for this task
        """
        raise ValueError("add_joint is DISABLED for this task. You cannot use joints or glue. Gravity and Friction only.")

    def get_structure_mass(self):
        """API: Returns total mass"""
        total_mass = 0.0
        for body in self._bodies:
            total_mass += body.mass
        return total_mass

    def get_max_x_position(self):
        """Get maximum x position of any block"""
        if not self._bodies:
            return 0.0
        return max(b.position.x for b in self._bodies)

    def get_terrain_bounds(self):
        """Get terrain bounds"""
        return {
            "table": {"x": [-10.0, 0.0]},
            "edge_x": 0.0,
            "max_block_length": self.MAX_BLOCK_LENGTH,
            "max_block_height": self.MAX_BLOCK_HEIGHT,
            "max_block_count": self.MAX_BLOCK_COUNT
        }
