import math

def build_agent(sandbox):
    cart = sandbox.get_cart_body()
    if cart:
        cart._integral_theta = 0.0
    return cart

def agent_action(sandbox, cart, step_count):
    theta_raw = sandbox.get_pole_angle()
    omega = sandbox.get_pole_angular_velocity()
    x = sandbox.get_cart_position()
    v = sandbox.get_cart_velocity()
    theta = math.atan2(math.sin(theta_raw), math.cos(theta_raw))
    dt = 1.0 / 60.0
    cart._integral_theta += theta * dt
    cart._integral_theta = max(-0.2, min(0.2, cart._integral_theta))
    kp_th = -3000.0
    kd_th = -800.0
    ki_th = -1000.0
    kp_x = -250.0
    kd_x = -400.0
    force = (kp_th * theta +
             kd_th * omega +
             ki_th * cart._integral_theta +
             kp_x * (x - 10.0) +
             kd_x * v)
    force = max(-450.0, min(450.0, force))
    sandbox.apply_cart_force(force)
