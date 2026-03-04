"""
E-06: Cantilever Endurance task environment.
Fundamentally different from symmetric truss: anchors ONLY in left support zone;
structure must cantilever to the right. Excitation is distance-scaled and moment-dominant.
"""
import math
import random
import Box2D
from Box2D.b2 import world, polygonShape, staticBody, dynamicBody, weldJoint, revoluteJoint


class Sandbox:
    """
    Sandbox for E-06: Cantilever Endurance.
    - Anchors allowed ONLY in left support zone (x in [5, 6.5]); elsewhere rejected.
    - Distance-scaled excitation: load increases toward tip (x direction).
    - Moment-dominant coherent pulse: overturning moment, tip gets most torque.
    - Progressive fatigue, beam spin destroy, cascade, phased storm.
    - No "avoid center" — structure must span 8m+ cantilever from tiny support.
    """

    BUILD_ZONE_X_MIN = 5.0
    BUILD_ZONE_X_MAX = 15.0
    BUILD_ZONE_Y_MIN = 1.5
    BUILD_ZONE_Y_MAX = 8.0
    MAX_STRUCTURE_MASS = 120.0  # Tight budget: must survive + tip stability with minimal mass
    MAX_GROUND_ANCHORS = 1  # Only one ground anchor — structure must cantilever from single support
    MAX_BEAMS = 48
    MAX_JOINTS = 75
    MIN_ANCHOR_SPACING = 0.7
    # Forbidden build zone: beam center x in [lo, hi] is rejected (agent must infer from feedback)
    FORBIDDEN_ZONE_X_LO = 9.7
    FORBIDDEN_ZONE_X_HI = 10.3
    # Damage hotspot: joints with anchor x in this range accumulate damage faster (discover via feedback)
    DAMAGE_HOTSPOT_X_LO = 8.5
    DAMAGE_HOTSPOT_X_HI = 11.0
    DAMAGE_HOTSPOT_MULT = 1.35
    MIN_BEAM_SIZE = 0.1
    MAX_BEAM_SIZE = 4.0

    # Anchors ONLY in left support zone (discover from error when anchoring elsewhere)
    ALLOWED_ANCHOR_X_LO = 5.0
    ALLOWED_ANCHOR_X_HI = 6.5
    SUPPORT_CENTER_X = 5.75

    # Distance-scaled excitation: bodies farther from support get stronger load
    DISTANCE_SCALE_FACTOR = 0.6  # mult = 1 + factor * (x - support_x) / span

    NOISE_STRENGTH = 42.0
    JOINT_BREAK_FORCE = 78.0
    JOINT_BREAK_TORQUE = 115.0

    DAMAGE_FORCE_THRESH = 12.0
    DAMAGE_TORQUE_THRESH = 18.0
    DAMAGE_FORCE_RATE = 2.9
    DAMAGE_TORQUE_RATE = 2.1
    DAMAGE_LIMIT = 100.0
    CASCADE_SHOCK_DAMAGE = 26.0
    CASCADE_RADIUS = 2.2

    GROUND_DAMAGE_FORCE_THRESH = 6.0
    GROUND_DAMAGE_TORQUE_THRESH = 10.0
    GROUND_DAMAGE_FORCE_RATE = 4.8
    GROUND_DAMAGE_TORQUE_RATE = 3.5

    BEAM_ANGVEL_THRESH = 2.2
    BEAM_ANGVEL_TOLERANCE_STEPS = 10

    PHASED_STORM_START = 100
    PHASED_STORM_END = 450
    PHASED_STORM_MULT = 1.9
    COHERENT_PULSE_INTERVAL = 58
    COHERENT_PULSE_FORCE = 36.0
    # Moment-dominant: torque proportional to distance from support (overturning)
    COHERENT_MOMENT_BASE = 18.0

    def __init__(self, *, terrain_config=None, physics_config=None):
        terrain_config = terrain_config or {}
        physics_config = physics_config or {}
        self._terrain_config = dict(terrain_config)
        self._physics_config = dict(physics_config)
        gravity = tuple(physics_config.get("gravity", (0, -10)))
        self._linear_damping = float(physics_config.get("linear_damping", 0.0))
        self._angular_damping = float(physics_config.get("angular_damping", 1.6))
        self._noise_strength = float(physics_config.get("noise_strength", self.NOISE_STRENGTH))

        _pc = physics_config
        if "coherent_pulse_interval" in _pc:
            self.COHERENT_PULSE_INTERVAL = int(_pc["coherent_pulse_interval"])
        if "coherent_pulse_force" in _pc:
            self.COHERENT_PULSE_FORCE = float(_pc["coherent_pulse_force"])
        if "joint_break_force" in _pc:
            self.JOINT_BREAK_FORCE = float(_pc["joint_break_force"])
        if "joint_break_torque" in _pc:
            self.JOINT_BREAK_TORQUE = float(_pc["joint_break_torque"])
        if "damage_limit" in _pc:
            self.DAMAGE_LIMIT = float(_pc["damage_limit"])
        if "damage_force_thresh" in _pc:
            self.DAMAGE_FORCE_THRESH = float(_pc["damage_force_thresh"])
        if "damage_torque_thresh" in _pc:
            self.DAMAGE_TORQUE_THRESH = float(_pc["damage_torque_thresh"])
        if "cascade_shock_damage" in _pc:
            self.CASCADE_SHOCK_DAMAGE = float(_pc["cascade_shock_damage"])
        if "beam_angvel_thresh" in _pc:
            self.BEAM_ANGVEL_THRESH = float(_pc["beam_angvel_thresh"])
        if "beam_angvel_tolerance_steps" in _pc:
            self.BEAM_ANGVEL_TOLERANCE_STEPS = int(_pc["beam_angvel_tolerance_steps"])
        if "phased_storm_mult" in _pc:
            self.PHASED_STORM_MULT = float(_pc["phased_storm_mult"])
        if "phased_storm_start" in _pc:
            self.PHASED_STORM_START = int(_pc["phased_storm_start"])
        if "phased_storm_end" in _pc:
            self.PHASED_STORM_END = int(_pc["phased_storm_end"])
        if "burst_prob" in _pc:
            self._burst_prob = float(_pc["burst_prob"])
        else:
            self._burst_prob = 0.026

        # Instance-specific constraints (overridable via terrain_config)
        self._max_structure_mass = float(terrain_config.get("max_structure_mass", self.MAX_STRUCTURE_MASS))
        self._max_ground_anchors = int(terrain_config.get("max_ground_anchors", self.MAX_GROUND_ANCHORS))
        self._forbidden_zone_x_lo = float(terrain_config.get("forbidden_zone_x_lo", self.FORBIDDEN_ZONE_X_LO))
        self._forbidden_zone_x_hi = float(terrain_config.get("forbidden_zone_x_hi", self.FORBIDDEN_ZONE_X_HI))
        self._allowed_anchor_x_lo = float(terrain_config.get("allowed_anchor_x_lo", self.ALLOWED_ANCHOR_X_LO))
        self._allowed_anchor_x_hi = float(terrain_config.get("allowed_anchor_x_hi", self.ALLOWED_ANCHOR_X_HI))

        self._world = world(gravity=gravity, doSleep=True)
        self._bodies = []
        self._joints = []
        self._joint_is_ground = {}
        self._joint_anchor = {}
        self._terrain_bodies = {}
        self._joint_peak_forces = {}
        self._joint_peak_torques = {}
        self._joint_damage = {}
        self._beam_high_spin_steps = {}
        self._step_counter = 0
        self._burst_remaining = 0
        self._ground_anchor_count = 0
        self._ground_anchor_x = []

        self.world = self._world
        self.bodies = self._bodies
        self.joints = self._joints

        self._create_terrain(terrain_config)

    def _create_terrain(self, terrain_config: dict):
        ground_length = 40.0
        ground_height = 1.0
        ground = self._world.CreateStaticBody(
            position=(ground_length / 2, ground_height / 2),
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(ground_length / 2, ground_height / 2)),
                friction=0.6,
            ),
        )
        self._terrain_bodies["ground"] = ground
        self._ground_y = ground_height

    def _get_noise_multiplier(self):
        if self._burst_remaining > 0:
            self._burst_remaining -= 1
            return 3.8
        if self._step_counter > 0 and random.random() < getattr(self, "_burst_prob", 0.026):
            self._burst_remaining = 12
        mult = 1.0
        if self.PHASED_STORM_START <= self._step_counter <= self.PHASED_STORM_END:
            mult *= self.PHASED_STORM_MULT
        return mult

    def _apply_impulses(self, sigma_mult):
        sigma = self._noise_strength * sigma_mult
        total_mass = sum(b.mass for b in self._bodies) or 1.0
        mass_factor = 1.0 + 0.25 * math.sqrt(total_mass / 60.0)

        # Moment-dominant coherent pulse: torque proportional to distance from support
        if self._step_counter > 0 and self._step_counter % self.COHERENT_PULSE_INTERVAL == 0:
            sign = 1 if (self._step_counter // self.COHERENT_PULSE_INTERVAL) % 2 == 0 else -1
            for body in self._bodies:
                dx = body.position.x - self.SUPPORT_CENTER_X
                tau = sign * self.COHERENT_MOMENT_BASE * mass_factor * max(0, dx) / 5.0
                body.ApplyTorque(tau, wake=True)
                # Also lateral force (creates moment)
                fx = sign * self.COHERENT_PULSE_FORCE * mass_factor * (0.3 + 0.7 * max(0, dx) / 10.0)
                body.ApplyForceToCenter((fx, 0), wake=True)

        span = self.BUILD_ZONE_X_MAX - self.SUPPORT_CENTER_X
        for i, body in enumerate(self._bodies):
            dx = body.position.x - self.SUPPORT_CENTER_X
            dist_mult = 1.0 + self.DISTANCE_SCALE_FACTOR * max(0, dx) / max(span, 0.1)
            s = sigma * dist_mult
            if random.random() < 0.28:
                if i % 2 == 0:
                    fx = random.gauss(0, s) + 1.6 * s
                    fy = random.gauss(0, s * 0.8)
                else:
                    fx = random.gauss(0, s) - 1.6 * s
                    fy = random.gauss(0, s * 0.8)
            else:
                fx = random.gauss(0, s)
                fy = random.gauss(0, s)
            body.ApplyForceToCenter((fx * mass_factor, fy * mass_factor), wake=True)

    def _get_joint_anchor_pos(self, joint):
        return self._joint_anchor.get(joint, (0, 0))

    def _destroy_body_and_joints(self, body):
        to_remove = [j for j in self._joints if j.bodyA == body or j.bodyB == body]
        for j in to_remove:
            try:
                self._world.DestroyJoint(j)
                self._joints.remove(j)
                self._joint_peak_forces.pop(j, None)
                self._joint_peak_torques.pop(j, None)
                self._joint_damage.pop(j, None)
                if self._joint_is_ground.get(j):
                    self._ground_anchor_count = max(0, self._ground_anchor_count - 1)
                    ax = self._joint_anchor.get(j, (0, 0))[0]
                    if ax in self._ground_anchor_x:
                        self._ground_anchor_x.remove(ax)
                self._joint_is_ground.pop(j, None)
                self._joint_anchor.pop(j, None)
            except Exception:
                pass
        try:
            self._world.DestroyBody(body)
            self._bodies.remove(body)
        except Exception:
            pass
        self._beam_high_spin_steps.pop(body, None)

    def step(self, time_step):
        self._step_counter += 1
        sigma_mult = self._get_noise_multiplier()
        self._apply_impulses(sigma_mult)
        self._world.Step(time_step, 10, 10)

        for body in list(self._bodies):
            av = abs(body.angularVelocity)
            if av > self.BEAM_ANGVEL_THRESH:
                self._beam_high_spin_steps[body] = self._beam_high_spin_steps.get(body, 0) + 1
                if self._beam_high_spin_steps[body] >= self.BEAM_ANGVEL_TOLERANCE_STEPS:
                    self._destroy_body_and_joints(body)
            else:
                self._beam_high_spin_steps[body] = 0

        joints_to_remove = []
        for joint in list(self._joints):
            try:
                if not hasattr(joint, "GetReactionForce"):
                    continue
                force = joint.GetReactionForce(1.0 / 60.0)
                force_mag = math.sqrt(force.x**2 + force.y**2)
                torque_mag = abs(joint.GetReactionTorque(1.0 / 60.0)) if hasattr(joint, "GetReactionTorque") else 0.0

                self._joint_peak_forces[joint] = max(self._joint_peak_forces.get(joint, 0.0), force_mag)
                self._joint_peak_torques[joint] = max(self._joint_peak_torques.get(joint, 0.0), torque_mag)

                if force_mag > self.JOINT_BREAK_FORCE or torque_mag > self.JOINT_BREAK_TORQUE:
                    joints_to_remove.append(joint)
                    continue

                is_ground = self._joint_is_ground.get(joint, False)
                f_thresh = self.GROUND_DAMAGE_FORCE_THRESH if is_ground else self.DAMAGE_FORCE_THRESH
                t_thresh = self.GROUND_DAMAGE_TORQUE_THRESH if is_ground else self.DAMAGE_TORQUE_THRESH
                f_rate = self.GROUND_DAMAGE_FORCE_RATE if is_ground else self.DAMAGE_FORCE_RATE
                t_rate = self.GROUND_DAMAGE_TORQUE_RATE if is_ground else self.DAMAGE_TORQUE_RATE

                jx, jy = self._get_joint_anchor_pos(joint)
                hotspot_mult = (
                    self.DAMAGE_HOTSPOT_MULT
                    if self.DAMAGE_HOTSPOT_X_LO <= jx <= self.DAMAGE_HOTSPOT_X_HI
                    else 1.0
                )

                damage = self._joint_damage.get(joint, 0.0)
                if force_mag > f_thresh:
                    damage += (force_mag - f_thresh) * f_rate * 0.016 * hotspot_mult
                if torque_mag > t_thresh:
                    damage += (torque_mag - t_thresh) * t_rate * 0.016 * hotspot_mult
                self._joint_damage[joint] = damage

                if damage >= self.DAMAGE_LIMIT:
                    joints_to_remove.append(joint)
            except Exception:
                continue

        for joint in joints_to_remove:
            try:
                ax, ay = self._get_joint_anchor_pos(joint)
                self._world.DestroyJoint(joint)
                self._joints.remove(joint)
                self._joint_peak_forces.pop(joint, None)
                self._joint_peak_torques.pop(joint, None)
                d = self._joint_damage.pop(joint, None)
                if self._joint_is_ground.get(joint):
                    self._ground_anchor_count = max(0, self._ground_anchor_count - 1)
                    ax0 = self._joint_anchor.get(joint, (0, 0))[0]
                    if ax0 in self._ground_anchor_x:
                        self._ground_anchor_x.remove(ax0)
                self._joint_is_ground.pop(joint, None)
                self._joint_anchor.pop(joint, None)

                for j in list(self._joints):
                    try:
                        jx, jy = self._get_joint_anchor_pos(j)
                        dist = math.sqrt((jx - ax)**2 + (jy - ay)**2)
                        if dist <= self.CASCADE_RADIUS and dist > 0.01:
                            self._joint_damage[j] = min(
                                self.DAMAGE_LIMIT,
                                self._joint_damage.get(j, 0) + self.CASCADE_SHOCK_DAMAGE
                            )
                    except Exception:
                        pass
            except Exception:
                pass

    def add_beam(self, x, y, width, height, angle=0, density=1.0):
        if len(self._bodies) >= self.MAX_BEAMS:
            raise ValueError(f"Maximum {self.MAX_BEAMS} beams allowed")
        if self._forbidden_zone_x_lo <= x <= self._forbidden_zone_x_hi:
            raise ValueError(
                "Beam placement not allowed in this region. "
                "Use feedback and trial to infer where geometry is restricted."
            )
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
        body.linearDamping = self._linear_damping
        body.angularDamping = self._angular_damping
        body.userData = {"width": width, "height": height}
        self._bodies.append(body)
        return body

    def add_joint(self, body_a, body_b, anchor_point, type="rigid"):
        if len(self._joints) >= self.MAX_JOINTS:
            raise ValueError(f"Maximum {self.MAX_JOINTS} joints allowed")
        if body_a is None:
            raise ValueError("add_joint: body_a cannot be None.")
        anchor_x, anchor_y = anchor_point[0], anchor_point[1]
        is_ground = body_b is None
        if is_ground:
            if self._ground_anchor_count >= self._max_ground_anchors:
                raise ValueError(f"Maximum {self._max_ground_anchors} ground anchors allowed")
            if not (self._allowed_anchor_x_lo <= anchor_x <= self._allowed_anchor_x_hi):
                raise ValueError(
                    "Ground anchors are allowed only in the left support zone. "
                    "The structure must cantilever from this support; use feedback to infer valid placement."
                )
            for gx in self._ground_anchor_x:
                if abs(anchor_x - gx) < self.MIN_ANCHOR_SPACING:
                    raise ValueError(f"Ground anchors must be at least {self.MIN_ANCHOR_SPACING} m apart")
        if body_b is None:
            body_b = self._terrain_bodies.get("ground")
            if body_b is None:
                raise ValueError("add_joint: Cannot anchor to ground.")
        if type == "rigid":
            joint = self._world.CreateWeldJoint(
                bodyA=body_a, bodyB=body_b,
                anchor=(anchor_x, anchor_y), collideConnected=False,
            )
        elif type == "pivot":
            joint = self._world.CreateRevoluteJoint(
                bodyA=body_a, bodyB=body_b,
                anchor=(anchor_x, anchor_y), collideConnected=False,
            )
        else:
            raise ValueError(f"Unknown joint type: {type}")
        self._joints.append(joint)
        self._joint_peak_forces[joint] = 0.0
        self._joint_peak_torques[joint] = 0.0
        self._joint_damage[joint] = 0.0
        self._joint_is_ground[joint] = is_ground
        self._joint_anchor[joint] = (anchor_x, anchor_y)
        if is_ground:
            self._ground_anchor_count += 1
            self._ground_anchor_x.append(anchor_x)
        return joint

    def get_structure_mass(self):
        return sum(b.mass for b in self._bodies)

    def set_material_properties(self, body, restitution=0.2):
        for fixture in body.fixtures:
            fixture.restitution = float(restitution)

    def get_build_zone(self):
        """Return (x_min, x_max, y_min, y_max) for build zone."""
        return (self.BUILD_ZONE_X_MIN, self.BUILD_ZONE_X_MAX, self.BUILD_ZONE_Y_MIN, self.BUILD_ZONE_Y_MAX)

    def get_structure_mass_limit(self):
        """Maximum allowed structure mass (kg)."""
        return self._max_structure_mass

    def get_terrain_bounds(self):
        return {
            "ground_y": self._ground_y,
            "build_zone": {
                "x": [self.BUILD_ZONE_X_MIN, self.BUILD_ZONE_X_MAX],
                "y": [self.BUILD_ZONE_Y_MIN, self.BUILD_ZONE_Y_MAX],
            },
            "max_structure_mass": self._max_structure_mass,
            "forbidden_zone": [self._forbidden_zone_x_lo, self._forbidden_zone_x_hi],
            "allowed_anchor_zone": [self._allowed_anchor_x_lo, self._allowed_anchor_x_hi],
            "max_ground_anchors": self._max_ground_anchors,
        }
