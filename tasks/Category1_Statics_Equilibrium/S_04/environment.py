"""
S-04: The Balancer task environment module
"""
import Box2D
from Box2D.b2 import (world, polygonShape, circleShape, staticBody, dynamicBody, revoluteJoint, weldJoint)
import math


class DaVinciSandbox:
    """DaVinci Sandbox environment wrapper for S-04: The Balancer"""
    
    MIN_BEAM_SIZE = 0.1
    MAX_BEAM_SIZE = 10.0
    MAX_BEAM_WIDTH = 7.0
    MAX_BEAM_HEIGHT = 2.0
    PIVOT_POSITION = (0.0, 0.0)
    LOAD_POSITION = (3.0, 0.0)
    LOAD_MASS = 200.0
    MAX_ANGLE_DEVIATION = 10.0 * math.pi / 180.0
    BALANCE_TIME = 15.0
    
    def __init__(self, *, terrain_config=None, physics_config=None):
        terrain_config = terrain_config or {}
        physics_config = physics_config or {}
        self._terrain_config = dict(terrain_config)
        self._physics_config = dict(physics_config)

        gravity = tuple(physics_config.get("gravity", (0, -10)))
        self._default_linear_damping = float(physics_config.get("linear_damping", 0.0))
        self._default_angular_damping = float(physics_config.get("angular_damping", 0.0))
        self._default_friction = float(physics_config.get("friction", 0.5))
        self._default_restitution = float(physics_config.get("restitution", 0.0))

        self._world = world(gravity=gravity, doSleep=True)
        self._bodies = []
        self._joints = []
        self._terrain_bodies = {}
        self._obstacles = []
        
        self.MAX_ANGLE_DEVIATION = terrain_config.get("max_angle_deviation_deg", 10.0) * math.pi / 180.0
        self.BALANCE_TIME = float(terrain_config.get("balance_time", 15.0))
        
        self.world = self._world
        self.bodies = self._bodies
        self.joints = self._joints
        
        self._obstacle_active = terrain_config.get("obstacle_active", False)
        self._drop_load = terrain_config.get("drop_load", False)
        self._wind_active = terrain_config.get("wind_active", False)
        self._wind_force_multiplier = float(terrain_config.get("wind_force_multiplier", 5.0))
        
        self._moving_obstacle = terrain_config.get("moving_obstacle", False)
        self._obstacle_amplitude = terrain_config.get("obstacle_amplitude", 2.0)
        self._obstacle_frequency = terrain_config.get("obstacle_frequency", 0.5)
        self._step_timer = 0.0

        self._fragile_joints = terrain_config.get("fragile_joints", False)
        self._max_joint_torque = float(terrain_config.get("max_joint_torque", 1000.0))

        self._create_terrain(terrain_config)
        self._setup_load(terrain_config)

    def _create_terrain(self, terrain_config: dict):
        pivot_shape = terrain_config.get("pivot_shape", "sharp")
        pivot_friction = float(terrain_config.get("pivot_friction", self._default_friction * 1.6))
        
        if pivot_shape == "rounded":
            pivot = self._world.CreateStaticBody(
                position=(0, 0),
                fixtures=Box2D.b2FixtureDef(shape=circleShape(radius=0.05), friction=pivot_friction),
            )
        else:
            pivot = self._world.CreateStaticBody(
                position=(0, 0),
                fixtures=Box2D.b2FixtureDef(shape=polygonShape(vertices=[(0, 0.05), (-0.05, 0), (0.05, 0)]), friction=pivot_friction),
            )
        self._terrain_bodies["pivot"] = pivot        
        
        if self._obstacle_active:
            if "obstacles" in terrain_config:
                rects = terrain_config["obstacles"]
            else:
                rects = [terrain_config.get("obstacle_rect", [-2.5, -0.1, -1.5, 1.5])]
                
            for i, rect in enumerate(rects):
                xmin, ymin, xmax, ymax = rect
                cx, cy = (xmin + xmax) / 2.0, (ymin + ymax) / 2.0
                hw, hh = (xmax - xmin) / 2.0, (ymax - ymin) / 2.0
                if self._moving_obstacle:
                    obs = self._world.CreateKinematicBody(
                        position=(cx, cy),
                        fixtures=Box2D.b2FixtureDef(shape=polygonShape(box=(hw, hh)), friction=0.5),
                    )
                else:
                    obs = self._world.CreateStaticBody(
                        position=(cx, cy),
                        fixtures=Box2D.b2FixtureDef(shape=polygonShape(box=(hw, hh)), friction=0.5),
                    )
                self._terrain_bodies[f"obstacle_{i}"] = obs
                self._obstacles.append(obs)

    def _setup_load(self, terrain_config: dict):
        self._load_mass = float(terrain_config.get("load_mass", 200.0))
        self._load_position = (3.0, 0.0)
        self._load_body = None
        self._load_attached = False
        self._initial_disturbance_applied = False
        self._initial_disturbance = terrain_config.get("initial_disturbance", None)

        if self._drop_load:
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
            self._load_attached = True
            self._terrain_bodies["load"] = self._load_body

    def step(self, time_step):
        if not self._initial_disturbance_applied:
            for body in self._bodies:
                body.angularVelocity = 0
                body.linearVelocity = (0, 0)
                body.angle = 0
            if self._load_body and not self._drop_load:
                self._load_body.angularVelocity = 0
                self._load_body.linearVelocity = (0, 0)
                self._load_body.angle = 0
            
            # If there's an explicit disturbance, apply it
            if self._bodies and self._initial_disturbance:
                main_beam = self._bodies[0]
                if "angular_velocity" in self._initial_disturbance:
                    main_beam.angularVelocity = float(self._initial_disturbance["angular_velocity"])
                if "linear_velocity" in self._initial_disturbance:
                    vx = float(self._initial_disturbance["linear_velocity"][0])
                    vy = float(self._initial_disturbance["linear_velocity"][1])
                    main_beam.linearVelocity = (vx, vy)
            
            self._initial_disturbance_applied = True
            
        # Auto-attach load
        if not self._load_attached and not self._drop_load and self._bodies:
            for body in self._bodies:
                dist = math.sqrt((body.position.x - 3.0)**2 + (body.position.y - 0.0)**2)
                if dist < 0.5:
                    self._load_body = self._world.CreateDynamicBody(
                        position=(3.0, 0.5),
                        fixtures=Box2D.b2FixtureDef(
                            shape=polygonShape(box=(0.5, 0.5)),
                            density=self._load_mass / (1.0 * 1.0),
                        )
                    )
                    self._world.CreateWeldJoint(
                        bodyA=body,
                        bodyB=self._load_body,
                        anchor=(3.0, 0.0),
                        collideConnected=False
                    )
                    self._load_attached = True
                    self._terrain_bodies["load"] = self._load_body
                    break
                    
        if self._wind_active:
            for body in self._bodies:
                body.ApplyForceToCenter((body.mass * self._wind_force_multiplier, 0), wake=True)
            if self._load_body:
                self._load_body.ApplyForceToCenter((self._load_body.mass * self._wind_force_multiplier, 0), wake=True)
        
        # Fragile Joints Static Equilibrium Check
        if self._fragile_joints:
            net_torque = 0.0
            gx, gy = self._world.gravity
            wind_f = self._wind_force_multiplier if self._wind_active else 0.0
            
            for b in self._bodies:
                rx, ry = b.position.x, b.position.y
                Fx = b.mass * wind_f + b.mass * gx
                Fy = b.mass * gy
                net_torque += (rx * Fy - ry * Fx)
                
            if self._load_attached and self._load_body:
                b = self._load_body
                rx, ry = b.position.x, b.position.y
                Fx = b.mass * wind_f + b.mass * gx
                Fy = b.mass * gy
                net_torque += (rx * Fy - ry * Fx)
                
            if abs(net_torque) > self._max_joint_torque:
                # print(f"Torque exceeded: {net_torque} > {self._max_joint_torque}")
                pivot = self._terrain_bodies.get("pivot")
                for j in list(self._joints):
                    # Only destroy WeldJoints (rigid). RevoluteJoints (pivot) are the task foundation.
                    if isinstance(j, Box2D.b2WeldJoint) and (j.bodyA == pivot or j.bodyB == pivot):
                        try:
                            self._world.DestroyJoint(j)
                            self._joints.remove(j)
                        except:
                            pass

        self._world.Step(time_step, 60, 60) # High iterations for stability
        self._step_timer += time_step

        if self._moving_obstacle and self._obstacles:
            obstacle = self._obstacles[0]
            xmin, ymin, xmax, ymax = self._terrain_config.get("obstacle_rect", [0,0,1,1])
            cx_init, cy_init = (xmin + xmax) / 2.0, (ymin + ymax) / 2.0
            new_cx = cx_init + self._obstacle_amplitude * math.sin(2 * math.pi * self._obstacle_frequency * self._step_timer)
            obstacle.position = (new_cx, cy_init)

    def add_beam(self, x, y, width, height, angle=0, density=1.0, friction=None):
        width = max(self.MIN_BEAM_SIZE, min(width, self.MAX_BEAM_WIDTH))
        height = max(self.MIN_BEAM_SIZE, min(height, self.MAX_BEAM_HEIGHT))
        if friction is None: friction = self._default_friction

        body = self._world.CreateDynamicBody(
            position=(x, y), angle=angle,
            fixtures=Box2D.b2FixtureDef(shape=polygonShape(box=(width/2, height/2)), density=density, friction=friction, restitution=self._default_restitution)
        )
        body.linearDamping = self._default_linear_damping
        body.angularDamping = self._default_angular_damping
        self._bodies.append(body)
        return body

    def add_joint(self, body_a, body_b, anchor_point, type='rigid'):
        anchor_x, anchor_y = anchor_point[0], anchor_point[1]
        pivot = self._terrain_bodies.get("pivot")
        if pivot and (body_a == pivot or body_b == pivot):
            other = body_b if body_a == pivot else body_a
            if self._terrain_config.get("force_pivot_joint", False) or type == 'pivot':
                joint = self._world.CreateRevoluteJoint(bodyA=other, bodyB=pivot, anchor=(0, 0), collideConnected=False)
            else:
                joint = self._world.CreateWeldJoint(bodyA=other, bodyB=pivot, anchor=(0, 0), collideConnected=False)
        elif type == 'rigid':
            joint = self._world.CreateWeldJoint(bodyA=body_a, bodyB=body_b, anchor=(anchor_x, anchor_y), collideConnected=False)
        elif type == 'pivot':
            joint = self._world.CreateRevoluteJoint(bodyA=body_a, bodyB=body_b, anchor=(anchor_x, anchor_y), collideConnected=False)
        else:
            raise ValueError(f"Unknown joint type: {type}")
        
        self._joints.append(joint)
        return joint

    def get_structure_mass(self):
        return sum(b.mass for b in self._bodies)

    def get_main_beam_angle(self):
        return self._bodies[0].angle if self._bodies else 0.0

    def get_terrain_bounds(self):
        return {
            "pivot": self.PIVOT_POSITION,
            "load_position": self.LOAD_POSITION,
            "max_angle_deviation": self.MAX_ANGLE_DEVIATION * 180 / math.pi,
            "max_beam_width": self.MAX_BEAM_WIDTH,
            "max_beam_height": self.MAX_BEAM_HEIGHT,
        }
