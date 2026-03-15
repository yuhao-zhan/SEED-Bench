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
        do_sleep = True if abs(gravity[1]) < 20 else False
        self._world = world(gravity=gravity, doSleep=do_sleep)
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

        self.CORE_X = float(terrain_config.get("core_x", 10.0))
        self.CORE_Y = float(terrain_config.get("core_y", 1.0))
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
        self._wind_force = float(terrain_config.get("wind_force", 0.0))
        self._meteor_restitution = float(terrain_config.get("meteor_restitution", 0.2))
        self._meteor_density = float(terrain_config.get("meteor_density", 5.0))
        self._floor_friction = float(terrain_config.get("floor_friction", 0.5))
        self._floor_restitution = float(terrain_config.get("floor_restitution", 0.0))
        self._structure_restitution = float(terrain_config.get("structure_restitution", 0.0))
        self._structure_friction = float(terrain_config.get("structure_friction", 0.5))
        self._meteor_vx_range = terrain_config.get("meteor_vx_range", [-2.0, 2.0])
        self._max_joint_force = float(terrain_config.get("max_joint_force", 1e12))
        self._max_joint_torque = float(terrain_config.get("max_joint_torque", 1e12))
        self._has_walls = terrain_config.get("has_walls", False)
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
                friction=self._floor_friction,
                restitution=self._floor_restitution,
                userData="floor"
            ),
        )
        self._terrain_bodies["floor"] = floor

        if self._has_walls:
            # Add left and right walls to contain the bouncing chaos
            wall_width = 0.5
            wall_height = 20.0
            left_wall = self._world.CreateStaticBody(
                position=(-wall_width / 2, wall_height / 2),
                fixtures=Box2D.b2FixtureDef(
                    shape=polygonShape(box=(wall_width / 2, wall_height / 2)),
                    friction=0.0,
                    restitution=1.0,
                    userData="wall"
                ),
            )
            right_wall = self._world.CreateStaticBody(
                position=(floor_length + wall_width / 2, wall_height / 2),
                fixtures=Box2D.b2FixtureDef(
                    shape=polygonShape(box=(wall_width / 2, wall_height / 2)),
                    friction=0.0,
                    restitution=1.0,
                    userData="wall"
                ),
            )
            self._terrain_bodies["left_wall"] = left_wall
            self._terrain_bodies["right_wall"] = right_wall

    def _create_core(self, terrain_config: dict):
        core = self._world.CreateDynamicBody(
            position=(self.CORE_X, self.CORE_Y),
            fixtures=Box2D.b2FixtureDef(
                shape=circleShape(radius=self.CORE_RADIUS),
                density=1.0,
                friction=0.5,
                userData="core"
            ),
            allowSleep=False,
        )
        self._terrain_bodies["core"] = core

    def _spawn_side_meteor(self):
        # Spawn from far left or right at lower height to ensure they hit the sides
        side = self._rng.choice([-1, 1])
        x = self.CORE_X + side * 15.0
        y = self._rng.uniform(1.0, 5.0)
        radius = self._rng.uniform(0.2, 0.4)
        vx = -side * self._rng.uniform(10.0, 20.0)
        vy = self._rng.uniform(0, 5.0)
        
        meteor = self._world.CreateDynamicBody(
            position=(x, y),
            fixtures=Box2D.b2FixtureDef(
                shape=circleShape(radius=radius),
                density=self._meteor_density,
                friction=0.0,
                restitution=self._meteor_restitution,
                userData="meteor"
            ),
            bullet=True
        )
        meteor.linearVelocity = (vx, vy)
        self._meteors.append(meteor)

    def _spawn_meteor(self):
        x = self._rng.uniform(self.BUILD_ZONE_X_MIN - 4, self.BUILD_ZONE_X_MAX + 4)
        y = 15.0
        radius = self._rng.uniform(0.2, 0.5)
        vx = self._rng.uniform(self._meteor_vx_range[0], self._meteor_vx_range[1])
        vy = self._rng.uniform(-15.0, -10.0)
        
        meteor = self._world.CreateDynamicBody(
            position=(x, y),
            fixtures=Box2D.b2FixtureDef(
                shape=circleShape(radius=radius),
                density=self._meteor_density,
                friction=0.5,
                restitution=self._meteor_restitution,
                userData="meteor"
            ),
            bullet=True
        )
        meteor.linearVelocity = (vx, vy)
        self._meteors.append(meteor)

    def add_beam(self, x, y, width, height, angle=0, density=1.0):
        # Build-time constraints check
        if x < self.BUILD_ZONE_X_MIN or x > self.BUILD_ZONE_X_MAX:
            raise ValueError(f"Beam center x={x} is outside build zone x=[{self.BUILD_ZONE_X_MIN}, {self.BUILD_ZONE_X_MAX}]")
        if y < self.BUILD_ZONE_Y_MIN or y > self.BUILD_ZONE_Y_MAX:
            raise ValueError(f"Beam center y={y} is outside build zone y=[{self.BUILD_ZONE_Y_MIN}, {self.BUILD_ZONE_Y_MAX}]")
        if y > self.MAX_STRUCTURE_HEIGHT:
            raise ValueError(f"Beam center y={y} exceeds height limit {self.MAX_STRUCTURE_HEIGHT}m")
        
        dist_to_core = math.sqrt((x - self.CORE_X)**2 + (y - self.CORE_Y)**2)
        if dist_to_core < 1.3 - 1e-6:
            raise ValueError(f"Beam center distance to core {dist_to_core:.2f}m is within 1.3m keep-out zone")

        if width < 0.1 or width > 10.0 or height < 0.1 or height > 10.0:
            raise ValueError(f"Beam dimensions must be in [0.1, 10.0] m; got width={width}, height={height}")

        body = self._world.CreateDynamicBody(position=(x, y), angle=angle)
        fixture = body.CreatePolygonFixture(box=(width/2, height/2), density=density, friction=self._structure_friction)
        fixture.restitution = self._structure_restitution
        fixture.userData = "beam"
        self._bodies.append(body)
        return body

    def add_joint(self, body_a, body_b, anchor, type='rigid'):
        # Anchor point checks: build zone and height
        if anchor[0] < self.BUILD_ZONE_X_MIN or anchor[0] > self.BUILD_ZONE_X_MAX:
            raise ValueError(f"Joint anchor x={anchor[0]} is outside build zone x=[{self.BUILD_ZONE_X_MIN}, {self.BUILD_ZONE_X_MAX}]")
        if anchor[1] < self.BUILD_ZONE_Y_MIN or anchor[1] > self.BUILD_ZONE_Y_MAX:
            raise ValueError(f"Joint anchor y={anchor[1]} is outside build zone y=[{self.BUILD_ZONE_Y_MIN}, {self.BUILD_ZONE_Y_MAX}]")
        if anchor[1] > self.MAX_STRUCTURE_HEIGHT:
            raise ValueError(f"Joint anchor y={anchor[1]} exceeds height limit {self.MAX_STRUCTURE_HEIGHT}m")

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
                
                # Side meteor for more horizontal reach (every 3 standard meteors)
                if self._step_count % (self._meteor_spawn_interval * 3) == 0:
                    self._spawn_side_meteor()
        
        self._step_count += 1

        # Apply wind force to all dynamic bodies (except static ones like the floor)
        if self._wind_force != 0:
            core = self._terrain_bodies.get("core")
            for body in self._world.bodies:
                if body.type == Box2D.b2_dynamicBody and body != core:
                    # Apply horizontal force proportional to mass (simulates acceleration-based wind)
                    body.ApplyForceToCenter((self._wind_force * body.mass, 0), True)

        # Balanced stability for cross-platform Box2D versions
        # 6 sub-steps (1/360s) is generally more stable than 10 for older solvers
        sub_steps = 6
        sub_dt = time_step / sub_steps
        for _ in range(sub_steps):
            self._world.Step(sub_dt, 30, 30)
        
        # Joint damage tracking
        inv_dt = 1.0 / time_step
        broken_joints = []
        for j in list(self._joints):
            try:
                force = j.GetReactionForce(inv_dt).length
                torque = abs(j.GetReactionTorque(inv_dt))
                if force > self._max_joint_force or torque > self._max_joint_torque:
                    broken_joints.append(j)
            except:
                continue
        
        for j in broken_joints:
            self._world.DestroyJoint(j)
            self._joints.remove(j)

        # Damage tracking: monitor impacts on core
        core = self._terrain_bodies["core"]
        
        for contact_edge in core.contacts:
            if contact_edge.contact.touching:
                # Approximate force from manifold normal impulse
                manifold = contact_edge.contact.manifold
                if manifold.pointCount > 0:
                    # Only track impacts from meteors or beams
                    # Skip if either fixture is floor or wall
                    f1, f2 = contact_edge.contact.fixtureA, contact_edge.contact.fixtureB
                    if f1.userData in ["floor", "wall"] or f2.userData in ["floor", "wall"]:
                        continue
                    
                    # Also ensure the other object is actually a meteor or beam
                    other_fixture = f2 if f1.userData == "core" else f1
                    if other_fixture.userData not in ["meteor", "beam"]:
                        continue

                    impulse = manifold.points[0].normalImpulse
                    force = impulse / time_step
                    self._max_force_on_core = max(self._max_force_on_core, force)

    def get_core_max_force(self):
        return self._max_force_on_core

    def reset_max_core_force(self):
        self._max_force_on_core = 0.0

    def get_terrain_bounds(self):
        return {
            "core": {"x": self.CORE_X, "y": self.CORE_Y, "radius": self.CORE_RADIUS},
            "build_zone": {"x": [self.BUILD_ZONE_X_MIN, self.BUILD_ZONE_X_MAX], "y": [self.BUILD_ZONE_Y_MIN, self.BUILD_ZONE_Y_MAX]},
            "core_max_force": self.CORE_MAX_FORCE,
            "max_structure_mass": self.MAX_STRUCTURE_MASS,
            "max_structure_height": self.MAX_STRUCTURE_HEIGHT,
            "meteor_count": self._meteor_count,
            "meteor_spawn_interval": self._meteor_spawn_interval,
        }
