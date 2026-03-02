"""
C-04: Counterintuitive unlock (backward force + low speed for 20 steps) + one-way + hold 60 steps.
Velocity sensor returns (0,0); control uses position and step_count; velocity estimated from position if needed.
"""
import math

DT = 1.0 / 60.0
_last_x, _last_y, _last_step = None, None, None


def _estimate_velocity(x, y, step_count):
    global _last_x, _last_y, _last_step
    if _last_x is None or step_count != _last_step + 1:
        vx_est, vy_est = 0.0, 0.0
    else:
        vx_est = (x - _last_x) / DT
        vy_est = (y - _last_y) / DT
    _last_x, _last_y, _last_step = x, y, step_count
    return vx_est, vy_est

EXIT_X_MIN = 18.0
EXIT_Y_MIN = 1.25
EXIT_Y_MAX = 1.45
TARGET_Y = 1.35

# Counterintuitive unlock: apply backward force (fx < -30) while speed < 1.0 for 20 consecutive steps
UNLOCK_BACKWARD_STEPS = 25
UNLOCK_FX = -50.0
UNLOCK_FY = 50.0  # counteract gravity so speed stays low

OBST1_X = 5.0
OBST1_PASS_ABOVE = 1.25
OBST2_X = 9.0
OBST2_SLIT_LO, OBST2_SLIT_HI = 1.0, 1.6
OBST3_X = 14.0
OBST3_PASS_BELOW = 1.45

MOMENTUM_DRAIN_X_LO, MOMENTUM_DRAIN_X_HI = 7.0, 9.5
CURRENT_X_LO, CURRENT_X_HI = 12.0, 15.0
WIND_X_LO, WIND_X_HI = 15.5, 18.0

WALL_THRESHOLD = 0.5
FRONT_OBSTACLE_THRESHOLD = 0.95
FRONT_CLOSE_THRESHOLD = 0.4
MAX_FORCE = 80.0
BASE_FX = 62.0
MOMENTUM_DRAIN_FX = 78.0
CURRENT_FX = 78.0
WIND_FY_BASE = 14.0
WIND_OSC_AMP = 11.0
WIND_OSC_OMEGA = 0.08


def build_agent(sandbox):
    return sandbox.get_agent_body()


def agent_action(sandbox, agent_body, step_count):
    """
    Phase 1: counterintuitive unlock — apply backward force while staying slow for 20+ steps.
    Phase 2: navigate to exit, then hold in exit 60 steps.
    """
    x, y = sandbox.get_agent_position()
    front, left, right = sandbox.get_whisker_readings()
    vx_est, vy_est = _estimate_velocity(x, y, step_count)

    fx = BASE_FX
    fy = 0.0

    # Phase 1: counterintuitive unlock — backward force + low speed for 20 consecutive steps
    if step_count < UNLOCK_BACKWARD_STEPS:
        fx = UNLOCK_FX
        fy = UNLOCK_FY
        fx = max(-MAX_FORCE, min(MAX_FORCE, fx))
        fy = max(-MAX_FORCE, min(MAX_FORCE, fy))
        sandbox.apply_agent_force(fx, fy)
        return

    # Phase 2: navigate to exit
    if left < WALL_THRESHOLD:
        fy -= 32.0
    if right < WALL_THRESHOLD:
        fy += 32.0

    if x < 5.2:
        if front < FRONT_OBSTACLE_THRESHOLD and y < 1.4:
            fy += 50.0
            fx *= 0.5
        else:
            if y > 1.5:
                fy -= 25.0
            elif y < 1.3:
                fy += 25.0
    elif x < 9.5:
        if front < FRONT_OBSTACLE_THRESHOLD:
            if y > OBST2_SLIT_HI - 0.1:
                fy -= 50.0
            elif y < OBST2_SLIT_LO + 0.15:
                fy += 50.0
            fx *= 0.6
        else:
            target_y = 1.3
            if y < target_y:
                fy += 35.0
            elif y > target_y:
                fy -= 35.0
    elif x < 13.0:
        target_y = 1.5
        if y < target_y:
            fy += 40.0
        elif y > target_y:
            fy -= 40.0
        if front < FRONT_CLOSE_THRESHOLD:
            fx = 55.0
    else:
        if x < OBST3_X + 1.2 and front < FRONT_OBSTACLE_THRESHOLD and y > OBST3_PASS_BELOW - 0.1:
            fy -= 55.0
            fx *= 0.55
        elif front < FRONT_CLOSE_THRESHOLD:
            if y > TARGET_Y + 0.15:
                fy -= 45.0
            elif y < TARGET_Y - 0.15:
                fy += 45.0
            fx = max(fx, 65.0)
        else:
            if y < EXIT_Y_MIN:
                fy += 58.0
            elif y > EXIT_Y_MAX:
                fy -= 50.0
            if x < 17.5:
                fx = max(fx, 70.0)
    if x >= 15.0 and y < EXIT_Y_MIN:
        fy += 52.0

    if MOMENTUM_DRAIN_X_LO <= x <= MOMENTUM_DRAIN_X_HI:
        fx = max(fx, MOMENTUM_DRAIN_FX)
    if CURRENT_X_LO <= x <= CURRENT_X_HI:
        fx = max(fx, CURRENT_FX)
    if WIND_X_LO <= x <= WIND_X_HI:
        wind_comp = WIND_FY_BASE + WIND_OSC_AMP * math.sin(step_count * WIND_OSC_OMEGA)
        fy += wind_comp
        if x >= 15 and y < EXIT_Y_MIN:
            fy += 35.0
        elif y > EXIT_Y_MAX and x >= 15:
            fy -= 30.0

    # Hold in exit zone for 60 consecutive steps
    if x >= EXIT_X_MIN and EXIT_Y_MIN <= y <= EXIT_Y_MAX:
        fx = 28.0
        if y < TARGET_Y:
            fy += 42.0
        elif y > TARGET_Y:
            fy -= 42.0
        else:
            fy = 0.0

    fx = max(-MAX_FORCE, min(MAX_FORCE, fx))
    fy = max(-MAX_FORCE, min(MAX_FORCE, fy))
    sandbox.apply_agent_force(fx, fy)
