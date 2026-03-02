"""
C-03: The Seeker task environment module (Fundamentally Hard variant)
Task is fundamentally different from "simple tracking":
- SINGLE THRUST VECTOR: Seeker has one thruster. You choose direction and magnitude (max 200 N total).
  Force is applied as one vector; you cannot independently set horizontal and vertical force.
- NO TARGET VELOCITY: get_target_velocity() is not provided. Target velocity must be estimated
  from the history of get_target_position() (which has variable delay and blind zones).
- ACTUATION DELAY: The force you command at step t is applied at step t+1 (one-step delay).
- INTERMITTENT TARGET POSITION: get_target_position() returns a new value only every few steps;
  on other steps it repeats the last value. So you get sparse, low-rate samples — must infer
  target motion from this (no velocity API).
- Variable delay, occlusion zone, target jumps, time-varying wind remain.
Failure: lose target (distance exceeds threshold).
"""
import math
import random
import Box2D
from Box2D.b2 import (
    world,
    polygonShape,
    circleShape,
    staticBody,
    dynamicBody,
)

# Max distance (m) from seeker to target; beyond this = "lost target"
LOSE_TARGET_DISTANCE = 7.5

# Variable delay: get_target_position() returns value from 2 to 6 steps ago; delay changes every ~2 s
DELAY_MIN_STEPS = 2
DELAY_MAX_STEPS = 6
DELAY_CHANGE_INTERVAL_STEPS = 120  # change delay every 2 s at 60 Hz

# Blind/occlusion zone: when seeker x in this range, get_target_position() returns last value (no new update)
BLIND_ZONE_X_MIN = 12.0
BLIND_ZONE_X_MAX = 15.0

# Speed-blind: if seeker speed exceeds this (m/s), target position returns last value (no new update)
SPEED_BLIND_THRESHOLD = 2.0

# Evasive target: when distance < this (m), target gets velocity boost away from seeker (agent must discover)
EVASIVE_DISTANCE = 4.0
EVASIVE_GAIN = 0.45  # extra target speed away from seeker per step (tuned so ref can close with velocity match)

# Thrust cooldown: after applying thrust above threshold, max thrust is reduced for N steps (agent must discover)
COOLDOWN_THRESHOLD = 120.0   # N
COOLDOWN_STEPS = 80
COOLDOWN_MAX_THRUST = 40.0   # N during cooldown

# Body-fixed thruster (nonholonomic): thrust is applied ONLY along seeker's current heading;
# heading turns toward commanded direction at limited rate (rad/step) — discover via feedback
MAX_ANGULAR_RATE = 0.12  # rad per step (~7 deg/step)

# Target jump: every JUMP_INTERVAL_STEPS, target teleports by random (dx, dy) in [-JUMP_MAG, JUMP_MAG]
JUMP_INTERVAL_STEPS = 300  # ~5 s
JUMP_MAG = 1.2

# Single thrust vector: total magnitude capped (one direction per step)
MAX_THRUST_MAGNITUDE = 200.0
# Actuation delay: force commanded at step t is applied at step t+1
ACTUATION_DELAY_STEPS = 1
# Intermittent target position: sensor returns a NEW reading only every N steps (otherwise last value)
# So control runs at 60 Hz but target position "updates" at 12 Hz — must infer motion from sparse samples
TARGET_POSITION_UPDATE_PERIOD = 5

# Obstacle definitions: (center_x, center_y, half_width, half_height)
# No obstacle inside blind zone (12-15) so seeker can exit and get fresh readings
OBSTACLES = [
    (7.5, 1.5, 0.3, 0.5),
    (14.0, 1.5, 0.3, 0.5),
    (20.5, 1.5, 0.3, 0.5),
]

# Moving obstacle: (cx, cy, hw, hh)
MOVING_OBSTACLE = (10.5, 1.5, 0.35, 0.55)
MOVING_AMP = 0.7
MOVING_PERIOD = 2.5

# Second moving obstacle (narrow corridor timing)
MOVING_OBSTACLE_2 = (17.0, 1.5, 0.3, 0.5)
MOVING_AMP_2 = 0.5
MOVING_PERIOD_2 = 3.5
MOVING_PHASE_2 = 0.8  # phase offset

