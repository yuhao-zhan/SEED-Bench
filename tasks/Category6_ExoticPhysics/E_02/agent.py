"""
E-02: Thick Air (Hard) — reference agent.
Passes through gates, overcomes momentum-drain, slippery, and oscillating-wind zones,
reaches target without overheating. Uses waypoints and zone-specific thrust.
"""
import math

# Target
TX_MIN, TX_MAX = 28.0, 32.0
TY_MIN, TY_MAX = 2.0, 5.0
TARGET_X, TARGET_Y = 30.0, 3.5

# Waypoints (gate gap centers — discovered in real task via feedback)
G1_X, G1_Y = 13.0, 2.0    # gate 1 gap center (y in [1.2, 2.8])
G2_X, G2_Y = 23.0, 2.4    # gate 2 gap center

# Zone x-ranges (discoverable)
DRAIN_LO, DRAIN_HI = 14.5, 17.0
SLIP_LO, SLIP_HI = 17.5, 20.0
WIND_LO, WIND_HI = 20.5, 28.0

# Wind compensation (environment uses WIND_AMPLITUDE=20, WIND_OMEGA≈0.055)
WIND_AMP = 20.0
WIND_OMEGA = 0.055

MAX_THRUST = 120.0
LOW_THRUST = 90.0
HEAT_SAFE_FRAC = 0.88


def build_agent(sandbox):
    return None


def _waypoint(x, y):
    """Next waypoint: gate1 -> gate2 -> target. Switch before reaching waypoint to avoid stall."""
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

    # Thrust magnitude: save heat early; use more near gate 1 (lift) and in drain/slip/wind
    if heat >= overheat_limit * HEAT_SAFE_FRAC:
        thrust_mag = min(LOW_THRUST, remaining * 0.25)
    else:
        thrust_mag = min(MAX_THRUST, remaining * 0.35)
    # Early phase: enough to overcome friction (~75 N) but save heat
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
    # Keep altitude above ground (craft half-height 0.25, ground y=1) -> center y >= 1.3
    if y < 1.4:
        wy = max(wy, 1.5)
    # Gate 2 gap y in [1.8, 3.0]: lift to pass through
    if G2_X - 1.0 <= x <= G2_X + 2.0 and y < 1.9:
        wy = max(wy, 2.2)
    # Approach gate 2: lift first so we pass through gap (y in [1.8, 3.0])
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
    # Overcome weight to lift off ground when in contact (gravity -3 -> weight ~75 N)
    if y < 1.4:
        fy += 100.0
    if x < G1_X + 1.0 and y < 1.1:
        fy += min(30.0, (1.2 - y) * 40.0)
    # Lift through gate 2 gap (y in [1.8, 3.0])
    if 20.5 <= x <= G2_X + 2.0 and y < 1.9:
        fy += 110.0

    # Slippery zone: extra forward thrust to overcome backward force
    if SLIP_LO <= x <= SLIP_HI:
        fx += 35.0

    # Wind zone: compensate oscillating vertical force
    if WIND_LO <= x <= WIND_HI:
        wind_fy = WIND_AMP * math.sin(WIND_OMEGA * step_idx)
        fy -= wind_fy

    total = math.sqrt(fx * fx + fy * fy)
    cap = thrust_mag * 2.0
    if y < 1.4:
        cap = max(cap, 180.0)  # allow lift force to overcome weight
    if 20.5 <= x <= G2_X + 2.0 and y < 1.9:
        cap = max(cap, 250.0)  # allow lift through gate 2 gap
    if total > cap:
        scale = cap / total
        fx *= scale
        fy *= scale

    sandbox.apply_thrust(fx, fy)