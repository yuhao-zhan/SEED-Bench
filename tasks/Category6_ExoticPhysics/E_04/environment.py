"""
E-04: Variable Mass task environment module.
Beam mass varies with multiple frequency components; support undergoes environmental vibration;
joints fatigue over time (effective strength decays). Failure: structure disintegrates (joints break).
"""
import math
import Box2D
from Box2D.b2 import world, polygonShape, staticBody, dynamicBody, weldJoint, revoluteJoint

# Kinematic body type for oscillating ground
_kinematicBody = getattr(Box2D.b2, "kinematicBody", 1)


class Sandbox:
    """
    Sandbox for E-04: Variable Mass (hard).
    - Beam mass varies with multiple frequency components (discoverable via feedback).
    - Support (ground) is driven with vertical oscillation (base excitation).
    - Joint strength decays over time (fatigue); effective limits depend on cumulative load.
    """

    # Build zone and limits
    BUILD_ZONE_X_MIN = 5.0
    BUILD_ZONE_X_MAX = 15.0
    BUILD_ZONE_Y_MIN = 1.5
    BUILD_ZONE_Y_MAX = 8.0
    MAX_STRUCTURE_MASS = 400.0
    MIN_BEAM_SIZE = 0.1
    MAX_BEAM_SIZE = 4.0

    # Minimum structure complexity (enforced by evaluator)
    MIN_BEAMS = 5
    MIN_JOINTS = 6
    REQUIRE_PIVOT_JOINT = True

    # Span requirement: at least one beam center x <= SPAN_LEFT, one >= SPAN_RIGHT
    SPAN_LEFT_X = 6.0
    SPAN_RIGHT_X = 14.0

    # Mass variation: fundamental + second harmonic, with SPATIAL PHASE (phase depends on beam x)
    MASS_FREQ_1 = 0.5
    MASS_AMP_1 = 0.2
    MASS_FREQ_2 = 1.0
    MASS_AMP_2 = 0.16
    MASS_PHASE_GRADIENT = 0.4   # rad/m: phase = (x - x_min) * this

    # Base excitation: 2D (vertical + horizontal) — ground moves in ellipse
    BASE_EXCITATION_VERTICAL_AMPLITUDE = 0.06   # m
    BASE_EXCITATION_HORIZONTAL_AMPLITUDE = 0.04 # m
    BASE_EXCITATION_FREQUENCY = 0.45   # Hz

    # Nominal joint limits; fatigue decays effective limit = nominal * exp(-t/FATIGUE_TAU)
    JOINT_BREAK_FORCE = 6.0
    JOINT_BREAK_TORQUE = 10.0
    FATIGUE_TAU_SECONDS = 100.0   # stricter decay

    # Simulation length (single source of truth; prompt and main.py use this when max_steps is None)
    MAX_STEPS = 12000

    def __init__(self, *, terrain_config=None, physics_config=None):
        terrain_config = terrain_config or {}
        physics_config = physics_config or {}
        self._terrain_config = dict(terrain_config)
        self._physics_config = dict(physics_config)
        gravity = tuple(physics_config.get("gravity", (0, -10)))
        self._linear_damping = float(physics_config.get("linear_damping", 0.0))
        self._angular_damping = float(physics_config.get("angular_damping", 0.0))

        # Overridable physics (for mutated tasks); fallback to class defaults
        self.MASS_FREQ_1 = physics_config.get("mass_freq_1", self.MASS_FREQ_1)
        self.MASS_AMP_1 = physics_config.get("mass_amp_1", self.MASS_AMP_1)
        self.MASS_FREQ_2 = physics_config.get("mass_freq_2", self.MASS_FREQ_2)
        self.MASS_AMP_2 = physics_config.get("mass_amp_2", self.MASS_AMP_2)
        self.MASS_PHASE_GRADIENT = physics_config.get("mass_phase_gradient", self.MASS_PHASE_GRADIENT)
        self.BASE_EXCITATION_VERTICAL_AMPLITUDE = physics_config.get(
            "base_excitation_vertical_amplitude", self.BASE_EXCITATION_VERTICAL_AMPLITUDE
        )
        self.BASE_EXCITATION_HORIZONTAL_AMPLITUDE = physics_config.get(
            "base_excitation_horizontal_amplitude", self.BASE_EXCITATION_HORIZONTAL_AMPLITUDE
        )
        self.BASE_EXCITATION_FREQUENCY = physics_config.get(
            "base_excitation_frequency", self.BASE_EXCITATION_FREQUENCY
        )
        # Force limits and fatigue
        self.JOINT_BREAK_FORCE = physics_config.get("joint_break_force", self.JOINT_BREAK_FORCE)
        self.JOINT_BREAK_TORQUE = physics_config.get("joint_break_torque", self.JOINT_BREAK_TORQUE)
        self.FATIGUE_TAU_SECONDS = physics_config.get("fatigue_tau_seconds", self.FATIGUE_TAU_SECONDS)
        self.WIND_PRESSURE = float(physics_config.get("wind_pressure", 0.0))

        # Instance-specific constraints (overridable via terrain_config)
        self._build_zone_x_min = float(terrain_config.get("build_zone_x_min", self.BUILD_ZONE_X_MIN))
        self._build_zone_x_max = float(terrain_config.get("build_zone_x_max", self.BUILD_ZONE_X_MAX))
        self._build_zone_y_min = float(terrain_config.get("build_zone_y_min", self.BUILD_ZONE_Y_MIN))
        self._build_zone_y_max = float(terrain_config.get("build_zone_y_max", self.BUILD_ZONE_Y_MAX))
        self._max_structure_mass = float(terrain_config.get("max_structure_mass", self.MAX_STRUCTURE_MASS))
        self._span_left_x = float(terrain_config.get("span_left_x", self.SPAN_LEFT_X))
        self._span_right_x = float(terrain_config.get("span_right_x", self.SPAN_RIGHT_X))
        self._min_beams = int(terrain_config.get("min_beams", self.MIN_BEAMS))
        self._min_joints = int(terrain_config.get("min_joints", self.MIN_JOINTS))

        self._world = world(gravity=gravity, doSleep=True)
        self._bodies = []
        self._joints = []
        self._terrain_bodies = {}
        self._time = 0.0
        self._joint_peak_forces = {}
        self._joint_peak_torques = {}
        self._joint_types = {}  # joint -> "rigid" | "pivot"

        self.world = self._world
        self.bodies = self._bodies
        self.joints = self._joints

        self._create_terrain(terrain_config)

    def _create_terrain(self, terrain_config: dict):
        """Ground: kinematic body so we can drive it (base excitation)."""
        ground_length = 40.0
        ground_height = 1.0
        self._ground_y = ground_height
        self._ground_y_base = ground_height / 2.0  # center of box
        body_def = Box2D.b2BodyDef()
        body_def.type = _kinematicBody
        body_def.position = (ground_length / 2, self._ground_y_base)
        ground = self._world.CreateBody(body_def)
        ground.CreateFixture(Box2D.b2FixtureDef(
            shape=polygonShape(box=(ground_length / 2, ground_height / 2)),
            friction=0.6,
        ))
        self._terrain_bodies["ground"] = ground

    def _mass_factor_for_phase(self, t, phase):
        """Multi-component mass variation with spatial phase (phase in rad)."""
        return (1.0
                + self.MASS_AMP_1 * math.sin(2.0 * math.pi * self.MASS_FREQ_1 * t + phase)
                + self.MASS_AMP_2 * math.sin(2.0 * math.pi * self.MASS_FREQ_2 * t + 2.0 * phase))

    def _effective_joint_force_limit(self, t):
        """Fatigue: effective force limit decays over time."""
        return self.JOINT_BREAK_FORCE * math.exp(-t / self.FATIGUE_TAU_SECONDS)

    def _effective_joint_torque_limit(self, t):
        """Fatigue: effective torque limit decays over time."""
        return self.JOINT_BREAK_TORQUE * math.exp(-t / self.FATIGUE_TAU_SECONDS)

    def step(self, time_step):
        """Update mass (per-body phase), drive ground (2D), step physics, then check joint breaking."""
        t = self._time
        # Mass variation: per-body phase (spatial phase gradient)
        for body in self._bodies:
            base = getattr(body, "_base_density", None)
            phase = getattr(body, "_mass_phase", 0.0)
            if base is not None:
                factor = self._mass_factor_for_phase(t, phase)
                for fixture in body.fixtures:
                    fixture.density = base * factor
                body.ResetMassData()
            
            # Apply constant lateral wind force based on area
            if self.WIND_PRESSURE != 0.0:
                area = getattr(body, "_area", 0.1)
                force_x = self.WIND_PRESSURE * area
                body.ApplyForceToCenter((force_x, 0.0), True)

        # Base excitation: 2D (horizontal + vertical) — ground velocity
        ground = self._terrain_bodies.get("ground")
        if ground is not None:
            omega = 2.0 * math.pi * self.BASE_EXCITATION_FREQUENCY
            vx = self.BASE_EXCITATION_HORIZONTAL_AMPLITUDE * omega * math.cos(omega * t)
            vy = self.BASE_EXCITATION_VERTICAL_AMPLITUDE * omega * math.sin(omega * t)
            ground.linearVelocity = (vx, vy)
        self._time += time_step
        try:
            self._world.Step(time_step, 10, 10)
        except Exception as e:
            print(f"CRASH at step {t}: {e}")
            raise e

        # Joint breaking with time-dependent (fatigue) limits
        force_limit = self._effective_joint_force_limit(self._time)
        torque_limit = self._effective_joint_torque_limit(self._time)
        joints_to_remove = []
        for joint in list(self._joints):
            try:
                if hasattr(joint, "GetReactionForce"):
                    force = joint.GetReactionForce(1.0 / 60.0)
                    force_mag = math.sqrt(force.x**2 + force.y**2)
                    self._joint_peak_forces[joint] = max(
                        self._joint_peak_forces.get(joint, 0.0), force_mag
                    )
                    torque_mag = 0.0
                    if hasattr(joint, "GetReactionTorque"):
                        torque_mag = abs(joint.GetReactionTorque(1.0 / 60.0))
                    self._joint_peak_torques[joint] = max(
                        self._joint_peak_torques.get(joint, 0.0), torque_mag
                    )
                    if (self._joint_peak_forces[joint] > force_limit or
                            self._joint_peak_torques[joint] > torque_limit):
                        joints_to_remove.append(joint)
            except Exception:
                continue
        for joint in joints_to_remove:
            try:
                self._world.DestroyJoint(joint)
                self._joints.remove(joint)
                self._joint_peak_forces.pop(joint, None)
                self._joint_peak_torques.pop(joint, None)
                self._joint_types.pop(joint, None)
            except Exception:
                pass

    def add_beam(self, x, y, width, height, angle=0, density=1.0):
        """Add a beam; mass varies over time with a phase that depends on position (not revealed)."""
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
        body._base_density = density
        body._mass_phase = (x - self._build_zone_x_min) * self.MASS_PHASE_GRADIENT
        body._area = width * height
        body.linearDamping = self._linear_damping
        body.angularDamping = self._angular_damping
        self._bodies.append(body)
        return body

    def add_joint(self, body_a, body_b, anchor_point, type="rigid"):
        """Add a joint. body_b=None anchors to ground. type: 'rigid' (weld) or 'pivot' (revolute)."""
        if body_a is None:
            raise ValueError("add_joint: body_a cannot be None.")
        anchor_x, anchor_y = anchor_point[0], anchor_point[1]
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
        self._joint_types[joint] = type
        return joint

    def get_structure_mass(self):
        """Total mass of all agent-created bodies (instantaneous, mass varies)."""
        total = 0.0
        for body in self._bodies:
            total += body.mass
        return total

    def get_max_joint_reaction_force(self):
        """Max reaction force (N) seen at any joint so far. For feedback/debugging."""
        if not self._joint_peak_forces:
            return 0.0
        return max(self._joint_peak_forces.values())

    def get_max_joint_reaction_torque(self):
        """Max reaction torque (N·m) seen at any joint so far. For feedback/debugging."""
        if not self._joint_peak_torques:
            return 0.0
        return max(self._joint_peak_torques.values())

    def get_effective_joint_force_limit(self):
        """Current effective force limit (N) after fatigue. For feedback."""
        return self._effective_joint_force_limit(self._time)

    def get_effective_joint_torque_limit(self):
        """Current effective torque limit (N·m) after fatigue. For feedback."""
        return self._effective_joint_torque_limit(self._time)

    def set_material_properties(self, body, restitution=0.2):
        """Set restitution for a body."""
        for fixture in body.fixtures:
            fixture.restitution = float(restitution)

    def get_ground_y_top(self):
        """Top surface y of ground (meters). Use for anchor placement."""
        return self._ground_y

    def get_build_zone(self):
        """Return (x_min, x_max, y_min, y_max) for build zone."""
        return (self._build_zone_x_min, self._build_zone_x_max, self._build_zone_y_min, self._build_zone_y_max)

    def get_span_bounds(self):
        """Return (left_x, right_x). Structure must span: at least one beam center x <= left_x, one >= right_x."""
        return (self._span_left_x, self._span_right_x)

    def get_structure_mass_limit(self):
        """Maximum allowed structure mass (kg)."""
        return self._max_structure_mass

    def get_min_beams(self):
        """Minimum number of beams required."""
        return self._min_beams

    def get_min_joints(self):
        """Minimum number of joints required."""
        return self._min_joints

    def get_terrain_bounds(self):
        """For evaluator/renderer."""
        return {
            "ground_y": self._ground_y,
            "build_zone": {
                "x": [self._build_zone_x_min, self._build_zone_x_max],
                "y": [self._build_zone_y_min, self._build_zone_y_max],
            },
            "max_structure_mass": self._max_structure_mass,
            "span_left_x": self._span_left_x,
            "span_right_x": self._span_right_x,
            "min_beams": self._min_beams,
            "min_joints": self._min_joints,
        }
