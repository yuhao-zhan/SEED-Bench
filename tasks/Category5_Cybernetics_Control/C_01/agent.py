import math

def normalize_angle(theta):
    return math.atan2(math.sin(theta), math.cos(theta))

def build_agent(sandbox): return sandbox.get_cart_body()

def agent_action(sandbox, cart, step_count):
    theta = normalize_angle(sandbox.get_pole_angle())
    omega = sandbox.get_pole_angular_velocity()
    x, v = sandbox.get_cart_position(), sandbox.get_cart_velocity()
    target_x = sandbox.TRACK_CENTER_X
    force = -4200.0 * theta - 1050.0 * omega - 62.0 * (x - target_x) - 155.0 * v
    sandbox.apply_cart_force(max(-450.0, min(450.0, force)))

def robust_control(sandbox, g, l, m_p, m_c, delay_steps=0, kx=150.0, kv=400.0):
    theta = normalize_angle(sandbox.get_pole_angle())
    omega = sandbox.get_pole_angular_velocity()
    x, v = sandbox.get_cart_position(), sandbox.get_cart_velocity()
    target_x = sandbox.TRACK_CENTER_X
    dt = 1.0/60.0
    theta_p = normalize_angle(theta + omega * delay_steps * dt)
    scale_g = g / 10.0
    scale_m = (m_p + m_c) / 11.0
    force = -6000.0 * scale_g * scale_m * theta_p - 1500.0 * scale_g * scale_m * omega
    force += -kx * scale_g * scale_m * (x - target_x) - kv * scale_g * scale_m * v
    limit = 450.0
    sandbox.apply_cart_force(max(-limit, min(limit, force)))

def build_agent_stage_1(sandbox): return sandbox.get_cart_body()

def agent_action_stage_1(sandbox, cart, step_count):
    robust_control(sandbox, 10.0, 2.0, 1.0, 10.0)

def build_agent_stage_2(sandbox): return sandbox.get_cart_body()

def agent_action_stage_2(sandbox, cart, step_count):
    robust_control(sandbox, 15.0, 2.0, 1.0, 10.0, kv=1000.0)

def build_agent_stage_3(sandbox): return sandbox.get_cart_body()

def agent_action_stage_3(sandbox, cart, step_count):
    robust_control(sandbox, 10.0, 2.0, 1.0, 10.0, delay_steps=2)

def build_agent_stage_4(sandbox): return sandbox.get_cart_body()

def agent_action_stage_4(sandbox, cart, step_count):
    robust_control(sandbox, 10.0, 2.0, 3.0, 7.0)
