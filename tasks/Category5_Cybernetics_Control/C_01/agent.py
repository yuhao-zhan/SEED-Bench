import math

def build_agent(sandbox):
    """
    Standard build_agent returns the main controllable body.
    Initialize state attributes directly on the body.
    """
    cart = sandbox.get_cart_body()
    if cart:
        cart._integral_theta = 0.0
    return cart

def agent_action(sandbox, cart, step_count):
    """
    Reference solution for the baseline Cart-Pole task.
    Designed for the initial environment (spawns upright).
    Naturally fails on mutants (spawn hanging down) without explicit identification.
    """
    # 1. Perception
    # Uses standard documented APIs.
    theta_raw = sandbox.get_pole_angle()
    omega = sandbox.get_pole_angular_velocity()
    x = sandbox.get_cart_position()
    v = sandbox.get_cart_velocity()

    # 2. Normalization
    # theta=0 is UP, PI/-PI is DOWN.
    theta = math.atan2(math.sin(theta_raw), math.cos(theta_raw))
    
    # 3. PID Balance Control
    # These gains are tuned for the M=10kg, m=1kg baseline.
    # High gains ensure perfect stability for the upright start.
    dt = 1.0 / 60.0
    
    # Update integral term (state stored on cart)
    cart._integral_theta += theta * dt
    cart._integral_theta = max(-0.2, min(0.2, cart._integral_theta))
    
    # PD terms for theta
    kp_th = -3000.0
    kd_th = -800.0
    ki_th = -1000.0
    
    # PD terms for cart position (center at x=10.0)
    kp_x = -250.0
    kd_x = -400.0
    
    force = (kp_th * theta + 
             kd_th * omega + 
             ki_th * cart._integral_theta + 
             kp_x * (x - 10.0) + 
             kd_x * v)
        
    # 4. Final Output
    # Clamp to actuator limits
    force = max(-450.0, min(450.0, force))
    sandbox.apply_cart_force(force)
