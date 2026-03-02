"""
D-04: The Swing agent (HARD: apex in zone or vertical fall into zone).
Pump with phase + wind-aware logic. Goal: apex (v≈0) in red zone, or fall vertically through zone after apex.
"""
import math

MIN_VX_FOR_PUMP = 0.10
INITIAL_IMPULSE = 38.0
WIND_OPPOSE_THRESHOLD = 14.0
DT = 1.0 / 60.0
# When very high and going up, stop pumping so next apex is in zone (avoid over-pump)
COAST_Y = 11.4   # coast when py > this and vy >= COAST_VY so apex lands in zone (y>=11.7)
COAST_VY = -0.3


def build_agent(sandbox):
    seat = sandbox.get_swing_seat()
    if seat is None:
        raise ValueError("Swing seat not found in environment")
    return seat


def agent_action(sandbox, agent_body, step_count):
    seat = sandbox.get_swing_seat()
    if seat is None:
        return
    vx = seat.linearVelocity.x
    vy = seat.linearVelocity.y
    px, py = seat.position.x, seat.position.y

    if step_count < 2:
        sandbox.apply_impulse_to_seat(INITIAL_IMPULSE, 0.0)
        return

    max_force = getattr(sandbox, "MAX_PUMP_FORCE", 42.0)
    if max_force <= 0:
        return
    if abs(vx) < MIN_VX_FOR_PUMP:
        return
    # Near apex / going up and already high: coast so apex lands in zone
    if py > COAST_Y and vy >= COAST_VY:
        return

    sim_time = sandbox.get_sim_time() + DT
    wind_fx = sandbox.get_wind_force_at_time(sim_time) if hasattr(sandbox, "get_wind_force_at_time") else 0.0
    if vx > 0 and wind_fx < -WIND_OPPOSE_THRESHOLD:
        return
    if vx < 0 and wind_fx > WIND_OPPOSE_THRESHOLD:
        return

    fx = math.copysign(max_force, vx)
    sandbox.apply_force_to_seat(fx, 0.0)