# Ice zones: ((cx, cy, hw, hh), friction)
ICE_ZONES = [
    ((9.0, 1.25, 1.0, 0.12), 0.08),
    ((16.5, 1.25, 1.0, 0.12), 0.08),
]

# Wind zone: (x_min, x_max); (ax, ay) is time-varying: base + amplitude*sin(omega*t)
WIND_ZONE_X = (14.0, 17.0)
WIND_BASE_X = -3.5
WIND_AMP_X = 2.5
WIND_OMEGA = 1.2  # rad/s

# Thrust impulse budget (N·s): total impulse from thrust over run cannot exceed this
# Tighter so naive full-thrust fails; only fuel-efficient trajectory passes
IMPULSE_BUDGET = 18500.0

# Activation gate (structural difficulty): rendezvous only counts if seeker has first "activated"
# by staying in activation zone for ACTIVATION_REQUIRED_STEPS consecutive steps (discover via feedback)
ACTIVATION_ZONE_X_MIN = 13.0
ACTIVATION_ZONE_X_MAX = 17.0
ACTIVATION_REQUIRED_STEPS = 120  # 2 s at 60 Hz
# Moving corridor: seeker must stay in x in [L(t), R(t)]; boundaries vary with time
# AMP 2.0 so corridor stays [10, 20] at worst; reference can pass while LLM must still reason
CORRIDOR_X_BASE_L = 8.0
CORRIDOR_X_BASE_R = 22.0
CORRIDOR_AMP = 2.0
CORRIDOR_OMEGA = 0.4  # rad/s
# Corridor pinch: during part of cycle corridor narrows (agent must time passage)
# Pinch phase offset so pinch starts after rendezvous window (~92 s), making tracking phase harder
CORRIDOR_PINCH_MARGIN = 2.0   # extra narrowing (m each side) when pinch active
CORRIDOR_PINCH_OMEGA = 0.35   # different phase so pinch not in sync with main corridor
CORRIDOR_PINCH_PHASE = 32.0   # pinch when sin(omega*t - phase) > threshold (delays pinch)
CORRIDOR_PINCH_THRESHOLD = 0.25  # when sin(pinch_omega*t - phase) > this, pinch active


