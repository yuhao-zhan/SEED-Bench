import math

TX_MIN, TX_MAX = 28.0, 32.0

TY_MIN, TY_MAX = 2.0, 5.0

TARGET_X, TARGET_Y = 30.0, 3.5

G1_X, G1_Y = 13.0, 2.0

G2_X, G2_Y = 23.0, 2.4

DRAIN_LO, DRAIN_HI = 14.5, 17.0

SLIP_LO, SLIP_HI = 17.5, 20.0

WIND_LO, WIND_HI = 20.5, 28.0

WIND_AMP = 20.0

WIND_OMEGA = 0.055

MAX_THRUST = 120.0

LOW_THRUST = 90.0

HEAT_SAFE_FRAC = 0.88

def build_agent(sandbox):
    return None

def _waypoint(x, y):
    if x < G1_X - 0.1:
        return (G1_X, G1_Y)
    if x < G2_X - 0.1:
        return (G2_X, G2_Y)
    return (TARGET_X, TARGET_Y)

def agent_action(sandbox, agent_body, step_count):
    if sandbox.is_overheated():
        return
    pos = sandbox.get_craft_position()
    if pos is None:
        return
    x, y = pos
    heat = sandbox.get_heat()
    overheat_limit = sandbox.get_overheat_limit()
    remaining = overheat_limit - heat
    step_idx = sandbox.get_step_count() if hasattr(sandbox, "get_step_count") else step_count
    if TX_MIN <= x <= TX_MAX and TY_MIN <= y <= TY_MAX:
        sandbox.apply_thrust(0.0, 0.0)
        return
    if heat >= overheat_limit * HEAT_SAFE_FRAC:
        thrust_mag = min(LOW_THRUST, remaining * 0.25)
    else:
        thrust_mag = min(MAX_THRUST, remaining * 0.35)
    if x < 10.0:
        thrust_mag = min(100.0, thrust_mag)
    if 10.0 <= x <= 15.0:
        thrust_mag = min(MAX_THRUST, thrust_mag * 1.2)
    if DRAIN_LO <= x <= DRAIN_HI:
        thrust_mag = min(MAX_THRUST, thrust_mag * 1.4)
    if thrust_mag < 75.0:
        sandbox.apply_thrust(0.0, 0.0)
        return
    wx, wy = _waypoint(x, y)
    if x < G1_X + 0.5 and y < 1.2:
        wy = max(wy, 1.3)
    if y < 1.4:
        wy = max(wy, 1.5)
    if G2_X - 1.0 <= x <= G2_X + 2.0 and y < 1.9:
        wy = max(wy, 2.2)
    if 20.5 <= x <= G2_X + 1.0 and y < 1.85:
        wx, wy = x + 0.3, 2.5
    dx = wx - x
    dy = wy - y
    dist = math.sqrt(dx * dx + dy * dy)
    if dist < 1e-6:
        sandbox.apply_thrust(0.0, 0.0)
        return
    ux = dx / dist
    uy = dy / dist
    fx = thrust_mag * ux
    fy = thrust_mag * uy
    if y < 1.4:
        fy += 100.0
    if x < G1_X + 1.0 and y < 1.1:
        fy += min(30.0, (1.2 - y) * 40.0)
    if 20.5 <= x <= G2_X + 2.0 and y < 1.9:
        fy += 110.0
    if SLIP_LO <= x <= SLIP_HI:
        fx += 35.0
    if WIND_LO <= x <= WIND_HI:
        wind_fy = WIND_AMP * math.sin(WIND_OMEGA * step_idx)
        fy -= wind_fy
    total = math.sqrt(fx * fx + fy * fy)
    cap = thrust_mag * 2.0
    if y < 1.4:
        cap = max(cap, 180.0)
    if 20.5 <= x <= G2_X + 2.0 and y < 1.9:
        cap = max(cap, 250.0)
    if total > cap:
        scale = cap / total
        fx *= scale
        fy *= scale
    sandbox.apply_thrust(fx, fy)
