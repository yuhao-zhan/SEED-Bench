"""
C-02: The Lander task Agent (hard variant: obstacle + partial observability + moving platform)
- No-fly barrier: must climb above it, then cross right, then descend and land (3-phase).
- Velocity is NOT read from sandbox; estimated from position history (output feedback).
- Predict platform position at expected touchdown time; steer to it and soft land.
"""
import math

DT = 1.0 / 60.0
GRAVITY = 10.0
MAX_THRUST = 600.0
MAX_TORQUE = 120.0

# Barrier: do not enter x in [BARRIER_X_LEFT, BARRIER_X_RIGHT] when y < BARRIER_Y_TOP
BARRIER_X_LEFT = 10.5
BARRIER_X_RIGHT = 13.5
BARRIER_Y_TOP = 6.0
BARRIER_CLEAR_Y = BARRIER_Y_TOP + 1.5  # climb above this before moving right (y=7.5)
CROSS_TARGET_X = 14.5  # right of barrier; then descend to platform

PLATFORM_CENTER_BASE = 17.0
PLATFORM_AMPLITUDE = 1.8
PLATFORM_PERIOD = 6.0

X_GAIN = 0.56
X_INTEGRAL_GAIN = 0.30
X_INTEGRAL_MAX = 2.0
MAX_TILT_FOR_X = 0.28
Kp_angle = 72.0
Kd_angle = 22.0
BURN_HEIGHT_THRESHOLD = 2.2
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
    """
    Partial observability: no velocity from API. Estimate vx, vy from position history.
    Moving platform: predict target x at expected touchdown time; steer and soft land.
    """
    global _x_integral, _x_prev, _y_prev, _step_prev, _vx_est, _vy_est

    x, y = sandbox.get_lander_position()
    angle = sandbox.get_lander_angle()
    omega = sandbox.get_lander_angular_velocity()

    # Estimate velocity from position history (no get_lander_velocity)
    if _step_prev is not None and step_count > _step_prev:
        dt_sec = (step_count - _step_prev) * DT
        if dt_sec > 0:
            vx_new = (x - _x_prev) / dt_sec
            vy_new = (y - _y_prev) / dt_sec
            alpha = 0.55
            _vx_est = alpha * vx_new + (1 - alpha) * _vx_est
            _vy_est = alpha * vy_new + (1 - alpha) * _vy_est
    _x_prev, _y_prev, _step_prev = x, y, step_count
    vx, vy = _vx_est, _vy_est

    ground_y_top = sandbox.get_ground_y_top()
    hw, half_h = sandbox.get_lander_size()
    bottom_y = y - abs(math.sin(angle)) * hw - math.cos(angle) * half_h
    height_above_ground = bottom_y - ground_y_top

    # 3-phase: (1) climb above barrier (only while left of barrier), (2) cross right, (3) descend and land
    # Once right of barrier (x >= BARRIER_X_RIGHT), do not go back to phase 1.
    phase1_climb = y < BARRIER_CLEAR_Y and x < BARRIER_X_RIGHT
    phase2_cross = (y >= BARRIER_CLEAR_Y or x >= BARRIER_X_RIGHT) and x < CROSS_TARGET_X
    phase3_land = x >= CROSS_TARGET_X

    if phase1_climb:
        target_x = x  # no horizontal; climb only to avoid barrier
        expected_land_step = step_count + 400
    elif phase2_cross:
        target_x = CROSS_TARGET_X  # move right above barrier
        expected_land_step = step_count + 300
    elif height_above_ground > 0.05 and vy < 0:
        avg_vy = 0.5 * (abs(vy) + math.sqrt(vy * vy + 2 * GRAVITY * height_above_ground))
        steps_to_land = height_above_ground / (avg_vy * DT)
        steps_to_land = max(15, min(350, steps_to_land))
        expected_land_step = step_count + int(steps_to_land)
        target_x = platform_center_at_step(expected_land_step)
        target_x = max(BARRIER_X_RIGHT + 0.3, target_x)  # never steer left into barrier
    else:
        target_x = platform_center_at_step(step_count)
        target_x = max(BARRIER_X_RIGHT + 0.3, target_x)
        expected_land_step = step_count

    dx = target_x - x
    _x_integral += dx * DT
    _x_integral = max(-X_INTEGRAL_MAX, min(X_INTEGRAL_MAX, _x_integral))
    if x > target_x + 0.5:
        _x_integral = min(0.0, _x_integral)
    if dx < -0.3:
        x_gain = X_GAIN * 1.6
    elif dx < 2.0:
        x_gain = X_GAIN * 0.5
    else:
        x_gain = X_GAIN
    if phase2_cross:
        max_tilt_now = 0.34
    else:
        max_tilt_now = MAX_TILT_FOR_X if height_above_ground > 0.7 else (0.16 if height_above_ground > 0.25 else 0.10)
    desired_angle_x = -x_gain * dx - X_INTEGRAL_GAIN * _x_integral
    if vx > 1.2:
        desired_angle_x += 0.14 * (vx - 1.2)
    if x > target_x + 1.0:
        desired_angle_x = max(desired_angle_x, 0.28)
    elif x > target_x + 0.4:
        desired_angle_x = max(desired_angle_x, 0.14)
    if phase1_climb:
        if x > BARRIER_X_LEFT - 1.0:
            desired_angle_x = 0.12
        else:
            desired_angle_x = 0.0
    desired_angle_x = max(-max_tilt_now, min(max_tilt_now, desired_angle_x))
    steering = Kp_angle * (desired_angle_x - angle) - Kd_angle * omega
    steering = max(-MAX_TORQUE, min(MAX_TORQUE, steering))

    if height_above_ground <= 0:
        main_thrust = HOVER_THRUST
    elif phase1_climb:
        target_vy = 1.25
        Kp_vy = 68.0
        desired_Fy = HOVER_THRUST + Kp_vy * (target_vy - vy)
        cos_a = max(0.15, min(1.0, math.cos(angle)))
        main_thrust = desired_Fy / cos_a
        main_thrust = max(0.0, min(MAX_THRUST, main_thrust))
    elif phase2_cross:
        if BARRIER_X_LEFT < x < BARRIER_X_RIGHT:
            target_vy = 0.05
            Kp_vy = 52.0
        else:
            target_vy = -0.18
            Kp_vy = 50.0
        desired_Fy = HOVER_THRUST * 0.78 + Kp_vy * (target_vy - vy)
        cos_a = max(0.15, min(1.0, math.cos(angle)))
        main_thrust = desired_Fy / cos_a
        main_thrust = max(0.0, min(MAX_THRUST * 0.82, main_thrust))
    elif height_above_ground > BURN_HEIGHT_THRESHOLD:
        target_vy = -min(1.6, math.sqrt(2.0 * GRAVITY * height_above_ground) * 0.42)
        Kp_vy = 65.0
        desired_Fy = HOVER_THRUST + Kp_vy * (target_vy - vy)
        cos_a = max(0.15, min(1.0, math.cos(angle)))
        main_thrust = desired_Fy / cos_a
        main_thrust = max(0.0, min(250.0, main_thrust))
    else:
        if height_above_ground < 0.15:
            target_vy = -0.12
        elif height_above_ground < 0.35:
            target_vy = -0.2
        elif height_above_ground < 0.65:
            target_vy = -0.32
        elif height_above_ground < 1.0:
            target_vy = -0.45
        elif height_above_ground < 1.3:
            target_vy = -0.55
        else:
            max_descent = min(0.55, math.sqrt(2.0 * GRAVITY * max(height_above_ground, 0.1)) * 0.20)
            target_vy = -max_descent
        Kp_vy = 195.0
        desired_Fy = HOVER_THRUST + Kp_vy * (target_vy - vy)
        cos_a = max(0.15, min(1.0, math.cos(angle)))
        main_thrust = desired_Fy / cos_a
        main_thrust = max(0.0, min(MAX_THRUST, main_thrust))

    sandbox.apply_thrust(main_thrust, steering)
