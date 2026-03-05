"""
C-06: The Governor task Agent module (hard variant v2)
Reference solution: delay compensation (predict current omega from delayed measurement),
anti-windup, speed-dependent feedforward + P + I, max torque at very low speed.
Handles: nonlinear load, step load, periodic disturbances, stiction,
speed-dependent torque limit, delayed measurement, time-varying target.
"""


DELAY_EST = 5

BASE_FF = 2.0
KFF_QUADRATIC = 0.55
KP = 18.0
KI = 0.5
INTEGRAL_CLAMP = 5.0

INTEGRAL_ERR_THRESHOLD = 1.5

LOW_SPEED_THRESHOLD = 0.65
STICTION_BOOST = 2.0
COGGING_EST = 0.0
DT = 1.0 / 60.0
DEADZONE_MIN_TORQUE = 2.2

_integral = 0.0
_omega_d_prev = 0.0
_angle_est = 0.0


def build_agent(sandbox):
    """Return the wheel body."""
    return sandbox.get_wheel_body()


def agent_action(sandbox, agent_body, step_count):
    """
    Governor control: delay comp, anti-windup, ff + P + I, low-speed max,
    cogging compensation (angle_est from integrated omega), deadzone overcoming.
    """
    global _integral, _omega_d_prev, _angle_est
    import math
    omega_d = sandbox.get_wheel_angular_velocity()
    target = sandbox.get_target_speed()

    if step_count >= 1 and abs(omega_d - _omega_d_prev) < 0.25:
        omega_pred = omega_d + DELAY_EST * (omega_d - _omega_d_prev)
        omega_pred = max(0.0, min(5.0, omega_pred))
    else:
        omega_pred = omega_d
    _omega_d_prev = omega_d
    _angle_est += omega_d * DT
    if abs(_angle_est) > 100.0:
        _angle_est = math.fmod(_angle_est, 2.0 * math.pi)

    err = target - omega_pred
    if abs(err) < INTEGRAL_ERR_THRESHOLD:
        _integral += err * DT
        _integral = max(-INTEGRAL_CLAMP, min(INTEGRAL_CLAMP, _integral))

    if abs(omega_d) < LOW_SPEED_THRESHOLD:
        torque = (1.0 if target >= 0 else -1.0) * 100.0
        if abs(omega_d) < 0.35:
            torque += STICTION_BOOST if target >= 0 else -STICTION_BOOST
    else:
        ff = BASE_FF + KFF_QUADRATIC * (omega_pred * omega_pred)
        torque = ff + KP * err + KI * _integral

        if COGGING_EST > 0:
            phase_advance = DELAY_EST * DT * max(0, omega_pred)
            torque += COGGING_EST * math.sin(_angle_est + phase_advance)

        if abs(err) > 0.08 and abs(torque) > 1e-6 and abs(torque) < DEADZONE_MIN_TORQUE:
            torque = (torque / abs(torque)) * DEADZONE_MIN_TORQUE

    sandbox.apply_motor_torque(torque)
