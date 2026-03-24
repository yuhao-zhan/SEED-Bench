import math

_INITIAL_REF_BARRIER_Y_BOTTOM = 20.0

def _get_thrust_torque_limits(sandbox):
    return getattr(sandbox, '_max_thrust', 600.0), getattr(sandbox, '_max_torque', 120.0)

def _lander_mass(sandbox):
    return float(getattr(sandbox, '_lander_mass', 50.0))

def _sim_dt(sandbox):
    return float(getattr(sandbox, "_time_step", 1.0 / 60.0))

def _gravity_magnitude(sandbox):
    try:
        gy = float(sandbox.world.gravity[1])
        return abs(gy) if abs(gy) > 1e-6 else 10.0
    except (AttributeError, TypeError, ValueError, IndexError):
        return 10.0

def _platform_kinematics(sandbox, t):
    base = float(getattr(sandbox, "_platform_center_base", 17.0))
    amp = float(getattr(sandbox, "_platform_amplitude", 1.8))
    per = float(getattr(sandbox, "_platform_period", 6.0))
    if per <= 1e-6:
        per = 6.0
    w = 2.0 * math.pi / per
    plat_x = base + amp * math.sin(w * t)
    plat_vx = amp * w * math.cos(w * t)
    return plat_x, plat_vx

def _barrier_geometry(sandbox):
    xr = float(getattr(sandbox, "_barrier_x_right", 13.5))
    yt = float(getattr(sandbox, "_barrier_y_top", 6.0))
    yb = float(getattr(sandbox, "_barrier_y_bottom", 20.0))
    return xr, yt, yb

def _corridor_target_altitude(yt, yb, clearance_obstacle=2.5, clearance_ceiling=1.5):
    y_lo = yt + clearance_obstacle
    y_hi = yb - clearance_ceiling
    if y_hi <= y_lo:
        return 0.5 * (yt + yb)
    inner = y_hi - y_lo
    y_pref = y_lo + 0.35 * inner
    return max(y_lo, min(y_pref, y_hi))

def _thrust_delay_steps(sandbox):
    if hasattr(sandbox, "get_thrust_delay_steps"):
        return int(sandbox.get_thrust_delay_steps())
    return int(getattr(sandbox, "_thrust_delay_steps", 3))

class BaselineLanderAgent:
    def __init__(self, agent_body):
        self.agent_body = agent_body
    @property
    def position(self): return self.agent_body.position
    @property
    def linearVelocity(self): return self.agent_body.linearVelocity
    def act(self, sandbox, step_count):
        pos, vel = self.agent_body.position, self.agent_body.linearVelocity
        x, y, vx, vy = pos.x, pos.y, vel.x, vel.y
        angle, omega = self.agent_body.angle, self.agent_body.angularVelocity
        dt = _sim_dt(sandbox)
        t_sim = step_count * dt
        t_p = t_sim + 0.15
        plat_x, plat_vx = _platform_kinematics(sandbox, t_p)
        xr, yt, _yb_actual = _barrier_geometry(sandbox)
        if x < xr + 0.5:
            tx = xr + 1.5
            ty = _corridor_target_altitude(
                yt, _INITIAL_REF_BARRIER_Y_BOTTOM, clearance_obstacle=2.5, clearance_ceiling=1.5
            )
            tvx, tvy = 2.5, 0.0
        else:
            tx, ty = plat_x, 1.05
            tvx, tvy = plat_vx, -1.2
            if y < 4.0:
                tvy = -0.25
        g, m = _gravity_magnitude(sandbox), _lander_mass(sandbox)
        ay = 4.0 * (ty - y) + 10.0 * (tvy - vy)
        thrust = m * (g + ay)
        thrust /= max(0.5, math.cos(angle))
        max_thrust, max_torque = _get_thrust_torque_limits(sandbox)
        thrust = max(0.0, min(max_thrust, thrust))
        ax = 2.5 * (tx - x) + 5.0 * (tvx - vx)
        target_angle = max(-0.6, min(0.6, -0.2 * ax))
        if y < 3.0: target_angle = 0.0
        torque = 1000.0 * (target_angle - angle) - 250.0 * omega
        torque = max(-max_torque, min(max_torque, torque))
        sandbox.apply_thrust(thrust, torque)

