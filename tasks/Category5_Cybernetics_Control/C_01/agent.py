"""
C-01: Cart-Pole Swing-up then Balance reference agent.
Phase 1 (swing-up): when |angle| > threshold, use energy-based forcing to pump energy.
Phase 2 (balance): when |angle| < threshold, use PD to hold upright.
Delay and rate limit handled; position term keeps cart in safe zone.
"""
import math

DT = 1.0 / 60.0
TRACK_CENTER_X = 10.0


SWITCH_RAD = 0.40
BLEND_RAD = 0.55


K_SWING = 260.0

NUDGE_PERIOD = 80
NUDGE_FORCE = 200.0

KP_POS_SWING = 220.0


KP = 520.0
KD = 185.0
KP_POS = 200.0


RATE_LIMIT = 75.0
RATE_LIMIT_BALANCE = 95.0
_last_force = 0.0


def build_agent(sandbox):
    return sandbox.get_cart_body()


def agent_action(sandbox, agent_body, step_count):
    global _last_force

    angle = sandbox.get_pole_angle()
    omega = sandbox.get_pole_angular_velocity()
    cart_x = sandbox.get_cart_position()
    cart_vx = sandbox.get_cart_velocity()

    abs_angle = abs(angle)

    if abs_angle > BLEND_RAD:

        cos_a = math.cos(angle)
        if abs(omega) < 0.08:
            nudge = NUDGE_FORCE if (step_count % NUDGE_PERIOD) < (NUDGE_PERIOD // 2) else -NUDGE_FORCE
            force_desired = nudge
        else:
            prod = omega * cos_a
            if prod > 0:
                force_desired = -K_SWING
            elif prod < 0:
                force_desired = K_SWING
            else:
                force_desired = 0.0
        dx = cart_x - TRACK_CENTER_X
        abs_dx = abs(dx)
        pos_gain = KP_POS_SWING * (2.2 if abs_dx > 6.0 else 1.0)
        force_desired -= pos_gain * dx
        if abs_dx > 5.0:
            force_desired -= 80.0 * math.copysign(1.0, dx)
        if cart_x < 4.5 and force_desired < 0:
            force_desired = 0.0
        if cart_x > 15.5 and force_desired > 0:
            force_desired = 0.0
    elif abs_angle > SWITCH_RAD:

        cos_a = math.cos(angle)
        force_swing = 0.0
        if abs(omega) >= 0.08:
            prod = omega * cos_a
            k_blend = K_SWING * 0.4 * (abs_angle - SWITCH_RAD) / (BLEND_RAD - SWITCH_RAD)
            if prod > 0:
                force_swing = -k_blend
            elif prod < 0:
                force_swing = k_blend
        force_balance = -KP * angle - KD * omega
        dx = cart_x - TRACK_CENTER_X
        force_position = -KP_POS * dx
        blend = (abs_angle - SWITCH_RAD) / (BLEND_RAD - SWITCH_RAD)
        force_desired = blend * force_swing + (1 - blend) * (force_balance + force_position)
    else:

        boundary_rad = math.radians(60.0)
        kp_eff = KP * (1.4 if abs_angle > boundary_rad else 1.0)
        kd_eff = KD * (1.3 if abs_angle > boundary_rad else 1.0)
        force_balance = -kp_eff * angle - kd_eff * omega
        dx = cart_x - TRACK_CENTER_X
        force_position = -KP_POS * dx
        force_desired = force_balance + force_position


    rate = RATE_LIMIT_BALANCE if abs_angle <= BLEND_RAD else RATE_LIMIT
    delta = max(-rate, min(rate, force_desired - _last_force))
    force_cmd = _last_force + delta
    _last_force = force_cmd

    sandbox.apply_cart_force(force_cmd)
