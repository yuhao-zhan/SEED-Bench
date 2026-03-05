"""
C-02: The Lander task Agent (hard variant: obstacle + partial observability + moving platform)
- Optimized for fuel efficiency: less aggressive climb and horizontal move.
- Suicide burn logic: let it fall faster at high altitude, slow down late.
"""
import math

DT = 1.0 / 60.0
GRAVITY = 10.0
MAX_THRUST = 600.0
MAX_TORQUE = 120.0

BARRIER_X_LEFT = 10.5
BARRIER_X_RIGHT = 13.5
BARRIER_Y_TOP = 6.0
BARRIER_CLEAR_Y = BARRIER_Y_TOP + 1.2
CROSS_TARGET_X = 14.5

PLATFORM_CENTER_BASE = 17.0
PLATFORM_AMPLITUDE = 1.8
PLATFORM_PERIOD = 6.0

X_GAIN = 0.50
Kp_angle = 70.0
Kd_angle = 20.0
BURN_HEIGHT_THRESHOLD = 3.5
HOVER_THRUST = 500.0

_x_integral = 0.0
_x_prev, _y_prev, _step_prev = None, None, None
_vx_est, _vy_est = 0.0, 0.0


def platform_center_at_step(step: int) -> float:
    t = step * DT
    return PLATFORM_CENTER_BASE + PLATFORM_AMPLITUDE * math.sin(
        2.0 * math.pi * t / PLATFORM_PERIOD
    )


def build_agent(sandbox):
    return sandbox.get_lander_body()


def agent_action(sandbox, agent_body, step_count):
    global _x_integral, _x_prev, _y_prev, _step_prev, _vx_est, _vy_est

    x, y = sandbox.get_lander_position()
    angle = sandbox.get_lander_angle()
    omega = sandbox.get_lander_angular_velocity()

    if _step_prev is not None and step_count > _step_prev:
        dt_sec = (step_count - _step_prev) * DT
        vx_new = (x - _x_prev) / dt_sec
        vy_new = (y - _y_prev) / dt_sec
        alpha = 0.6
        _vx_est = alpha * vx_new + (1 - alpha) * _vx_est
        _vy_est = alpha * vy_new + (1 - alpha) * _vy_est
    _x_prev, _y_prev, _step_prev = x, y, step_count
    vx, vy = _vx_est, _vy_est

    ground_y_top = sandbox.get_ground_y_top()
    hw, half_h = sandbox.get_lander_size()
    bottom_y = y - abs(math.sin(angle)) * hw - math.cos(angle) * half_h
    height_above_ground = bottom_y - ground_y_top

    phase1_climb = y < BARRIER_CLEAR_Y and x < BARRIER_X_RIGHT
    phase2_cross = (y >= BARRIER_CLEAR_Y or x >= BARRIER_X_RIGHT) and x < CROSS_TARGET_X
    phase3_land = x >= CROSS_TARGET_X

    if phase1_climb:
        target_x = x
        expected_land_step = step_count + 500
    elif phase2_cross:
        target_x = CROSS_TARGET_X
        expected_land_step = step_count + 400
    elif height_above_ground > 0.05 and vy < 0:
        avg_vy = 0.5 * (abs(vy) + math.sqrt(vy * vy + 2 * GRAVITY * height_above_ground))
        steps_to_land = height_above_ground / (max(0.1, avg_vy) * DT)
        expected_land_step = step_count + int(min(400, steps_to_land))
        target_x = platform_center_at_step(expected_land_step)
        target_x = max(BARRIER_X_RIGHT + 0.5, target_x)
    else:
        target_x = platform_center_at_step(step_count)
        expected_land_step = step_count

    dx = target_x - x
    _x_integral = max(-1.0, min(1.0, _x_integral + dx * DT))

    max_tilt = 0.3 if height_above_ground > 1.0 else 0.15
    desired_angle = -0.4 * dx - 0.2 * _x_integral + 0.1 * vx
    desired_angle = max(-max_tilt, min(max_tilt, desired_angle))

    steering = Kp_angle * (desired_angle - angle) - Kd_angle * omega
    steering = max(-MAX_TORQUE, min(MAX_TORQUE, steering))

    if height_above_ground <= 0:
        main_thrust = 0.0
    elif phase1_climb:
        target_vy = 0.8
        desired_Fy = HOVER_THRUST + 40.0 * (target_vy - vy)
        main_thrust = desired_Fy / max(0.5, math.cos(angle))
    elif phase2_cross:
        target_vy = 0.0
        desired_Fy = HOVER_THRUST * 0.9 + 30.0 * (target_vy - vy)
        main_thrust = desired_Fy / max(0.5, math.cos(angle))
    elif height_above_ground > BURN_HEIGHT_THRESHOLD:
        main_thrust = 0.0
    else:

        if height_above_ground < 0.3:
            target_vy = -0.15
        elif height_above_ground < 1.0:
            target_vy = -0.4
        else:
            target_vy = -0.8

        Kp_vy = 250.0
        desired_Fy = HOVER_THRUST + Kp_vy * (target_vy - vy)
        main_thrust = desired_Fy / max(0.5, math.cos(angle))

    main_thrust = max(0.0, min(MAX_THRUST, main_thrust))
    sandbox.apply_thrust(main_thrust, steering)