class Sandbox:
    """
    Sandbox environment for C-03: The Seeker (Very Hard).
    Variable delay, blind zone, target jumps, asymmetric thrust, time-varying wind.
    """

    def __init__(self, *, terrain_config=None, physics_config=None):
        terrain_config = terrain_config or {}
        physics_config = physics_config or {}
        self._terrain_config = dict(terrain_config)
        self._physics_config = dict(physics_config)

        gravity = tuple(physics_config.get("gravity", (0, -10)))
        self._default_linear_damping = float(physics_config.get("linear_damping", 0.5))
        self._default_angular_damping = float(physics_config.get("angular_damping", 0.5))

        self._world = world(gravity=gravity, doSleep=True)
        self._bodies = []
        self._joints = []
        self._terrain_bodies = {}
        self._obstacle_bodies = []
        self._obstacle_shapes = []
        self._moving_obstacle = None
        self._moving_obstacle_shape = None
        self._moving_obstacle_2 = None
        self._moving_obstacle_2_shape = None
        self._ice_bodies = []

        self._target_history = []
        self._step_count = 0
        self._current_delay_steps = int(terrain_config.get("initial_delay_steps", 4))
        self._delay_change_counter = 0
        self._last_reported_target = (0.0, 0.0)
        self._target_jump_counter = 0

        self.world = self._world
        self.bodies = self._bodies
        self.joints = self._joints

        self._lose_target_distance = float(
            terrain_config.get("lose_target_distance", LOSE_TARGET_DISTANCE)
        )
        self._target_speed = float(terrain_config.get("target_speed", 1.5))
        self._target_change_interval = float(terrain_config.get("target_change_interval", 1.2))
        self._ground_y_top = float(terrain_config.get("ground_y_top", 1.0))
        self._seeker_mass = float(terrain_config.get("seeker_mass", 20.0))
        self._seeker_radius = float(terrain_config.get("seeker_radius", 0.35))
        self._spawn_x = float(terrain_config.get("spawn_x", 11.0))
        self._spawn_y = float(terrain_config.get("spawn_y", 1.35))

        rng_seed = terrain_config.get("target_rng_seed", None)
        self._delay_rng = random.Random(rng_seed if rng_seed is not None else 42)

        self._create_ground(terrain_config)
        self._create_obstacles(terrain_config)
        self._create_moving_obstacle(terrain_config)
        self._create_moving_obstacle_2(terrain_config)
        self._create_ice_zones(terrain_config)
        self._create_seeker(terrain_config)
        self._init_target(terrain_config)

        # Force applied THIS step (set by previous agent_action; actuation delay)
        self._thrust_x = 0.0
        self._thrust_y = 0.0
        # Force commanded for NEXT step (set by current agent_action)
        self._thrust_next_x = 0.0
        self._thrust_next_y = 0.0
        self._sim_time = 0.0
        # Thrust impulse budget: total F*dt used; exceeding fails
        self._thrust_impulse_used = 0.0
        self._out_of_fuel = False
        self._impulse_budget = float(terrain_config.get("impulse_budget", IMPULSE_BUDGET))
        # Moving corridor: leave bounds = fail
        self._corridor_violation = False
        # Thrust cooldown: after high thrust, max thrust reduced for N steps
        self._cooldown_remaining = 0
        # Activation gate: must stay in activation zone for ACTIVATION_REQUIRED_STEPS consecutive steps
        self._activation_achieved = False
        self._activation_consecutive_steps = 0
        # Body-fixed thruster: seeker heading (radians), thrust applied along this direction only
        self._seeker_heading = 0.0
        self._thrust_next_mag = 0.0
        self._thrust_next_desired_angle = 0.0

    def _create_ground(self, terrain_config: dict):
        """Create horizontal ground (static)."""
        ground_len = 30.0
        ground_h = 0.5
        center_y = self._ground_y_top - ground_h / 2
        ground = self._world.CreateStaticBody(
            position=(ground_len / 2, center_y),
            fixtures=Box2D.b2FixtureDef(
                shape=polygonShape(box=(ground_len / 2, ground_h / 2)),
                friction=float(terrain_config.get("ground_friction", 0.4)),
                restitution=0.0,
            ),
        )
        self._terrain_bodies["ground"] = ground
        self._ground_length = ground_len

    def _create_obstacles(self, terrain_config: dict):
        """Create rectangular obstacles (static)."""
        obstacles_cfg = terrain_config.get("obstacles", OBSTACLES)
        for cx, cy, hw, hh in obstacles_cfg:
            obs = self._world.CreateStaticBody(
                position=(cx, cy),
                fixtures=Box2D.b2FixtureDef(
                    shape=polygonShape(box=(hw, hh)),
                    friction=0.5,
                    restitution=0.1,
                ),
            )
            self._obstacle_bodies.append(obs)
            self._obstacle_shapes.append((hw, hh))

    def _create_moving_obstacle(self, terrain_config: dict):
        """Create first kinematic obstacle."""
        mob_cfg = terrain_config.get("moving_obstacle", MOVING_OBSTACLE)
        if mob_cfg is None:
            return
        cx, cy, hw, hh = mob_cfg[:4]
        body_def = Box2D.b2BodyDef()
        body_def.type = getattr(Box2D.b2, "kinematicBody", 1)
        body_def.position = (cx, cy)
        mob = self._world.CreateBody(body_def)
        mob.CreateFixture(Box2D.b2FixtureDef(
            shape=polygonShape(box=(hw, hh)),
            friction=0.5,
            restitution=0.1,
        ))
        self._moving_obstacle = mob
        self._moving_obstacle_shape = (hw, hh)
        self._moving_obstacle_center_x = cx

    def _create_moving_obstacle_2(self, terrain_config: dict):
        """Create second kinematic obstacle."""
        mob_cfg = terrain_config.get("moving_obstacle_2", MOVING_OBSTACLE_2)
        if mob_cfg is None:
            return
        cx, cy, hw, hh = mob_cfg[:4]
        body_def = Box2D.b2BodyDef()
        body_def.type = getattr(Box2D.b2, "kinematicBody", 1)
        body_def.position = (cx, cy)
        mob = self._world.CreateBody(body_def)
        mob.CreateFixture(Box2D.b2FixtureDef(
            shape=polygonShape(box=(hw, hh)),
            friction=0.5,
            restitution=0.1,
        ))
        self._moving_obstacle_2 = mob
        self._moving_obstacle_2_shape = (hw, hh)
        self._moving_obstacle_2_center_x = cx

    def _create_ice_zones(self, terrain_config: dict):
        """Create low-friction overlay strips."""
        ice_cfg = terrain_config.get("ice_zones", ICE_ZONES)
        for (cx, cy, hw, hh), friction in ice_cfg:
            ice = self._world.CreateStaticBody(
                position=(cx, cy),
                fixtures=Box2D.b2FixtureDef(
                    shape=polygonShape(box=(hw, hh)),
                    friction=friction,
                    restitution=0.0,
                ),
            )
            self._ice_bodies.append((ice, friction))

    def _create_seeker(self, terrain_config: dict):
        """Create seeker vehicle (dynamic circle)."""
        radius = self._seeker_radius
        density = self._seeker_mass / (math.pi * radius * radius)
        seeker = self._world.CreateDynamicBody(
            position=(self._spawn_x, self._spawn_y),
            fixtures=Box2D.b2FixtureDef(
                shape=circleShape(radius=radius),
                density=density,
                friction=0.5,
                restitution=0.1,
            ),
        )
        seeker.linearDamping = self._default_linear_damping
        seeker.angularDamping = self._default_angular_damping
        self._terrain_bodies["seeker"] = seeker

    def _init_target(self, terrain_config: dict):
        """Initialize target state."""
        self._target_x = float(terrain_config.get("target_start_x", 12.0))
        self._target_y = float(terrain_config.get("target_start_y", 2.0))
        self._target_vx = 0.0
        self._target_vy = 0.0
        self._target_change_time = 0.0
        self._target_rng_seed = terrain_config.get("target_rng_seed", None)
        if self._target_rng_seed is not None:
            self._target_rng = random.Random(self._target_rng_seed)
        else:
            self._target_rng = random
        max_delay = max(DELAY_MAX_STEPS, 10)
        for _ in range(max_delay + 1):
            self._target_history.append((self._target_x, self._target_y))
        self._last_reported_target = (self._target_x, self._target_y)

    def get_seeker_position(self):
        """Return seeker center (x, y) in meters."""
        seeker = self._terrain_bodies.get("seeker")
        if seeker is None:
            return (0.0, 0.0)
        return (seeker.position.x, seeker.position.y)

    def get_seeker_velocity(self):
        """Return seeker velocity (vx, vy) in m/s."""
        seeker = self._terrain_bodies.get("seeker")
        if seeker is None:
            return (0.0, 0.0)
        return (seeker.linearVelocity.x, seeker.linearVelocity.y)

    def get_seeker_heading(self):
        """Return seeker thrust heading (radians). Thrust is applied only along this direction; heading turns toward commanded direction at limited rate."""
        return self._seeker_heading

    def get_target_position(self):
        """
        Return target position: variable delay, blind zone, speed-blind, and INTERMITTENT updates.
        - New reading only every TARGET_POSITION_UPDATE_PERIOD steps; otherwise returns last value.
        - When seeker in blind zone (x in [12, 15]), returns last value (no update).
        - When seeker speed exceeds threshold, returns last value (no update) — discover via feedback.
        - When not in blind and (step % period == 0), read from delayed history; else repeat last.
        """
        sx, sy = self.get_seeker_position()
        vx, vy = self.get_seeker_velocity()
        seeker_speed = math.sqrt(vx * vx + vy * vy)
        in_blind = BLIND_ZONE_X_MIN <= sx <= BLIND_ZONE_X_MAX
        speed_blind = seeker_speed > SPEED_BLIND_THRESHOLD
        if in_blind or speed_blind:
            return self._last_reported_target
        # Intermittent: only "sample" target position every PERIOD steps
        if self._step_count % TARGET_POSITION_UPDATE_PERIOD != 0:
            return self._last_reported_target
        delay = min(len(self._target_history) - 1, max(0, self._current_delay_steps))
        if delay >= 0 and self._target_history:
            idx = len(self._target_history) - 1 - delay
            if idx >= 0:
                out = self._target_history[idx]
                self._last_reported_target = out
                return out
        self._last_reported_target = (self._target_x, self._target_y)
        return self._last_reported_target

    def apply_seeker_force(self, force_x, force_y):
        """
        Set thrust for NEXT step (actuation delay). Body-fixed: (fx, fy) is desired direction;
        actual thrust is applied ONLY along seeker's current heading; heading turns toward
        desired direction at limited rate. Magnitude capped (or lower during cooldown).
        """
        fx, fy = float(force_x), float(force_y)
        mag = math.sqrt(fx * fx + fy * fy)
        max_mag = COOLDOWN_MAX_THRUST if self._cooldown_remaining > 0 else MAX_THRUST_MAGNITUDE
        if mag > 1e-9:
            self._thrust_next_mag = min(max_mag, mag)
            self._thrust_next_desired_angle = math.atan2(fy, fx)
        else:
            self._thrust_next_mag = 0.0
            self._thrust_next_desired_angle = self._seeker_heading

    def get_terrain_obstacles(self):
        """Return obstacles as (center_x, center_y, half_width, half_height). Includes moving obstacles."""
        result = [
            (b.position.x, b.position.y, hw, hh)
            for b, (hw, hh) in zip(self._obstacle_bodies, self._obstacle_shapes)
        ]
        if self._moving_obstacle is not None:
            mx, my = self._moving_obstacle.position.x, self._moving_obstacle.position.y
            hw, hh = self._moving_obstacle_shape
            result.append((mx, my, hw, hh))
        if self._moving_obstacle_2 is not None:
            mx, my = self._moving_obstacle_2.position.x, self._moving_obstacle_2.position.y
            hw, hh = self._moving_obstacle_2_shape
            result.append((mx, my, hw, hh))
        return result

    def get_local_friction(self):
        """Return ground friction at seeker position."""
        sx, sy = self.get_seeker_position()
        for (ice_body, friction) in self._ice_bodies:
            pos = ice_body.position
            hw, hh = 1.0, 0.12
            if abs(sx - pos.x) <= hw and abs(sy - pos.y) <= (hh + self._seeker_radius):
                return friction
        return 0.4

    def get_local_wind(self):
        """Return (ax, ay) external acceleration at seeker position. Time-varying in wind zone."""
        sx, sy = self.get_seeker_position()
        x_min, x_max = WIND_ZONE_X
        if x_min <= sx <= x_max:
            wx = WIND_BASE_X + WIND_AMP_X * math.sin(WIND_OMEGA * self._sim_time)
            wy = 0.0
            return (wx, wy)
        return (0.0, 0.0)

    def step(self, time_step):
        """Physics step: update delay, target (with jump), moving obstacles, wind, seeker force."""
        self._step_count += 1
        self._sim_time += time_step

        # Variable delay: change every DELAY_CHANGE_INTERVAL_STEPS
        self._delay_change_counter += 1
        if self._delay_change_counter >= DELAY_CHANGE_INTERVAL_STEPS:
            self._delay_change_counter = 0
            self._current_delay_steps = self._delay_rng.randint(DELAY_MIN_STEPS, DELAY_MAX_STEPS)

        # Store current target before update (for history)
        self._target_history.append((self._target_x, self._target_y))
        if len(self._target_history) > DELAY_MAX_STEPS + 20:
            self._target_history.pop(0)

        # Evasive target: when seeker is close, target accelerates away (agent must discover)
        dist_to_seeker = self.get_distance_to_target()
        if dist_to_seeker < EVASIVE_DISTANCE and dist_to_seeker > 0.01:
            sx, sy = self.get_seeker_position()
            dx = self._target_x - sx
            dy = self._target_y - sy
            inv_d = 1.0 / dist_to_seeker
            ux, uy = dx * inv_d, dy * inv_d
            self._target_vx += ux * EVASIVE_GAIN * time_step
            self._target_vy += uy * EVASIVE_GAIN * time_step
            # Cap target speed so evasive doesn't explode
            tv_mag = math.sqrt(self._target_vx**2 + self._target_vy**2)
            if tv_mag > 2.8:
                s = 2.8 / tv_mag
                self._target_vx *= s
                self._target_vy *= s
        # Target motion
        self._target_change_time += time_step
        if self._target_change_time >= self._target_change_interval:
            self._target_change_time = 0.0
            angle = self._target_rng.uniform(0, 2 * math.pi)
            speed = self._target_speed
            self._target_vx = speed * math.cos(angle)
            self._target_vy = speed * math.sin(angle)
        self._target_x += self._target_vx * time_step
        self._target_y += self._target_vy * time_step

        # Target jump (occasional teleport; breaks naive velocity prediction)
        self._target_jump_counter += 1
        if self._target_jump_counter >= JUMP_INTERVAL_STEPS:
            self._target_jump_counter = 0
            dx = self._target_rng.uniform(-JUMP_MAG, JUMP_MAG)
            dy = self._target_rng.uniform(-JUMP_MAG, JUMP_MAG)
            self._target_x += dx
            self._target_y += dy

        # Constrain target to central region
        margin_x = 4.0
        target_x_min = 6.0
        target_x_max = self._ground_length - 4.0
        self._target_x = max(target_x_min, min(target_x_max, self._target_x))
        target_y_min = self._ground_y_top + 0.5
        target_y_max = self._ground_y_top + 2.0
        self._target_y = max(target_y_min, min(target_y_max, self._target_y))

        # Moving obstacle 1
        if self._moving_obstacle is not None:
            t = self._sim_time
            omega = 2.0 * math.pi / MOVING_PERIOD
            new_x = self._moving_obstacle_center_x + MOVING_AMP * math.sin(omega * t)
            cy = self._moving_obstacle.position.y
            if hasattr(self._moving_obstacle, 'SetTransform'):
                self._moving_obstacle.SetTransform((new_x, cy), 0.0)
            else:
                self._moving_obstacle.transform = ((new_x, cy), 0)

        # Moving obstacle 2
        if self._moving_obstacle_2 is not None:
            t = self._sim_time + MOVING_PHASE_2
            omega = 2.0 * math.pi / MOVING_PERIOD_2
            new_x = self._moving_obstacle_2_center_x + MOVING_AMP_2 * math.sin(omega * t)
            cy = self._moving_obstacle_2.position.y
            if hasattr(self._moving_obstacle_2, 'SetTransform'):
                self._moving_obstacle_2.SetTransform((new_x, cy), 0.0)
            else:
                self._moving_obstacle_2.transform = ((new_x, cy), 0)

        seeker = self._terrain_bodies.get("seeker")
        if seeker is not None:
            wx, wy = self.get_local_wind()
            if wx != 0 or wy != 0:
                wind_force = (self._seeker_mass * wx, self._seeker_mass * wy)
                seeker.ApplyForceToCenter(wind_force, True)
            # Body-fixed: force applied along current heading only; magnitude from last command
            self._thrust_x = self._thrust_next_mag * math.cos(self._seeker_heading)
            self._thrust_y = self._thrust_next_mag * math.sin(self._seeker_heading)
            # Apply thrust from PREVIOUS command (actuation delay); count impulse; update cooldown
            if self._thrust_x != 0.0 or self._thrust_y != 0.0:
                seeker.ApplyForceToCenter((self._thrust_x, self._thrust_y), True)
                thrust_mag = math.sqrt(self._thrust_x ** 2 + self._thrust_y ** 2)
                self._thrust_impulse_used += thrust_mag * time_step
                if self._thrust_impulse_used > self._impulse_budget:
                    self._out_of_fuel = True
                if thrust_mag > COOLDOWN_THRESHOLD:
                    self._cooldown_remaining = COOLDOWN_STEPS
            if self._cooldown_remaining > 0:
                self._cooldown_remaining -= 1
            # Turn heading toward commanded direction (rate-limited)
            delta = self._thrust_next_desired_angle - self._seeker_heading
            while delta > math.pi:
                delta -= 2.0 * math.pi
            while delta < -math.pi:
                delta += 2.0 * math.pi
            step = max(-MAX_ANGULAR_RATE, min(MAX_ANGULAR_RATE, delta))
            self._seeker_heading += step
            while self._seeker_heading > math.pi:
                self._seeker_heading -= 2.0 * math.pi
            while self._seeker_heading < -math.pi:
                self._seeker_heading += 2.0 * math.pi
        self._world.Step(time_step, 10, 10)

        # Moving corridor: fail if seeker leaves allowed x bounds (small tolerance for numerics)
        if seeker is not None and not self._corridor_violation:
            sx, _ = self.get_seeker_position()
            x_lo, x_hi = self._corridor_bounds_at_time(self._sim_time)
            tol = 0.02
            if sx < x_lo - tol or sx > x_hi + tol:
                self._corridor_violation = True

        # Activation gate: count consecutive steps inside activation zone
        if seeker is not None and not self._activation_achieved:
            sx, _ = self.get_seeker_position()
            if ACTIVATION_ZONE_X_MIN <= sx <= ACTIVATION_ZONE_X_MAX:
                self._activation_consecutive_steps += 1
                if self._activation_consecutive_steps >= ACTIVATION_REQUIRED_STEPS:
                    self._activation_achieved = True
            else:
                self._activation_consecutive_steps = 0

    def get_distance_to_target(self):
        """Return distance (m) from seeker to actual (current) target."""
        sx, sy = self.get_seeker_position()
        dx = self._target_x - sx
        dy = self._target_y - sy
        return math.sqrt(dx * dx + dy * dy)

    def get_target_position_true(self):
        """Return actual current target position (for evaluator/feedback only)."""
        return (self._target_x, self._target_y)

    def get_target_velocity_true(self):
        """Return actual current target velocity (vx, vy) in m/s (for evaluator only; not exposed to agent)."""
        return (self._target_vx, self._target_vy)

    def _corridor_bounds_at_time(self, t):
        """Return (x_min, x_max) for moving corridor at time t (seconds). Pinch narrows corridor periodically."""
        s = math.sin(CORRIDOR_OMEGA * t)
        x_lo = CORRIDOR_X_BASE_L + CORRIDOR_AMP * s
        x_hi = CORRIDOR_X_BASE_R - CORRIDOR_AMP * s
        pinch = math.sin(CORRIDOR_PINCH_OMEGA * t - CORRIDOR_PINCH_PHASE)
        if pinch > CORRIDOR_PINCH_THRESHOLD:
            x_lo += CORRIDOR_PINCH_MARGIN
            x_hi -= CORRIDOR_PINCH_MARGIN
        return (x_lo, x_hi)

    def get_corridor_bounds(self):
        """Return current allowed (x_min, x_max) for the seeker. Leaving this corridor fails the run."""
        return self._corridor_bounds_at_time(self._sim_time)

    def get_remaining_impulse_budget(self):
        """Return remaining thrust impulse budget (N·s). Exceeding the total budget fails the run."""
        return max(0.0, self._impulse_budget - self._thrust_impulse_used)

    def get_out_of_fuel(self):
        """Return True if thrust budget has been exceeded (for evaluator)."""
        return self._out_of_fuel

    def get_corridor_violation(self):
        """Return True if seeker has left the allowed corridor (for evaluator)."""
        return self._corridor_violation

    def get_activation_achieved(self):
        """Return True if seeker has completed activation (consecutive steps in activation zone). For evaluator."""
        return self._activation_achieved

    def get_terrain_bounds(self):
        """Return terrain bounds for evaluator/renderer."""
        return {
            "ground_y_top": self._ground_y_top,
            "ground_length": self._ground_length,
            "seeker_radius": self._seeker_radius,
            "lose_target_distance": self._lose_target_distance,
        }

    def get_seeker_body(self):
        """Return the seeker body."""
        return self._terrain_bodies.get("seeker")

    def get_ground_y_top(self):
        """Return y coordinate of ground top surface."""
        return self._ground_y_top
