"""
S-05: The Shelter task environment module
"""
import Box2D
from Box2D.b2 import (world, polygonShape, circleShape, staticBody, dynamicBody)
import math
import random


class DaVinciSandbox:
    """DaVinci Sandbox environment wrapper for S-05: The Shelter"""
    
    def __init__(self, *, terrain_config=None, physics_config=None):
        terrain_config = terrain_config or {}
        physics_config = physics_config or {}
        self._terrain_config = dict(terrain_config)
        self._physics_config = dict(physics_config)

        gravity = tuple(physics_config.get("gravity", (0, -10)))
        self._default_linear_damping = float(physics_config.get("linear_damping", 0.0))
        self._default_angular_damping = float(physics_config.get("angular_damping", 0.0))

        self._world = world(gravity=gravity, doSleep=True)
        self._bodies = []
        self._joints = []
        self._terrain_bodies = {}
        self._meteors = []
        
        self.world = self._world
        self.bodies = self._bodies
        self.joints = self._joints
        
        # Earthquake parameters
        self._earthquake_enabled = physics_config.get("earthquake_enabled", False)
        self._earthquake_frequency = physics_config.get("earthquake_frequency", 1.0)  # Hz
        self._earthquake_amplitude = physics_config.get("earthquake_amplitude", 0.0)  # m/s²
        self._earthquake_direction = physics_config.get("earthquake_direction", "horizontal")  # "horizontal" or "vertical"
        
        # Wind parameters
        self._wind_enabled = physics_config.get("wind_enabled", False)
        self._wind_force = physics_config.get("wind_force", 0.0)  # N per kg
        self._wind_direction = physics_config.get("wind_direction", 1.0)  # 1.0 for right, -1.0 for left
        
        # Meteor parameters (can be overridden)
        self._meteor_mass_override = terrain_config.get("meteor_mass", None)
        self._meteor_count_override = terrain_config.get("meteor_count", None)
        self._meteor_spawn_interval_override = terrain_config.get("meteor_spawn_interval", None)
        if "random_seed" in terrain_config:
            random.seed(terrain_config["random_seed"])
        
        self._simulation_time = 0.0
        
        # Allow MAX_MASS and CORE_MAX_FORCE to be overridden
        # These are class constants, but we can override them as instance attributes
        if "max_mass" in terrain_config:
            self.MAX_MASS = float(terrain_config["max_mass"])
        if "core_max_force" in terrain_config:
            self.CORE_MAX_FORCE = float(terrain_config["core_max_force"])
        
        self._create_terrain(terrain_config)
        self._setup_core(terrain_config)
        self._setup_meteors(terrain_config)

    def _create_terrain(self, terrain_config: dict):
        """Create ground"""
        ground = self._world.CreateStaticBody(
            position=(0, 0),
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(50, 0.5)),
                friction=0.8,
            ),
        )
        self._terrain_bodies["ground"] = ground

    def _setup_core(self, terrain_config: dict):
        """Create fragile Core (1x1m box at origin)"""
        # Core is a sensor that breaks if Force exceeds CORE_MAX_FORCE
        core = self._world.CreateStaticBody(
            position=(0, 0.5),
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(0.5, 0.5)),
                isSensor=True,  # Sensor to detect collisions
            ),
        )
        self._terrain_bodies["core"] = core
        # Use CORE_MAX_FORCE (may have been overridden in __init__)
        self._core_max_force = self.CORE_MAX_FORCE
        self._core_damage = 0.0

    def _setup_meteors(self, terrain_config: dict):
        """Setup boulders: most from CENTER (2 of every 3) so core is heavily targeted; left/right for sides"""
        self._meteor_count = self._meteor_count_override if self._meteor_count_override is not None else 28
        self._meteor_mass = self._meteor_mass_override if self._meteor_mass_override is not None else 260.0  # Very heavy: deflect/absorb very hard
        self._meteor_radius = 0.5
        self._meteor_spawn_height = 20.0
        self._meteors_spawned = 0
        self._meteor_spawn_interval = self._meteor_spawn_interval_override if self._meteor_spawn_interval_override is not None else 0.85
        self._last_meteor_time = 0.0
        # Spawn: 2 of every 3 from CENTER (19 of 28); 1 of 3 left/right alternating
        self._meteor_spawn_left = (-5.0, -2.0)
        self._meteor_spawn_right = (2.0, 5.0)
        self._meteor_spawn_center = (-2.0, 2.0)

    def step(self, time_step):
        """Physics step with meteor spawning, earthquake, and wind"""
        # Update simulation time
        self._simulation_time += time_step
        current_time = self._simulation_time
        
        # Apply earthquake forces (periodic acceleration)
        if self._earthquake_enabled:
            earthquake_accel = self._earthquake_amplitude * math.sin(2 * math.pi * self._earthquake_frequency * current_time)
            if self._earthquake_direction == "horizontal":
                # Apply horizontal acceleration to all dynamic bodies
                for body in self._bodies:
                    if body.type == dynamicBody:
                        body.linearVelocity = (
                            body.linearVelocity.x + earthquake_accel * time_step,
                            body.linearVelocity.y
                        )
                # Also apply to meteors
                for meteor in self._meteors:
                    meteor.linearVelocity = (
                        meteor.linearVelocity.x + earthquake_accel * time_step,
                        meteor.linearVelocity.y
                    )
            elif self._earthquake_direction == "vertical":
                # Apply vertical acceleration
                for body in self._bodies:
                    if body.type == dynamicBody:
                        body.linearVelocity = (
                            body.linearVelocity.x,
                            body.linearVelocity.y + earthquake_accel * time_step
                        )
                for meteor in self._meteors:
                    meteor.linearVelocity = (
                        meteor.linearVelocity.x,
                        meteor.linearVelocity.y + earthquake_accel * time_step
                    )
        
        # Apply wind forces (constant horizontal force)
        if self._wind_enabled:
            for body in self._bodies:
                if body.type == dynamicBody:
                    wind_force_x = self._wind_force * body.mass * self._wind_direction
                    # Apply as impulse
                    body.ApplyLinearImpulse(
                        (wind_force_x * time_step, 0),
                        body.worldCenter,
                        True
                    )
        
        # Spawn: 2 of every 3 from CENTER (n%3==0 or n%3==1 -> center); 1 of 3 left/right
        if (self._meteors_spawned < self._meteor_count and
            current_time >= self._last_meteor_time + self._meteor_spawn_interval):
            left_lo, left_hi = self._meteor_spawn_left
            right_lo, right_hi = self._meteor_spawn_right
            center_lo, center_hi = self._meteor_spawn_center
            n = self._meteors_spawned
            if n % 3 == 2:
                x_offset = random.uniform(right_lo, right_hi) if n % 6 == 5 else random.uniform(left_lo, left_hi)
            else:
                x_offset = random.uniform(center_lo, center_hi)

            meteor = self._world.CreateDynamicBody(
                position=(x_offset, self._meteor_spawn_height),
                fixtures=Box2D.b2FixtureDef(
                    shape=circleShape(radius=self._meteor_radius),
                    density=self._meteor_mass / (math.pi * self._meteor_radius**2),
                    friction=0.5,
                )
            )
            self._meteors.append(meteor)
            self._meteors_spawned += 1
            self._last_meteor_time = current_time
        
        self._world.Step(time_step, 10, 10)

        # Core damage: (1) from contacts (impulse), (2) from meteor-core OVERLAP (core is sensor so impulse can be 0!)
        core = self._terrain_bodies.get("core")
        if core:
            for contact_edge in core.contacts:
                contact = contact_edge.contact
                if contact.touching:
                    manifold = contact.manifold
                    if manifold.pointCount > 0:
                        impulse = manifold.points[0].normalImpulse
                        force = abs(impulse) / time_step if time_step > 0 else 0
                        self._core_damage = max(self._core_damage, force)
            # If any meteor OVERLAPS the core (circle-rectangle overlap), count as hit -> fail
            # (Sensor often has no impulse, so we must check geometry. "Touch" = any overlap.)
            core_x, core_y = core.position.x, core.position.y
            core_half = 0.5
            # Core AABB: [core_x - core_half, core_x + core_half] x [core_y - core_half, core_y + core_half]
            for meteor in self._meteors:
                mx, my = meteor.position.x, meteor.position.y
                # Closest point on core AABB to meteor center
                cx = max(core_x - core_half, min(core_x + core_half, mx))
                cy = max(core_y - core_half, min(core_y + core_half, my))
                dist_sq = (mx - cx) ** 2 + (my - cy) ** 2
                if dist_sq <= self._meteor_radius ** 2:
                    # Meteor circle overlaps core rectangle -> hit
                    self._core_damage = max(self._core_damage, self._core_max_force + 1.0)

    # --- Physical constraint constants ---
    MIN_BEAM_SIZE = 0.1
    MAX_BEAM_SIZE = 10.0
    CORE_POSITION = (0.0, 0.0)
    KEEP_OUT_RADIUS = 1.3  # Cannot build within 1.3m of Core (very tight)
    MAX_MASS = 120.0  # kg (very tight budget; can be overridden in terrain_config)
    CORE_MAX_FORCE = 14.0  # N (core fails if any impact exceeds this; strict; overlap counts as limit+1)
    MAX_STRUCTURE_HEIGHT = 4.5  # No part of any beam may extend above y=4.5m

    def add_beam(self, x, y, width, height, angle=0, density=1.0):
        """API: Add a beam"""
        # Check keep-out zone
        dist_to_core = math.sqrt((x - self.CORE_POSITION[0])**2 + (y - self.CORE_POSITION[1])**2)
        if dist_to_core < self.KEEP_OUT_RADIUS:
            raise ValueError(f"Cannot build within {self.KEEP_OUT_RADIUS}m of core")
        
        width = max(self.MIN_BEAM_SIZE, min(width, self.MAX_BEAM_SIZE))
        height = max(self.MIN_BEAM_SIZE, min(height, self.MAX_BEAM_SIZE))
        # Check max structure height: beam AABB top (y + half extent along vertical) must not exceed limit
        half_extent_vertical = max(width, height) / 2.0  # conservative upper bound for any angle
        if y + half_extent_vertical > self.MAX_STRUCTURE_HEIGHT:
            raise ValueError(f"Structure height limit: no beam may extend above y={self.MAX_STRUCTURE_HEIGHT}m")
        
        body = self._world.CreateDynamicBody(
            position=(x, y),
            angle=angle,
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(width/2, height/2)),
                density=density,
                friction=0.5,
            )
        )
        body.linearDamping = self._default_linear_damping
        body.angularDamping = self._default_angular_damping
        self._bodies.append(body)
        return body

    def add_joint(self, body_a, body_b, anchor_point, type='rigid'):
        """API: Add a joint"""
        anchor_x, anchor_y = anchor_point[0], anchor_point[1]
        
        if type == 'rigid':
            joint = self._world.CreateWeldJoint(
                bodyA=body_a,
                bodyB=body_b,
                anchor=(anchor_x, anchor_y),
                collideConnected=False
            )
        elif type == 'pivot':
            joint = self._world.CreateRevoluteJoint(
                bodyA=body_a,
                bodyB=body_b,
                anchor=(anchor_x, anchor_y),
                collideConnected=False
            )
        else:
            raise ValueError(f"Unknown joint type: {type}")
        
        self._joints.append(joint)
        return joint

    def get_structure_mass(self):
        """API: Returns total mass"""
        total_mass = 0.0
        for body in self._bodies:
            total_mass += body.mass
        return total_mass

    def set_material_properties(self, body, restitution=0.2):
        """API: Set material properties"""
        for fixture in body.fixtures:
            fixture.restitution = float(restitution)

    def get_core_damage(self):
        """Get core damage level"""
        return self._core_damage

    def get_terrain_bounds(self):
        """Get terrain bounds"""
        return {
            "core_position": self.CORE_POSITION,
            "keep_out_radius": self.KEEP_OUT_RADIUS,
            "max_mass": self.MAX_MASS,
            "core_max_force": self.CORE_MAX_FORCE,
            "max_structure_height": self.MAX_STRUCTURE_HEIGHT,
            "meteor_count": self._meteor_count,
            "meteor_spawn_interval": self._meteor_spawn_interval,
        }
