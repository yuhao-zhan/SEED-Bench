"""
C-04: The Escaper (Simplified for verification)
"""

import math
import Box2D
from Box2D import b2World, b2PolygonShape, b2CircleShape, b2FixtureDef, b2BodyDef, b2_dynamicBody, b2_staticBody

# Simulation constants
FPS = 60
TIME_STEP = 1.0 / FPS
VEL_ITERS, POS_ITERS = 10, 10
# Command / state history caps (prompt documents these; keep in sync)
FORCE_HISTORY_CAP = 100
STATE_HISTORY_CAP = 300
# Episode length (single source of truth; prompt and evaluation/utils TASK_MAX_STEPS category_5_04)
MAX_STEPS = 250000

# Physical constants
AGENT_MASS = 5.0
WHISKER_RANGE = 3.0
HOLD_STEPS = 5
LINEAR_DAMPING = 1.0
RESTITUTION = 0.1

# Maze layout (walls)
MAZE_WALLS = [
    (0.0, 0.0, 20.0, 0.5),    # Floor
    (0.0, 2.5, 20.0, 0.5),    # Ceiling
    (0.0, 0.0, 0.5, 3.0),     # Left Wall
    (20.0, 0.0, 0.5, 3.0),    # Right Wall
    (5.0, 0.0, 0.2, 1.0),     # Internal Wall 1 (Shortened)
    (9.0, 1.8, 0.2, 1.2),     # Internal Wall 2 (Shortened)
    (14.0, 1.8, 0.2, 1.2),    # Internal Wall 3 (Shortened)
]

# Physical constants
WIND_OSCILLATION_AMP = 5.0 # Reduced
WIND_OSCILLATION_OMEGA = 0.05
# Reference height (m) for shear term (y − ref); matches default spawn y
SHEAR_WIND_REFERENCE_Y = 1.5

# Behavioral unlock: commanded Fx (after lag) must be < BACKWARD_FX_THRESHOLD (e.g. threshold−1 N satisfies)
BACKWARD_FX_THRESHOLD = -34.0
BACKWARD_SPEED_MAX = 100.0
BACKWARD_STEPS_REQUIRED = HOLD_STEPS

# Default structural impulse scale k (N·s per kg agent mass); overridable via physics_config
STRUCTURAL_IMPULSE_SCALE_K = 25.0
ACTIVATION_X_MIN = 5.0 
ACTIVATION_X_MAX = 10.0 

# Higher friction for stability
SLIP_FRICTION = 0.5
# One-way current
ONEWAY_X = 10.2
ONEWAY_FORCE_RIGHT = 50.0

# Lock corridor (must match prompt / feedback)
LOCK_GATE_X_MIN = 12.0
LOCK_GATE_X_MAX = 16.0
LOCK_GATE_FX = -1200.0

# Exit zone (single source of truth for success + bounds reporting)
EXIT_X_MIN = 15.0
EXIT_Y_MIN = 0.5
EXIT_Y_MAX = 2.5

