"""
E-05: The Magnet task agent module.
Reference solution: dual-gate timing + oscillating keyhole.

Strategy: ascend → gate1 (wait weak) → wait for gate2 weak → gate2 → traverse →
         keyhole (wait weak) → target.
"""
import math

TARGET_X_MIN = 28.0
TARGET_X_MAX = 32.0
TARGET_Y_MIN = 8.2
TARGET_Y_MAX = 9.5
TARGET_X_CENTER = 30.0
TARGET_Y_CENTER = 8.85

CORRIDOR_Y = 8.95
KEYHOLE_Y = 6.75

# Gate 1: period 52, weak steps 8-20
G1_PERIOD, G1_WEAK_LO, G1_WEAK_HI = 52, 8, 20
# Gate 2: period ~42 (omega 0.15), phase π, weak when step % 42 in [28, 35]
G2_PERIOD, G2_WEAK_LO, G2_WEAK_HI = 42, 28, 35
# Keyhole: period ~38 (omega 0.165), weak when step % 38 in [8, 18]
KH_PERIOD, KH_WEAK_LO, KH_WEAK_HI = 38, 8, 18

GRAVITY_COMPENSATION = 102.0
MAX_THRUST = 165.0
K_P = 11.0


def _gate1_weak(s):
    return G1_WEAK_LO <= (s % G1_PERIOD) <= G1_WEAK_HI


def _gate2_weak(s):
    return G2_WEAK_LO <= (s % G2_PERIOD) <= G2_WEAK_HI


def _keyhole_weak(s):
    return KH_WEAK_LO <= (s % KH_PERIOD) <= KH_WEAK_HI


def build_agent(sandbox):
    return None


def agent_action(sandbox, agent_body, step_count):
    pos = sandbox.get_body_position()
    if pos is None:
        return
    x, y = pos
    vel = sandbox.get_body_velocity() or (0.0, 0.0)
    vx, vy = vel[0], vel[1]
    step = sandbox.get_step_count() if hasattr(sandbox, 'get_step_count') else step_count

    in_target = (TARGET_X_MIN <= x <= TARGET_X_MAX and TARGET_Y_MIN <= y <= TARGET_Y_MAX)
    if in_target:
        fx = -6.0 * vx
        fy = GRAVITY_COMPENSATION - 6.0 * vy
    else:
        # Strong descent only when well above corridor (y>9.65)
        fy_ceiling = -60.0 if y > 9.65 else 0.0

        if x < 11.0:
            dy = CORRIDOR_Y - y
            if y < CORRIDOR_Y - 0.15:
                fx = 40.0
                fy = GRAVITY_COMPENSATION + 10.0 * min(dy, 1.0) + fy_ceiling
            else:
                dx = 11.5 - x
                fy = GRAVITY_COMPENSATION + 5.0 * dy + fy_ceiling
                fx = 110.0 if dx > 0 else max(-80, min(80, -2.5 * vx))

        elif x < 17.0:
            if _gate1_weak(step):
                fx = 78.0
                fy = GRAVITY_COMPENSATION + 28.0 + fy_ceiling
            else:
                fx = max(-50, min(50, -2.5 * vx))
                fy = GRAVITY_COMPENSATION + 4.0 * (CORRIDOR_Y - y) + fy_ceiling

        elif x < 20.5:
            if _gate2_weak(step):
                fx = 78.0
                fy = GRAVITY_COMPENSATION + 28.0 + fy_ceiling
            else:
                fx = max(-50, min(50, -2.5 * vx))
                fy = GRAVITY_COMPENSATION + 4.0 * (CORRIDOR_Y - y) + fy_ceiling

        elif x < 23.5:
            dx, dy = 25.0 - x, CORRIDOR_Y - y
            fx = K_P * dx
            fy = GRAVITY_COMPENSATION + K_P * dy

        elif x < 26.0:
            if _keyhole_weak(step):
                dx, dy = 28.0 - x, KEYHOLE_Y - y
                fx = K_P * dx
                fy = GRAVITY_COMPENSATION + K_P * dy
            else:
                fx = max(-65, min(65, -3.0 * vx))
                fy = GRAVITY_COMPENSATION + 6.0 * (CORRIDOR_Y - y)

        else:
            dx = TARGET_X_CENTER - x
            dy = TARGET_Y_CENTER - y
            fx = K_P * dx
            fy = GRAVITY_COMPENSATION + K_P * dy

        f = math.sqrt(fx * fx + fy * fy)
        if f > MAX_THRUST:
            scale = MAX_THRUST / f
            fx *= scale
            fy *= scale

    sandbox.apply_thrust(fx, fy)
