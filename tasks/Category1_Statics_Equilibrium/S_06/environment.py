"""
S-06: The Overhang task environment module
"""
import Box2D
from Box2D.b2 import (world, polygonShape, staticBody, dynamicBody)
import math


class DaVinciSandbox:
    """DaVinci Sandbox environment wrapper for S-06: The Overhang"""

    MAX_BLOCK_LENGTH = 4.0
    MAX_BLOCK_HEIGHT = 0.5
    MAX_BLOCK_COUNT = 15
    START_ZONE_X_MAX = 0.0

    def __init__(self, terrain_config=None, physics_config=None):
        terrain_config = terrain_config or {}
        physics_config = physics_config or {}
        self._terrain_config = dict(terrain_config)
        self._physics_config = dict(physics_config)

        gravity = tuple(physics_config.get("gravity", (0, -10)))
        self._world = world(gravity=gravity, doSleep=True)
        self._bodies = []
        self._joints = []
        self._terrain_bodies = {}

        self.world = self._world
        self.bodies = self._bodies
        self.joints = self._joints

        self._create_terrain(terrain_config)

    def _create_terrain(self, terrain_config: dict):
        # Table top: ends at x=0
        floor_length = 20.0
        floor_height = 1.0
        table = self._world.CreateStaticBody(
            position=(-floor_length / 2, -floor_height / 2),
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(floor_length / 2, floor_height / 2)),
                friction=0.8,
            ),
        )
        self._terrain_bodies["table"] = table

    def add_block(self, x, y, width, height, angle=0, density=1.0):
        """API: Add a block for the overhang structure."""
        # Verification: block right edge (x + width/2) should initially be on the table (<= 0) 
        # unless it is supported by another block.
        # For simplicity in this specific task, we rely on physics simulation to determine stability.
        
        body = self._world.CreateDynamicBody(position=(x, y), angle=angle)
        body.CreatePolygonFixture(box=(width/2, height/2), density=density, friction=0.6)
        self._bodies.append(body)
        return body

    def get_max_x_position(self):
        """Returns the rightmost x-coordinate of any structural component."""
        if not self._bodies: return 0.0
        max_x = -1e9
        for body in self._bodies:
            for fixture in body.fixtures:
                shape = fixture.shape
                if isinstance(shape, polygonShape):
                    for v in shape.vertices:
                        wv = body.GetWorldPoint(v)
                        max_x = max(max_x, wv.x)
        return max(0.0, max_x)

    def get_structure_mass(self):
        return sum(b.mass for b in self._bodies)

    def step(self, time_step):
        self._world.Step(time_step, 10, 10)

    def get_terrain_bounds(self):
        return {
            "table": {"x": [-10.0, 0.0]},
            "edge_x": 0.0,
            "max_block_length": self.MAX_BLOCK_LENGTH,
            "max_block_height": self.MAX_BLOCK_HEIGHT,
            "max_block_count": self.MAX_BLOCK_COUNT
        }