class Sandbox:
    def __init__(self, terrain_config: dict = None, physics_config: dict = None):
        if physics_config is None: physics_config = {}
        if terrain_config is None: terrain_config = {}
        self.physics_config = physics_config
        self.terrain_config = terrain_config
        
        g_val = physics_config.get("gravity", -9.8)
        if isinstance(g_val, (list, tuple)):
            g_y = float(g_val[1])
        else:
            g_y = float(g_val)
        self._world = b2World(gravity=(0, g_y))
        self._terrain_bodies = {}
        self._current_step = 0
        
        self._current_force_back = float(physics_config.get("current_force_back", 0.0))
        self._shear_wind_gradient = float(physics_config.get("shear_wind_gradient", 0.0))
        
        self._whisker_delay_steps = int(terrain_config.get("whisker_delay_steps", 0))
        self._position_delay_steps = int(terrain_config.get("position_delay_steps", 0))
        self._whisker_blind_front_x_lo = float(terrain_config.get("whisker_blind_front_x_lo", -999.0))
        self._whisker_blind_front_x_hi = float(terrain_config.get("whisker_blind_front_x_hi", -999.0))
        
        self._control_reversal_x_min = float(physics_config.get("control_reversal_x_min", -999.0))
        self._control_reversal_x_max = float(physics_config.get("control_reversal_x_max", -999.0))
        self._fluid_drag_x_min = float(physics_config.get("fluid_drag_x_min", -999.0))
        self._fluid_drag_x_max = float(physics_config.get("fluid_drag_x_max", -999.0))
        self._fluid_drag_coeff = float(physics_config.get("fluid_drag_coeff", 0.0))
        self._magnetic_floor_y_max = float(physics_config.get("magnetic_floor_y_max", -999.0))
        self._magnetic_floor_force = float(physics_config.get("magnetic_floor_force", 0.0))
        
        self._control_lag_steps = int(physics_config.get("control_lag_steps", 0))
        self._turbulence_intensity = float(physics_config.get("turbulence_intensity", 0.0))
        
        # New configurable physical parameters
        self._slip_friction = float(physics_config.get("slip_friction", SLIP_FRICTION))
        self._oneway_x = float(terrain_config.get("oneway_x", ONEWAY_X))
        self._oneway_force_right = float(physics_config.get("oneway_force_right", ONEWAY_FORCE_RIGHT))
        self._lock_gate_fx = float(physics_config.get("lock_gate_fx", LOCK_GATE_FX))
        self._lock_gate_x_min = float(physics_config.get("lock_gate_x_min", LOCK_GATE_X_MIN))
        self._lock_gate_x_max = float(physics_config.get("lock_gate_x_max", LOCK_GATE_X_MAX))
        self._activation_x_min = float(physics_config.get("activation_x_min", ACTIVATION_X_MIN))
        self._activation_x_max = float(physics_config.get("activation_x_max", ACTIVATION_X_MAX))
        self._wind_oscillation_amp = float(physics_config.get("wind_oscillation_amp", WIND_OSCILLATION_AMP))
        self._wind_oscillation_omega = float(physics_config.get("wind_oscillation_omega", WIND_OSCILLATION_OMEGA))
        self._shear_wind_reference_y = float(
            physics_config.get("shear_wind_reference_y", SHEAR_WIND_REFERENCE_Y)
        )

        # Impulse scale k (N·s per kg of agent mass → compare to normal impulse in N·s).
        # Legacy key `collision_velocity_limit` is accepted as an alias for the same numeric k (historical name).
        self._structural_impulse_scale_k = float(
            physics_config.get(
                "structural_impulse_scale_k",
                physics_config.get("collision_velocity_limit", STRUCTURAL_IMPULSE_SCALE_K),
            )
        )

        self._backward_fx_threshold = float(
            physics_config.get("backward_fx_threshold", BACKWARD_FX_THRESHOLD)
        )
        self._backward_speed_max = float(
            physics_config.get("backward_speed_max", BACKWARD_SPEED_MAX)
        )
        self._backward_steps_required = int(
            physics_config.get("backward_steps_required", BACKWARD_STEPS_REQUIRED)
        )

        self._force_history = []
        
        self._behavioral_unlock = False
        self._backward_steps = 0
        self._is_destroyed = False
        self._destruction_reason = None

        self._create_maze(terrain_config)
        self._create_agent(terrain_config)

        # Initialize history with starting state for consistent delay reporting from step 0
        p_init = (self._terrain_bodies["agent"].position.x, self._terrain_bodies["agent"].position.y)
        self._position_history = [p_init]
        self._whisker_readings_history = [tuple(self.get_whisker_readings())]

        self._force_x = 0.0
        self._force_y = 0.0
        self.MAX_STEPS = int(physics_config.get("max_steps", MAX_STEPS))

    def _create_maze(self, terrain_config: dict):
        walls = list(MAZE_WALLS)
        overrides = terrain_config.get("wall_overrides", {})
        for idx_str, val in overrides.items():
            walls[int(idx_str)] = val

        for i, (x, y, w, h) in enumerate(walls):
            body = self._world.CreateStaticBody(
                position=(x + w/2, y + h/2),
                shapes=b2PolygonShape(box=(w/2, h/2)),
            )
            body.fixtures[0].friction = self._slip_friction
            self._terrain_bodies[f"wall_{i}"] = body

    def _create_agent(self, terrain_config: dict):
        self._agent_radius = 0.2
        body_def = b2BodyDef(
            type=b2_dynamicBody,
            position=(2.0, 1.5),
            fixedRotation=True,
            linearDamping=LINEAR_DAMPING,
        )
        agent = self._world.CreateBody(body_def)
        shape = b2CircleShape(radius=self._agent_radius)
        fixture_def = b2FixtureDef(
            shape=shape,
            density=AGENT_MASS / (math.pi * self._agent_radius**2),
            friction=self._slip_friction,
            restitution=RESTITUTION,
        )
        agent.CreateFixture(fixture_def)
        self._terrain_bodies["agent"] = agent
        
        class MyContactListener(Box2D.b2ContactListener):
            def __init__(self, sandbox):
                super().__init__()
                self.sandbox = sandbox
            def PostSolve(self, contact, impulse):
                for i in range(contact.manifold.pointCount):
                    if impulse.normalImpulses[i] > self.sandbox._structural_impulse_scale_k * AGENT_MASS:
                        self.sandbox._is_destroyed = True
                        self.sandbox._destruction_reason = f"Structural Failure: Collision impulse {impulse.normalImpulses[i]:.1f} exceeded limit."
        
        self._world.contactListener = MyContactListener(self)

    def _raycast(self, p1, p2, ignore_body):
        class RayCastCallback(Box2D.b2RayCastCallback):
            def __init__(self, ignore):
                super().__init__()
                self.ignore = ignore
                self.hit_fraction = 1.0
            def ReportFixture(self, fixture, point, normal, fraction):
                if fixture.body == self.ignore:
                    return -1
                self.hit_fraction = fraction
                return 0
        callback = RayCastCallback(ignore_body)
        self._world.RayCast(callback, p1, p2)
        return callback.hit_fraction

    def get_agent_position(self):
        agent = self._terrain_bodies.get("agent")
        if agent is None: return (0.0, 0.0)
        p = (agent.position.x, agent.position.y)
        delay = max(0, self._position_delay_steps)
        if delay > 0:
            if len(self._position_history) > delay:
                return self._position_history[-(delay + 1)]
            return self._position_history[0]
        return p

    def get_agent_velocity(self):
        agent = self._terrain_bodies.get("agent")
        if agent is None: return (0.0, 0.0)
        return (agent.linearVelocity.x, agent.linearVelocity.y)

    def get_whisker_readings(self):
        agent = self._terrain_bodies.get("agent")
        if agent is None: return [WHISKER_RANGE] * 3
        
        x, y = agent.position.x, agent.position.y
        if self._whisker_blind_front_x_lo <= x <= self._whisker_blind_front_x_hi:
            return [WHISKER_RANGE] * 3

        delay = max(0, self._whisker_delay_steps)
        if delay > 0:
            if len(self._whisker_readings_history) > delay:
                return list(self._whisker_readings_history[-(delay + 1)])
            return list(self._whisker_readings_history[0])
        
        r = WHISKER_RANGE
        directions = [(1, 0), (0, 1), (0, -1)]
        out = []
        for dx, dy in directions:
            p2 = (x + dx * r, y + dy * r)
            frac = self._raycast((x, y), p2, agent)
            out.append(frac * r)
        return out

    def apply_agent_force(self, force_x, force_y):
        self._force_history.append((float(force_x), float(force_y)))
        if len(self._force_history) > FORCE_HISTORY_CAP:
            self._force_history.pop(0)
        
        delay = max(0, self._control_lag_steps)
        if delay > 0 and len(self._force_history) > delay:
            fx, fy = self._force_history[-(delay + 1)]
        else:
            fx, fy = float(force_x), float(force_y)
        
        self._force_x, self._force_y = fx, fy

    def step(self, time_step):
        import random
        if self._is_destroyed:
            self._world.Step(time_step, VEL_ITERS, POS_ITERS)
            self._current_step += 1
            return
        agent = self._terrain_bodies.get("agent")
        if agent is not None:
            x, y = agent.position.x, agent.position.y
            # Reported pose (matches exit evaluation when position_delay_steps > 0)
            px, py = self.get_agent_position()
            vx, vy = agent.linearVelocity.x, agent.linearVelocity.y
            speed = math.sqrt(vx * vx + vy * vy)
            
            # Record history BEFORE potential delay in readings
            # (Though in apply_agent_force we already handled control lag)
            # Actually history should be of the TRUE state
            self._position_history.append((x, y))
            if len(self._position_history) > STATE_HISTORY_CAP:
                self._position_history.pop(0)
            
            # For whisker history, we need the "true" readings at that moment
            r = WHISKER_RANGE
            directions = [(1, 0), (0, 1), (0, -1)]
            true_whiskers = []
            for dx, dy in directions:
                p2 = (x + dx * r, y + dy * r)
                frac = self._raycast((x, y), p2, agent)
                true_whiskers.append(frac * r)
            self._whisker_readings_history.append(tuple(true_whiskers))
            if len(self._whisker_readings_history) > STATE_HISTORY_CAP:
                self._whisker_readings_history.pop(0)

            # Unlock uses reported position (same frame as exit zone) and commanded Fx after control lag
            if (
                self._activation_x_min <= px <= self._activation_x_max
                and self._force_x < self._backward_fx_threshold
                and speed < self._backward_speed_max
            ):
                self._backward_steps += 1
                if self._backward_steps >= self._backward_steps_required:
                    self._behavioral_unlock = True
            else:
                self._backward_steps = 0

            # Apply forces with anomalies
            force_x_applied = self._force_x
            force_y_applied = self._force_y
            
            # 1. Control Reversal Zone (X-axis only): use reported x like unlock/exit (not raw body x)
            if self._control_reversal_x_min <= px <= self._control_reversal_x_max:
                force_x_applied *= -1.0
                
            agent.ApplyForceToCenter((force_x_applied, force_y_applied), True)
            
            # 2. Viscous Fluid Drag Zone (reported px, same frame as unlock/exit/lock/one-way)
            if self._fluid_drag_x_min <= px <= self._fluid_drag_x_max:
                drag_x = -self._fluid_drag_coeff * vx * abs(vx)
                drag_y = -self._fluid_drag_coeff * vy * abs(vy)
                agent.ApplyForceToCenter((drag_x, drag_y), True)
                
            # 3. Magnetic Floor Anomaly
            if y < self._magnetic_floor_y_max:
                agent.ApplyForceToCenter((0.0, self._magnetic_floor_force), True)

            # 4. Turbulence
            if self._turbulence_intensity > 0:
                tx = (random.random() - 0.5) * self._turbulence_intensity
                ty_turb = (random.random() - 0.5) * self._turbulence_intensity
                agent.ApplyForceToCenter((tx, ty_turb), True)

            osc = self._wind_oscillation_amp * math.sin(self._wind_oscillation_omega * self._current_step)
            wind_x = (
                -self._current_force_back
                + self._shear_wind_gradient * (y - self._shear_wind_reference_y)
                + osc
            )
            agent.ApplyForceToCenter((wind_x, 0), True)
            if px > self._oneway_x:
                agent.ApplyForceToCenter((self._oneway_force_right, 0), True)

            # 5. Lock Gate (reported px; consistent with evaluator metrics / feedback)
            if not self._behavioral_unlock and self._lock_gate_x_min <= px <= self._lock_gate_x_max:
                agent.ApplyForceToCenter((self._lock_gate_fx, 0.0), True)

        self._world.Step(time_step, VEL_ITERS, POS_ITERS)
        self._current_step += 1

    def get_metrics(self):
        agent = self._terrain_bodies.get("agent")
        if agent is None:
            return {}
        px, py = self.get_agent_position()
        return {"x": px, "y": py, "unlocked": self._behavioral_unlock, "step": self._current_step}

    def get_agent_body(self): return self._terrain_bodies.get("agent")
    def get_terrain_bounds(self):
        return {
            "x_min": 0.0,
            "x_max": 20.0,
            "y_min": 0.0,
            "y_max": 3.0,
            "exit_x_min": EXIT_X_MIN,
            "exit_y_min": EXIT_Y_MIN,
            "exit_y_max": EXIT_Y_MAX,
        }

    def get_agent_components(self):
        return {
            "agent": self.get_agent_body(),
            "exit_x_min": EXIT_X_MIN,
            "exit_y_min": EXIT_Y_MIN,
            "exit_y_max": EXIT_Y_MAX,
        }

    def has_reached_exit(self):
        """Uses get_agent_position() so success and reported metrics stay consistent when position_delay_steps is set."""
        if self._is_destroyed:
            return False
        b = self.get_terrain_bounds()
        ex, ey0, ey1 = b["exit_x_min"], b["exit_y_min"], b["exit_y_max"]
        x, y = self.get_agent_position()
        return x >= ex and ey0 <= y <= ey1
    def get_whisker_max_range(self): return WHISKER_RANGE
    def is_destroyed(self): return self._is_destroyed
    def get_destruction_reason(self): return self._destruction_reason
    @property
    def world(self): return self._world
