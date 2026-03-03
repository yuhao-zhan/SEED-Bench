"""
S-03: The Cantilever task environment module
"""
import Box2D
from Box2D.b2 import (world, polygonShape, circleShape, staticBody, dynamicBody, revoluteJoint, weldJoint)
import math


class DaVinciSandbox:
    """DaVinci Sandbox environment wrapper for S-03: The Cantilever"""

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
        
        # Design limits
        self.MIN_BEAM_SIZE = 0.1
        self.MAX_BEAM_WIDTH = 1.2
        self.MAX_BEAM_HEIGHT = 1.5
        self.MAX_BEAM_SIZE = 10.0 
        self.MAX_STRUCTURE_MASS = float(terrain_config.get("max_structure_mass", 1500.0))
        
        # Load setup
        self._load_1_active = False
        self._load_2_active = False
        self._load_attach_time = 5.0
        self._load_2_attach_time = 15.0
        
        self._forbidden_anchor_y = terrain_config.get("forbidden_anchor_y", None)
        self._obstacle_active = terrain_config.get("obstacle_active", False)
        self._obstacle_rect = terrain_config.get("obstacle_rect", [6.0, 0.0, 8.5, 3.5])
        
        self._simulation_time = 0.0
        
        # Consistent Build Zone (aligned with reference solutions)
        self.BUILD_ZONE_X_MIN = 0.0
        self.BUILD_ZONE_X_MAX = 35.0 
        self.BUILD_ZONE_Y_MIN = 0.0
        self.BUILD_ZONE_Y_MAX = 15.0
        
        self._setup_terrain()

    @property
    def world(self):
        return self._world

    def _setup_terrain(self):
        wall = self._world.CreateStaticBody(
            position=(-0.5, 10),
            fixtures=Box2D.b2FixtureDef(shape=polygonShape(box=(0.5, 10.0)), friction=0.8),
        )
        self._terrain_bodies["wall"] = wall
        
        if self._obstacle_active:
            x_min, y_min, x_max, y_max = self._obstacle_rect
            hw, hh = (x_max - x_min) / 2, (y_max - y_min) / 2
            obs = self._world.CreateStaticBody(
                position=(x_min + hw, y_min + hh),
                fixtures=Box2D.b2FixtureDef(shape=polygonShape(box=(hw, hh)), friction=0.5),
            )
            self._terrain_bodies["obstacle"] = obs

    def add_beam(self, x, y, width, height, angle=0, density=1.0):
        width = max(self.MIN_BEAM_SIZE, min(width, self.MAX_BEAM_SIZE))
        height = max(self.MIN_BEAM_SIZE, min(height, self.MAX_BEAM_SIZE))
        body = self._world.CreateDynamicBody(position=(x, y), angle=angle)
        body.CreatePolygonFixture(box=(width/2, height/2), density=density, friction=0.5)
        self._bodies.append(body)
        return body

    def add_joint(self, body_a, body_b, anchor, type='rigid'):
        if body_b is None: body_b = self._terrain_bodies["wall"]
        anchor_x, anchor_y = anchor
        if body_b == self._terrain_bodies["wall"] and self._forbidden_anchor_y:
            y_min, y_max = self._forbidden_anchor_y
            if y_min <= anchor_y <= y_max:
                raise ValueError(f"Anchor y={anchor_y} forbidden")
        if type == 'rigid':
            joint_def = Box2D.b2WeldJointDef()
            joint_def.Initialize(body_a, body_b, anchor)
        else:
            joint_def = Box2D.b2RevoluteJointDef()
            joint_def.Initialize(body_a, body_b, anchor)
        j = self._world.CreateJoint(joint_def)
        self._joints.append(j)
        return j

    def get_max_reach(self):
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
        self._simulation_time += time_step
        if self._simulation_time >= self._load_attach_time and not self._load_1_active:
            self._attach_load(1)
            self._load_1_active = True
        if self._simulation_time >= self._load_2_attach_time and not self._load_2_active:
            self._attach_load(2)
            self._load_2_active = True
        self._world.Step(time_step, 10, 10)
        joints_to_remove = []
        for joint in self._joints:
            try:
                force = joint.GetReactionForce(1.0/60.0)
                torque = abs(joint.GetReactionTorque(1.0/60.0))
                max_f = self._terrain_config.get("max_anchor_force", 2000.0)
                max_t = self._terrain_config.get("max_anchor_torque", 1500.0)
                if math.sqrt(force.x**2 + force.y**2) > max_f or torque > max_t:
                    joints_to_remove.append(joint)
            except Exception: pass
        for j in joints_to_remove:
            self._world.DestroyJoint(j)
            if j in self._joints: self._joints.remove(j)

    def _attach_load(self, load_id):
        if not self._bodies: return
        tip_body = max(self._bodies, key=lambda b: b.position.x)
        mass = float(self._terrain_config.get("load_mass", 1000.0))
        if load_id == 1:
            # First load at tip
            tip_body.ApplyForceToCenter((0, -mass * 10), True)
        else:
            # Second load midway
            mid_body = sorted(self._bodies, key=lambda b: b.position.x)[len(self._bodies)//2]
            mid_body.ApplyForceToCenter((0, -mass * 15), True)

    def get_terrain_bounds(self):
        return {
            "wall": {"x": [-1.0, 0.0]},
            "max_beam_width": self.MAX_BEAM_WIDTH,
            "max_beam_height": self.MAX_BEAM_HEIGHT,
            "obstacle_active": self._obstacle_active,
            "obstacle_rect": self._obstacle_rect if self._obstacle_active else None,
            "forbidden_anchor_y": self._forbidden_anchor_y,
            "build_zone": {"x": [self.BUILD_ZONE_X_MIN, self.BUILD_ZONE_X_MAX], "y": [self.BUILD_ZONE_Y_MIN, self.BUILD_ZONE_Y_MAX]}
        }
