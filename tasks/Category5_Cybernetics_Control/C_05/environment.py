"""
C-05: Tight Temporal Chain + Timed Gate + State-Dependent Triggers (essentially hard).
Trigger A -> B -> C in order. Each zone only accepts stay-steps if the agent was in the
*previous* zone within a short sliding window (temporal chain). Barrier opens N steps after A.
C also requires recent high path (max y). No new regions—hardness from temporal coupling.
Discovery: timing, sequence tightness, and path conditions via interaction and feedback.
"""
import math
import Box2D

# Default integration dt; must match ``common.simulator.TIME_STEP`` (TARGET_FPS = 60).
DEFAULT_SIMULATION_TIME_STEP = 1.0 / 60.0
from Box2D.b2 import (
    world,
    polygonShape,
    circleShape,
    staticBody,
    dynamicBody,
)

REQUIRED_ORDER = ("A", "B", "C")
TRIGGER_STAY_STEPS = 25
SPEED_CAP_INSIDE = 0.5
REPULSION_MAG = 22.0
# Evaluator/feedback: treat repulsion at or above this magnitude as “strong” (curriculum uses ≥40)
REPULSION_STRONG_THRESHOLD = 40.0
REPULSION_RANGE = 1.5
REPULSION_TANGENTIAL_MAG = 0.0  # default radial-only; overridden via physics_config
COOLDOWN_STEPS = 55
# Barrier opens this many steps AFTER A is triggered (not immediately) — must discover via waiting/failure
BARRIER_DELAY_STEPS = 70
BARRIER_X = 4.5
BARRIER_HALFW = 0.08
BARRIER_LO = 0.0
BARRIER_HI = 4.0
WIND_AMP = 0.0  # Baseline: no wind; may be overridden via physics_config for evaluation variants
WIND_PERIOD = 200
# Zone C only counts stay-steps if agent's max y over last C_HIGH_HISTORY steps >= C_REQUIRED_MAX_Y (must come from elevated path)
C_HIGH_HISTORY = 150
C_REQUIRED_MAX_Y = 2.9
# Temporal chain: B only counts if agent was in A within last RECENT_A_FOR_B steps; C only if in B within RECENT_B_FOR_C
# Barrier opens 70 steps after A; agent leaves A ~25 steps after trigger, so needs RECENT_A_FOR_B - 70 steps to reach B
RECENT_A_FOR_B = 160
RECENT_B_FOR_C = 400  # B→C path long (ramp down + flat); window must allow reference to reach C
# Max applied-force magnitude (per step) while in zone; above this resets dwell (must be < ~70.7 with ±50 axis cap)
FORCE_LIMIT_INSIDE = 60.0

# Zone centers and half-size (cx, cy, hw, hh): A ground, B elevated, C ground
ZONE_A = (2.0, 2.0, 0.5, 0.5)
ZONE_B = (4.95, 3.2, 0.7, 0.4)  # x [4.25, 5.65], y [2.8, 3.6] so ramp approach can trigger
ZONE_C = (8.0, 2.0, 0.5, 0.5)

# Defaults for terrain_config / physics_config (single source for prompt sync in stages.py)
SPAWN_X = 0.5
SPAWN_Y = 1.95
AGENT_RADIUS = 0.2
AGENT_MASS = 3.0
MAX_AGENT_FORCE_PER_AXIS = 50.0
GROUND_FRICTION_DEFAULT = 0.5
RAMP_FRICTION_DEFAULT = 0.12
PLATFORM_FRICTION_DEFAULT = 0.45
AGENT_FIXTURE_FRICTION = 0.4
BARRIER_FIXTURE_FRICTION = 0.3
# Dynamic agent body damping (Box2D); single source for prompt.py
DEFAULT_LINEAR_DAMPING = 0.3
DEFAULT_ANGULAR_DAMPING = 0.3


