"""
F-01: The Dam task environment module (EXTREME variant)
EXTREME: ZERO floor anchors; right strip at most 2 beams; underflow y>=0.5; max beam width 0.6;
MAX BEAM HEIGHT 1.5 m (no tall single beams); BREAKABLE JOINTS (force > threshold -> joint breaks);
narrow build zones; at most 15 beam-to-beam joints; 18 beams max, 380 kg; stronger surge + upward.
"""
import Box2D
from Box2D.b2 import (world, polygonShape, circleShape, staticBody, dynamicBody, weldJoint)
import math
import random


class Sandbox:
    """Sandbox for F-01: The Dam (extreme variant).

    EXTREME: ZERO floor anchors; RIGHT STRIP AT MOST 2 BEAMS; mandatory underflow y>=0.5;
    MAX BEAM WIDTH 0.6 m; **MAX BEAM HEIGHT 1.5 m** (no tall beams — weak under surge);
    **BREAKABLE JOINTS**: weld joints break if reaction force exceeds threshold (weak chains fail);
    NARROW build zones; at most 15 beam-to-beam joints; nine **STRONGER** surge + upward events;
    at most 18 beams, mass <= 380 kg.
    """

    def __init__(self, *, terrain_config=None, physics_config=None):
        terrain_config = terrain_config or {}
        physics_config = physics_config or {}
        self._terrain_config = dict(terrain_config)
        self._physics_config = dict(physics_config)

        gravity = tuple(physics_config.get("gravity", (0, -10)))
        self._default_linear_damping = float(physics_config.get("linear_damping", 0.1))
        self._default_angular_damping = float(physics_config.get("angular_damping", 0.05))

        self._world = world(gravity=gravity, doSleep=True)
        self._bodies = []
        self._joints = []
        self._terrain_joints = []
        self._terrain_bodies = {}
        self._water_particles = []
        self._debris_bodies = []  # spawned debris (not part of dam); hit dam at 2000, 5000, 8000

        self.world = self._world
        self.bodies = self._bodies
        self.joints = self._joints

        self._create_terrain(terrain_config)

        self.DAM_X_LEFT = 12.0
        self.DAM_X_RIGHT = 14.0
        self.DOWNSTREAM_X_START = 14.0
        self.RESERVOIR_X_MAX = 12.0

        # THREE disjoint build strips — left [12.4,12.6], MIDDLE [12.9,13.1] (bridge), right [13.4,13.6]
        self.BUILD_ZONE_LEFT_X_MIN = float(terrain_config.get("build_zone_left_x_min", 12.4))
        self.BUILD_ZONE_LEFT_X_MAX = float(terrain_config.get("build_zone_left_x_max", 12.6))
        self.BUILD_ZONE_MIDDLE_X_MIN = float(terrain_config.get("build_zone_middle_x_min", 12.9))
        self.BUILD_ZONE_MIDDLE_X_MAX = float(terrain_config.get("build_zone_middle_x_max", 13.1))
        self.BUILD_ZONE_RIGHT_X_MIN = float(terrain_config.get("build_zone_right_x_min", 13.4))
        self.BUILD_ZONE_RIGHT_X_MAX = float(terrain_config.get("build_zone_right_x_max", 13.6))
        self.BUILD_ZONE_Y_MIN = 0.0
        self.BUILD_ZONE_Y_MAX = float(terrain_config.get("build_zone_y_max", 7.5))
        self.BUILD_ZONE_X_MIN = self.BUILD_ZONE_LEFT_X_MIN
        self.BUILD_ZONE_X_MAX = self.BUILD_ZONE_RIGHT_X_MAX

        self.MAX_STRUCTURE_MASS = float(terrain_config.get("max_structure_mass", 380.0))
        self.MAX_BEAM_COUNT = int(terrain_config.get("max_beam_count", 18))
        self.MIN_BEAM_COUNT = int(terrain_config.get("min_beam_count", 10))
        self.MAX_BEAMS_MIDDLE_STRIP = int(terrain_config.get("max_beams_middle_strip", 1))  # at most 1 beam in narrow middle — forces bridge topology
        self.MAX_BEAMS_RIGHT_STRIP = int(terrain_config.get("max_beams_right_strip", 2))
        self.RESERVOIR_FILL_HEIGHT = float(terrain_config.get("fluid_height", 7.0))
        self.MAX_TERRAIN_ANCHORS = 0  # ZERO floor anchors — dam must be free-standing
        self.MIN_BEAM_BOTTOM_Y = float(terrain_config.get("min_beam_bottom_y", 0.5))
        self.MAX_BEAM_WIDTH = float(terrain_config.get("max_beam_width", 0.6))  # narrower beams
        self.MAX_BEAM_HEIGHT = float(terrain_config.get("max_beam_height", 1.5))  # no tall beams — break under surge
        self.MAX_JOINT_COUNT = int(terrain_config.get("max_joint_count", 15))  # at most 15 beam-to-beam welds — forces sparse topology; one cross-joint needed for connectivity
        self.JOINT_BREAK_FORCE = float(terrain_config.get("joint_break_force", 50000.0))  # breakable welds — very high so short-beam reference survives
        self.MIN_BEAMS_PER_BAND = int(terrain_config.get("min_beams_per_band", 3))  # at least 3 beam centers in each vertical band [0.5,2.5], [2.5,5], [5,7.5]
        self.MAX_LEAKAGE_RATE = float(terrain_config.get("max_leakage_rate", 0.001))  # success threshold; mutated tasks may use stricter (e.g. 0.0005)

        self._create_water_particles(terrain_config)
        self._initial_particle_count = len(self._water_particles)
        self._step_count = 0
        self._surge_steps_applied = 0
        self._joint_force_history = {}  # joint -> list of recent force magnitudes for break check
        # Critical-threshold mutation: fewer consecutive over-threshold steps => welds fail faster (not just lower N·threshold)
        self._joint_force_history_len = int(terrain_config.get("joint_break_consecutive_steps", 3))
        self._joint_force_history_len = max(1, min(self._joint_force_history_len, 10))
        # Nine surge waves at 1000, 2000, ..., 9000 — STRONGER impulses (tall/weak structures break)
        default_impulses = [0.7, 0.85, 1.0, 1.15, 1.3, 1.4, 1.5, 1.6, 1.7]
        surge_impulses = terrain_config.get("surge_impulses")
        if surge_impulses is not None:
            self._surge_impulses = list(surge_impulses)
        else:
            self._surge_impulses = default_impulses
        self._surge_steps = [1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000][:len(self._surge_impulses)]
        if len(self._surge_steps) < len(self._surge_impulses):
            self._surge_impulses = self._surge_impulses[:len(self._surge_steps)]
        self._backward_slosh_steps = [1500, 3000, 4500, 6000, 7500, 9000, 10000]
        self._backward_slosh_impulse_x = float(terrain_config.get("backward_slosh_impulse_x", -0.7))
        # Upward surge: stronger — water jumps then slams down (weak joints break)
        self._upward_surge_steps = [2500, 5500, 8500]
        self._upward_surge_impulse_y = float(terrain_config.get("upward_surge_impulse_y", 1.0))
        # Default simulation horizon when the harness does not override max_steps (see main.py).
        self.MAX_STEPS = int(terrain_config.get("max_steps", 10000))

    def _create_terrain(self, terrain_config: dict):
        floor_length = 40.0
        floor_height = 0.3
        floor = self._world.CreateStaticBody(
            position=(floor_length / 2, -floor_height / 2),
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(floor_length / 2, floor_height / 2)),
                friction=0.6,
            ),
        )
        self._terrain_bodies["floor"] = floor

        wall_height = 10.0
        wall_width = 0.5
        left_wall = self._world.CreateStaticBody(
            position=(wall_width / 2, wall_height / 2),
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(wall_width / 2, wall_height / 2)),
                friction=0.5,
            ),
        )
        self._terrain_bodies["left_wall"] = left_wall
        # MOVING downstream wall: kinematic, oscillates x = 13.85 + 0.4*sin(step/100) — dam gets squeezed/relaxed
        self._downstream_wall_y = wall_height / 2
        self._downstream_wall_half_w = 0.25  # spans 0.5 m total
        downstream_wall_x0 = 13.85  # center baseline
        downstream_wall = self._world.CreateDynamicBody(
            position=(downstream_wall_x0, self._downstream_wall_y),
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(self._downstream_wall_half_w, wall_height / 2)),
                density=0.0,
                friction=0.5,
            ),
        )
        try:
            kinematicBody = getattr(Box2D.b2, 'kinematicBody', 1)
            downstream_wall.type = kinematicBody
        except Exception:
            pass
        self._terrain_bodies["downstream_wall"] = downstream_wall
        # Debris spawn config: at steps 2000, 5000, 8000 spawn heavy block toward dam
        self._debris_spawn_steps = [2000, 5000, 8000]
        self._debris_spawned = []
        self._earthquake_steps = [2500, 5000, 7500, 10000]
        self._earthquake_impulse_x = float(terrain_config.get("earthquake_impulse_x", 0.35))  # horizontal shake — dam must resist
        # Downstream wall squeeze amplitude (m); larger => harsher time-varying confinement / leak geometry
        self._downstream_wall_amplitude = float(terrain_config.get("downstream_wall_amplitude", 0.4))
        self._downstream_wall_phase_divisor = float(terrain_config.get("downstream_wall_phase_divisor", 100.0))
        self._downstream_wall_phase_divisor = max(1.0, self._downstream_wall_phase_divisor)
        # Beam–fluid / beam–beam contact friction for dam members (default matches historical 0.5)
        self._structure_friction = terrain_config.get("structure_friction")
        if self._structure_friction is not None:
            self._structure_friction = float(self._structure_friction)
        # Debris spawn velocity (hidden kinetic-energy lever; not a simple mass scale)
        self._debris_linear_velocity_x = float(terrain_config.get("debris_linear_velocity_x", 2.2))
        self._debris_linear_velocity_y = float(terrain_config.get("debris_linear_velocity_y", 0.0))

    def _create_water_particles(self, terrain_config: dict):
        fluid_config = terrain_config.get("fluid", {})
        num_particles = int(fluid_config.get("count", 300))
        particle_radius = float(fluid_config.get("particle_radius", 0.12))
        fluid_density = float(fluid_config.get("density", 1000.0))
        seed = int(fluid_config.get("seed", 42))
        initial_flow_speed = float(fluid_config.get("initial_flow_speed", 0.65))
        # Stage mutations: particle friction / restitution change granular coupling and impact rebound.
        fp_override = terrain_config.get("fluid_particle_friction")
        if fp_override is not None:
            particle_friction = float(fp_override)
        else:
            particle_friction = float(fluid_config.get("particle_friction", 0.1))
        pr_override = terrain_config.get("fluid_particle_restitution")
        if pr_override is not None:
            particle_restitution = float(pr_override)
        else:
            particle_restitution = float(fluid_config.get("particle_restitution", 0.05))
        random.seed(seed)

        reservoir_x_min = 1.0
        reservoir_x_max = 11.0
        reservoir_y_min = particle_radius + 0.1
        reservoir_y_max = self.RESERVOIR_FILL_HEIGHT
        self.RESERVOIR_X_MIN = reservoir_x_min

        for _ in range(num_particles):
            x = random.uniform(reservoir_x_min, reservoir_x_max)
            y = random.uniform(reservoir_y_min, reservoir_y_max)
            mass = fluid_density * (math.pi * particle_radius ** 2)
            density = mass / (math.pi * particle_radius ** 2)
            particle = self._world.CreateDynamicBody(
                position=(x, y),
                fixtures=Box2D.b2FixtureDef(
                    shape=circleShape(radius=particle_radius),
                    density=density,
                    friction=particle_friction,
                    restitution=particle_restitution,
                ),
            )
            particle.linearDamping = self._default_linear_damping
            particle.angularDamping = self._default_angular_damping
            particle.linearVelocity = (initial_flow_speed, 0.0)
            self._water_particles.append(particle)

        self._initial_particle_count = len(self._water_particles)

    MIN_BEAM_SIZE = 0.2
    MAX_BEAM_SIZE = 4.0
    # Class defaults match the extreme F-01 instance defaults (see __init__ max_beam_width/height).
    MAX_BEAM_WIDTH = 0.6
    MAX_BEAM_HEIGHT = 1.5

    def add_beam(self, x, y, width, height, angle=0, density=500.0):
        if len(self._bodies) >= self.MAX_BEAM_COUNT:
            raise ValueError(f"Beam count would exceed maximum {self.MAX_BEAM_COUNT}")
        max_w = getattr(self, 'MAX_BEAM_WIDTH', 0.6)
        max_h = getattr(self, 'MAX_BEAM_HEIGHT', 1.5)
        width = max(self.MIN_BEAM_SIZE, min(width, self.MAX_BEAM_SIZE, max_w))
        height = max(self.MIN_BEAM_SIZE, min(height, self.MAX_BEAM_SIZE, max_h))
        sf = self._structure_friction if self._structure_friction is not None else 0.5
        body = self._world.CreateDynamicBody(
            position=(x, y),
            angle=angle,
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(width / 2, height / 2)),
                density=density,
                friction=float(sf),
            ),
        )
        body.linearDamping = self._default_linear_damping
        body.angularDamping = self._default_angular_damping
        self._bodies.append(body)
        return body

    def add_joint(self, body_a, body_b, anchor_point, type='rigid'):
        if body_a is None:
            raise ValueError("add_joint: body_a cannot be None.")
        anchor_x, anchor_y = anchor_point[0], anchor_point[1]

        floor_body = self._terrain_bodies.get("floor")
        if body_b is None:
            body_b = floor_body
        if body_b is None:
            raise ValueError("add_joint: terrain body not found for anchor.")
        if body_b == floor_body:
            if len(self._terrain_joints) >= self.MAX_TERRAIN_ANCHORS:
                raise ValueError(f"Terrain anchor count would exceed maximum {self.MAX_TERRAIN_ANCHORS}")

        # Enforce max beam-to-beam joint count (no limit on terrain joints when 0)
        if body_b != floor_body:
            beam_joints = len(self._joints) - len(self._terrain_joints)
            max_joints = getattr(self, 'MAX_JOINT_COUNT', 15)
            if beam_joints >= max_joints:
                raise ValueError(f"Beam-to-beam joint count would exceed maximum {max_joints}")

        if type != 'rigid':
            type = 'rigid'
        joint = self._world.CreateWeldJoint(
            bodyA=body_a,
            bodyB=body_b,
            anchor=(anchor_x, anchor_y),
            collideConnected=False
        )
        self._joints.append(joint)
        if body_b == floor_body:
            self._terrain_joints.append(joint)
        return joint

    def get_terrain_joint_count(self):
        return len(self._terrain_joints)

    def get_structure_mass(self):
        total_mass = 0.0
        for body in self._bodies:
            total_mass += body.mass
        return total_mass

    def set_material_properties(self, body, restitution=0.1):
        for fixture in body.fixtures:
            fixture.restitution = float(restitution)

    def set_damping(self, body, linear=None, angular=None):
        """Adjusts linear and angular damping for a specific body."""
        if linear is not None:
            body.linearDamping = float(linear)
        if angular is not None:
            body.angularDamping = float(angular)

    def apply_force(self, body, force_vector):
        """Applies a linear force to the center of the body."""
        body.ApplyForce(force_vector, body.worldCenter, True)

    def _in_build_zone(self, x, y):
        in_left = self.BUILD_ZONE_LEFT_X_MIN <= x <= self.BUILD_ZONE_LEFT_X_MAX
        in_middle = getattr(self, 'BUILD_ZONE_MIDDLE_X_MIN', 12.9) <= x <= getattr(self, 'BUILD_ZONE_MIDDLE_X_MAX', 13.1)
        in_right = self.BUILD_ZONE_RIGHT_X_MIN <= x <= self.BUILD_ZONE_RIGHT_X_MAX
        in_y = self.BUILD_ZONE_Y_MIN <= y <= self.BUILD_ZONE_Y_MAX
        return (in_left or in_middle or in_right) and in_y

    def step(self, time_step):
        self._step_count += 1
        # MOVING WALL: oscillate downstream wall so dam is periodically squeezed/relaxed
        wall = self._terrain_bodies.get("downstream_wall")
        if wall is not None:
            amp = getattr(self, "_downstream_wall_amplitude", 0.4)
            ph = getattr(self, "_downstream_wall_phase_divisor", 100.0)
            new_x = 13.85 + amp * math.sin(self._step_count / ph)
            try:
                wall.SetTransform((new_x, self._downstream_wall_y), 0)
            except Exception:
                pass
        # DEBRIS: at 2000, 5000, 8000 spawn heavy block (50 kg) toward dam — dam must survive impact
        for t in self._debris_spawn_steps:
            if self._step_count == t and t not in self._debris_spawned:
                debris = self._world.CreateDynamicBody(
                    position=(11.2, 3.8),
                    fixtures=Box2D.b2FixtureDef(
                        shape=polygonShape(box=(0.25, 0.25)),
                        density=200.0,
                        friction=0.4,
                        restitution=0.1,
                    ),
                )
                dvx = getattr(self, "_debris_linear_velocity_x", 2.2)
                dvy = getattr(self, "_debris_linear_velocity_y", 0.0)
                debris.linearVelocity = (dvx, dvy)
                debris.linearDamping = 0.05
                self._debris_bodies.append(debris)
                self._debris_spawned.append(t)
                break
        # EARTHQUAKE: at 2500, 5000, 7500, 10000 apply horizontal impulse to all dam bodies
        for t in self._earthquake_steps:
            if self._step_count == t:
                sign = 1 if (self._step_count // 2500) % 2 == 0 else -1
                for body in self._bodies:
                    if body is not None and body.active:
                        vx, vy = body.linearVelocity
                        body.linearVelocity = (vx + sign * self._earthquake_impulse_x, vy)
                break
        self._world.Step(time_step, 10, 10)
        # Breakable joints: beam-to-beam welds break if reaction force exceeds threshold
        if time_step > 0:
            inv_dt = 1.0 / time_step
            to_remove = []
            floor_body = self._terrain_bodies.get("floor")
            for joint in list(self._joints):
                if joint.bodyB == floor_body:
                    continue
                try:
                    force = joint.GetReactionForce(inv_dt)
                    mag = math.sqrt(force.x ** 2 + force.y ** 2)
                    hist = self._joint_force_history.setdefault(joint, [])
                    hist.append(mag)
                    if len(hist) > self._joint_force_history_len:
                        hist.pop(0)
                    threshold = getattr(self, 'JOINT_BREAK_FORCE', 50000.0)
                    if len(hist) >= self._joint_force_history_len and all(h >= threshold for h in hist):
                        to_remove.append(joint)
                except Exception:
                    pass
            for joint in to_remove:
                self._joint_force_history.pop(joint, None)
                try:
                    self._world.DestroyJoint(joint)
                    if joint in self._joints:
                        self._joints.remove(joint)
                except Exception:
                    pass
        # Nine surge waves with increasing impulse (forward push)
        if self._surge_steps_applied < len(self._surge_steps) and self._step_count >= self._surge_steps[self._surge_steps_applied]:
            impulse = self._surge_impulses[self._surge_steps_applied]
            self._surge_steps_applied += 1
            for p in self._water_particles:
                if p is not None and p.active and p.position.x < self.RESERVOIR_X_MAX:
                    vx, vy = p.linearVelocity
                    p.linearVelocity = (vx + impulse, vy)
        # Periodic backward slosh: reservoir gets negative-x impulse (dam must withstand)
        for t in self._backward_slosh_steps:
            if self._step_count == t:
                for p in self._water_particles:
                    if p is not None and p.active and p.position.x < self.RESERVOIR_X_MAX:
                        vx, vy = p.linearVelocity
                        p.linearVelocity = (vx + self._backward_slosh_impulse_x, vy)
                break
        # Upward surge: water jumps then falls — dam must withstand splash/impact
        for t in self._upward_surge_steps:
            if self._step_count == t:
                for p in self._water_particles:
                    if p is not None and p.active and p.position.x < self.RESERVOIR_X_MAX:
                        vx, vy = p.linearVelocity
                        p.linearVelocity = (vx, vy + self._upward_surge_impulse_y)
                break

    def get_terrain_bounds(self):
        res_x_min = getattr(self, "RESERVOIR_X_MIN", 1.0)
        return {
            "reservoir": {"x_min": res_x_min, "x_max": self.RESERVOIR_X_MAX, "fill_height": self.RESERVOIR_FILL_HEIGHT},
            "dam_zone": {"x_min": self.DAM_X_LEFT, "x_max": self.DAM_X_RIGHT},
            "downstream_x_start": self.DOWNSTREAM_X_START,
            "build_zone_left": {"x": [self.BUILD_ZONE_LEFT_X_MIN, self.BUILD_ZONE_LEFT_X_MAX], "y": [self.BUILD_ZONE_Y_MIN, self.BUILD_ZONE_Y_MAX]},
            "build_zone_middle": {"x": [self.BUILD_ZONE_MIDDLE_X_MIN, self.BUILD_ZONE_MIDDLE_X_MAX], "y": [self.BUILD_ZONE_Y_MIN, self.BUILD_ZONE_Y_MAX]},
            "build_zone_right": {"x": [self.BUILD_ZONE_RIGHT_X_MIN, self.BUILD_ZONE_RIGHT_X_MAX], "y": [self.BUILD_ZONE_Y_MIN, self.BUILD_ZONE_Y_MAX]},
        }

    def get_initial_particle_count(self):
        return self._initial_particle_count

    def get_particle_count(self):
        return len([p for p in self._water_particles if p is not None and p.active])

    def get_leaked_particle_count(self):
        """Leak boundary = moving wall left edge. Full leak if x > wall_left; half-leak in seepage band before wall."""
        count = 0.0
        wall = self._terrain_bodies.get("downstream_wall")
        if wall is not None:
            leak_x = wall.position.x - getattr(self, '_downstream_wall_half_w', 0.25)
        else:
            leak_x = 14.0
        seepage_start = leak_x - 0.5
        for p in self._water_particles:
            if p is not None and p.active:
                x = p.position.x
                if x > leak_x:
                    count += 1.0
                elif x > seepage_start:
                    count += 0.5
        return count