def build_agent(sandbox): return BaselineLanderAgent(sandbox.get_lander_body())

def agent_action(sandbox, agent, step_count): agent.act(sandbox, step_count)

def build_agent_stage_1(sandbox): return sandbox.get_lander_body()

def agent_action_stage_1(sandbox, agent, step_count):
    dt = _sim_dt(sandbox)
    pos, vel = agent.position, agent.linearVelocity
    x, y, vx, vy = pos.x, pos.y, vel.x, vel.y
    angle, omega = agent.angle, agent.angularVelocity
    plat_x, plat_vx = _platform_kinematics(sandbox, step_count * dt + 0.15)
    xr, yt, yb = _barrier_geometry(sandbox)
    if x < xr + 0.5:
        tx = xr + 1.5
        ty = max(yt + 2.5, min(13.0, yb - 1.5))
        tvx, tvy = 2.5, 0.0
    else:
        tx, ty, tvx, tvy = plat_x, 1.05, plat_vx, -0.3
        if y < 4.0: tvy = -0.15
        if y < 2.0: tvy = -0.1
    g, m = _gravity_magnitude(sandbox), _lander_mass(sandbox)
    ay = 10.0 * (ty - y) + 15.0 * (tvy - vy)
    thrust = m * (g + ay) / max(0.1, math.cos(angle))
    max_thrust, _ = _get_thrust_torque_limits(sandbox)
    thrust = max(0.0, min(max_thrust, thrust))
    ax = 10.0 * (tx - x) + 15.0 * (tvx - vx)
    target_angle = max(-0.4, min(0.4, -0.1 * ax))
    if y < 2.0: target_angle = 0.0
    torque = 3000.0 * (target_angle - angle) - 800.0 * omega
    max_torque = _get_thrust_torque_limits(sandbox)[1]
    torque = max(-max_torque, min(max_torque, torque))
    sandbox.apply_thrust(thrust, torque)

def build_agent_stage_2(sandbox): return sandbox.get_lander_body()

def agent_action_stage_2(sandbox, agent, step_count):
    dt = _sim_dt(sandbox)
    delay_t = 0.22
    g = _gravity_magnitude(sandbox)
    pos, vel = agent.position, agent.linearVelocity
    x, y, vx, vy = pos.x, pos.y, vel.x, vel.y
    angle, omega = agent.angle, agent.angularVelocity
    x_p = x + vx * delay_t
    y_p = y + vy * delay_t - 0.5 * g * delay_t**2
    vx_p = vx
    vy_p = vy - g * delay_t
    angle_p = angle + omega * delay_t
    ds = _thrust_delay_steps(sandbox)
    plat_x, plat_vx = _platform_kinematics(sandbox, (step_count + ds) * dt + 0.15)
    xr, yt, yb = _barrier_geometry(sandbox)
    if x < xr + 1.0:
        tx = xr + 2.5
        ty = max(yt + 2.5, min(18.0, yb - 1.5))
        tvx, tvy = 2.5, 0.0
        if y < ty - 2.0:
            tvx = 0.5
    else:
        tx, ty, tvx, tvy = plat_x, 1.05, plat_vx, -0.4
        if y < 4.0: tvy = -0.15
    m = _lander_mass(sandbox)
    ay = 15.0 * (ty - y_p) + 25.0 * (tvy - vy_p)
    thrust = m * (g + ay) / max(0.1, math.cos(angle_p))
    max_thrust, max_torque = _get_thrust_torque_limits(sandbox)
    thrust = max(0.0, min(max_thrust, thrust))
    ax = 4.0 * (tx - x_p) + 8.0 * (tvx - vx_p)
    target_angle = max(-0.35, min(0.35, -0.1 * ax))
    if y < 4.5: target_angle = 0.0
    torque = 5000.0 * (target_angle - angle_p) - 1500.0 * omega
    torque = max(-max_torque, min(max_torque, torque))
    sandbox.apply_thrust(thrust, torque)

