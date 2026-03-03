"""
S-05: The Shelter task environment module
"""
import Box2D
from Box2D.b2 import (world, polygonShape, circleShape, staticBody, dynamicBody)
import math
import random


class DaVinciSandbox:
    """DaVinci Sandbox environment wrapper for S-05: The Shelter"""

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
        self._meteors = []
        self._max_force_on_core = 0.0
        
        self._seed = int(terrain_config.get("seed", 42))
        self._rng = random.Random(self._seed)

        self.world = self._world
        self.bodies = self._bodies
        self.joints = self._joints

        self.CORE_X = 10.0
        self.CORE_Y = 1.0
        self.CORE_RADIUS = 0.5
        self.CORE_MAX_FORCE = float(terrain_config.get("max_core_force", 150.0))
        
        self.BUILD_ZONE_X_MIN = 5.0
        self.BUILD_ZONE_X_MAX = 15.0
        self.BUILD_ZONE_Y_MIN = 0.0
        self.BUILD_ZONE_Y_MAX = 8.0
        self.MAX_STRUCTURE_HEIGHT = 7.5
        self.MAX_STRUCTURE_MASS = float(terrain_config.get("max_structure_mass", 300.0))

        self._meteor_count = int(terrain_config.get("meteor_count", 12))
        self._meteor_spawn_interval = int(terrain_config.get("meteor_spawn_interval", 30))
        self._step_count = 0

        self._create_terrain(terrain_config)
        self._create_core(terrain_config)

    def _create_terrain(self, terrain_config: dict):
        floor_length = 40.0
        floor_height = 0.5
        floor = self._world.CreateStaticBody(
            position=(floor_length / 2, -floor_height / 2),
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(floor_length / 2, floor_height / 2)),
                friction=0.5,
            ),
        )
        self._terrain_bodies["floor"] = floor

    def _create_core(self, terrain_config: dict):
        core = self._world.CreateDynamicBody(
            position=(self.CORE_X, self.CORE_Y),
            fixtures=Box2D.b2FixtureDef(
                shape=circleShape(radius=self.CORE_RADIUS),
                density=1.0,
                friction=0.5,
            ),
        )
        self._terrain_bodies["core"] = core

    def _spawn_meteor(self):
        x = self._rng.uniform(self.BUILD_ZONE_X_MIN - 2, self.BUILD_ZONE_X_MAX + 2)
        y = 15.0
        radius = self._rng.uniform(0.2, 0.5)
        vx = self._rng.uniform(-2.0, 2.0)
        vy = self._rng.uniform(-15.0, -10.0)
        
        meteor = self._world.CreateDynamicBody(
            position=(x, y),
            fixtures=Box2D.b2FixtureDef(
                shape=circleShape(radius=radius),
                density=5.0,
                friction=0.5,
                restitution=0.2,
            ),
        )
        meteor.linearVelocity = (vx, vy)
        self._meteors.append(meteor)

    def add_beam(self, x, y, width, height, angle=0, density=1.0):
        body = self._world.CreateDynamicBody(position=(x, y), angle=angle)
        body.CreatePolygonFixture(box=(width/2, height/2), density=density, friction=0.5)
        self._bodies.append(body)
        return body

    def add_joint(self, body_a, body_b, anchor, type='rigid'):
        if body_b is None: body_b = self._terrain_bodies["floor"]
        joint_def = Box2D.b2WeldJointDef()
        joint_def.Initialize(body_a, body_b, anchor)
        j = self._world.CreateJoint(joint_def)
        self._joints.append(j)
        return j

    def get_structure_mass(self):
        return sum(b.mass for b in self._bodies)

    def set_material_properties(self, body, restitution=0.2):
        for fixture in body.fixtures:
            fixture.restitution = float(restitution)

    def step(self, time_step):
        if self._step_count < self._meteor_count * self._meteor_spawn_interval:
            if self._step_count % self._meteor_spawn_interval == 0:
                self._spawn_meteor()
        
        self._step_count += 1
        self._world.Step(time_step, 10, 10)
        
        # Damage tracking: monitor impacts on core
        core = self._terrain_bodies["core"]
        for contact_edge in core.contacts:
            if contact_edge.contact.touching:
                # Approximate force from manifold normal impulse
                manifold = contact_edge.contact.manifold
                if manifold.pointCount > 0:
                    impulse = manifold.points[0].normalImpulse
                    force = impulse / time_step
                    self._max_force_on_core = max(self._max_force_on_core, force)

    def get_core_max_force(self):
        return self._max_force_on_core

    def get_terrain_bounds(self):
        return {
            "core": {"x": self.CORE_X, "y": self.CORE_Y, "radius": self.CORE_RADIUS},
            "build_zone": {"x": [self.BUILD_ZONE_X_MIN, self.BUILD_ZONE_X_MAX], "y": [self.BUILD_ZONE_Y_MIN, self.BUILD_ZONE_Y_MAX]},
            "core_max_force": self.CORE_MAX_FORCE,
            "max_structure_height": self.MAX_STRUCTURE_HEIGHT,
            "meteor_count": self._meteor_count,
            "meteor_spawn_interval": self._meteor_spawn_interval,
        }
