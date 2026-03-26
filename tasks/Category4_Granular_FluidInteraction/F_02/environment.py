
import math
import numpy as np
import pymunk
from pymunk.vec2d import Vec2d
from tasks.primitives_api import get_environment_class

# Constants
GROUND_FRICTION = 1.0
GROUND_ELASTICITY = 0.6
OBJECT_FRICTION = 1.0
OBJECT_ELASTICITY = 0.6

# --- Start of Forensic Tracking Properties ---
PEAK_STRESS_TORQUE = "peak_stress_torque"
JOINT_BREAK_STEP = "joint_break_step"
JOINT_BREAK_LOCATION = "joint_break_location"
BROKEN_JOINT_COUNT = "broken_joint_count"
MAX_HORIZONTAL_DISPLACEMENT = "max_horizontal_displacement"
# --- End of Forensic Tracking Properties ---

def get_primitives_library():
    return {
        "create_box": create_box, "create_poly": create_poly, "create_segment": create_segment,
        "create_circle": create_circle, "create_pivot_joint": create_pivot_joint, "create_motor": create_motor,
    }

def create_box(space, body_type, position, size, mass, friction, elasticity, angle=0, color="blue"):
    if body_type == "dynamic": body = pymunk.Body(mass, pymunk.moment_for_box(mass, size))
    elif body_type == "static": body = pymunk.Body(body_type=pymunk.Body.STATIC)
    else: raise ValueError(f"Invalid body type: {body_type}")
    body.position, body.angle = position, angle
    shape = pymunk.Poly.create_box(body, size)
    shape.friction, shape.elasticity, shape.color = friction, elasticity, color
    space.add(body, shape)
    return body

def create_poly(space, body_type, position, vertices, mass, friction, elasticity, angle=0, color="blue"):
    if body_type == "dynamic": body = pymunk.Body(mass, pymunk.moment_for_poly(mass, vertices))
    elif body_type == "static": body = pymunk.Body(body_type=pymunk.Body.STATIC)
    else: raise ValueError(f"Invalid body type: {body_type}")
    body.position, body.angle = position, angle
    shape = pymunk.Poly(body, vertices)
    shape.friction, shape.elasticity, shape.color = friction, elasticity, color
    space.add(body, shape)
    return body

def create_segment(space, body_type, a, b, radius, mass, friction, elasticity, color="blue"):
    if body_type == "dynamic": body = pymunk.Body(mass, pymunk.moment_for_segment(mass, a, b, radius))
    elif body_type == "static": body = pymunk.Body(body_type=pymunk.Body.STATIC)
    else: raise ValueError(f"Invalid body type: {body_type}")
    shape = pymunk.Segment(body, a, b, radius)
    shape.friction, shape.elasticity, shape.color = friction, elasticity, color
    space.add(body, shape)
    return body

def create_circle(space, body_type, position, radius, mass, friction, elasticity, angle=0, color="blue"):
    if body_type == "dynamic": body = pymunk.Body(mass, pymunk.moment_for_circle(mass, 0, radius))
    elif body_type == "static": body = pymunk.Body(body_type=pymunk.Body.STATIC)
    else: raise ValueError(f"Invalid body type: {body_type}")
    body.position, body.angle = position, angle
    shape = pymunk.Circle(body, radius)
    shape.friction, shape.elasticity, shape.color = friction, elasticity, color
    space.add(body, shape)
    return body

def create_pivot_joint(space, a, b, anchor_a=(0, 0), anchor_b=(0, 0), max_force=float("inf"), collide_bodies=True):
    joint = pymunk.PivotJoint(a, b, anchor_a, anchor_b)
    joint.max_force, joint.collide_bodies = max_force, collide_bodies
    space.add(joint)
    return joint

def create_motor(space, a, b, rate, max_force=float("inf")):
    motor = pymunk.SimpleMotor(a, b, rate)
    motor.max_force = max_force
    space.add(motor)
    return motor

class BaseEnvironment:
    def __init__(self, width=600, height=600, gravity=(0, -981), liquid_level=0, liquid_density=0.001, liquid_damping=0.1, max_simulation_steps=3000, **kwargs):
        self.width, self.height, self.gravity = width, height, gravity
        self.liquid_level, self.liquid_density, self.liquid_damping = liquid_level, liquid_density, liquid_damping
        self.max_simulation_steps = max_simulation_steps
        self.space, self.simulation_step_count = None, 0
        self._bodies, self._joints = [], []
        self.initial_metrics = {}
    def setup(self):
        self.space = pymunk.Space()
        self.space.gravity = self.gravity
        self.simulation_step_count, self._bodies, self._joints = 0, [], []
        self._add_ground()
        if self.liquid_level > 0: self._add_liquid()
        self._create_scene()
    def _add_ground(self):
        ground = pymunk.Segment(self.space.static_body, (-10000, 0), (10000, 0), 5)
        ground.friction, ground.elasticity, ground.color = GROUND_FRICTION, GROUND_ELASTICITY, "gray"
        self.space.add(ground)
    def _add_liquid(self):
        self.space.damping = self.liquid_damping
        liquid_body = pymunk.Body(body_type=pymunk.Body.STATIC)
        liquid_shape = pymunk.Poly(liquid_body, [(-self.width, 0), (self.width, 0), (self.width, self.liquid_level), (-self.width, self.liquid_level)])
        liquid_shape.sensor, liquid_shape.color = True, "lightblue"
        self.space.add(liquid_body, liquid_shape)
        def buoyant_force(body, gravity, damping, dt):
            area, centroid = 0, Vec2d.zero()
            for shape in body.shapes:
                try:
                    area += shape.area
                    centroid += shape.center_of_gravity * shape.area
                except: pass
            if area == 0: return
            centroid /= area
            cog = body.local_to_world(centroid)
            submerged_area = area * min(1, (self.liquid_level - cog.y) / (2 * np.sqrt(area / np.pi))) if cog.y < self.liquid_level else 0
            if submerged_area > 0: body.apply_force_at_world_point((0, submerged_area * self.liquid_density * -gravity[1]), cog)
        for body in self.space.bodies:
            if body.body_type == pymunk.Body.DYNAMIC: body.velocity_func = buoyant_force
    def _create_scene(self): raise NotImplementedError
    def step(self, dt=1.0 / 60.0):
        if self.simulation_step_count < self.max_simulation_steps:
            self.space.step(dt); self.simulation_step_count += 1; self._after_step(); return True
        return False
    def _after_step(self): pass
    def get_metrics(self):
        metrics = {"simulation_step_count": self.simulation_step_count}
        metrics.update(self._get_task_specific_metrics()); return metrics
    def _get_task_specific_metrics(self): raise NotImplementedError

