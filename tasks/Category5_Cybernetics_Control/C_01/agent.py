import math

STATE = {}

def robust_control(sandbox, cart, step_count, gravity, pole_length, delay, swingup):
    global STATE
    sid = id(sandbox)
    if step_count == 0 or sid not in STATE:
        STATE[sid] = {
            'mode': 'swing' if swingup else 'bal',
            'it': 0.0,
            'timer': 0
        }
    s = STATE[sid]
    theta_raw = sandbox.get_pole_angle()
    omega = sandbox.get_pole_angular_velocity()
    x = sandbox.get_cart_position()
    v = sandbox.get_cart_velocity()
    theta = math.atan2(math.sin(theta_raw), math.cos(theta_raw))
    dt = 1.0/60.0
    comp = delay + 1.0 if delay > 0 else 0.5
    t_est = math.atan2(math.sin(theta + omega * dt * comp),
                       math.cos(theta + omega * dt * comp))
    if s['mode'] == 'swing':
        if abs(t_est) < 0.5 and abs(omega) < 5.0:
            s['mode'] = 'bal'
            s['it'] = 0.0
    else:
        if abs(t_est) > 0.8:
            s['mode'] = 'swing'
    if s['mode'] == 'swing':
        force = -450.0 * math.copysign(1.0, omega * math.cos(theta))
        if abs(omega) < 0.1:
            force = 450.0 if (step_count // 30) % 2 == 0 else -450.0
        if x + v * 0.4 > 15.0: force = -450.0
        elif x + v * 0.4 < 5.0: force = 450.0
        sandbox.apply_cart_force(max(-450.0, min(450.0, force)))
    else:
        s['timer'] += 1
        s['it'] += t_est * dt
        g_scale = gravity / 9.8
        l_scale = pole_length / 2.0
        kp_th = -8000.0 * g_scale * l_scale
        kd_th = -2000.0 * g_scale * math.sqrt(l_scale)
        ki_th = -2000.0 * g_scale
        kp_x = -250.0
        kd_x = -800.0
        force = kp_th * t_est + kd_th * omega + ki_th * s['it'] + kp_x * (x - 10.0) + kd_x * v
        sandbox.apply_cart_force(max(-450.0, min(450.0, force)))

def build_agent(sandbox): return sandbox.get_cart_body()

def agent_action(sandbox, cart, step_count):
    robust_control(sandbox, cart, step_count, 9.8, 2.0, 0, False)

def build_agent_stage_1(sandbox): return sandbox.get_cart_body()

def agent_action_stage_1(sandbox, cart, step_count):
    robust_control(sandbox, cart, step_count, 9.8, 2.0, 0, True)

def build_agent_stage_2(sandbox): return sandbox.get_cart_body()

def agent_action_stage_2(sandbox, cart, step_count):
    robust_control(sandbox, cart, step_count, 11.0, 2.0, 0, True)

def build_agent_stage_3(sandbox): return sandbox.get_cart_body()

def agent_action_stage_3(sandbox, cart, step_count):
    robust_control(sandbox, cart, step_count, 9.8, 2.0, 2, True)

def build_agent_stage_4(sandbox): return sandbox.get_cart_body()

def agent_action_stage_4(sandbox, cart, step_count):
    robust_control(sandbox, cart, step_count, 10.5, 2.1, 0, True)
