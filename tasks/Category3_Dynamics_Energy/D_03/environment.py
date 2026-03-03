"""
D-03: Phase-Locked Gate (相位锁定门)
Category3_Dynamics_Energy — 动力学 + 时间窗口 + 相位匹配。

场景：小车从左侧以初速出发，前方有一根绕固定轴匀速旋转的“门杆”。
门仅在角度接近竖直的短暂时间窗口内可通过；其余时间撞杆即失败。
同时有周期性侧向风，影响小车到达门处的时刻。
智能体只能在小车上安装有限数量、有限质量的梁（不可接地），通过改变质量和受力，
使小车“恰好”在门开时通过，并到达右侧目标区且末速在给定范围内。

难点：需同时推理 (1) 动力学 x(t)、v(t)，(2) 门角 θ(t) 与开窗，(3) 风对轨迹的调制，
(4) 质量/布局对到达时间的影响 — 强非线性、多变量耦合。
"""
import math
import Box2D
from Box2D.b2 import (
    world,
    polygonShape,
    circleShape,
    staticBody,
    dynamicBody,
    weldJoint,
)
from Box2D import b2ContactFilter


class Sandbox:
    """Sandbox for D-03: Phase-Locked Gate — cart, rotating gate, wind."""

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
        self._step_count = 0

        self.world = self._world
        self.bodies = self._bodies
        self.joints = self._joints

        self._create_terrain(terrain_config)
        self._create_cart(terrain_config)
        self._create_rotating_gate(terrain_config)
        self._create_second_gate(terrain_config)
        self._create_third_gate(terrain_config)
        self._create_fourth_gate(terrain_config)
        self._install_contact_listener()
        self._install_contact_filter()

        self.BUILD_ZONE_X_MIN = float(terrain_config.get("build_zone_x_min", 4.8))
        self.BUILD_ZONE_X_MAX = float(terrain_config.get("build_zone_x_max", 9.0))
        self.BUILD_ZONE_Y_MIN = float(terrain_config.get("build_zone_y_min", 2.0))
        self.BUILD_ZONE_Y_MAX = float(terrain_config.get("build_zone_y_max", 3.2))
        self.MAX_STRUCTURE_MASS = float(terrain_config.get("max_structure_mass", 14.0))
        self.MAX_BEAM_COUNT = int(terrain_config.get("max_beam_count", 5))
        self.allow_ground_anchors = False

        # Gate open window: angle in [pi/2 - delta, pi/2 + delta] (rad) — narrow for true phase-lock
        self._gate_open_half_width = float(terrain_config.get("gate_open_half_width", 0.56))
        self._target_x_min = float(terrain_config.get("target_x_min", 11.75))
        self._target_speed_min = float(terrain_config.get("target_speed_min", 0.45))
        self._target_speed_max = float(terrain_config.get("target_speed_max", 2.6))
        # Mud zone [x_min, x_max]: strong velocity damping (N·s/m)
        self._mud_zone_x_min = float(terrain_config.get("mud_zone_x_min", 5.5))
        self._mud_zone_x_max = float(terrain_config.get("mud_zone_x_max", 7.5))
        self._mud_damping = float(terrain_config.get("mud_damping", 4.2))
        # Braking zone: extra damping so final speed must be tuned
        self._brake_zone_x_min = float(terrain_config.get("brake_zone_x_min", 12.0))
        self._brake_zone_x_max = float(terrain_config.get("brake_zone_x_max", 15.0))
        self._brake_damping = float(terrain_config.get("brake_damping", 0.0))
        # Minimum beams required (hard constraint — trivial solutions fail)
        self.MIN_BEAM_COUNT = int(terrain_config.get("min_beam_count", 4))
        # Impulse zone [x_min, x_max]: periodic backward impulse (N·s) — must have enough mass to survive
        self._impulse_zone_x_min = float(terrain_config.get("impulse_zone_x_min", 8.0))
        self._impulse_zone_x_max = float(terrain_config.get("impulse_zone_x_max", 9.0))
        self._impulse_magnitude = float(terrain_config.get("impulse_magnitude", 1.5))
        self._impulse_interval = int(terrain_config.get("impulse_interval_steps", 28))
        self._impulse_zone_applied = False  # apply at most once per passage through [8,9]
        # Second impulse zone [10.5, 11]: one-time backward impulse AFTER gate 1 — must survive two kicks
        self._impulse2_zone_x_min = float(terrain_config.get("impulse2_zone_x_min", 10.5))
        self._impulse2_zone_x_max = float(terrain_config.get("impulse2_zone_x_max", 11.0))
        self._impulse2_magnitude = float(terrain_config.get("impulse2_magnitude", 0.55))
        self._impulse2_zone_applied = False
        # Speed trap: when cart center first crosses this x, speed must be >= speed_trap_min or fail
        self._speed_trap_x = float(terrain_config.get("speed_trap_x", 9.0))
        self._speed_trap_min = float(terrain_config.get("speed_trap_min", 2.8))
        self._speed_trap_checked = False
        self._speed_trap_failed = False
        # Decel zone [9.5, 11]: strong damping — must shed speed so v(11) lands in narrow band (velocity profile constraint)
        self._decel_zone_x_min = float(terrain_config.get("decel_zone_x_min", 9.5))
        self._decel_zone_x_max = float(terrain_config.get("decel_zone_x_max", 11.0))
        self._decel_damping = float(terrain_config.get("decel_damping", 3.2))
        # Checkpoint at x=11: first time crossing x=11, speed MUST be in [1.3, 2.5] — couples to gate phase timing
        self._checkpoint_11_x = float(terrain_config.get("checkpoint_11_x", 11.0))
        self._checkpoint_11_speed_min = float(terrain_config.get("checkpoint_11_speed_min", 1.1))
        self._checkpoint_11_speed_max = float(terrain_config.get("checkpoint_11_speed_max", 2.7))
        self._checkpoint_11_checked = False
        self._checkpoint_11_failed = False

    def _create_terrain(self, terrain_config: dict):
        ground_len = 35.0
        ground_h = 0.4
        ground = self._world.CreateStaticBody(
            position=(ground_len / 2, ground_h / 2),
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(ground_len / 2, ground_h / 2)),
                friction=float(terrain_config.get("ground_friction", 0.45)),
            ),
        )
        self._terrain_bodies["ground"] = ground
        self._ground_y = ground_h
        self._ground_len = ground_len

    def _create_cart(self, terrain_config: dict):
        spawn_x = float(terrain_config.get("cart_spawn_x", 4.0))
        spawn_y = float(terrain_config.get("cart_spawn_y", 2.5))
        v0 = float(terrain_config.get("cart_initial_speed", 10.0))

        cabin_w = 0.7
        cabin_h = 0.35
        cabin_density = 120.0
        cabin = self._world.CreateDynamicBody(
            position=(spawn_x, spawn_y),
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(cabin_w / 2, cabin_h / 2)),
                density=cabin_density,
                friction=0.5,
                restitution=0.05,
            ),
        )
        cabin.linearVelocity = (v0, 0)
        cabin.linearDamping = self._default_linear_damping
        cabin.angularDamping = self._default_angular_damping
        self._terrain_bodies["vehicle_cabin"] = cabin
        self._terrain_bodies["cart"] = cabin

    def _create_rotating_gate(self, terrain_config: dict):
        gate_x = float(terrain_config.get("gate_pivot_x", 10.0))
        gate_y = float(terrain_config.get("gate_pivot_y", 2.5))
        rod_len = float(terrain_config.get("gate_rod_length", 0.9))
        rod_w = 0.12
        rod_density = 80.0
        omega = float(terrain_config.get("gate_angular_velocity", 1.8))
        theta0 = float(terrain_config.get("gate_initial_angle", 0.38))

        pivot = self._world.CreateStaticBody(position=(gate_x, gate_y))
        self._terrain_bodies["gate_pivot"] = pivot

        rod = self._world.CreateDynamicBody(
            position=(gate_x, gate_y),
            angle=theta0,
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(rod_len / 2, rod_w / 2)),
                density=rod_density,
                friction=0.4,
                restitution=0.1,
            ),
        )
        rod.angularVelocity = omega
        rod.linearDamping = 0.0
        rod.angularDamping = 0.0
        self._terrain_bodies["gate_rod"] = rod

        jd = Box2D.b2RevoluteJointDef()
        jd.Initialize(pivot, rod, Box2D.b2Vec2(gate_x, gate_y))
        jd.enableMotor = True
        jd.motorSpeed = float(omega)
        jd.maxMotorTorque = 5000.0
        jd.collideConnected = False
        self._world.CreateJoint(jd)
        self._gate_pivot_x = gate_x
        self._gate_pivot_y = gate_y
        self._gate_omega = omega

    def _create_second_gate(self, terrain_config: dict):
        """Second rotating gate at x=13 — cart must pass BOTH gates when open."""
        gate_x = float(terrain_config.get("gate2_pivot_x", 11.75))
        gate_y = float(terrain_config.get("gate2_pivot_y", 2.5))
        rod_len = float(terrain_config.get("gate2_rod_length", 0.75))
        rod_w = 0.12
        rod_density = 80.0
        omega = float(terrain_config.get("gate2_angular_velocity", 0.58))
        theta0 = float(terrain_config.get("gate2_initial_angle", 0.63))
        pivot = self._world.CreateStaticBody(position=(gate_x, gate_y))
        self._terrain_bodies["gate_pivot_2"] = pivot
        rod = self._world.CreateDynamicBody(
            position=(gate_x, gate_y),
            angle=theta0,
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(rod_len / 2, rod_w / 2)),
                density=rod_density,
                friction=0.4,
                restitution=0.1,
            ),
        )
        rod.angularVelocity = omega
        rod.linearDamping = 0.0
        rod.angularDamping = 0.0
        self._terrain_bodies["gate_rod_2"] = rod
        jd = Box2D.b2RevoluteJointDef()
        jd.Initialize(pivot, rod, Box2D.b2Vec2(gate_x, gate_y))
        jd.enableMotor = True
        jd.motorSpeed = float(omega)
        jd.maxMotorTorque = 5000.0
        jd.collideConnected = False
        self._world.CreateJoint(jd)
        self._gate2_pivot_x = gate_x
        self._gate2_open_half_width = float(terrain_config.get("gate2_open_half_width", 1.50))

    def _create_third_gate(self, terrain_config: dict):
        """Third rotating gate at x=11.5 — cart must pass ALL THREE gates when open."""
        gate_x = float(terrain_config.get("gate3_pivot_x", 11.5))
        gate_y = float(terrain_config.get("gate3_pivot_y", 2.5))
        rod_len = float(terrain_config.get("gate3_rod_length", 0.7))
        rod_w = 0.12
        rod_density = 80.0
        omega = float(terrain_config.get("gate3_angular_velocity", 1.2))
        theta0 = float(terrain_config.get("gate3_initial_angle", 0.0))
        pivot = self._world.CreateStaticBody(position=(gate_x, gate_y))
        self._terrain_bodies["gate_pivot_3"] = pivot
        rod = self._world.CreateDynamicBody(
            position=(gate_x, gate_y),
            angle=theta0,
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(rod_len / 2, rod_w / 2)),
                density=rod_density,
                friction=0.4,
                restitution=0.1,
            ),
        )
        rod.angularVelocity = omega
        rod.linearDamping = 0.0
        rod.angularDamping = 0.0
        self._terrain_bodies["gate_rod_3"] = rod
        jd = Box2D.b2RevoluteJointDef()
        jd.Initialize(pivot, rod, Box2D.b2Vec2(gate_x, gate_y))
        jd.enableMotor = True
        jd.motorSpeed = float(omega)
        jd.maxMotorTorque = 5000.0
        jd.collideConnected = False
        self._world.CreateJoint(jd)
        self._gate3_pivot_x = gate_x
        self._gate3_open_half_width = float(terrain_config.get("gate3_open_half_width", 0.60))

    def _create_fourth_gate(self, terrain_config: dict):
        """Fourth rotating gate at x=12.5 — cart must pass ALL FOUR gates when open."""
        gate_x = float(terrain_config.get("gate4_pivot_x", 11.75))
        gate_y = float(terrain_config.get("gate4_pivot_y", 2.5))
        rod_len = float(terrain_config.get("gate4_rod_length", 0.65))
        rod_w = 0.12
        rod_density = 80.0
        omega = float(terrain_config.get("gate4_angular_velocity", 0.9))
        theta0 = float(terrain_config.get("gate4_initial_angle", 0.4))
        pivot = self._world.CreateStaticBody(position=(gate_x, gate_y))
        self._terrain_bodies["gate_pivot_4"] = pivot
        rod = self._world.CreateDynamicBody(
            position=(gate_x, gate_y),
            angle=theta0,
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(rod_len / 2, rod_w / 2)),
                density=rod_density,
                friction=0.4,
                restitution=0.1,
            ),
        )
        rod.angularVelocity = omega
        rod.linearDamping = 0.0
        rod.angularDamping = 0.0
        self._terrain_bodies["gate_rod_4"] = rod
        jd = Box2D.b2RevoluteJointDef()
        jd.Initialize(pivot, rod, Box2D.b2Vec2(gate_x, gate_y))
        jd.enableMotor = True
        jd.motorSpeed = float(omega)
        jd.maxMotorTorque = 5000.0
        jd.collideConnected = False
        self._world.CreateJoint(jd)
        self._gate4_pivot_x = gate_x
        self._gate4_open_half_width = float(terrain_config.get("gate4_open_half_width", 0.56))

    def _install_contact_listener(self):
        self._gate_collision_occurred = False
        self._cart_assembly = set()

        class Listener(Box2D.b2ContactListener):
            def __init__(outer_self, env):
                Box2D.b2ContactListener.__init__(outer_self)
                outer_self.env = env

            def BeginContact(self, contact):
                a, b = contact.fixtureA.body, contact.fixtureB.body
                cart = self.env._terrain_bodies.get("vehicle_cabin")
                agent_bodies = set(getattr(self.env, "_bodies", []))
                cart_assembly = {cart} | agent_bodies if cart else agent_bodies
                gate_rod = self.env._terrain_bodies.get("gate_rod")
                gate_rod_2 = self.env._terrain_bodies.get("gate_rod_2")
                gate_rod_3 = self.env._terrain_bodies.get("gate_rod_3")
                gate_rod_4 = self.env._terrain_bodies.get("gate_rod_4")
                for rod in (gate_rod, gate_rod_2, gate_rod_3, gate_rod_4):
                    if rod is None:
                        continue
                    if (a == rod and b in cart_assembly) or (b == rod and a in cart_assembly):
                        if rod == gate_rod and not self.env.is_gate_open():
                            self.env._gate_collision_occurred = True
                        elif rod == gate_rod_2 and not self.env.is_gate2_open():
                            self.env._gate_collision_occurred = True
                        elif rod == gate_rod_3 and not self.env.is_gate3_open():
                            self.env._gate_collision_occurred = True
                        elif rod == gate_rod_4 and not self.env.is_gate4_open():
                            self.env._gate_collision_occurred = True
                        break

        self._world.contactListener = Listener(self)

    def _install_contact_filter(self):
        """When a gate is open, its rod does not collide with cart/beams so the cart can pass through."""
        gate_rod = self._terrain_bodies.get("gate_rod")
        gate_rod_2 = self._terrain_bodies.get("gate_rod_2")
        gate_rod_3 = self._terrain_bodies.get("gate_rod_3")
        gate_rod_4 = self._terrain_bodies.get("gate_rod_4")
        cabin = self._terrain_bodies.get("vehicle_cabin")
        env_ref = self

        class GateContactFilter(b2ContactFilter):
            def ShouldCollide(self, fixtureA, fixtureB):
                a_body = fixtureA.body
                b_body = fixtureB.body
                cart_assembly = {cabin} | set(env_ref._bodies) if cabin else set(env_ref._bodies)
                for (rod, is_open_fn) in [
                    (gate_rod, env_ref.is_gate_open),
                    (gate_rod_2, env_ref.is_gate2_open),
                    (gate_rod_3, env_ref.is_gate3_open),
                    (gate_rod_4, env_ref.is_gate4_open),
                ]:
                    if rod is None:
                        continue
                    if (a_body == rod and b_body in cart_assembly) or (b_body == rod and a_body in cart_assembly):
                        return not is_open_fn()
                return True

        self._contact_filter = GateContactFilter()
        self._world.contactFilter = self._contact_filter

    MIN_BEAM_SIZE = 0.08
    MAX_BEAM_SIZE = 2.0

    def add_beam(self, x, y, width, height, angle=0, density=1.0):
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

    def add_joint(self, body_a, body_b, anchor_point, type="rigid"):
        if body_a is None:
            raise ValueError("add_joint: body_a cannot be None.")
        anchor_x, anchor_y = anchor_point[0], anchor_point[1]
        if body_b is None:
            raise ValueError(
                "Ground anchoring is not allowed. Attach beams to the cart only."
            )
        if type == "rigid":
            joint = self._world.CreateWeldJoint(
                bodyA=body_a,
                bodyB=body_b,
                anchor=(anchor_x, anchor_y),
                collideConnected=False,
            )
        elif type == "pivot":
            joint = self._world.CreateRevoluteJoint(
                bodyA=body_a,
                bodyB=body_b,
                anchor=(anchor_x, anchor_y),
                collideConnected=False,
            )
        else:
            raise ValueError(f"Unknown joint type: {type}")
        self._joints.append(joint)
        return joint

    def set_material_properties(self, body, restitution=0.2):
        for fixture in body.fixtures:
            fixture.restitution = float(restitution)

    def get_structure_mass(self):
        return sum(b.mass for b in self._bodies)

    def step(self, time_step):
        self._step_count += 1
        cabin = self._terrain_bodies.get("vehicle_cabin")
        cabin_x = cabin.position.x if cabin else 0.0

        # Dual-frequency wind (hard to phase-lock)
        wind_enabled = bool(self._terrain_config.get("wind_enabled", False))
        if wind_enabled:
            A1 = float(self._terrain_config.get("wind_amplitude_1", 2.0))
            A2 = float(self._terrain_config.get("wind_amplitude_2", 0.5))
            T1, T2 = 50, 37
            ph1 = 2.0 * math.pi * (self._step_count % T1) / T1
            ph2 = 2.0 * math.pi * (self._step_count % T2) / T2
            fx = A1 * math.sin(ph1) + A2 * math.sin(ph2)
            if cabin is not None and cabin.awake:
                cabin.ApplyForceToCenter((fx, 0.0), wake=True)
            for body in self._bodies:
                if body.awake:
                    body.ApplyForceToCenter((fx * 0.2, 0.0), wake=True)

        # Mud zone: strong linear damping when cart center in [5.5, 7.5]
        mud_min, mud_max = self._mud_zone_x_min, self._mud_zone_x_max
        if mud_min <= cabin_x <= mud_max:
            k = self._mud_damping
            if cabin is not None and cabin.awake:
                vx, vy = cabin.linearVelocity.x, cabin.linearVelocity.y
                cabin.ApplyForceToCenter((-k * vx, -k * vy), wake=True)
            for body in self._bodies:
                if body.awake:
                    vx, vy = body.linearVelocity.x, body.linearVelocity.y
                    body.ApplyForceToCenter((-k * vx, -k * vy), wake=True)

        # Impulse zone [8, 9]: one-time backward impulse when first entering — need enough mass to survive
        imp_min = getattr(self, "_impulse_zone_x_min", 8.0)
        imp_max = getattr(self, "_impulse_zone_x_max", 9.0)
        if imp_min <= cabin_x <= imp_max:
            if not getattr(self, "_impulse_zone_applied", False):
                mag = getattr(self, "_impulse_magnitude", 2.0)
                impulse = (-mag, 0.0)
                if cabin is not None and cabin.awake:
                    cabin.ApplyLinearImpulse(impulse, cabin.worldCenter, wake=True)
                for body in self._bodies:
                    if body.awake:
                        body.ApplyLinearImpulse(impulse, body.worldCenter, wake=True)
                self._impulse_zone_applied = True
        elif cabin_x < imp_min:
            self._impulse_zone_applied = False  # reset when re-entering from left

        # Second impulse zone [10.5, 11]: one-time backward impulse when first entering (after gate 1)
        imp2_min = getattr(self, "_impulse2_zone_x_min", 10.5)
        imp2_max = getattr(self, "_impulse2_zone_x_max", 11.0)
        if imp2_min <= cabin_x <= imp2_max:
            if not getattr(self, "_impulse2_zone_applied", False):
                mag2 = getattr(self, "_impulse2_magnitude", 1.3)
                impulse2 = (-mag2, 0.0)
                if cabin is not None and cabin.awake:
                    cabin.ApplyLinearImpulse(impulse2, cabin.worldCenter, wake=True)
                for body in self._bodies:
                    if body.awake:
                        body.ApplyLinearImpulse(impulse2, body.worldCenter, wake=True)
                self._impulse2_zone_applied = True
        elif cabin_x < imp2_min:
            self._impulse2_zone_applied = False

        # Decel zone [9.5, 11]: strong damping — must land v(11) in [1.7, 2.1] for gate phase alignment
        dec_min = getattr(self, "_decel_zone_x_min", 9.5)
        dec_max = getattr(self, "_decel_zone_x_max", 11.0)
        if dec_min <= cabin_x <= dec_max:
            k = getattr(self, "_decel_damping", 5.0)
            if cabin is not None and cabin.awake:
                vx, vy = cabin.linearVelocity.x, cabin.linearVelocity.y
                cabin.ApplyForceToCenter((-k * vx, -k * vy), wake=True)
            for body in self._bodies:
                if body.awake:
                    vx, vy = body.linearVelocity.x, body.linearVelocity.y
                    body.ApplyForceToCenter((-k * vx, -k * vy), wake=True)

        # Braking zone [12, 15]: extra damping so final speed band is hard to hit
        br_min, br_max = self._brake_zone_x_min, self._brake_zone_x_max
        if br_min <= cabin_x <= br_max:
            k = self._brake_damping
            if cabin is not None and cabin.awake:
                vx, vy = cabin.linearVelocity.x, cabin.linearVelocity.y
                cabin.ApplyForceToCenter((-k * vx, -k * vy), wake=True)
            for body in self._bodies:
                if body.awake:
                    vx, vy = body.linearVelocity.x, body.linearVelocity.y
                    body.ApplyForceToCenter((-k * vx, -k * vy), wake=True)

        self._world.Step(time_step, 10, 10)

        # Speed trap: when cart center first crosses speed_trap_x, speed must be >= speed_trap_min
        if not getattr(self, "_speed_trap_checked", False) and cabin_x >= getattr(self, "_speed_trap_x", 9.0):
            self._speed_trap_checked = True
            vx = cabin.linearVelocity.x if cabin else 0.0
            vy = cabin.linearVelocity.y if cabin else 0.0
            speed = math.sqrt(vx * vx + vy * vy)
            if speed < getattr(self, "_speed_trap_min", 2.8):
                self._speed_trap_failed = True

        # Checkpoint at x=11: first crossing speed must be in [1.7, 2.1] — velocity profile constraint
        cp_x = getattr(self, "_checkpoint_11_x", 11.0)
        cp_lo = getattr(self, "_checkpoint_11_speed_min", 1.3)
        cp_hi = getattr(self, "_checkpoint_11_speed_max", 2.5)
        if not getattr(self, "_checkpoint_11_checked", False) and cabin_x >= cp_x:
            self._checkpoint_11_checked = True
            vx = cabin.linearVelocity.x if cabin else 0.0
            vy = cabin.linearVelocity.y if cabin else 0.0
            speed = math.sqrt(vx * vx + vy * vy)
            if speed < cp_lo or speed > cp_hi:
                self._checkpoint_11_failed = True

    def get_gate_angle(self):
        rod = self._terrain_bodies.get("gate_rod")
        if rod is None:
            return None
        return rod.angle

    def is_gate_open(self):
        angle = self.get_gate_angle()
        if angle is None:
            return False
        half = self._gate_open_half_width
        return (math.pi / 2 - half) <= angle <= (math.pi / 2 + half)

    def get_gate2_angle(self):
        rod = self._terrain_bodies.get("gate_rod_2")
        if rod is None:
            return None
        return rod.angle

    def is_gate2_open(self):
        angle = self.get_gate2_angle()
        if angle is None:
            return False
        half = getattr(self, "_gate2_open_half_width", 0.32)
        return (math.pi / 2 - half) <= angle <= (math.pi / 2 + half)

    def get_gate3_angle(self):
        rod = self._terrain_bodies.get("gate_rod_3")
        if rod is None:
            return None
        return rod.angle

    def is_gate3_open(self):
        angle = self.get_gate3_angle()
        if angle is None:
            return False
        half = getattr(self, "_gate3_open_half_width", 0.65)
        return (math.pi / 2 - half) <= angle <= (math.pi / 2 + half)

    def get_gate4_angle(self):
        rod = self._terrain_bodies.get("gate_rod_4")
        if rod is None:
            return None
        return rod.angle

    def is_gate4_open(self):
        angle = self.get_gate4_angle()
        if angle is None:
            return False
        half = getattr(self, "_gate4_open_half_width", 0.6)
        return (math.pi / 2 - half) <= angle <= (math.pi / 2 + half)

    def get_terrain_bounds(self):
        return {
            "ground_y": self._ground_y,
            "build_zone": {
                "x": [self.BUILD_ZONE_X_MIN, self.BUILD_ZONE_X_MAX],
                "y": [self.BUILD_ZONE_Y_MIN, self.BUILD_ZONE_Y_MAX],
            },
            "cart_spawn": (
                self._terrain_config.get("cart_spawn_x", 4.0),
                self._terrain_config.get("cart_spawn_y", 2.5),
            ),
            "cart_initial_speed": self._terrain_config.get("cart_initial_speed", 10.0),
            "gate_pivot_x": getattr(self, "_gate_pivot_x", 10.0),
            "gate2_pivot_x": getattr(self, "_gate2_pivot_x", 13.0),
            "gate3_pivot_x": getattr(self, "_gate3_pivot_x", 11.5),
            "gate4_pivot_x": getattr(self, "_gate4_pivot_x", 12.5),
            "gate_angular_velocity": getattr(self, "_gate_omega", 1.85),
            "speed_trap_x": getattr(self, "_speed_trap_x", 9.0),
            "speed_trap_min": getattr(self, "_speed_trap_min", 2.8),
            "decel_zone": [getattr(self, "_decel_zone_x_min", 9.5), getattr(self, "_decel_zone_x_max", 11.0)],
            "checkpoint_11_x": getattr(self, "_checkpoint_11_x", 11.0),
            "checkpoint_11_speed_min": getattr(self, "_checkpoint_11_speed_min", 1.3),
            "checkpoint_11_speed_max": getattr(self, "_checkpoint_11_speed_max", 2.5),
            "min_beam_count": getattr(self, "MIN_BEAM_COUNT", 3),
            "impulse_zone": [getattr(self, "_impulse_zone_x_min", 8.0), getattr(self, "_impulse_zone_x_max", 9.0)],
            "impulse2_zone": [getattr(self, "_impulse2_zone_x_min", 10.5), getattr(self, "_impulse2_zone_x_max", 11.0)],
            "gate_open_half_width": self._gate_open_half_width,
            "target_x_min": self._target_x_min,
            "target_speed_min": self._target_speed_min,
            "target_speed_max": self._target_speed_max,
            "mud_zone": [self._mud_zone_x_min, self._mud_zone_x_max],
            "brake_zone": [self._brake_zone_x_min, self._brake_zone_x_max],
            "max_beam_count": getattr(self, "MAX_BEAM_COUNT", 5),
            "max_structure_mass": getattr(self, "MAX_STRUCTURE_MASS", 14.0),
        }

    def get_passenger_position(self):
        cabin = self._terrain_bodies.get("vehicle_cabin")
        if cabin is None:
            return None
        return (cabin.position.x, cabin.position.y)

    def get_vehicle_position(self):
        """Alias for evaluator compatibility."""
        return self.get_passenger_position()

    def get_passenger_velocity(self):
        cabin = self._terrain_bodies.get("vehicle_cabin")
        if cabin is None:
            return None
        return (cabin.linearVelocity.x, cabin.linearVelocity.y)

    def get_vehicle_velocity(self):
        """Alias for evaluator compatibility."""
        return self.get_passenger_velocity()

    def get_vehicle_cabin(self):
        return self._terrain_bodies.get("vehicle_cabin")
