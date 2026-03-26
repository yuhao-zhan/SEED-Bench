"""
F-03: The Excavator — environment module.
Per user spec: Pit x=[0,5], 200 sand particles (high friction); Hopper at x=-5, y=3;
Base fixed at x=-2, y=0; mechanism must have at least 2 DOF (Arm + Bucket).
"""
import Box2D
from Box2D.b2 import (world, polygonShape, circleShape, staticBody, dynamicBody, weldJoint)
import math
import random


class Sandbox:
    """Sandbox environment for F-03: The Excavator (pit → hopper, base at -2, 2 DOF)."""

    def __init__(self, *, terrain_config=None, physics_config=None):
        terrain_config = terrain_config or {}
        physics_config = physics_config or {}
        self._terrain_config = dict(terrain_config)
        self._physics_config = dict(physics_config)

        gravity = tuple(physics_config.get("gravity", (0, -10)))
        self._default_linear_damping = float(physics_config.get("linear_damping", 0.02))
        self._default_angular_damping = float(physics_config.get("angular_damping", 0.02))
        # Joint breaking: when set, joints are destroyed if reaction force/torque exceeds limit (default: no break)
        self._joint_max_force = float(physics_config.get("joint_max_force", float("inf")))
        self._joint_max_torque = float(physics_config.get("joint_max_torque", float("inf")))
        self._max_motor_torque = float(physics_config.get("max_motor_torque", 100.0))

        self._world = world(gravity=gravity, doSleep=True)
        self._bodies = []
        self._joints = []
        self._revolute_joints = []  # for 2-DOF check (Arm + Bucket)
        self._terrain_bodies = {}
        self._particles = []
        self._scoop_bodies = []  # bodies that carry particles when level (scoop mechanic)
        self._prev_scoop_state = {}  # body -> (position vec, angle) for carry logic

        self.world = self._world
        self.bodies = self._bodies
        self.joints = self._joints

        # Per user spec: Pit x=[0,5], Hopper at (-5, 3), Base at (-2, 0)
        self.PIT_X_MIN = 0.0
        self.PIT_X_MAX = 5.0
        self.PIT_Y_MIN = 0.0
        self.PIT_Y_MAX = 2.5
        self.HOPPER_X_MIN = -6.0
        self.HOPPER_X_MAX = -4.0
        self.HOPPER_Y_MIN = 0.5
        self.HOPPER_Y_MAX = 5.0
        self.HOPPER_CENTER_X = -5.0
        self.HOPPER_CENTER_Y = 3.0
        self.BASE_X = -2.0
        self.BASE_Y = 0.0
        self.BUILD_ZONE_X_MIN = float(terrain_config.get("build_zone_x_min", -4.0))
        self.BUILD_ZONE_X_MAX = float(terrain_config.get("build_zone_x_max", 2.0))
        self.BUILD_ZONE_Y_MIN = float(terrain_config.get("build_zone_y_min", 0.0))
        self.BUILD_ZONE_Y_MAX = float(terrain_config.get("build_zone_y_max", 5.0))
        self.MAX_STRUCTURE_MASS = float(terrain_config.get("max_structure_mass", 800.0))
        self.MIN_PARTICLES_IN_HOPPER = int(terrain_config.get("min_particles_in_hopper", 15))
        self.MAX_TIME_SECONDS = float(terrain_config.get("max_time_seconds", 40.0))
        # Pit drift: particles in pit get constant horizontal force (simulate slope/conveyor)
        self.PIT_DRIFT_FORCE = float(terrain_config.get("pit_drift_force", 0.0))
        # Valid hopper zone: default full hopper; can tighten via config for dump-accuracy difficulty
        self.HOPPER_VALID_X_MIN = float(terrain_config.get("hopper_valid_x_min", self.HOPPER_X_MIN))
        self.HOPPER_VALID_X_MAX = float(terrain_config.get("hopper_valid_x_max", self.HOPPER_X_MAX))
        self.HOPPER_VALID_Y_MIN = float(terrain_config.get("hopper_valid_y_min", self.HOPPER_Y_MIN))
        self.HOPPER_VALID_Y_MAX = float(terrain_config.get("hopper_valid_y_max", self.HOPPER_Y_MAX))
        # Scoop capacity and mechanics
        self.SCOOP_CAPACITY = int(terrain_config.get("scoop_capacity", 999))
        self.DUMP_ANGLE_THRESHOLD = float(terrain_config.get("dump_angle_threshold", 0.6))
        self.CARRY_MARGIN = float(terrain_config.get("carry_margin", 2.0))

        self.agent_arm_joint = None  # Set by agent in build_agent for agent_action
        self.agent_bucket_joint = None

        self._create_terrain(terrain_config)
        self._create_particles(terrain_config)

    def has_central_wall(self):
        """Return True if central wall obstacle is present (arm must lift to clear)."""
        return self._terrain_bodies.get("central_wall") is not None

    def _create_terrain(self, terrain_config: dict):
        """Create floor, central wall obstacle, and hopper zone (sensor for drawing)."""
        floor_length = 20.0
        floor_height = 0.3
        floor_center_x = 0.0
        floor = self._world.CreateStaticBody(
            position=(floor_center_x, -floor_height / 2),
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(floor_length / 2, floor_height / 2)),
                friction=0.5,
            ),
        )
        self._terrain_bodies["floor"] = floor

        # Central wall: enabled by default to match prompt; arm must lift to clear
        if terrain_config.get("central_wall", True):
            wall_x = -1.0
            wall_bottom = 0.5
            wall_top = 1.5
            wall_height = wall_top - wall_bottom
            wall_half_w = 0.12
            central_wall = self._world.CreateStaticBody(
                position=(wall_x, (wall_bottom + wall_top) / 2),
                fixtures=Box2D.b2FixtureDef(
                    shape=polygonShape(box=(wall_half_w, wall_height / 2)),
                    friction=0.6,
                    restitution=0.05,
                ),
            )
            self._terrain_bodies["central_wall"] = central_wall

        hopper_w = 2.0
        hopper_h = 4.5  # From y=0.5 to y=5.0
        hopper_body = self._world.CreateStaticBody(
            position=(self.HOPPER_CENTER_X, self.HOPPER_CENTER_Y),
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(hopper_w / 2, hopper_h / 2)),
                friction=0.4,
                isSensor=True,
            ),
        )
        self._terrain_bodies["hopper"] = hopper_body

    def _create_particles(self, terrain_config: dict):
        """Create 200 sand particles in the pit (high friction)."""
        pit_config = terrain_config.get("particles", {})
        num_particles = int(pit_config.get("count", 200))
        particle_radius = float(pit_config.get("radius", 0.06))
        density = float(pit_config.get("density", 1500.0))
        friction = float(pit_config.get("friction", 0.7))
        seed = int(pit_config.get("seed", 42))
        random.seed(seed)

        for _ in range(num_particles):
            x = random.uniform(self.PIT_X_MIN + particle_radius, self.PIT_X_MAX - particle_radius)
            y = random.uniform(self.PIT_Y_MIN + particle_radius, self.PIT_Y_MAX - particle_radius)
            p = self._world.CreateDynamicBody(
                position=(x, y),
                fixtures=Box2D.b2FixtureDef(
                    shape=circleShape(radius=particle_radius),
                    density=density,
                    friction=friction,
                    restitution=0.05,
                ),
            )
            p.linearDamping = self._default_linear_damping
            p.angularDamping = self._default_angular_damping
            self._particles.append(p)

        self._initial_particle_count = len(self._particles)

    MIN_BEAM_SIZE = 0.1
    MAX_BEAM_SIZE = 1.5

    def add_beam(self, x, y, width, height, angle=0, density=300.0):
        """API: Add a beam (arm, bucket, etc.)."""
        width = max(self.MIN_BEAM_SIZE, min(width, self.MAX_BEAM_SIZE))
        height = max(self.MIN_BEAM_SIZE, min(height, self.MAX_BEAM_SIZE))
        body = self._world.CreateDynamicBody(
            position=(x, y),
            angle=angle,
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(width / 2, height / 2)),
                density=density,
                friction=0.5,
            ),
        )
        body.linearDamping = self._default_linear_damping
        body.angularDamping = self._default_angular_damping
        self._bodies.append(body)
        return body

    def add_anchored_base(self, x, y, width, height, angle=0, density=400.0):
        """API: Add base anchored to the floor. Per spec: base at x=-2, y=0."""
        beam = self.add_beam(x, y, width, height, angle=angle, density=density)
        self.add_joint(beam, None, (x, 0.0))
        return beam

    def add_bucket(self, x, y, width, height, angle=0, density=280.0):
        """API: Add a bucket (scoop); not anchored — control in agent_action."""
        beam = self.add_beam(x, y, width, height, angle=angle, density=density)
        self.set_material_properties(beam, restitution=0.05)
        return beam

    def register_scoop_body(self, body):
        """Register a body as a scoop: particles inside its AABB (when scoop is level) are carried with it."""
        if body is not None and body not in self._scoop_bodies:
            self._scoop_bodies.append(body)

    def add_scoop(self, x, y, width, height, angle=0, density=280.0):
        """API: Add an L-shaped scoop (back + floor) so it can hold and carry particles. Returns the scoop body.
        L opens toward -x (floor to the left); hinge corner at body position (x,y)."""
        width = max(self.MIN_BEAM_SIZE, min(width, self.MAX_BEAM_SIZE))
        height = max(self.MIN_BEAM_SIZE, min(height, self.MAX_BEAM_SIZE))
        w, h = width, height
        thickness = 0.15
        body = self._world.CreateDynamicBody(
            position=(x, y),
            angle=angle,
        )
        # Back wall: vertical centered on hinge (0,0)
        back_verts = [(-thickness / 2, -h / 2), (thickness / 2, -h / 2), (thickness / 2, h / 2), (-thickness / 2, h / 2)]
        body.CreateFixture(
            shape=Box2D.b2PolygonShape(vertices=back_verts),
            density=density,
            friction=0.6,
            restitution=0.05,
        )
        # Floor: horizontal from bottom of back wall (-h/2) toward -x
        floor_verts = [(-w, -h / 2 - thickness / 2), (0, -h / 2 - thickness / 2), (0, -h / 2 + thickness / 2), (-w, -h / 2 + thickness / 2)]
        body.CreateFixture(
            shape=Box2D.b2PolygonShape(vertices=floor_verts),
            density=density,
            friction=0.7,
            restitution=0.05,
        )
        body.linearDamping = self._default_linear_damping
        body.angularDamping = self._default_angular_damping
        self._bodies.append(body)
        self._scoop_bodies.append(body)
        return body

    def add_joint(self, body_a, body_b, anchor_point, type='rigid'):
        """API: Add weld joint. body_b=None anchors to the floor."""
        if body_a is None:
            raise ValueError("add_joint: body_a cannot be None.")
        anchor_x, anchor_y = anchor_point[0], anchor_point[1]
        if body_b is None:
            body_b = self._terrain_bodies.get("floor")
            if body_b is None:
                raise ValueError("add_joint: floor not found.")
        joint = self._world.CreateWeldJoint(
            bodyA=body_a,
            bodyB=body_b,
            anchor=(anchor_x, anchor_y),
            collideConnected=False
        )
        self._joints.append(joint)
        return joint

    def add_revolute_joint(self, body_a, body_b, anchor_point, enable_motor=False, motor_speed=0.0, max_motor_torque=None):
        """API: Add revolute joint (for Arm or Bucket — 2 DOF). Returns joint so you can set motor in agent_action."""
        if body_a is None or body_b is None:
            raise ValueError("add_revolute_joint: body_a and body_b cannot be None.")
        
        limit = getattr(self, "_max_motor_torque", 100.0)
        if max_motor_torque is None:
            max_motor_torque = limit
        else:
            max_motor_torque = min(float(max_motor_torque), limit)

        anchor_x, anchor_y = anchor_point[0], anchor_point[1]
        anchor_world = Box2D.b2Vec2(anchor_x, anchor_y)
        jd = Box2D.b2RevoluteJointDef()
        jd.Initialize(body_a, body_b, anchor_world)
        jd.collideConnected = False
        jd.enableMotor = bool(enable_motor)
        jd.motorSpeed = float(motor_speed)
        jd.maxMotorTorque = float(max_motor_torque)
        joint = self._world.CreateJoint(jd)
        self._joints.append(joint)
        self._revolute_joints.append(joint)
        return joint

    def get_structure_mass(self):
        """API: Total mass of excavator structure."""
        return sum(b.mass for b in self._bodies)

    def set_material_properties(self, body, restitution=0.1):
        """API: Set restitution for a body."""
        for fixture in body.fixtures:
            fixture.restitution = float(restitution)

    def step(self, time_step):
        """Physics step: pit drift, carry particles with scoops (before step), step, then clamp hopper."""
        # Pit drift: particles in pit get constant force toward +x (simulate slope/conveyor)
        drift = getattr(self, "PIT_DRIFT_FORCE", 0.0)
        if drift > 0:
            for p in self._particles:
                if p is None or not p.active:
                    continue
                px, py = p.position.x, p.position.y
                if self.PIT_X_MIN <= px <= self.PIT_X_MAX and self.PIT_Y_MIN <= py <= self.PIT_Y_MAX:
                    p.ApplyForce((drift, 0), p.position, wake=True)

        dump_angle_limit = getattr(self, "DUMP_ANGLE_THRESHOLD", 0.6)
        carry_margin = getattr(self, "CARRY_MARGIN", 2.0)
        scoop_cap = getattr(self, "SCOOP_CAPACITY", 999)
        for body in self._scoop_bodies:
            if not body.active:
                continue
            bx, by = body.position.x, body.position.y
            ba = body.angle
            prev = self._prev_scoop_state.get(id(body))
            if prev is None:
                self._prev_scoop_state[id(body)] = (bx, by)
                prev = (bx, by)
            w, h = 0.6, 0.35
            try:
                for fixt in body.fixtures:
                    if hasattr(fixt.shape, 'vertices') and fixt.shape.vertices:
                        vs = list(fixt.shape.vertices)
                        if vs:
                            xs = [v[0] for v in vs]
                            ys = [v[1] for v in vs]
                            w = max(w, max(xs) - min(xs) + 0.2)
                            h = max(h, max(ys) - min(ys) + 0.2)
            except Exception:
                pass
            dx = w / 2 + carry_margin
            dy = h / 2 + carry_margin
            over_hopper = (self.HOPPER_X_MIN <= bx <= self.HOPPER_X_MAX and by >= self.HOPPER_Y_MIN)
            dumping = ba > dump_angle_limit and over_hopper
            carried = 0
            for p in self._particles:
                if p is None or not p.active:
                    continue
                if carried >= scoop_cap:
                    break
                px, py = p.position.x, p.position.y
                in_aabb = abs(px - bx) <= dx and abs(py - by) <= dy
                if in_aabb and not dumping:
                    p.linearVelocity = body.linearVelocity
                    p.angularVelocity = body.angularVelocity
                    if prev is not None:
                        p.position = (px + (bx - prev[0]), py + (by - prev[1]))
                    carried += 1
        self._world.Step(time_step, 10, 10)
        for body in self._scoop_bodies:
            if body.active:
                self._prev_scoop_state[id(body)] = (body.position.x, body.position.y)
        # Joint breaking: destroy joints that exceed reaction force/torque limits (when limits are set)
        if self._joint_max_force < float("inf") or self._joint_max_torque < float("inf"):
            inv_dt = 1.0 / time_step if time_step > 0 else 0.0
            to_destroy = []
            for j in list(self._joints):
                try:
                    force = j.GetReactionForce(inv_dt).length
                    torque = abs(j.GetReactionTorque(inv_dt))
                    if force > self._joint_max_force or torque > self._joint_max_torque:
                        to_destroy.append(j)
                except Exception:
                    continue
            for j in to_destroy:
                if j in self._joints:
                    self._world.DestroyJoint(j)
                    self._joints.remove(j)
                    if j in self._revolute_joints:
                        self._revolute_joints.remove(j)
        # Clamp particles that entered hopper zone (retain in hopper)
        margin = 1.0
        x_lo = self.HOPPER_X_MIN - margin
        x_hi = self.HOPPER_X_MAX + margin
        y_lo = self.HOPPER_Y_MIN
        y_hi = self.HOPPER_Y_MAX
        for p in self._particles:
            if p is None or not p.active:
                continue
            x, y = p.position.x, p.position.y
            if x_lo <= x <= x_hi and y_lo <= y <= y_hi:
                cx = max(self.HOPPER_X_MIN, min(self.HOPPER_X_MAX, x))
                cy = max(self.HOPPER_Y_MIN, min(self.HOPPER_Y_MAX, y))
                p.position = (cx, cy)
                p.linearVelocity = (0.0, 0.0)
                p.angularVelocity = 0.0

    def get_terrain_bounds(self):
        """Get terrain bounds for evaluation and rendering."""
        return {
            "pit": {"x_min": self.PIT_X_MIN, "x_max": self.PIT_X_MAX,
                    "y_min": self.PIT_Y_MIN, "y_max": self.PIT_Y_MAX},
            "hopper": {"x_min": self.HOPPER_X_MIN, "x_max": self.HOPPER_X_MAX,
                       "y_min": self.HOPPER_Y_MIN, "y_max": self.HOPPER_Y_MAX},
            "build_zone": {"x": [self.BUILD_ZONE_X_MIN, self.BUILD_ZONE_X_MAX],
                           "y": [self.BUILD_ZONE_Y_MIN, self.BUILD_ZONE_Y_MAX]},
        }

    def get_initial_particle_count(self):
        return self._initial_particle_count

    def get_particles_in_hopper_count(self):
        """Particles whose center is inside the valid hopper zone (stricter center region)."""
        x_min = getattr(self, "HOPPER_VALID_X_MIN", self.HOPPER_X_MIN)
        x_max = getattr(self, "HOPPER_VALID_X_MAX", self.HOPPER_X_MAX)
        y_min = getattr(self, "HOPPER_VALID_Y_MIN", self.HOPPER_Y_MIN)
        y_max = getattr(self, "HOPPER_VALID_Y_MAX", self.HOPPER_Y_MAX)
        count = 0
        for p in self._particles:
            if p is None or not p.active:
                continue
            x, y = p.position.x, p.position.y
            if x_min <= x <= x_max and y_min <= y <= y_max:
                count += 1
        return count

    def get_particles_in_truck_count(self):
        """Alias for evaluator compatibility."""
        return self.get_particles_in_hopper_count()
