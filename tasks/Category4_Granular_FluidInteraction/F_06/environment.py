"""
F-06: The Pipeline task environment module (HARD variant)
Defines physics world, source, target, fluid particles, PIT (loss), HEADWIND, GRAVITY WELL, API.
"""
import Box2D
from Box2D.b2 import (world, polygonShape, circleShape, staticBody, dynamicBody, weldJoint)
import math
import random


class Sandbox:
    """Sandbox environment wrapper for F-06: The Pipeline (hard: pit, headwind, gravity well)"""

    def __init__(self, *, terrain_config=None, physics_config=None):
        terrain_config = terrain_config or {}
        physics_config = physics_config or {}
        self._terrain_config = dict(terrain_config)
        self._physics_config = dict(physics_config)

        gravity = tuple(physics_config.get("gravity", (0, -10)))
        self._default_linear_damping = float(physics_config.get("linear_damping", 0.05))
        self._default_angular_damping = float(physics_config.get("angular_damping", 0.05))

        self._world = world(gravity=gravity, doSleep=True)
        self._bodies = []
        self._joints = []
        self._terrain_bodies = {}
        self._fluid_particles = []
        self._step_counter = 0  # for time-varying headwind/gravity

        self.world = self._world
        self.bodies = self._bodies
        self.joints = self._joints

        # Zones (set before _create_particles)
        self.SOURCE_X_MIN = 2.0
        self.SOURCE_X_MAX = 6.0
        self.SOURCE_Y_MIN = 0.0
        self.SOURCE_Y_MAX = 1.5
        # Target zone: (18, 22) x (0, 1.5) so reference passing at ground level succeeds
        self.TARGET_X_MIN = float(terrain_config.get("target_x_min", 18.0))
        self.TARGET_X_MAX = float(terrain_config.get("target_x_max", 22.0))
        self.TARGET_Y_MIN = float(terrain_config.get("target_y_min", 0.0))
        self.TARGET_Y_MAX = float(terrain_config.get("target_y_max", 1.5))
        self.BUILD_ZONE_X_MIN = 6.0
        self.BUILD_ZONE_X_MAX = 18.0
        self.BUILD_ZONE_Y_MIN = 0.0
        self.BUILD_ZONE_Y_MAX = 6.0
        # Pit 1: enabled for hard variant
        self.PIT_X_MIN = 13.5
        self.PIT_X_MAX = 15.5
        self.PIT_Y_MIN = 0.0
        self.PIT_Y_MAX = float(terrain_config.get("pit1_y_max", 2.0))
        # Pit 2: enabled for hard variant
        self.PIT2_X_MIN = 16.0
        self.PIT2_X_MAX = 17.5
        self.PIT2_Y_MIN = 0.0
        self.PIT2_Y_MAX = float(terrain_config.get("pit2_y_max", 1.6))
        # Pit 3: enabled for hard variant
        self.PIT3_X_MIN = float(terrain_config.get("pit3_x_min", 11.0))
        self.PIT3_X_MAX = float(terrain_config.get("pit3_x_max", 12.5))
        self.PIT3_Y_MIN = 0.0
        self.PIT3_Y_MAX = float(terrain_config.get("pit3_y_max", 1.6))
        # Headwind: configurable for mutated tasks
        self.HEADWIND_Y_THRESHOLD = 3.0
        self.HEADWIND_FX_BASE = float(terrain_config.get("headwind_fx_base", -120.0))
        # Gravity well: configurable for mutated tasks
        self.GRAVWELL_X_MIN = 10.0
        self.GRAVWELL_X_MAX = 14.0
        self.GRAVWELL_Y_MIN = 1.5
        self.GRAVWELL_Y_MAX = 3.5
        self.GRAVWELL_FY = float(terrain_config.get("gravwell_fy", -120.0))
        self.MAX_TIME_SECONDS = float(physics_config.get("max_time_seconds", 40.0))
        self.FORCE_BUDGET_PER_STEP = float(physics_config.get("force_budget", 12000.0))
        self._force_budget_used = 0.0
        self.MAX_STEPS = int(self.MAX_TIME_SECONDS * 60)
        self.MAX_STRUCTURE_MASS = float(terrain_config.get("max_structure_mass", 380.0))
        self.MIN_DELIVERY_RATIO = float(terrain_config.get("min_delivery_ratio", 0.90))

        self._create_terrain(terrain_config)
        self._create_fluid_particles(terrain_config)

    def _create_terrain(self, terrain_config: dict):
        """Create floor, source container (sensor), target container (sensor)."""
        floor_length = 26.0
        floor_height = 0.3
        floor = self._world.CreateStaticBody(
            position=(floor_length / 2, -floor_height / 2),
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(floor_length / 2, floor_height / 2)),
                friction=0.5,
            ),
        )
        self._terrain_bodies["floor"] = floor

        source_width = 4.0
        source_height = 1.5
        source_center_x = 4.0
        source_center_y = 0.75
        source_body = self._world.CreateStaticBody(
            position=(source_center_x, source_center_y),
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(source_width / 2, source_height / 2)),
                friction=0.3,
                isSensor=True,
            ),
        )
        self._terrain_bodies["source"] = source_body

        target_center_x = (self.TARGET_X_MIN + self.TARGET_X_MAX) / 2
        target_center_y = (self.TARGET_Y_MIN + self.TARGET_Y_MAX) / 2
        target_hw = (self.TARGET_X_MAX - self.TARGET_X_MIN) / 2
        target_hh = (self.TARGET_Y_MAX - self.TARGET_Y_MIN) / 2
        target_body = self._world.CreateStaticBody(
            position=(target_center_x, target_center_y),
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(target_hw, target_hh)),
                friction=0.3,
                isSensor=True,
            ),
        )
        self._terrain_bodies["target"] = target_body

    def _create_fluid_particles(self, terrain_config: dict):
        """Create fluid particles in the source container."""
        fluid_config = terrain_config.get("fluid", {})
        num_particles = int(fluid_config.get("count", 60))
        particle_radius = float(fluid_config.get("radius", 0.10))
        density = float(fluid_config.get("density", 800.0))
        viscosity = float(fluid_config.get("viscosity", 0.25))
        seed = int(fluid_config.get("seed", 42))
        random.seed(seed)

        for _ in range(num_particles):
            x = random.uniform(self.SOURCE_X_MIN + particle_radius, self.SOURCE_X_MAX - particle_radius)
            y = random.uniform(self.SOURCE_Y_MIN + particle_radius, self.SOURCE_Y_MAX - particle_radius)
            mass = density * (math.pi * particle_radius ** 2)
            body = self._world.CreateDynamicBody(
                position=(x, y),
                fixtures=Box2D.b2FixtureDef(
                    shape=circleShape(radius=particle_radius),
                    density=mass / (math.pi * particle_radius ** 2),
                    friction=0.2,
                    restitution=0.05,
                ),
            )
            body.linearDamping = viscosity
            body.angularDamping = viscosity
            self._fluid_particles.append(body)

        self._initial_particle_count = len(self._fluid_particles)

    # --- Physical constraint constants ---
    MIN_BEAM_SIZE = 0.1
    MAX_BEAM_SIZE = 1.2
    BUILD_ZONE_X_MIN = 6.0
    BUILD_ZONE_X_MAX = 18.0
    BUILD_ZONE_Y_MIN = 0.0
    BUILD_ZONE_Y_MAX = 6.0
    MAX_STRUCTURE_MASS = 380.0

    def add_beam(self, x, y, width, height, angle=0, density=250.0):
        """API: Add a beam (pipeline / pump / screw element)."""
        width = max(self.MIN_BEAM_SIZE, min(width, self.MAX_BEAM_SIZE))
        height = max(self.MIN_BEAM_SIZE, min(height, self.MAX_BEAM_SIZE))
        body = self._world.CreateDynamicBody(
            position=(x, y),
            angle=angle,
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(width / 2, height / 2)),
                density=density,
                friction=0.4,
            ),
        )
        body.linearDamping = self._default_linear_damping
        body.angularDamping = self._default_angular_damping
        self._bodies.append(body)
        return body

    def add_joint(self, body_a, body_b, anchor_point, type='rigid'):
        """API: Add a joint. body_b can be None to anchor to the floor."""
        if body_a is None:
            raise ValueError("add_joint: body_a cannot be None.")
        anchor_x, anchor_y = anchor_point[0], anchor_point[1]
        if body_b is None:
            body_b = self._terrain_bodies.get("floor")
            if body_b is None:
                raise ValueError("add_joint: floor not found.")
        if type != 'rigid':
            type = 'rigid'
        joint = self._world.CreateWeldJoint(
            bodyA=body_a,
            bodyB=body_b,
            anchor=(anchor_x, anchor_y),
            collideConnected=False
        )
        self._joints.append(joint)
        return joint

    def get_structure_mass(self):
        """API: Total mass of pipeline/pump structure."""
        return sum(b.mass for b in self._bodies)

    def set_material_properties(self, body, restitution=0.1):
        """API: Set restitution for a body."""
        for fixture in body.fixtures:
            fixture.restitution = float(restitution)

    # Floor top y=0; particle radius 0.1 -> min valid y to correct tunneling (no difficulty change)
    _PARTICLE_RADIUS = 0.10

    def step(self, time_step):
        """Physics step: world step, pits (deactivate), time-varying headwind, gravity well; reset force budget for next step."""
        self._step_counter += 1
        self._world.Step(time_step, 20, 20)
        # Correct tunneling: any particle below floor gets moved back to just above floor
        for p in self._fluid_particles:
            if p is not None and p.active:
                x, y = p.position.x, p.position.y
                if y < self._PARTICLE_RADIUS:
                    p.transform = ((x, self._PARTICLE_RADIUS), p.angle)
                    vx = p.linearVelocity.x
                    p.linearVelocity = (vx, 0.0)
        # Headwind: y > threshold -> force -X (time-varying: oscillations between -60 and -180 N)
        headwind_fx = self.HEADWIND_FX_BASE + 60.0 * math.sin(self._step_counter / 50.0)
        for p in self._fluid_particles:
            if p is None or not p.active:
                continue
            x, y = p.position.x, p.position.y
            # Pit 3 (NEW): corridor trap - route above y>1.6 when x in [11, 12.5]
            if (self.PIT3_X_MIN <= x <= self.PIT3_X_MAX and
                    self.PIT3_Y_MIN <= y <= self.PIT3_Y_MAX):
                p.active = False
                continue
            # Pit 1
            if (self.PIT_X_MIN <= x <= self.PIT_X_MAX and
                    self.PIT_Y_MIN <= y <= self.PIT_Y_MAX):
                p.active = False
                continue
            # Pit 2
            if (self.PIT2_X_MIN <= x <= self.PIT2_X_MAX and
                    self.PIT2_Y_MIN <= y <= self.PIT2_Y_MAX):
                p.active = False
                continue
            # Headwind application
            if y > self.HEADWIND_Y_THRESHOLD:
                p.ApplyForceToCenter((headwind_fx, 0), wake=True)
            # Gravity well
            if (self.GRAVWELL_X_MIN <= x <= self.GRAVWELL_X_MAX and
                    self.GRAVWELL_Y_MIN <= y <= self.GRAVWELL_Y_MAX):
                p.ApplyForceToCenter((0, self.GRAVWELL_FY), wake=True)
        # Reset force budget for next agent_action
        self._force_budget_used = 0.0

    def get_fluid_particles(self):
        """Return list of fluid particle bodies for agent_action. Use with apply_force_to_particle."""
        return [p for p in self._fluid_particles if p is not None and p.active]

    def apply_force_to_particle(self, particle, fx, fy):
        """
        Apply force to a particle subject to per-step force budget.
        Only applies if (fx,fy) would not exceed FORCE_BUDGET_PER_STEP for this step.
        Agent must use this (not particle.ApplyForceToCenter) so force is limited.
        """
        if particle not in self._fluid_particles or not particle.active:
            return
        mag = math.sqrt(fx * fx + fy * fy)
        if mag <= 0:
            return
        if self._force_budget_used + mag <= self.FORCE_BUDGET_PER_STEP:
            particle.ApplyForceToCenter((fx, fy), wake=True)
            self._force_budget_used += mag

    def get_terrain_bounds(self):
        """Get terrain bounds for evaluation and rendering."""
        return {
            "source": {"x_min": self.SOURCE_X_MIN, "x_max": self.SOURCE_X_MAX,
                      "y_min": self.SOURCE_Y_MIN, "y_max": self.SOURCE_Y_MAX},
            "target": {"x_min": self.TARGET_X_MIN, "x_max": self.TARGET_X_MAX,
                       "y_min": self.TARGET_Y_MIN, "y_max": self.TARGET_Y_MAX},
            "build_zone": {"x": [self.BUILD_ZONE_X_MIN, self.BUILD_ZONE_X_MAX],
                           "y": [self.BUILD_ZONE_Y_MIN, self.BUILD_ZONE_Y_MAX]},
            "pit": {"x_min": self.PIT_X_MIN, "x_max": self.PIT_X_MAX,
                    "y_min": self.PIT_Y_MIN, "y_max": self.PIT_Y_MAX},
            "pit2": {"x_min": self.PIT2_X_MIN, "x_max": self.PIT2_X_MAX,
                     "y_min": self.PIT2_Y_MIN, "y_max": self.PIT2_Y_MAX},
            "pit3": {"x_min": self.PIT3_X_MIN, "x_max": self.PIT3_X_MAX,
                     "y_min": self.PIT3_Y_MIN, "y_max": self.PIT3_Y_MAX},
        }

    def get_initial_particle_count(self):
        """Initial number of fluid particles in the source."""
        return self._initial_particle_count

    def get_particles_in_target_count(self):
        """Number of fluid particles currently inside the target (high) container."""
        count = 0
        for p in self._fluid_particles:
            if p is None or not p.active:
                continue
            x, y = p.position.x, p.position.y
            if (self.TARGET_X_MIN <= x <= self.TARGET_X_MAX and
                    self.TARGET_Y_MIN <= y <= self.TARGET_Y_MAX):
                count += 1
        return count

    def get_delivery_ratio(self):
        """Delivery ratio = particles in target / initial particles."""
        total = self.get_initial_particle_count()
        if total == 0:
            return 1.0
        return self.get_particles_in_target_count() / total

    def get_particles_in_source_count(self):
        """Number of fluid particles currently inside the source container."""
        count = 0
        for p in self._fluid_particles:
            if p is None or not p.active:
                continue
            x, y = p.position.x, p.position.y
            if (self.SOURCE_X_MIN <= x <= self.SOURCE_X_MAX and
                    self.SOURCE_Y_MIN <= y <= self.SOURCE_Y_MAX):
                count += 1
        return count

    def get_particles_in_build_zone_count(self):
        """Number of fluid particles currently inside the build zone [6,18] x [0,6]."""
        count = 0
        for p in self._fluid_particles:
            if p is None or not p.active:
                continue
            x, y = p.position.x, p.position.y
            if (self.BUILD_ZONE_X_MIN <= x <= self.BUILD_ZONE_X_MAX and
                    self.BUILD_ZONE_Y_MIN <= y <= self.BUILD_ZONE_Y_MAX):
                count += 1
        return count

    def get_particle_stats(self):
        """Return mean x, mean y, and active count of fluid particles."""
        xs, ys, n = [], [], 0
        for p in self._fluid_particles:
            if p is None or not p.active:
                continue
            xs.append(p.position.x)
            ys.append(p.position.y)
            n += 1
        mean_x = sum(xs) / n if n else 0.0
        mean_y = sum(ys) / n if n else 0.0
        return {"mean_x": mean_x, "mean_y": mean_y, "active_count": n}
