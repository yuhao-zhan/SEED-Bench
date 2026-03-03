"""
S-06: The Overhang task environment module
Redesigned for extreme difficulty with dynamic forces and structural constraints.
"""
import Box2D
from Box2D.b2 import (world, polygonShape, staticBody, dynamicBody, kinematicBody)
import math


class DaVinciSandbox:
    """DaVinci Sandbox environment wrapper for S-06: The Overhang"""

    MAX_BLOCK_LENGTH = 4.0 
    MAX_BLOCK_HEIGHT = 0.4
    MAX_BLOCK_COUNT = 20
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

        # Set world damping
        self._world.linearDamping = physics_config.get("linear_damping", 0.1)
        self._world.angularDamping = physics_config.get("angular_damping", 0.1)

        # Oscillation parameters
        self._oscillate = terrain_config.get("oscillate", False)
        self._osc_amplitude = terrain_config.get("osc_amplitude", 0.2)
        self._osc_frequency = terrain_config.get("osc_frequency", 5.0)
        self._timer = 0.0
        
        # Table Angle
        self._table_angle = terrain_config.get("table_angle", 0.0)

        self._create_terrain(terrain_config)

    def _create_terrain(self, terrain_config: dict):
        floor_length = 20.0
        floor_height = 1.0
        table_friction = terrain_config.get("table_friction", 0.8)
        angle_rad = math.radians(self._table_angle)
        
        # Static or kinematic table
        # Pivot point is (0, 0)
        # Position of center must be adjusted based on angle to keep edge at 0,0
        # For simplicity, we just use the previous logic.
        pos = (-10.0, -0.5)
        
        if self._oscillate:
            table = self._world.CreateKinematicBody(
                position=pos,
                angle=angle_rad,
                fixtures=Box2D.b2FixtureDef(
                    shape=polygonShape(box=(floor_length / 2, floor_height / 2)),
                    friction=table_friction,
                ),
            )
        else:
            table = self._world.CreateStaticBody(
                position=pos,
                angle=angle_rad,
                fixtures=Box2D.b2FixtureDef(
                    shape=polygonShape(box=(floor_length / 2, floor_height / 2)),
                    friction=table_friction,
                ),
            )
        self._terrain_bodies["table"] = table

        # Optional Ceiling
        if "ceiling_y" in terrain_config:
            cy = terrain_config["ceiling_y"]
            ceiling = self._world.CreateStaticBody(
                position=(0, cy + 0.5), 
                fixtures=Box2D.b2FixtureDef(
                    shape=polygonShape(box=(20.0, 0.5)),
                    friction=0.2,
                ),
            )
            self._terrain_bodies["ceiling"] = ceiling

    def add_block(self, x, y, width, height, angle=0, density=None):
        """API: Add a block for the overhang structure."""
        if density is None:
            density = self._terrain_config.get("block_density", 1.0)
        
        block_friction = self._terrain_config.get("block_friction", 0.6)
        
        body = self._world.CreateDynamicBody(position=(x, y), angle=angle)
        body.CreatePolygonFixture(box=(width/2, height/2), density=density, friction=block_friction)
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
        if self._oscillate:
            self._timer += time_step
            vx = self._osc_amplitude * self._osc_frequency * math.cos(self._osc_frequency * self._timer)
            self._terrain_bodies["table"].linearVelocity = (vx, 0)
            
        self._world.Step(time_step, 10, 10)

    def get_terrain_bounds(self):
        bounds = {
            "table": {"x": [-10.0, 0.0], "angle": self._table_angle},
            "edge_x": 0.0,
            "max_block_length": self.MAX_BLOCK_LENGTH,
            "max_block_height": self.MAX_BLOCK_HEIGHT,
            "max_block_count": self.MAX_BLOCK_COUNT,
            "spawn_zone": self._terrain_config.get("spawn_zone", [-10.0, 0.0])
        }
        if "ceiling_y" in self._terrain_config:
            bounds["ceiling_y"] = self._terrain_config["ceiling_y"]
        return bounds
