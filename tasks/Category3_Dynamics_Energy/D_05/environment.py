"""
D-05: The Hammer task environment module
Shell (breakable), ground, build zone for hammer. Mechanics: kinetic energy, moment of inertia.
Mutation: target hardness (break threshold), hammer head mass. Failure: shell not broken.
"""
import math
import Box2D
from Box2D.b2 import (
    world,
    polygonShape,
    staticBody,
    dynamicBody,
    revoluteJoint,
    weldJoint,
)


class Sandbox:
    # Collision filter: only agent (hammer) can break the shell; pendulum must not hit shell
    _CAT_SHELL = 0x0001
    _CAT_AGENT = 0x0002
    _CAT_PENDULUM = 0x0004
    _CAT_GROUND = 0x0008
    _CAT_SHIELD = 0x0010
    _CAT_GATE = 0x0020
    _CAT_WALL = 0x0040
    _CAT_SLOT = 0x0080  # Static slot walls — hammer must pass through the gap (thread the needle)
    _CAT_SLOT_BAR = 0x0100  # Oscillating bar INSIDE the slot — must pass when bar is away (geometry + timing)

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
        self._shell_joint = None
        self._shell_broken = False
        self._shell_break_threshold = float(terrain_config.get("shell_break_force", 5000.0))
        self._step_count = 0
        self._hammer_hit_pendulum_before_shell = False
        self._hammer_hit_gate_before_shell = False
        self._hammer_hit_gate2_before_shell = False
        self._hammer_hit_wall_before_shell = False
        self._hammer_hit_slot_wall_before_shell = False
        self._hammer_hit_slot_bar_before_shell = False
        self.world = self._world
        self.bodies = self._bodies
        self.joints = self._joints
        self._create_terrain(terrain_config)
        self._create_shell(terrain_config)
        # Static narrow slot: hammer must pass through the GAP (no timed windows — trajectory must "thread the needle")
        if terrain_config.get("slot_barrier_enabled", True):
            self._create_slot_barrier(terrain_config)
        # Oscillating bar INSIDE the slot: bar moves up/down; must pass when bar is away (geometry + timing)
        if terrain_config.get("slot_oscillating_bar_enabled", True):
            self._create_slot_oscillating_bar(terrain_config)
        # Central wall: when enabled, blocks direct path; hammer must swing OVER wall (high arc)
        if terrain_config.get("central_wall_enabled", False):
            self._create_central_wall(terrain_config)
        # Shield/gate: optional timed obstacles (disabled by default when slot is used — slot is the main challenge)
        if terrain_config.get("shield_enabled", False):
            self._create_shield(terrain_config)
        if terrain_config.get("gate_enabled", False):
            self._create_gate(terrain_config)
        if terrain_config.get("pendulum_enabled", True):
            self._create_pendulum_obstacle(terrain_config)
            # Second pendulum: when enabled, BOTH must clear
            if terrain_config.get("pendulum2_enabled", False):
                self._create_second_pendulum(terrain_config)
        self._install_contact_listener()
        self.BUILD_ZONE_X_MIN = float(terrain_config.get("build_zone_x_min", 2.0))
        self.BUILD_ZONE_X_MAX = float(terrain_config.get("build_zone_x_max", 12.0))
        self.BUILD_ZONE_Y_MIN = float(terrain_config.get("build_zone_y_min", 2.0))
        self.BUILD_ZONE_Y_MAX = float(terrain_config.get("build_zone_y_max", 8.0))
        self.MAX_STRUCTURE_MASS = float(terrain_config.get("max_structure_mass", 70.0))

    def _create_terrain(self, terrain_config: dict):
        ground_len = 35.0
        ground_h = 0.5
        gfd = Box2D.b2FixtureDef(
            shape=polygonShape(box=(ground_len / 2, ground_h / 2)),
            friction=0.6,
        )
        gfd.filter.categoryBits = self._CAT_GROUND
        gfd.filter.maskBits = self._CAT_SHELL | self._CAT_AGENT | self._CAT_PENDULUM | self._CAT_SHIELD | self._CAT_GATE | self._CAT_WALL
        ground = self._world.CreateStaticBody(
            position=(ground_len / 2, ground_h / 2),
            fixtures=gfd,
        )
        self._terrain_bodies["ground"] = ground
        self._ground_y = ground_h

    def _create_shell(self, terrain_config: dict):
        # Shell behind slot at (16, 2.6); hammer must pass through slot gap first (thread the needle)
        shell_x = float(terrain_config.get("shell_x", 16.0))
        shell_y = float(terrain_config.get("shell_y", 2.6))
        shell_w = 1.0
        shell_h = 0.8
        shell_density = 50.0
        sfd = Box2D.b2FixtureDef(
            shape=polygonShape(box=(shell_w / 2, shell_h / 2)),
            density=shell_density,
            friction=0.4,
            restitution=0.0,
        )
        sfd.filter.categoryBits = self._CAT_SHELL
        sfd.filter.maskBits = self._CAT_AGENT  # only hammer can hit shell (not pendulum)
        shell = self._world.CreateDynamicBody(
            position=(shell_x, shell_y),
            fixtures=sfd,
        )
        shell.linearDamping = self._default_linear_damping
        shell.angularDamping = self._default_angular_damping
        self._terrain_bodies["shell"] = shell
        ground = self._terrain_bodies["ground"]
        anchor_x = shell_x
        anchor_y = shell_y - shell_h / 2
        self._shell_joint = self._world.CreateWeldJoint(
            bodyA=shell,
            bodyB=ground,
            anchor=(anchor_x, anchor_y),
            collideConnected=False,
        )
        self._shell_x = shell_x
        self._shell_y = shell_y

    def _create_central_wall(self, terrain_config: dict):
        """Vertical wall (x=15, y 0.5–7.5). Direct path blocked; hammer must swing OVER wall in a high arc."""
        if not terrain_config.get("central_wall_enabled", True):
            return
        wall_x = float(terrain_config.get("wall_x", 15.0))  # x=15: arc from (12,2) over wall passes (15,13.2)
        wall_y_center = float(terrain_config.get("wall_y_center", 4.0))
        wall_half_h = float(terrain_config.get("wall_half_height", 3.5))
        wall_half_w = 0.25
        wfd = Box2D.b2FixtureDef(
            shape=polygonShape(box=(wall_half_w, wall_half_h)),
            friction=0.6,
        )
        wfd.filter.categoryBits = self._CAT_WALL
        wfd.filter.maskBits = self._CAT_AGENT
        wall = self._world.CreateStaticBody(
            position=(wall_x, wall_y_center),
            fixtures=wfd,
        )
        self._terrain_bodies["central_wall"] = wall

    def _create_slot_barrier(self, terrain_config: dict):
        """Static wall with a VERY narrow vertical GAP at x=slot_x. With any single constant angular velocity
        the head's vertical motion per step exceeds the gap — MUST use two-phase control (fast then SLOW through slot)."""
        slot_x = float(terrain_config.get("slot_x", 15.0))
        # Gap for head (center ~2.89 at x=15); single constant omega hits wall or bar — two-phase passes
        gap_y_low = float(terrain_config.get("slot_gap_y_low", 1.85))
        gap_y_high = float(terrain_config.get("slot_gap_y_high", 3.35))
        wall_w = 0.12
        # Left wall: below the gap (y from ground to gap_y_low)
        left_center_y = (0.5 + gap_y_low) / 2
        left_h = (gap_y_low - 0.5) / 2
        sfd = Box2D.b2FixtureDef(
            shape=polygonShape(box=(wall_w / 2, left_h)),
            friction=0.6,
        )
        sfd.filter.categoryBits = self._CAT_SLOT
        sfd.filter.maskBits = self._CAT_AGENT
        slot_left = self._world.CreateStaticBody(
            position=(slot_x - wall_w / 2, left_center_y),
            fixtures=sfd,
        )
        self._terrain_bodies["slot_left"] = slot_left
        # Right wall: above the gap (y from gap_y_high upward)
        right_center_y = (gap_y_high + 6.0) / 2
        right_h = (6.0 - gap_y_high) / 2
        sfd2 = Box2D.b2FixtureDef(
            shape=polygonShape(box=(wall_w / 2, right_h)),
            friction=0.6,
        )
        sfd2.filter.categoryBits = self._CAT_SLOT
        sfd2.filter.maskBits = self._CAT_AGENT
        slot_right = self._world.CreateStaticBody(
            position=(slot_x + wall_w / 2, right_center_y),
            fixtures=sfd2,
        )
        self._terrain_bodies["slot_right"] = slot_right

    def _create_slot_oscillating_bar(self, terrain_config: dict):
        """Horizontal bar that oscillates VERTICALLY inside the slot gap. Hammer must pass when bar is away (geometry + timing)."""
        slot_x = float(terrain_config.get("slot_x", 15.0))
        bar_y_center = float(terrain_config.get("slot_bar_y_center", 2.6))
        bar_half_w = float(terrain_config.get("slot_bar_half_width", 0.25))
        bar_half_h = float(terrain_config.get("slot_bar_half_height", 0.1))
        self._slot_bar_x = slot_x
        self._slot_bar_y_center = bar_y_center
        self._slot_bar_amplitude = float(terrain_config.get("slot_bar_amplitude", 0.35))
        # LATE safe window: bar at bottom only at step ~409; single-omega passes at ~85 → bar blocks. Ref must WAIT then time swing.
        self._slot_bar_omega = float(terrain_config.get("slot_bar_omega", 0.0115))
        ffd = Box2D.b2FixtureDef(
            shape=polygonShape(box=(bar_half_w, bar_half_h)),
            friction=0.5,
        )
        ffd.filter.categoryBits = self._CAT_SLOT_BAR
        ffd.filter.maskBits = self._CAT_AGENT
        bar = self._world.CreateDynamicBody(
            position=(slot_x, bar_y_center),
            fixtures=ffd,
        )
        try:
            bar.type = getattr(Box2D.b2, "kinematicBody", 1)
        except Exception:
            pass
        self._terrain_bodies["slot_bar"] = bar

    def _create_shield(self, terrain_config: dict):
        """Shield blocks the shell; removed for a short window then reappears. Hammer must strike in that window."""
        shield_enabled = terrain_config.get("shield_enabled", True)
        if not shield_enabled:
            return
        # Shield in front of shell
        shield_x = float(terrain_config.get("shield_x", 15.2))
        shield_y = float(terrain_config.get("shield_y", 2.6))
        shield_w = float(terrain_config.get("shield_width", 0.6))
        shield_h = float(terrain_config.get("shield_height", 1.8))
        self._shield_params = (shield_x, shield_y, shield_w, shield_h)  # for reappear
        sfd = Box2D.b2FixtureDef(
            shape=polygonShape(box=(shield_w / 2, shield_h / 2)),
            friction=0.6,
        )
        sfd.filter.categoryBits = self._CAT_SHIELD
        sfd.filter.maskBits = self._CAT_AGENT
        shield = self._world.CreateStaticBody(
            position=(shield_x, shield_y),
            fixtures=sfd,
        )
        self._terrain_bodies["shield"] = shield
        # Very narrow window: shield + gate overlap ~5 steps — discover trigger by trial
        self._shield_remove_step = int(terrain_config.get("shield_remove_step", 68))
        self._shield_reappear_step = int(terrain_config.get("shield_reappear_step", 76))
        self._shield_recreated = False

    def _create_gate(self, terrain_config: dict):
        """Horizontal bar blocking path; removed for a short window so hammer must pass then."""
        gate_x = float(terrain_config.get("gate_x", 15.5))
        gate_y = float(terrain_config.get("gate_y", 3.5))
        gate_w = float(terrain_config.get("gate_width", 3.0))
        gate_h = float(terrain_config.get("gate_height", 0.35))
        self._gate_params = (gate_x, gate_y, gate_w, gate_h)
        gfd = Box2D.b2FixtureDef(
            shape=polygonShape(box=(gate_w / 2, gate_h / 2)),
            friction=0.5,
        )
        gfd.filter.categoryBits = self._CAT_GATE
        gfd.filter.maskBits = self._CAT_AGENT
        gate = self._world.CreateStaticBody(
            position=(gate_x, gate_y),
            fixtures=gfd,
        )
        self._terrain_bodies["gate"] = gate
        self._gate_remove_step = int(terrain_config.get("gate_remove_step", 70))
        self._gate_reappear_step = int(terrain_config.get("gate_reappear_step", 79))
        self._gate_recreated = False
        # Second gate: when enabled, BOTH gates must be open
        if terrain_config.get("gate2_enabled", False):
            self._create_second_gate(terrain_config)

    def _create_second_gate(self, terrain_config: dict):
        """Second gate (high corridor); different open/close steps — BOTH gates must be open to pass."""
        g2_x = float(terrain_config.get("gate2_x", 14.5))
        g2_y = float(terrain_config.get("gate2_y", 6.5))
        g2_w = float(terrain_config.get("gate2_width", 2.5))
        g2_h = float(terrain_config.get("gate2_height", 0.3))
        self._gate2_params = (g2_x, g2_y, g2_w, g2_h)
        gfd = Box2D.b2FixtureDef(
            shape=polygonShape(box=(g2_w / 2, g2_h / 2)),
            friction=0.5,
        )
        gfd.filter.categoryBits = self._CAT_GATE
        gfd.filter.maskBits = self._CAT_AGENT
        gate2 = self._world.CreateStaticBody(position=(g2_x, g2_y), fixtures=gfd)
        self._terrain_bodies["gate2"] = gate2
        self._gate2_remove_step = int(terrain_config.get("gate2_remove_step", 114))
        self._gate2_reappear_step = int(terrain_config.get("gate2_reappear_step", 136))
        self._gate2_recreated = False

    def _create_pendulum_obstacle(self, terrain_config: dict):
        """Swinging pendulum in the path; hammer must time swing when pendulum has cleared."""
        # Left of build zone so high-arc path (pivot 12,8 → shell 18,8) can pass above
        pivot_x = float(terrain_config.get("pendulum_pivot_x", 7.0))
        pivot_y = float(terrain_config.get("pendulum_pivot_y", 4.0))
        rod_len = float(terrain_config.get("pendulum_rod_length", 3.5))
        rod_w = 0.35
        # Static anchor (small box) for revolute
        anchor = self._world.CreateStaticBody(
            position=(pivot_x, pivot_y),
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(0.2, 0.2)),
                friction=0.5,
            ),
        )
        self._terrain_bodies["pendulum_anchor"] = anchor
        # Rod: center so top is at pivot; rod hangs down (angle 0 = vertical down)
        rod_center_x = pivot_x
        rod_center_y = pivot_y - rod_len / 2
        rfd = Box2D.b2FixtureDef(
            shape=polygonShape(box=(rod_w / 2, rod_len / 2)),
            density=25.0,
            friction=0.4,
        )
        rfd.filter.categoryBits = self._CAT_PENDULUM
        rfd.filter.maskBits = self._CAT_AGENT | self._CAT_GROUND  # no collision with shell
        # Initial angle so that during shield-down window (112–138) rod is swung left and
        # a narrow gap exists; LLM must discover trigger step by trial.
        rod = self._world.CreateDynamicBody(
            position=(rod_center_x, rod_center_y),
            angle=float(terrain_config.get("pendulum_initial_angle", -0.6)),
            fixtures=rfd,
        )
        rod.linearDamping = self._default_linear_damping
        rod.angularDamping = 0.2
        rod.angularVelocity = float(terrain_config.get("pendulum_angular_velocity", -0.92))
        self._terrain_bodies["pendulum_rod"] = rod
        self._world.CreateRevoluteJoint(
            bodyA=rod,
            bodyB=anchor,
            anchor=(pivot_x, pivot_y),
            collideConnected=False,
        )
        self._pendulum_pivot = (pivot_x, pivot_y)
        self._pendulum_rod_length = rod_len

    def _create_second_pendulum(self, terrain_config: dict):
        """Second pendulum (high corridor); low arc passes under, but phase adds timing constraint."""
        pivot_x = float(terrain_config.get("pendulum2_pivot_x", 14.0))
        pivot_y = float(terrain_config.get("pendulum2_pivot_y", 6.0))
        rod_len = float(terrain_config.get("pendulum2_rod_length", 1.0))
        rod_w = 0.35
        anchor = self._world.CreateStaticBody(
            position=(pivot_x, pivot_y),
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(0.2, 0.2)),
                friction=0.5,
            ),
        )
        self._terrain_bodies["pendulum2_anchor"] = anchor
        rod_center_x = pivot_x
        rod_center_y = pivot_y - rod_len / 2
        rfd = Box2D.b2FixtureDef(
            shape=polygonShape(box=(rod_w / 2, rod_len / 2)),
            density=25.0,
            friction=0.4,
        )
        rfd.filter.categoryBits = self._CAT_PENDULUM
        rfd.filter.maskBits = self._CAT_AGENT | self._CAT_GROUND
        rod2 = self._world.CreateDynamicBody(
            position=(rod_center_x, rod_center_y),
            angle=float(terrain_config.get("pendulum2_initial_angle", -0.55)),
            fixtures=rfd,
        )
        rod2.linearDamping = self._default_linear_damping
        rod2.angularDamping = 0.2
        rod2.angularVelocity = float(terrain_config.get("pendulum2_angular_velocity", -0.82))
        self._terrain_bodies["pendulum_rod_2"] = rod2
        self._world.CreateRevoluteJoint(
            bodyA=rod2,
            bodyB=anchor,
            anchor=(pivot_x, pivot_y),
            collideConnected=False,
        )

    def _install_contact_listener(self):
        """Track hammer touching any pendulum, gate, gate2, or wall before shell broken → failure."""
        world = self._world
        sandbox = self
        pendulum_rod = self._terrain_bodies.get("pendulum_rod")
        pendulum_rod_2 = self._terrain_bodies.get("pendulum_rod_2")
        gate = self._terrain_bodies.get("gate")
        gate2 = self._terrain_bodies.get("gate2")
        central_wall = self._terrain_bodies.get("central_wall")
        slot_left = self._terrain_bodies.get("slot_left")
        slot_right = self._terrain_bodies.get("slot_right")
        slot_bar = self._terrain_bodies.get("slot_bar")

        class HammerObstacleListener(Box2D.b2ContactListener):
            def BeginContact(self, contact):
                if sandbox._shell_broken:
                    return
                fa, fb = contact.fixtureA, contact.fixtureB
                body_a, body_b = fa.body, fb.body
                agent_hit = body_a in sandbox._bodies or body_b in sandbox._bodies
                if not agent_hit:
                    return
                other = body_b if body_a in sandbox._bodies else body_a
                if other == pendulum_rod or other == pendulum_rod_2:
                    sandbox._hammer_hit_pendulum_before_shell = True
                if gate is not None and other == gate:
                    sandbox._hammer_hit_gate_before_shell = True
                if gate2 is not None and other == gate2:
                    sandbox._hammer_hit_gate2_before_shell = True
                if central_wall is not None and other == central_wall:
                    sandbox._hammer_hit_wall_before_shell = True
                if slot_left is not None and other == slot_left:
                    sandbox._hammer_hit_slot_wall_before_shell = True
                if slot_right is not None and other == slot_right:
                    sandbox._hammer_hit_slot_wall_before_shell = True
                if slot_bar is not None and other == slot_bar:
                    sandbox._hammer_hit_slot_bar_before_shell = True

        self._contact_listener = HammerObstacleListener()
        world.contactListener = self._contact_listener

    MIN_BEAM_SIZE = 0.1
    MAX_BEAM_SIZE = 4.0

    def add_beam(self, x, y, width, height, angle=0, density=1.0):
        width = max(self.MIN_BEAM_SIZE, min(width, self.MAX_BEAM_SIZE))
        height = max(self.MIN_BEAM_SIZE, min(height, self.MAX_BEAM_SIZE))
        bfd = Box2D.b2FixtureDef(
            shape=polygonShape(box=(width / 2, height / 2)),
            density=density,
            friction=0.5,
        )
        bfd.filter.categoryBits = self._CAT_AGENT
        bfd.filter.maskBits = self._CAT_SHELL | self._CAT_GROUND | self._CAT_PENDULUM | self._CAT_SHIELD | self._CAT_GATE | self._CAT_WALL | self._CAT_SLOT | self._CAT_SLOT_BAR
        body = self._world.CreateDynamicBody(
            position=(x, y),
            angle=angle,
            fixtures=bfd,
        )
        body.linearDamping = self._default_linear_damping
        body.angularDamping = self._default_angular_damping
        self._bodies.append(body)
        return body

    def add_joint(self, body_a, body_b, anchor_point, type="rigid"):
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
        return joint

    def get_structure_mass(self):
        return sum(b.mass for b in self._bodies)

    def set_material_properties(self, body, restitution=0.2):
        for fixture in body.fixtures:
            fixture.restitution = float(restitution)

    def step(self, time_step):
        self._step_count += 1
        # Oscillating bar inside slot: move bar vertically so hammer must time passage
        slot_bar = self._terrain_bodies.get("slot_bar")
        if slot_bar is not None and hasattr(self, "_slot_bar_x") and hasattr(self, "_slot_bar_y_center"):
            y_bar = self._slot_bar_y_center + self._slot_bar_amplitude * math.sin(self._step_count * self._slot_bar_omega)
            try:
                slot_bar.SetTransform((self._slot_bar_x, y_bar), 0.0)
            except AttributeError:
                slot_bar.transform = ((self._slot_bar_x, y_bar), 0.0)
        # Remove shield at given step (opens window)
        if hasattr(self, "_shield_remove_step") and self._terrain_bodies.get("shield") is not None:
            if self._step_count >= self._shield_remove_step:
                shield_body = self._terrain_bodies["shield"]
                self._world.DestroyBody(shield_body)
                self._terrain_bodies["shield"] = None
        # Recreate shield after window (closes window — hammer must have struck by then)
        if (
            hasattr(self, "_shield_reappear_step")
            and self._terrain_bodies.get("shield") is None
            and getattr(self, "_shield_recreated", False) is False
            and self._step_count >= self._shield_reappear_step
        ):
            self._shield_recreated = True
            sx, sy, sw, sh = self._shield_params
            sfd = Box2D.b2FixtureDef(
                shape=polygonShape(box=(sw / 2, sh / 2)),
                friction=0.6,
            )
            sfd.filter.categoryBits = self._CAT_SHIELD
            sfd.filter.maskBits = self._CAT_AGENT
            new_shield = self._world.CreateStaticBody(position=(sx, sy), fixtures=sfd)
            self._terrain_bodies["shield"] = new_shield
        # Gate: remove at step, reappear later (hammer must pass when gate is open)
        if hasattr(self, "_gate_remove_step") and self._terrain_bodies.get("gate") is not None:
            if self._step_count >= self._gate_remove_step:
                gate_body = self._terrain_bodies["gate"]
                self._world.DestroyBody(gate_body)
                self._terrain_bodies["gate"] = None
        if (
            hasattr(self, "_gate_reappear_step")
            and self._terrain_bodies.get("gate") is None
            and getattr(self, "_gate_recreated", False) is False
            and self._step_count >= self._gate_reappear_step
        ):
            self._gate_recreated = True
            gx, gy, gw, gh = self._gate_params
            gfd = Box2D.b2FixtureDef(
                shape=polygonShape(box=(gw / 2, gh / 2)),
                friction=0.5,
            )
            gfd.filter.categoryBits = self._CAT_GATE
            gfd.filter.maskBits = self._CAT_AGENT
            new_gate = self._world.CreateStaticBody(position=(gx, gy), fixtures=gfd)
            self._terrain_bodies["gate"] = new_gate
        # Gate2: remove / reappear (second gate — both must be open)
        if hasattr(self, "_gate2_remove_step") and self._terrain_bodies.get("gate2") is not None:
            if self._step_count >= self._gate2_remove_step:
                g2_body = self._terrain_bodies["gate2"]
                self._world.DestroyBody(g2_body)
                self._terrain_bodies["gate2"] = None
        if (
            hasattr(self, "_gate2_reappear_step")
            and self._terrain_bodies.get("gate2") is None
            and getattr(self, "_gate2_recreated", False) is False
            and self._step_count >= self._gate2_reappear_step
        ):
            self._gate2_recreated = True
            g2x, g2y, g2w, g2h = self._gate2_params
            gfd2 = Box2D.b2FixtureDef(
                shape=polygonShape(box=(g2w / 2, g2h / 2)),
                friction=0.5,
            )
            gfd2.filter.categoryBits = self._CAT_GATE
            gfd2.filter.maskBits = self._CAT_AGENT
            new_gate2 = self._world.CreateStaticBody(position=(g2x, g2y), fixtures=gfd2)
            self._terrain_bodies["gate2"] = new_gate2
        if self._shell_joint is not None and not self._shell_broken:
            try:
                inv_dt = 1.0 / time_step if time_step > 0 else 60.0
                force = self._shell_joint.GetReactionForce(inv_dt)
                mag = math.sqrt(force.x ** 2 + force.y ** 2)
                if mag >= self._shell_break_threshold:
                    self._world.DestroyJoint(self._shell_joint)
                    self._shell_joint = None
                    self._shell_broken = True
            except Exception:
                self._shell_joint = None
                self._shell_broken = True
        self._world.Step(time_step, 10, 10)

    def get_terrain_bounds(self):
        out = {
            "ground_y": self._ground_y,
            "shell_x": self._shell_x,
            "shell_y": self._shell_y,
            "shell_break_force": self._shell_break_threshold,
            "build_zone": {
                "x": [self.BUILD_ZONE_X_MIN, self.BUILD_ZONE_X_MAX],
                "y": [self.BUILD_ZONE_Y_MIN, self.BUILD_ZONE_Y_MAX],
            },
        }
        if hasattr(self, "_pendulum_pivot"):
            out["pendulum_pivot"] = self._pendulum_pivot
            out["pendulum_rod_length"] = self._pendulum_rod_length
        if hasattr(self, "_shield_remove_step"):
            out["shield_has_window"] = True
        if hasattr(self, "_gate_remove_step"):
            out["gate_has_window"] = True
        if self._terrain_bodies.get("central_wall") is not None:
            out["central_wall"] = True
        return out

    def is_shell_broken(self):
        return self._shell_broken

    def hammer_hit_pendulum_before_shell(self):
        """True if any agent body contacted any pendulum before the shell was broken."""
        return getattr(self, "_hammer_hit_pendulum_before_shell", False)

    def hammer_hit_gate_before_shell(self):
        """True if any agent body contacted the gate before the shell was broken."""
        return getattr(self, "_hammer_hit_gate_before_shell", False)

    def hammer_hit_gate2_before_shell(self):
        """True if any agent body contacted the second gate before the shell was broken."""
        return getattr(self, "_hammer_hit_gate2_before_shell", False)

    def hammer_hit_wall_before_shell(self):
        """True if any agent body contacted the central wall before the shell was broken."""
        return getattr(self, "_hammer_hit_wall_before_shell", False)

    def hammer_hit_slot_wall_before_shell(self):
        """True if any agent body hit the slot barrier (left or right wall) before the shell was broken — must pass through the gap."""
        return getattr(self, "_hammer_hit_slot_wall_before_shell", False)

    def hammer_hit_slot_bar_before_shell(self):
        """True if any agent body hit the oscillating bar inside the slot before the shell was broken — must pass when bar is away."""
        return getattr(self, "_hammer_hit_slot_bar_before_shell", False)