def build_agent_stage_3(sandbox): return sandbox.get_lander_body()

def agent_action_stage_3(sandbox, agent, step_count):
    dt = _sim_dt(sandbox)
    pos, vel = agent.position, agent.linearVelocity
    x, y, vx, vy = pos.x, pos.y, vel.x, vel.y
    angle, omega = agent.angle, agent.angularVelocity
    plat_x, plat_vx = _platform_kinematics(sandbox, step_count * dt + 0.15)
    xr, yt, yb = _barrier_geometry(sandbox)
    if x < xr + 0.3:
        tx = xr + 1.5
        ty = max(yt + 2.5, min(9.0, yb - 1.5))
        tvx, tvy = 2.5, 0.0
    else:
        tx, ty, tvx, tvy = plat_x, 1.05, plat_vx, -0.6
        if y < 4.0: tvy = -0.15
    g, m = _gravity_magnitude(sandbox), _lander_mass(sandbox)
    ay = 8.0 * (ty - y) + 12.0 * (tvy - vy)
    thrust = m * (g + ay) / max(0.1, math.cos(angle))
    max_thrust, max_torque = _get_thrust_torque_limits(sandbox)
    thrust = max(0.0, min(max_thrust, thrust))
    ax = 4.0 * (tx - x) + 8.0 * (tvx - vx)
    target_angle = max(-0.5, min(0.5, -0.1 * ax))
    if y < 2.0: target_angle = 0.0
    torque = 3000.0 * (target_angle - angle) - 800.0 * omega
    torque = max(-max_torque, min(max_torque, torque))
    sandbox.apply_thrust(thrust, torque)

def build_agent_stage_4(sandbox): return sandbox.get_lander_body()

def agent_action_stage_4(sandbox, agent, step_count):
    dt = _sim_dt(sandbox)
    delay_t = 0.22
    g = _gravity_magnitude(sandbox)
    pos, vel = agent.position, agent.linearVelocity
    x, y, vx, vy = pos.x, pos.y, vel.x, vel.y
    angle, omega = agent.angle, agent.angularVelocity
    angle_p = angle + omega * delay_t
    vx_p = vx
    vy_p = vy - g * delay_t
    x_p = x + vx * delay_t
    y_p = y + vy * delay_t - 0.5 * g * delay_t**2
    ds = _thrust_delay_steps(sandbox)
    plat_x, plat_vx = _platform_kinematics(sandbox, (step_count + ds) * dt + 0.15)
    xr, yt, yb = _barrier_geometry(sandbox)
    if x < xr + 1.7:
        tx = xr + 3.0
        ty = max(yt + 2.5, min(13.5, yb - 1.5))
        tvx, tvy = 0.4, 0.0
    else:
        tx, ty, tvx, tvy = plat_x, 1.05, plat_vx, -0.2
        if y < 4.0:
            tvy = -0.10
            tvx = plat_vx
    m = _lander_mass(sandbox)
    ay = 15.0 * (ty - y_p) + 20.0 * (tvy - vy_p)
    acc_y = max(3.0, g + ay)
    thrust = m * acc_y / max(0.1, math.cos(angle_p))
    max_thrust, max_torque = _get_thrust_torque_limits(sandbox)
    thrust = max(0.0, min(max_thrust, thrust))
    ax = 2.0 * (tx - x_p) + 6.0 * (tvx - vx_p)
    target_angle = max(-0.35, min(0.35, -0.1 * ax))
    if y < 3.0: target_angle = 0.0
    tkp, tkd = 4000.0, 1200.0
    if y < 3.0:
        tkp, tkd = 2000.0, 800.0
    torque = tkp * (target_angle - angle_p) - tkd * omega
    torque = max(-max_torque, min(max_torque, torque))
    sandbox.apply_thrust(thrust, torque)