class Sandbox:
    """
    C-05: Tight Temporal Chain + Timed Gate + State-Dependent Triggers.
    A -> B -> C in order. B only counts stay-steps if agent was in A within
    RECENT_A_FOR_B steps; C only if in B within RECENT_B_FOR_C and recent max y >= threshold.
    Barrier opens BARRIER_DELAY_STEPS after A. Stay-to-trigger with speed cap; cooldown.
    """

    def __init__(self, *, terrain_config=None, physics_config=None):
        terrain_config = terrain_config or {}
        physics_config = physics_config or {}

        self._terrain_config = dict(terrain_config)
        self._physics_config = dict(physics_config)
        gravity = tuple(physics_config.get("gravity", (0, -10)))
        self._default_linear_damping = float(
            physics_config.get("linear_damping", DEFAULT_LINEAR_DAMPING)
        )
        self._default_angular_damping = float(
            physics_config.get("angular_damping", DEFAULT_ANGULAR_DAMPING)
        )

        # Allow overriding key timing/hidden parameters via physics_config for mutated tasks
        self._trigger_stay_steps = int(physics_config.get("trigger_stay_steps", TRIGGER_STAY_STEPS))
        self._speed_cap_inside = float(physics_config.get("speed_cap_inside", SPEED_CAP_INSIDE))
        self._repulsion_mag = float(physics_config.get("repulsion_mag", REPULSION_MAG))
        self._repulsion_range = float(physics_config.get("repulsion_range", REPULSION_RANGE))
        self._cooldown_steps = int(physics_config.get("cooldown_steps", COOLDOWN_STEPS))
        self._barrier_delay_steps = int(physics_config.get("barrier_delay_steps", BARRIER_DELAY_STEPS))
        self._wind_amp = float(physics_config.get("wind_amp", WIND_AMP))
        self._wind_period = int(physics_config.get("wind_period", WIND_PERIOD))
        self._c_high_history = int(physics_config.get("c_high_history", C_HIGH_HISTORY))
        self._c_required_max_y = float(physics_config.get("c_required_max_y", C_REQUIRED_MAX_Y))
        self._recent_a_for_b = int(physics_config.get("recent_a_for_b", RECENT_A_FOR_B))
        self._recent_b_for_c = int(physics_config.get("recent_b_for_c", RECENT_B_FOR_C))

        # New mutation parameters
        self._repulsion_tangential_mag = float(
            physics_config.get("repulsion_tangential_mag", REPULSION_TANGENTIAL_MAG)
        )
        self._force_limit_inside = float(physics_config.get("force_limit_inside", FORCE_LIMIT_INSIDE))
        self._max_agent_force = float(
            physics_config.get("max_agent_force_per_axis", MAX_AGENT_FORCE_PER_AXIS)
        )
        self._barrier_x = float(terrain_config.get("barrier_x", BARRIER_X))

        self._world = world(gravity=gravity, doSleep=True)
        self._bodies = []
        self._joints = []
        self._terrain_bodies = {}

        self.world = self._world
        self.bodies = self._bodies
        self.joints = self._joints

        self._zones = {"A": ZONE_A, "B": ZONE_B, "C": ZONE_C}
        self._triggered_order = []
        self._wrong_order = False
        self._trigger_step = {}
        self._zone_contact_steps = {"A": 0, "B": 0, "C": 0}
        self._last_zone = None

        self._agent_radius = float(terrain_config.get("agent_radius", AGENT_RADIUS))
        self._agent_mass = float(terrain_config.get("agent_mass", AGENT_MASS))
        self._spawn_x = float(terrain_config.get("spawn_x", SPAWN_X))
        self._spawn_y = float(terrain_config.get("spawn_y", SPAWN_Y))

        # Friction overrides
        self._ground_friction = float(
            terrain_config.get("ground_friction", GROUND_FRICTION_DEFAULT)
        )
        self._ramp_friction = float(terrain_config.get("ramp_friction", RAMP_FRICTION_DEFAULT))
        self._platform_friction = float(
            terrain_config.get("platform_friction", PLATFORM_FRICTION_DEFAULT)
        )
        self._agent_fixture_friction = float(
            terrain_config.get("agent_fixture_friction", AGENT_FIXTURE_FRICTION)
        )
        self._barrier_fixture_friction = float(
            terrain_config.get("barrier_fixture_friction", BARRIER_FIXTURE_FRICTION)
        )

        self._step_count = 0
        self._barrier_remove_at_step = None  # barrier opens at this step (set when A triggers)
        self._agent_y_history = []  # last C_HIGH_HISTORY y values for C's "high path" check
        self._last_step_in_A = -9999  # temporal chain: B only counts if recently in A
        self._last_step_in_B = -9999  # temporal chain: C only counts if recently in B
        self._create_ground(terrain_config)
        self._create_barrier()
        self._create_agent(terrain_config)

        self._force_x = 0.0
        self._force_y = 0.0

    def _create_ground(self, terrain_config: dict):
        """Ground: flat 0-4 at y=2, ramp up 4-5 to platform at y=3.5, platform 5-6, ramp down 6-7, flat 7-12. Ramps use low friction (ramp_friction)."""
        ground_y = 2.0
        h = 0.25  # half-height of segment
        ground_segments = self._terrain_bodies.setdefault("ground_segments", [])

        # Flat segment [0, 4] at y=2
        body_flat_left = self._world.CreateStaticBody(
            position=(2.0, ground_y - h),
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(2.0, h)),
                friction=self._ground_friction,
                restitution=0.0,
            ),
        )
        ground_segments.append(body_flat_left)

        # Ramp up: top edge (4, 2) to (5.5, 3.5) so it meets platform; body center (4.75, 2.75)
        ramp1_verts = [(-0.75, -1.25), (0.75, 0.25), (0.75, 0.75), (-0.75, -0.75)]
        body_ramp1 = self._world.CreateStaticBody(
            position=(4.75, 2.75),
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(vertices=ramp1_verts),
                friction=self._ramp_friction,
                restitution=0.0,
            ),
        )
        ground_segments.append(body_ramp1)

        # Platform [5, 6]: top at y=3.5, bottom at 3 so it meets ramp at x=5 (center 5.5, 3.25)
        platform_hh = 0.25
        body_platform = self._world.CreateStaticBody(
            position=(5.5, 3.25),
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(0.5, platform_hh)),
                friction=self._platform_friction,
                restitution=0.0,
            ),
        )
        ground_segments.append(body_platform)

        # Ramp down: top edge (6, 3.5) to (7, 2). Body center (6.5, 2.75). Local CCW: left-bottom, left-top, right-top, right-bottom
        ramp2_verts = [(-0.5, 0.5), (-0.5, 0.75), (0.5, -0.75), (0.5, -1.0)]
        body_ramp2 = self._world.CreateStaticBody(
            position=(6.5, 2.75),
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(vertices=ramp2_verts),
                friction=self._ramp_friction,
                restitution=0.0,
            ),
        )
        ground_segments.append(body_ramp2)

        # Flat [7, 12] at y=2
        body_flat_right = self._world.CreateStaticBody(
            position=(9.5, ground_y - h),
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(2.5, h)),
                friction=self._ground_friction,
                restitution=0.0,
            ),
        )
        ground_segments.append(body_flat_right)

        self._ground_y_top = ground_y


    def _create_barrier(self):
        """Barrier at x=self._barrier_x blocking passage until removed after A triggers (see BARRIER_DELAY_STEPS)."""
        cx = self._barrier_x
        cy = (BARRIER_LO + BARRIER_HI) / 2
        hh = (BARRIER_HI - BARRIER_LO) / 2
        self._barrier_body = self._world.CreateStaticBody(
            position=(cx, cy),
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(BARRIER_HALFW, hh)),
                friction=self._barrier_fixture_friction,
                restitution=0.0,
            ),
        )
        self._terrain_bodies["barrier"] = self._barrier_body

    def _schedule_barrier_removal(self):
        """Barrier will be removed at step = current + BARRIER_DELAY_STEPS (timed gate)."""
        if self._barrier_remove_at_step is None:
            self._barrier_remove_at_step = self._step_count + int(self._barrier_delay_steps)

    def _create_agent(self, terrain_config: dict):
        """Create agent (dynamic circle)."""
        r = self._agent_radius
        density = self._agent_mass / (math.pi * r * r)
        agent = self._world.CreateDynamicBody(
            position=(self._spawn_x, self._spawn_y),
            fixtures=Box2D.b2FixtureDef(
                shape=circleShape(radius=r),
                density=density,
                friction=self._agent_fixture_friction,
                restitution=0.0,
            ),
        )
        agent.linearDamping = self._default_linear_damping
        agent.angularDamping = self._default_angular_damping
        self._terrain_bodies["agent"] = agent

    def _point_in_zone(self, x, y, zone_name):
        cx, cy, hw, hh = self._zones[zone_name]
        return (cx - hw <= x <= cx + hw) and (cy - hh <= y <= cy + hh)

    def _zone_center(self, zone_name):
        cx, cy, _, _ = self._zones[zone_name]
        return (cx, cy)

    def _update_sequence(self):
        """Stay-to-trigger with speed cap. Temporal chain: B/C only count if recently in A/B. Barrier when A triggered."""
        agent = self._terrain_bodies.get("agent")
        if agent is None:
            return
        x, y = agent.position.x, agent.position.y

        next_required = REQUIRED_ORDER[len(self._triggered_order)] if len(self._triggered_order) < 3 else None
        current_zone = None
        for name in REQUIRED_ORDER:
            if self._point_in_zone(x, y, name):
                current_zone = name
                break

        # Update "last step in zone" for temporal chain (B/C only count if recently in previous zone)
        if current_zone == "A":
            self._last_step_in_A = self._step_count
        if current_zone == "B":
            self._last_step_in_B = self._step_count

        if self._last_zone != current_zone:
            for z in REQUIRED_ORDER:
                self._zone_contact_steps[z] = 0
        self._last_zone = current_zone

        if current_zone is None:
            return

        if current_zone in self._triggered_order:
            return

        if current_zone != next_required:
            self._wrong_order = True
            return

        # Cooldown after previous trigger
        prev_zone = REQUIRED_ORDER[len(self._triggered_order) - 1] if self._triggered_order else None
        if prev_zone and prev_zone in self._trigger_step:
            steps_since = self._step_count - self._trigger_step[prev_zone]
            if steps_since < int(self._cooldown_steps):
                return

        vx = agent.linearVelocity.x
        vy = agent.linearVelocity.y
        speed = math.sqrt(vx * vx + vy * vy)
        if speed > float(self._speed_cap_inside):
            self._zone_contact_steps[current_zone] = 0
            return

        # Progress resets if applying too much force while in zone
        applied_f_mag = math.sqrt(self._force_x**2 + self._force_y**2)
        if applied_f_mag > float(self._force_limit_inside):
            self._zone_contact_steps[current_zone] = 0
            return

        # Temporal chain: B only counts if agent was in A within last recent_a_for_b steps
        if current_zone == "B":
            if self._step_count - self._last_step_in_A > int(self._recent_a_for_b):
                return  # too long since A; B won't accept
        # Temporal chain + path: C only counts if in B recently AND recent max y >= threshold
        if current_zone == "C":
            if self._step_count - self._last_step_in_B > int(self._recent_b_for_c):
                return  # too long since B; C won't accept
            # Use available history if window is not yet full
            ch = int(self._c_high_history)
            if not self._agent_y_history:
                return
            relevant_history = self._agent_y_history[-ch:]
            max_recent_y = max(relevant_history)
            if max_recent_y < float(self._c_required_max_y):
                return  # high-path condition not satisfied

        self._zone_contact_steps[current_zone] += 1
        if self._zone_contact_steps[current_zone] >= int(self._trigger_stay_steps):
            self._triggered_order.append(current_zone)
            self._trigger_step[current_zone] = self._step_count
            self._zone_contact_steps[current_zone] = 0
            if current_zone == "A":
                self._schedule_barrier_removal()

    def _repulsion_force(self, x, y):
        """Repulsion from B until A triggered, from C until B triggered. Supports tangential force."""
        fx, fy = 0.0, 0.0
        
        rep_mag = float(self._repulsion_mag)
        rep_range = float(self._repulsion_range)
        t_mag = float(self._repulsion_tangential_mag)

        # Zone B repulsion
        if "A" not in self._triggered_order:
            bx, by = self._zone_center("B")
            dist = math.sqrt((x - bx) ** 2 + (y - by) ** 2)
            if dist < rep_range and dist > 1e-6:
                strength = rep_mag * (1.0 - dist / rep_range)
                ux, uy = (x - bx) / dist, (y - by) / dist
                fx += strength * ux
                fy += strength * uy
                if t_mag != 0:
                    t_strength = t_mag * (1.0 - dist / rep_range)
                    fx += t_strength * (-uy)
                    fy += t_strength * ux

        # Zone C repulsion
        if "B" not in self._triggered_order:
            cx, cy = self._zone_center("C")
            dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
            if dist < rep_range and dist > 1e-6:
                strength = rep_mag * (1.0 - dist / rep_range)
                ux, uy = (x - cx) / dist, (y - cy) / dist
                fx += strength * ux
                fy += strength * uy
                if t_mag != 0:
                    t_strength = t_mag * (1.0 - dist / rep_range)
                    fx += t_strength * (-uy)
                    fy += t_strength * ux

        return (fx, fy)

    def get_agent_position(self):
        agent = self._terrain_bodies.get("agent")
        if agent is None:
            return (0.0, 0.0)
        return (agent.position.x, agent.position.y)

    def get_agent_velocity(self):
        agent = self._terrain_bodies.get("agent")
        if agent is None:
            return (0.0, 0.0)
        return (agent.linearVelocity.x, agent.linearVelocity.y)

    def get_next_required_switch(self):
        if self._wrong_order:
            return None
        idx = len(self._triggered_order)
        if idx >= len(REQUIRED_ORDER):
            return None
        return REQUIRED_ORDER[idx]

    def get_triggered_switches(self):
        return list(self._triggered_order)

    def get_sequence_correct(self):
        return (
            not self._wrong_order
            and self._triggered_order == list(REQUIRED_ORDER)
        )

    def get_steps_in_current_zone(self):
        next_req = self.get_next_required_switch()
        if next_req is None:
            return 0
        return self._zone_contact_steps.get(next_req, 0)

    def get_steps_required_to_trigger(self):
        return int(self._trigger_stay_steps)

    def get_cooldown_remaining(self):
        if not self._triggered_order:
            return 0
        prev = self._triggered_order[-1]
        if prev not in self._trigger_step:
            return 0
        elapsed = self._step_count - self._trigger_step[prev]
        return max(0, int(self._cooldown_steps) - elapsed)

    def get_barrier_delay_steps(self):
        return int(self._barrier_delay_steps)

    def get_barrier_x(self):
        return float(self._barrier_x)

    def apply_agent_force(self, force_x, force_y):
        max_f = float(self._max_agent_force)
        self._force_x = max(-max_f, min(max_f, float(force_x)))
        self._force_y = max(-max_f, min(max_f, float(force_y)))

    def _wind_force(self):
        phase = 2.0 * math.pi * self._step_count / max(1, int(self._wind_period))
        return (float(self._wind_amp) * math.sin(phase), 0.0)

    def step(self, time_step=None):
        """Advance physics by one simulation step.

        If ``time_step`` is omitted, uses ``common.simulator.TIME_STEP`` so behavior matches
        the dt stated in the task prompt.
        """
        dt = float(DEFAULT_SIMULATION_TIME_STEP if time_step is None else time_step)
        # Timed barrier: remove only when step >= barrier_remove_at_step
        if self._barrier_remove_at_step is not None and self._step_count >= self._barrier_remove_at_step:
            self._barrier_remove_at_step = None
            if "barrier" in self._terrain_bodies:
                body = self._terrain_bodies.pop("barrier", None)
                if body is not None and body.world is not None:
                    self._world.DestroyBody(body)
        self._step_count += 1
        # Record agent y for C's "high path" requirement
        agent = self._terrain_bodies.get("agent")
        if agent is not None:
            self._agent_y_history.append(agent.position.y)
            if len(self._agent_y_history) > int(self._c_high_history):
                self._agent_y_history.pop(0)
        self._update_sequence()
        agent = self._terrain_bodies.get("agent")
        if agent is not None:
            x, y = agent.position.x, agent.position.y
            wx, wy = self._wind_force()
            rx, ry = self._repulsion_force(x, y)
            total_fx = self._force_x + wx + rx
            total_fy = self._force_y + wy + ry
            if total_fx != 0.0 or total_fy != 0.0:
                agent.ApplyForceToCenter((total_fx, total_fy), True)
            self._force_x = 0.0
            self._force_y = 0.0
        self._world.Step(dt, 10, 10)

    def get_terrain_bounds(self):
        """Snapshot of task-relevant bounds, timing, repulsion, and friction (for tools and debugging).

        Includes repulsion and friction because those are stated in the task prompt. Omits gravity,
        linear/angular damping, and wind amplitude/period; read those from ``sandbox.world`` or
        instance fields when debugging.
        """
        return {
            "zones": dict(self._zones),
            "required_order": list(REQUIRED_ORDER),
            "trigger_stay_steps": int(self._trigger_stay_steps),
            "speed_cap_inside": float(self._speed_cap_inside),
            "cooldown_steps": int(self._cooldown_steps),
            "barrier_delay_steps": int(self._barrier_delay_steps),
            "barrier_x": float(self._barrier_x),
            "recent_a_for_b": int(self._recent_a_for_b),
            "recent_b_for_c": int(self._recent_b_for_c),
            "c_high_history": int(self._c_high_history),
            "c_required_max_y": float(self._c_required_max_y),
            "force_limit_inside": float(self._force_limit_inside),
            "repulsion_mag": float(self._repulsion_mag),
            "repulsion_range": float(self._repulsion_range),
            "repulsion_tangential_mag": float(self._repulsion_tangential_mag),
            "max_agent_force_per_axis": float(self._max_agent_force),
            "ground_friction": float(self._ground_friction),
            "ramp_friction": float(self._ramp_friction),
            "platform_friction": float(self._platform_friction),
            "agent_fixture_friction": float(self._agent_fixture_friction),
            "barrier_fixture_friction": float(self._barrier_fixture_friction),
        }

    def get_agent_body(self):
        return self._terrain_bodies.get("agent")

    def get_wrong_order(self):
        return self._wrong_order
