import math

STATE = {}

def robust_control(sandbox, cart, step_count, gravity, pole_length, delay, swingup):
    global STATE
    sid = id(sandbox)
    if step_count == 0 or sid not in STATE:
        STATE[sid] = {'mode': 'swing' if swingup else 'bal', 'it': 0.0, 'target_x': 10.0}
    s = STATE[sid]
    theta_raw = sandbox.get_pole_angle()
    omega_raw = sandbox.get_pole_angular_velocity()
    x = sandbox.get_cart_position()
    v = sandbox.get_cart_velocity()
    dt = 1.0/60.0
    comp = float(delay) + 1.0 if delay > 0 else 0.5
    theta = math.atan2(math.sin(theta_raw + omega_raw * dt * comp),
                       math.cos(theta_raw + omega_raw * dt * comp))
    omega = omega_raw
    if s['mode'] == 'swing':
        if abs(theta) < 0.25 and abs(omega) < 2.5:
            s['mode'] = 'bal'
            s['it'] = 0.0
            s['target_x'] = max(5.0, min(15.0, x))
    else:
        if abs(theta) > 0.8:
            s['mode'] = 'swing'
    if s['mode'] == 'swing':
        g_eff = gravity / (pole_length / 2.0)
        E = 0.5 * omega**2 + g_eff * (math.cos(theta) - 1.0)
        target_E = 0.0
        err_E = E - target_E
        k_E = 100.0
        force = -k_E * err_E * omega * math.cos(theta)
        if abs(omega) < 0.1 and abs(theta) > 3.0:
            force = 450.0 if (step_count // 15) % 2 == 0 else -450.0
        force -= 10.0 * (x - 10.0) + 20.0 * v
        if x > 17.5 and force > 0: force = -450.0
        elif x < 2.5 and force < 0: force = 450.0
        sandbox.apply_cart_force(max(-450.0, min(450.0, force)))
    else:
        g_scale = gravity / 9.8
        l_scale = pole_length / 2.0
        kp_th = -8000.0 * g_scale * l_scale
        kd_th = -2000.0 * g_scale * math.sqrt(l_scale)
        ki_th = -2000.0 * g_scale
        kp_x = -250.0
        kd_x = -800.0
        if delay > 0:
            kd_th *= 1.5
        s['it'] += theta * dt
        s['it'] = max(-0.2, min(0.2, s['it']))
        force = (kp_th * theta + kd_th * omega + ki_th * s['it'] +
                 kp_x * (x - s['target_x']) + kd_x * v)
        if x > 17.5: force = -450.0
        elif x < 2.5: force = 450.0
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