class TaskEnvironment(BaseEnvironment):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.metrics_tracker = {
            PEAK_STRESS_TORQUE: 0.0, JOINT_BREAK_STEP: -1, JOINT_BREAK_LOCATION: None,
            BROKEN_JOINT_COUNT: 0, MAX_HORIZONTAL_DISPLACEMENT: 0.0,
        }
        self.initial_com, self.initial_joint_count = None, 0
    def _create_scene(self):
        try:
            bodies, joints = self.create_structure(self.space, width=self.width, height=self.height)
            self._bodies, self._joints = bodies, joints
        except Exception as e:
            print(f"Error creating structure: {e}"); self._bodies, self._joints = [], []
        self.initial_joint_count = len(self._joints)
        total_mass = self.get_structure_mass()
        if total_mass > 0:
            com_x = sum(b.position.x * b.mass for b in self._bodies if b.mass != float('inf')) / total_mass
            com_y = sum(b.position.y * b.mass for b in self._bodies if b.mass != float('inf')) / total_mass
            self.initial_com = Vec2d(com_x, com_y)
        self.initial_metrics = self._get_task_specific_metrics()
    def create_structure(self, space, **kwargs):
        raise NotImplementedError("The 'create_structure' function is not defined by the agent.")
    def _after_step(self):
        super()._after_step()
        live_joints = [j for j in self._joints if j in self.space.constraints]
        if live_joints:
            max_impulse = max((j.impulse for j in live_joints), default=0)
            self.metrics_tracker[PEAK_STRESS_TORQUE] = max(self.metrics_tracker[PEAK_STRESS_TORQUE], max_impulse)
        num_broken = self.initial_joint_count - len(live_joints)
        if num_broken > self.metrics_tracker[BROKEN_JOINT_COUNT]:
            if self.metrics_tracker[JOINT_BREAK_STEP] == -1:
                self.metrics_tracker[JOINT_BREAK_STEP] = self.simulation_step_count
                broken_joint = next((j for j in self._joints if j not in self.space.constraints), None)
                if broken_joint:
                    loc = (broken_joint.a.position + broken_joint.b.position) / 2
                    self.metrics_tracker[JOINT_BREAK_LOCATION] = (loc.x, loc.y)
            self.metrics_tracker[BROKEN_JOINT_COUNT] = num_broken
        if self._bodies and self.initial_com is not None:
            total_mass = self.get_structure_mass()
            if total_mass > 0:
                com_x = sum(b.position.x * b.mass for b in self._bodies if b.mass != float('inf')) / total_mass
                self.metrics_tracker[MAX_HORIZONTAL_DISPLACEMENT] = max(self.metrics_tracker[MAX_HORIZONTAL_DISPLACEMENT], abs(com_x - self.initial_com.x))
    def get_structure_mass(self):
        return sum(b.mass for b in self._bodies if b.mass != float('inf')) if self._bodies else 0
    def get_vehicle_lowest_y(self):
        if not self._bodies: return None
        min_y = float("inf")
        for body in self._bodies:
            for shape in body.shapes:
                if isinstance(shape, pymunk.Poly):
                    min_y = min(min_y, min(v.y for v in [body.local_to_world(v) for v in shape.get_vertices()]))
                elif isinstance(shape, pymunk.Circle):
                    min_y = min(min_y, body.position.y - shape.radius)
        return min_y if min_y != float("inf") else None
    def get_vehicle_front_x(self):
        if not self._bodies: return None
        max_x = float("-inf")
        for body in self._bodies:
            for shape in body.shapes:
                if isinstance(shape, pymunk.Poly):
                    max_x = max(max_x, max(v.x for v in [body.local_to_world(v) for v in shape.get_vertices()]))
                elif isinstance(shape, pymunk.Circle):
                    max_x = max(max_x, body.position.x + shape.radius)
        return max_x if max_x != float("-inf") else None
    def get_vehicle_velocity(self):
        if not self._bodies or (total_mass := self.get_structure_mass()) == 0: return (0, 0)
        vx = sum(b.velocity.x * b.mass for b in self._bodies) / total_mass
        vy = sum(b.velocity.y * b.mass for b in self._bodies) / total_mass
        return (vx, vy)
    def _get_task_specific_metrics(self):
        metrics = {
            "structure_mass": self.get_structure_mass(),
            "max_height_achieved": self.get_vehicle_lowest_y(),
            "structure_integrity": self.initial_joint_count == len([j for j in self._joints if j in self.space.constraints]),
        }
        metrics.update(self.metrics_tracker)
        return metrics

def get_environment():
    return get_environment_class(TaskEnvironment)
