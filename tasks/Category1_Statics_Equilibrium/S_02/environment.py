"""
S-02: The Skyscraper task environment module
"""
import Box2D
from Box2D.b2 import (world, polygonShape, staticBody, dynamicBody, weldJoint)
import math


class S02Sandbox:
    def __init__(self, terrain_config=None, physics_config=None):
        self._terrain_config = terrain_config or {}
        self._physics_config = physics_config or {}
        
        # Physics world
        gravity = self._physics_config.get("gravity", (0, -10.0))
        self._world = world(gravity=gravity, doSleep=True)
        self._bodies = []
        self._joints = []
        self._springs = []
        self._terrain_bodies = {}
        
        self._simulation_time = 0.0
        self._earthquake_amplitude = self._terrain_config.get("earthquake_amplitude", 0.5)
        self._earthquake_frequency = self._terrain_config.get("earthquake_frequency", 2.0)
        self._earthquake_start_time = self._terrain_config.get("earthquake_start_time", 2.0)
        self._earthquake_amplitude_evolution = self._terrain_config.get("earthquake_amplitude_evolution", 0.0)
        
        self._wind_force = self._terrain_config.get("wind_force", 100.0)
        self._wind_height_threshold = self._terrain_config.get("wind_height_threshold", 20.0)
        self._wind_shear_factor = self._terrain_config.get("wind_shear_factor", 0.0)
        self._wind_oscillation_frequency = self._terrain_config.get("wind_oscillation_frequency", 0.0)
        
        self._max_joint_force = self._physics_config.get("max_joint_force", float('inf'))
        self._max_joint_torque = self._physics_config.get("max_joint_torque", float('inf'))
        
        self.TARGET_HEIGHT = 30.0
        
        self._setup_terrain()

    @property
    def world(self):
        return self._world

    def _setup_terrain(self):
        # Static ground
        self._terrain_bodies["ground"] = self._world.CreateStaticBody(
            position=(0, -5), shapes=polygonShape(box=(50, 5)))
        
        # Foundation
        self._terrain_bodies["foundation"] = self._world.CreateKinematicBody(
            position=(0, 0.5), shapes=polygonShape(box=(2.0, 0.5)))

    def add_beam(self, x, y, width, height, angle=0, density=1.0):
        body = self._world.CreateDynamicBody(position=(x, y), angle=angle, linearDamping=0.1, angularDamping=0.1)
        body.CreatePolygonFixture(box=(float(width)/2, float(height)/2), density=density, friction=0.5, restitution=0.1)
        self._bodies.append(body)
        return body

    def add_joint(self, body_a, body_b, anchor, type='rigid'):
        if body_b is None: body_b = self._terrain_bodies["ground"]
        joint_def = Box2D.b2WeldJointDef()
        joint_def.Initialize(body_a, body_b, anchor)
        j = self._world.CreateJoint(joint_def)
        self._joints.append(j)
        return j

    def add_spring(self, body_a, body_b, anchor_a, anchor_b, stiffness, damping):
        joint_def = Box2D.b2DistanceJointDef(bodyA=body_a, bodyB=body_b, anchorA=anchor_a, anchorB=anchor_b,
                                            frequencyHz=stiffness, dampingRatio=damping)
        j = self._world.CreateJoint(joint_def)
        self._springs.append(j)
        return j

    def get_terrain_bounds(self):
        return (-50, 50, 0, 150) # Arena limits (aligned with safety limit)

    def get_vehicle_position(self): return (0.0, 100.0)

    def get_structure_bounds(self):
        if not self._bodies: return {"top": 0, "width": 0, "center_x": 0}
        min_x, max_x, max_y = float('inf'), float('-inf'), float('-inf')
        for b in self._bodies:
            if b.type != Box2D.b2_dynamicBody: continue
            for f in b.fixtures:
                for v in f.shape.vertices:
                    wv = b.GetWorldPoint(v)
                    min_x, max_x, max_y = min(min_x, wv.x), max(max_x, wv.x), max(max_y, wv.y)
        return {"top": max_y, "width": max_x - min_x, "center_x": (min_x + max_x) / 2.0}

    def step(self, time_step):
        self._simulation_time += time_step
        if self._simulation_time >= self._earthquake_start_time:
            f = self._terrain_bodies["foundation"]
            p = self._earthquake_frequency * (self._simulation_time - self._earthquake_start_time)
            
            # Evolving amplitude
            current_amplitude = self._earthquake_amplitude * (1.0 + self._earthquake_amplitude_evolution * (self._simulation_time - self._earthquake_start_time))
            
            tx = current_amplitude * math.sin(p)
            f.position = (tx, 0.5)
            f.linearVelocity = (current_amplitude * self._earthquake_frequency * math.cos(p), 0)
        
        # Wind logic
        wind_mod = 1.0
        if self._wind_oscillation_frequency > 0:
            wind_mod = 0.5 + 0.5 * math.sin(self._wind_oscillation_frequency * self._simulation_time)
            
        for b in self._bodies:
            if b.position.y > self._wind_height_threshold:
                h_factor = 1.0 + self._wind_shear_factor * (b.position.y - self._wind_height_threshold)
                force = self._wind_force * h_factor * wind_mod
                b.ApplyForce((force, 0), b.worldCenter, True)
                
        self._world.Step(time_step, 10, 10)
        
        # Joint breaking check
        if self._max_joint_force < float('inf') or self._max_joint_torque < float('inf'):
            to_destroy = []
            for j in self._joints:
                try:
                    force = j.GetReactionForce(1.0/time_step).length
                    torque = abs(j.GetReactionTorque(1.0/time_step))
                    if force > self._max_joint_force or torque > self._max_joint_torque:
                        to_destroy.append(j)
                except:
                    continue # Joint might have been destroyed already
            
            for j in to_destroy:
                if j in self._joints:
                    self._world.DestroyJoint(j)
                    self._joints.remove(j)
