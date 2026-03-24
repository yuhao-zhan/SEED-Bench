import math

_ZONE_CENTERS_FALLBACK = {"A": (2.0, 2.0), "B": (4.95, 3.2), "C": (8.0, 2.0)}

_ZONE_EXTENTS_FALLBACK = {
    "A": (1.5, 2.5, 1.5, 2.5),
    "B": (4.25, 5.65, 2.8, 3.6),
    "C": (7.5, 8.5, 1.5, 2.5),

}

def _max_agent_force(sandbox):
    fn = getattr(sandbox, "get_terrain_bounds", None)
    if callable(fn):
        tb = fn()
        if isinstance(tb, dict) and "max_agent_force_per_axis" in tb:
            return float(tb["max_agent_force_per_axis"])
    return 50.0

def _zone_center(sandbox, name: str):
    fn = getattr(sandbox, "get_terrain_bounds", None)
    if callable(fn):
        tb = fn()
        zones = tb.get("zones") if isinstance(tb, dict) else None
        if zones and name in zones:
            cx, cy, _, _ = zones[name]
            return (cx, cy)
    return _ZONE_CENTERS_FALLBACK[name]

def is_inside_zone(sandbox, x, y, zone_name):
    fn = getattr(sandbox, "get_terrain_bounds", None)
    if callable(fn):
        tb = fn()
        zones = tb.get("zones") if isinstance(tb, dict) else None
        if zones and zone_name in zones:
            cx, cy, hw, hh = zones[zone_name]
            return (cx - hw <= x <= cx + hw) and (cy - hh <= y <= cy + hh)
    x_min, x_max, y_min, y_max = _ZONE_EXTENTS_FALLBACK[zone_name]
    return x_min <= x <= x_max and y_min <= y <= y_max

HOLD_RADIUS = 0.75

APPROACH_RADIUS = 2.0

GAIN_APPROACH = 6.0

GAIN_NORMAL = 15.0

HOLD_GAIN = 2.5

HOLD_DAMP = 5.5

APPROACH_DAMP = 1.8

RAMP_X_LO, RAMP_X_HI = 3.5, 6.0

RAMP_Y_TARGET = 3.5

RAMP_X_FRAC = 0.3

RAMP_Y_GAIN = 48.0

_step_when_a_triggered = [None]

def build_agent(sandbox):
    _step_when_a_triggered[0] = None
    return sandbox.get_agent_body()

def agent_action(sandbox, agent_body, step_count):
    bx = float(getattr(sandbox, "get_barrier_x", lambda: 4.5)())
    mf = _max_agent_force(sandbox)
    triggered = sandbox.get_triggered_switches()
    if triggered and "A" in triggered and _step_when_a_triggered[0] is None:
        _step_when_a_triggered[0] = step_count
    next_switch = sandbox.get_next_required_switch()
    cooldown = getattr(sandbox, "get_cooldown_remaining", lambda: 0)()
    if next_switch is None:
        vx, vy = sandbox.get_agent_velocity()
        sandbox.apply_agent_force(-HOLD_DAMP * 2.0 * vx, -HOLD_DAMP * 2.0 * vy)
        return
    if cooldown > 0:
        vx, vy = sandbox.get_agent_velocity()
        sandbox.apply_agent_force(-HOLD_DAMP * 2.0 * vx, -HOLD_DAMP * 2.0 * vy)
        return
    if next_switch == "B" and _step_when_a_triggered[0] is not None:
        delay = int(
            getattr(sandbox, "get_barrier_delay_steps", lambda: 70)()
        )
        steps_since_a = step_count - _step_when_a_triggered[0]
        if steps_since_a < delay:
            tx, ty = _zone_center(sandbox, "A")
            x, y = sandbox.get_agent_position()
            vx, vy = sandbox.get_agent_velocity()
            dx, dy = tx - x, ty - y
            sandbox.apply_agent_force(15.0 * dx - HOLD_DAMP * vx, 15.0 * dy - HOLD_DAMP * vy)
            return
    tx, ty = _zone_center(sandbox, next_switch)
    x, y = sandbox.get_agent_position()
    vx, vy = sandbox.get_agent_velocity()
    dx = tx - x
    dy = ty - y
    dist = math.sqrt(dx * dx + dy * dy)
    in_ramp = RAMP_X_LO <= x <= RAMP_X_HI
    use_ramp = in_ramp and (next_switch == "B" or (next_switch == "C" and (x < bx or y > 2.4)))
    on_flat_for_c = (y <= 2.6 or x >= 6.4) and not (3.5 <= x < bx)
    if next_switch == "C" and x < 7.5 and dist > 0.2 and on_flat_for_c:
        fx = mf * 0.98 if dx > 0 else -mf * 0.4
        fy = -HOLD_DAMP * vy
        sandbox.apply_agent_force(fx, fy)
        return
    if dist < 1e-6:
        sandbox.apply_agent_force(-HOLD_DAMP * vx, -HOLD_DAMP * vy)
        return
    inside = is_inside_zone(sandbox, x, y, next_switch)
    if inside or dist < HOLD_RADIUS:
        speed = math.sqrt(vx * vx + vy * vy)
        if next_switch == "C" or speed > 0.1:
            fx = 10.0 * dx - HOLD_DAMP * 8.0 * vx
            fy = 10.0 * dy - HOLD_DAMP * 8.0 * vy
        else:
            fx = HOLD_GAIN * 10.0 * dx - HOLD_DAMP * 2.0 * vx
            fy = HOLD_GAIN * 10.0 * dy - HOLD_DAMP * 2.0 * vy
        mag = math.sqrt(fx * fx + fy * fy)
        if mag > mf:
            fx, fy = fx * mf / mag, fy * mf / mag
        sandbox.apply_agent_force(fx, fy)
        return
    if use_ramp:
        if next_switch == "B" or (next_switch == "C" and x < bx):
            y_target = 3.3
            fx = min(mf * 0.6, 30.0) * (1.0 if dx > 0 else -0.5) - APPROACH_DAMP * 2.0 * vx
            fy = RAMP_Y_GAIN * (y_target - y) - APPROACH_DAMP * 2.0 * vy
        else:
            y_target = 2.0
            dy_local = y_target - y
            if y > 3.0:
                fx = mf * 0.98 if dx > 0 else -mf * 0.3
                y_target_local = 3.9 if x < 6.4 else 2.0
                fy = 60.0 * (y_target_local - y) - APPROACH_DAMP * vy
            else:
                fx = min(mf * 0.95, 47.0) * (1.0 if dx > 0 else 0.5) - APPROACH_DAMP * 2.0 * vx
                fy = RAMP_Y_GAIN * dy_local - APPROACH_DAMP * 2.0 * vy
        mag = math.sqrt(fx * fx + fy * fy)
        if mag > mf:
            fx, fy = fx * mf / mag, fy * mf / mag
        sandbox.apply_agent_force(fx, fy)
        return
    if dist < APPROACH_RADIUS:
        force_mag = min(mf * 0.5, GAIN_APPROACH * 2.0 * dist)
        ux, uy = (dx / dist, dy / dist) if dist > 1e-6 else (0, 0)
        fx = force_mag * ux - APPROACH_DAMP * 3.0 * vx
        fy = force_mag * uy - APPROACH_DAMP * 3.0 * vy
        mag = math.sqrt(fx * fx + fy * fy)
        if mag > mf:
            fx, fy = fx * mf / mag, fy * mf / mag
        sandbox.apply_agent_force(fx, fy)
        return
    gain = GAIN_NORMAL * 0.8 if next_switch == "B" else GAIN_NORMAL
    force_mag = min(mf, gain * dist)
    ux, uy = (dx / dist, dy / dist) if dist > 1e-6 else (0, 0)
    sandbox.apply_agent_force(force_mag * ux - 2.0 * vx, force_mag * uy - 2.0 * vy)

_step_when_a_triggered_s1 = [None]

def build_agent_stage_1(sandbox):
    return sandbox.get_agent_body()

def agent_action_stage_1(sandbox, agent_body, step_count):
    bx = float(getattr(sandbox, "get_barrier_x", lambda: 4.5)())
    delay_barrier = int(getattr(sandbox, "get_barrier_delay_steps", lambda: 70)())
    mf = _max_agent_force(sandbox)
    SPEED_CAP_S1 = 0.05
    triggered = sandbox.get_triggered_switches()
    if triggered and triggered[0] == "A" and _step_when_a_triggered_s1[0] is None:
        _step_when_a_triggered_s1[0] = step_count
    next_switch = sandbox.get_next_required_switch()
    cooldown = getattr(sandbox, "get_cooldown_remaining", lambda: 0)()
    if next_switch is None:
        vx, vy = sandbox.get_agent_velocity()
        sandbox.apply_agent_force(-HOLD_DAMP * vx, -HOLD_DAMP * vy)
        return
    if cooldown > 0:
        vx, vy = sandbox.get_agent_velocity()
        sandbox.apply_agent_force(-HOLD_DAMP * vx, -HOLD_DAMP * vy)
        return
    if next_switch == "B" and _step_when_a_triggered_s1[0] is not None:
        steps_since_a = step_count - _step_when_a_triggered_s1[0]
        if steps_since_a < delay_barrier:
            tx, ty = _zone_center(sandbox, "A")
            x, y = sandbox.get_agent_position()
            vx, vy = sandbox.get_agent_velocity()
            dx, dy = tx - x, ty - y
            sandbox.apply_agent_force(10.0 * dx - HOLD_DAMP * vx, 10.0 * dy - HOLD_DAMP * vy)
            return
    tx, ty = _zone_center(sandbox, next_switch)
    x, y = sandbox.get_agent_position()
    vx, vy = sandbox.get_agent_velocity()
    dx, dy = tx - x, ty - y
    dist = math.sqrt(dx * dx + dy * dy)
    speed_s1 = math.sqrt(vx * vx + vy * vy)
    in_ramp = RAMP_X_LO <= x <= RAMP_X_HI
    use_ramp = in_ramp and (next_switch == "B" or (next_switch == "C" and (x < bx or y > 2.4)))
    on_flat_for_c = (y <= 2.6 or x >= 6.4) and not (3.5 <= x < bx)
    inside = is_inside_zone(sandbox, x, y, next_switch)
    if next_switch == "C" and x < 7.5 and dist > 0.2 and on_flat_for_c:
        fx = mf * 0.98 if dx > 0 else -mf * 0.4
        fy = -HOLD_DAMP * vy
        sandbox.apply_agent_force(fx, fy)
        return
    if dist < 1e-6:
        sandbox.apply_agent_force(-HOLD_DAMP * vx, -HOLD_DAMP * vy)
        return
    if inside or dist < 0.5:
        if next_switch == "C" or speed_s1 > 0.035:
            fx = -HOLD_DAMP * 15.0 * vx
            fy = -HOLD_DAMP * 15.0 * vy + (25.0 if in_ramp else 0.0)
        else:
            fx = 100.0 * dx - HOLD_DAMP * 8.0 * vx
            fy = 100.0 * dy - HOLD_DAMP * 8.0 * vy + (28.0 if in_ramp else 0.0)
        mag = math.sqrt(fx * fx + fy * fy)
        if mag > 35.0:
            fx, fy = fx * 35.0 / mag, fy * 35.0 / mag
        sandbox.apply_agent_force(fx, fy)
        return
    if use_ramp:
        if next_switch == "B" or (next_switch == "C" and x < bx):
            y_target = RAMP_Y_TARGET
            fx = min(mf * 0.75, 36.0) * (1.0 if dx > 0 else -0.5) - APPROACH_DAMP * vx
            fy = RAMP_Y_GAIN * (y_target - y) - APPROACH_DAMP * vy
        else:
            y_target = 2.0
            dy_local = y_target - y
            if y > 3.0:
                fx = mf * 0.98 if dx > 0 else -mf * 0.3
                y_target_local = 3.9 if x < 6.4 else 2.0
                fy = 60.0 * (y_target_local - y) - APPROACH_DAMP * vy
            else:
                fx = min(mf * 0.95, 47.0) * (1.0 if dx > 0 else 0.5) - APPROACH_DAMP * vx
                fy = RAMP_Y_GAIN * dy_local - APPROACH_DAMP * vx
        mag = math.sqrt(fx * fx + fy * fy)
        if mag > mf:
            fx, fy = fx * mf / mag, fy * mf / mag
        sandbox.apply_agent_force(fx, fy)
        return
    if dist < APPROACH_RADIUS:
        force_mag = min(mf * 0.35, GAIN_APPROACH * dist)
        ux, uy = (dx / dist, dy / dist) if dist > 1e-6 else (0, 0)
        fx = force_mag * ux - APPROACH_DAMP * vx
        fy = force_mag * uy - APPROACH_DAMP * vy
        mag = math.sqrt(fx * fx + fy * fy)
        if mag > mf:
            fx, fy = fx * mf / mag, fy * mf / mag
        sandbox.apply_agent_force(fx, fy)
        return
    gain = GAIN_NORMAL * 1.2 if next_switch == "B" else GAIN_NORMAL
    force_mag = min(mf, gain * dist)
    ux, uy = (dx / dist, dy / dist) if dist > 1e-6 else (0, 0)
    sandbox.apply_agent_force(force_mag * ux, force_mag * uy)

_step_when_a_triggered_s2 = [None]

def build_agent_stage_2(sandbox):
    return sandbox.get_agent_body()

def agent_action_stage_2(sandbox, agent_body, step_count):
    bx = float(getattr(sandbox, "get_barrier_x", lambda: 4.5)())
    delay_barrier = int(getattr(sandbox, "get_barrier_delay_steps", lambda: 70)())
    mf = _max_agent_force(sandbox)
    SPEED_CAP_S2 = 0.05
    triggered = sandbox.get_triggered_switches()
    if triggered and triggered[0] == "A" and _step_when_a_triggered_s2[0] is None:
        _step_when_a_triggered_s2[0] = step_count
    next_switch = sandbox.get_next_required_switch()
    cooldown = getattr(sandbox, "get_cooldown_remaining", lambda: 0)()
    if next_switch is None:
        vx, vy = sandbox.get_agent_velocity()
        sandbox.apply_agent_force(-HOLD_DAMP * vx, -HOLD_DAMP * vy)
        return
    if cooldown > 0:
        vx, vy = sandbox.get_agent_velocity()
        sandbox.apply_agent_force(-HOLD_DAMP * vx, -HOLD_DAMP * vy)
        return
    if next_switch == "B" and _step_when_a_triggered_s2[0] is not None:
        steps_since_a = step_count - _step_when_a_triggered_s2[0]
        if steps_since_a < delay_barrier:
            tx, ty = _zone_center(sandbox, "A")
            x, y = sandbox.get_agent_position()
            vx, vy = sandbox.get_agent_velocity()
            dx, dy = tx - x, ty - y
            sandbox.apply_agent_force(15.0 * dx - HOLD_DAMP * vx, 15.0 * dy - HOLD_DAMP * vy)
            return
    tx, ty = _zone_center(sandbox, next_switch)
    x, y = sandbox.get_agent_position()
    vx, vy = sandbox.get_agent_velocity()
    dx, dy = tx - x, ty - y
    dist = math.sqrt(dx * dx + dy * dy)
    speed = math.sqrt(vx * vx + vy * vy)
    in_ramp = RAMP_X_LO <= x <= RAMP_X_HI
    use_ramp = in_ramp and (next_switch == "B" or (next_switch == "C" and (x < bx or y > 2.4)))
    on_flat_for_c = (y <= 2.6 or x >= 6.4) and not (3.5 <= x < bx)
    inside = is_inside_zone(sandbox, x, y, next_switch)
    if next_switch == "C" and x < 7.5 and dist > 0.2 and on_flat_for_c:
        fx = mf * 0.98 if dx > 0 else -mf * 0.4
        fy = -HOLD_DAMP * vy
        sandbox.apply_agent_force(fx, fy)
        return
    if dist < 1e-6:
        sandbox.apply_agent_force(-HOLD_DAMP * vx, -HOLD_DAMP * vy)
        return
    if inside or dist < 1.0:
        fy_boost = 35.0 if in_ramp else 0.0
        if speed > 0.025:
            fx = -HOLD_DAMP * 60.0 * vx
            fy = -HOLD_DAMP * 60.0 * vy + fy_boost
        else:
            fx = 300.0 * dx - HOLD_DAMP * 20.0 * vx
            fy = 300.0 * dy - HOLD_DAMP * 20.0 * vy + fy_boost
        mag = math.sqrt(fx * fx + fy * fy)
        if mag > mf:
            fx, fy = fx * mf / mag, fy * mf / mag
        sandbox.apply_agent_force(fx, fy)
        return
    if use_ramp:
        if next_switch == "B" or (next_switch == "C" and x < bx):
            y_target = RAMP_Y_TARGET
            fx = min(mf * 0.95, 45.0) * (1.0 if dx > 0 else -0.5) - APPROACH_DAMP * vx
            fy = RAMP_Y_GAIN * (y_target - y) + (40.0 if y < 3.2 else 0.0) - APPROACH_DAMP * vy
        else:
            y_target = 2.0
            dy_local = y_target - y
            if y > 3.0:
                fx = mf * 0.98 if dx > 0 else -mf * 0.3
                y_target_local = 3.9 if x < 6.4 else 2.0
                fy = 60.0 * (y_target_local - y) - APPROACH_DAMP * vy
            else:
                fx = min(mf * 0.95, 47.0) * (1.0 if dx > 0 else 0.5) - APPROACH_DAMP * vx
                fy = RAMP_Y_GAIN * dy_local - APPROACH_DAMP * vx
        mag = math.sqrt(fx * fx + fy * fy)
        if mag > mf:
            fx, fy = fx * mf / mag, fy * mf / mag
        sandbox.apply_agent_force(fx, fy)
        return
    if dist < APPROACH_RADIUS:
        force_mag = min(mf * 0.5, GAIN_APPROACH * 2.0 * dist)
        ux, uy = (dx / dist, dy / dist) if dist > 1e-6 else (0, 0)
        fx = force_mag * ux - APPROACH_DAMP * 1.5 * vx
        fy = (force_mag * uy if y > 2.2 else 15.0) - APPROACH_DAMP * 1.5 * vy
        mag = math.sqrt(fx * fx + fy * fy)
        if mag > mf:
            fx, fy = fx * mf / mag, fy * mf / mag
        sandbox.apply_agent_force(fx, fy)
        return
    gain = GAIN_NORMAL * 2.0 if next_switch == "B" else GAIN_NORMAL * 1.5
    force_mag = min(mf, gain * dist)
    ux, uy = (dx / dist, dy / dist) if dist > 1e-6 else (0, 0)
    sandbox.apply_agent_force(force_mag * ux, force_mag * uy)

_step_when_a_triggered_s3 = [None]

def build_agent_stage_3(sandbox):
    return sandbox.get_agent_body()

def agent_action_stage_3(sandbox, agent_body, step_count):
    bx = float(getattr(sandbox, "get_barrier_x", lambda: 4.5)())
    delay_barrier = int(getattr(sandbox, "get_barrier_delay_steps", lambda: 70)())
    mf = _max_agent_force(sandbox)
    FORCE_LIMIT = 45.0
    triggered = sandbox.get_triggered_switches()
    if triggered and triggered[0] == "A" and _step_when_a_triggered_s3[0] is None:
        _step_when_a_triggered_s3[0] = step_count
    next_switch = sandbox.get_next_required_switch()
    cooldown = getattr(sandbox, "get_cooldown_remaining", lambda: 0)()
    if next_switch is None:
        vx, vy = sandbox.get_agent_velocity()
        sandbox.apply_agent_force(-HOLD_DAMP * vx, -HOLD_DAMP * vy)
        return
    if cooldown > 0:
        vx, vy = sandbox.get_agent_velocity()
        sandbox.apply_agent_force(-HOLD_DAMP * vx, -HOLD_DAMP * vy)
        return
    if next_switch == "B" and _step_when_a_triggered_s3[0] is not None:
        steps_since_a = step_count - _step_when_a_triggered_s3[0]
        if steps_since_a < delay_barrier:
            tx, ty = _zone_center(sandbox, "A")
            x, y = sandbox.get_agent_position()
            vx, vy = sandbox.get_agent_velocity()
            dx, dy = tx - x, ty - y
            sandbox.apply_agent_force(20.0 * dx - HOLD_DAMP * vx, 20.0 * dy - HOLD_DAMP * vy)
            return
    tx, ty = _zone_center(sandbox, next_switch)
    x, y = sandbox.get_agent_position()
    vx, vy = sandbox.get_agent_velocity()
    dx, dy = tx - x, ty - y
    dist = math.sqrt(dx * dx + dy * dy)
    in_ramp = RAMP_X_LO <= x <= RAMP_X_HI
    use_ramp = in_ramp and (next_switch == "B" or (next_switch == "C" and (x < bx or y > 2.4)))
    on_flat_for_c = (y <= 2.6 or x >= 6.4) and not (3.5 <= x < bx)
    inside = is_inside_zone(sandbox, x, y, next_switch)
    force_cap = (FORCE_LIMIT * 0.9) if inside else mf
    if next_switch == "C" and x < 7.5 and dist > 0.2 and on_flat_for_c:
        fx = min(mf * 0.98, force_cap) if dx > 0 else max(-mf * 0.4, -force_cap)
        fy = -HOLD_DAMP * vy
        sandbox.apply_agent_force(fx, fy)
        return
    if dist < 1e-6:
        sandbox.apply_agent_force(-HOLD_DAMP * vx, -HOLD_DAMP * vy)
        return
    if inside or dist < 0.5:
        speed = math.sqrt(vx * vx + vy * vy)
        if speed > 0.12:
            fx = -HOLD_DAMP * 20.0 * vx
            fy = -HOLD_DAMP * 20.0 * vy
        else:
            fx = 300.0 * dx - HOLD_DAMP * 15.0 * vx
            fy = 300.0 * dy - HOLD_DAMP * 15.0 * vy
        mag = math.sqrt(fx * fx + fy * fy)
        if mag > force_cap:
            fx, fy = fx * force_cap / mag, fy * force_cap / mag
        sandbox.apply_agent_force(fx, fy)
        return
    if use_ramp:
        if next_switch == "B" or (next_switch == "C" and x < bx):
            y_target = RAMP_Y_TARGET
            fx = min(mf * 0.95, force_cap) * (1.0 if dx > 0 else -0.5) - APPROACH_DAMP * 1.5 * vx
            fy = RAMP_Y_GAIN * 0.8 * (y_target - y) - APPROACH_DAMP * 1.5 * vy
        else:
            y_target = 2.0
            dy_local = y_target - y
            if y > 3.0:
                fx = min(mf * 0.98, force_cap) if dx > 0 else max(-mf * 0.3, -force_cap)
                y_target_local = 3.9 if x < 6.4 else 2.0
                fy = 60.0 * (y_target_local - y) - APPROACH_DAMP * vy
            else:
                fx = min(mf * 0.95, force_cap) if dx > 0 else max(-mf * 0.3, -force_cap)
                fy = RAMP_Y_GAIN * 0.6 * dy_local - APPROACH_DAMP * vx
        mag = math.sqrt(fx * fx + fy * fy)
        if mag > force_cap:
            fx, fy = fx * force_cap / mag, fy * force_cap / mag
        sandbox.apply_agent_force(fx, fy)
        return
    if dist < APPROACH_RADIUS:
        force_mag = min(force_cap, max(45.0, GAIN_APPROACH * 10.0 * dist))
        ux, uy = (dx / dist, dy / dist) if dist > 1e-6 else (0, 0)
        fx = force_mag * ux - APPROACH_DAMP * vx
        fy = (force_mag * uy if y > 2.2 else 25.0) - APPROACH_DAMP * vy
        mag = math.sqrt(fx * fx + fy * fy)
        if mag > force_cap:
            fx, fy = fx * force_cap / mag, fy * force_cap / mag
        sandbox.apply_agent_force(fx, fy)
        return
    gain = GAIN_NORMAL * 5.0 if next_switch == "B" else GAIN_NORMAL * 3.0
    force_mag = min(force_cap, gain * dist)
    ux, uy = (dx / dist, dy / dist) if dist > 1e-6 else (0, 0)
    sandbox.apply_agent_force(force_mag * ux, force_mag * uy)

_step_when_a_triggered_s4 = [None]

def build_agent_stage_4(sandbox):
    return sandbox.get_agent_body()

def agent_action_stage_4(sandbox, agent_body, step_count):
    bx = float(getattr(sandbox, "get_barrier_x", lambda: 4.5)())
    delay_barrier = int(getattr(sandbox, "get_barrier_delay_steps", lambda: 70)())
    mf = _max_agent_force(sandbox)
    FORCE_LIMIT_S4 = 60.0
    HOLD_DAMP_S4 = 10.0
    triggered = sandbox.get_triggered_switches()
    if triggered and triggered[0] == "A" and _step_when_a_triggered_s4[0] is None:
        _step_when_a_triggered_s4[0] = step_count
    next_switch = sandbox.get_next_required_switch()
    cooldown = getattr(sandbox, "get_cooldown_remaining", lambda: 0)()
    if next_switch is None:
        vx, vy = sandbox.get_agent_velocity()
        sandbox.apply_agent_force(-HOLD_DAMP_S4 * vx, -HOLD_DAMP_S4 * vy)
        return
    if cooldown > 0:
        vx, vy = sandbox.get_agent_velocity()
        sandbox.apply_agent_force(-HOLD_DAMP_S4 * vx, -HOLD_DAMP_S4 * vy)
        return
    if next_switch == "B" and _step_when_a_triggered_s4[0] is not None:
        steps_since_a = step_count - _step_when_a_triggered_s4[0]
        if steps_since_a < delay_barrier:
            tx, ty = _zone_center(sandbox, "A")
            x, y = sandbox.get_agent_position()
            vx, vy = sandbox.get_agent_velocity()
            dx, dy = tx - x, ty - y
            sandbox.apply_agent_force(60.0 * dx - HOLD_DAMP_S4 * vx, 60.0 * dy - HOLD_DAMP_S4 * vy)
            return
    tx, ty = _zone_center(sandbox, next_switch)
    x, y = sandbox.get_agent_position()
    vx, vy = sandbox.get_agent_velocity()
    dx, dy = tx - x, ty - y
    dist = math.sqrt(dx * dx + dy * dy)
    speed = math.sqrt(vx * vx + vy * vy)
    in_ramp = RAMP_X_LO <= x <= RAMP_X_HI
    use_ramp = in_ramp and (next_switch == "B" or (next_switch == "C" and (x < bx or y > 2.4)))
    on_flat_for_c = (y <= 2.6 or x >= 6.4) and not (3.5 <= x < bx)
    inside = is_inside_zone(sandbox, x, y, next_switch)
    force_cap = (FORCE_LIMIT_S4 * 0.95) if inside else mf
    if next_switch == "C" and x < 7.5 and dist > 0.2 and on_flat_for_c:
        fx = min(mf * 0.98, force_cap) if dx > 0 else max(-mf * 0.4, -force_cap)
        fy = -HOLD_DAMP_S4 * vy
        sandbox.apply_agent_force(fx, fy)
        return
    if dist < 1e-6:
        sandbox.apply_agent_force(-HOLD_DAMP_S4 * vx, -HOLD_DAMP_S4 * vy)
        return
    if inside or dist < 1.0:
        fy_boost = 100.0 if in_ramp else 50.0
        fx = 5000.0 * dx - HOLD_DAMP_S4 * 100.0 * vx
        fy = 5000.0 * dy - HOLD_DAMP_S4 * 100.0 * vy + fy_boost
        mag = math.sqrt(fx * fx + fy * fy)
        if mag > force_cap:
            fx, fy = fx * force_cap / mag, fy * force_cap / mag
        sandbox.apply_agent_force(fx, fy)
        return
    if use_ramp:
        if next_switch == "B" or (next_switch == "C" and x < bx):
            y_target = RAMP_Y_TARGET
            fx = min(mf * 0.95, force_cap) * (1.0 if dx > 0 else -0.5) - HOLD_DAMP_S4 * vx
            fy = RAMP_Y_GAIN * (0.4 if dist < 1.0 else 0.9) * (y_target - y) + (60.0 if y < 3.2 else 0.0) - HOLD_DAMP_S4 * vy
        else:
            y_target = 2.0
            dy_local = y_target - y
            if y > 3.0:
                fx = mf * 0.98 if dx > 0 else -mf * 0.3
                y_target_local = 3.9 if x < 6.4 else 2.0
                fy = 60.0 * (y_target_local - y) - HOLD_DAMP_S4 * vy
            else:
                fx = min(mf * 0.95, force_cap) if dx > 0 else -mf * 0.3
                fy = RAMP_Y_GAIN * (0.4 if dist < 1.0 else 0.9) * dy_local - HOLD_DAMP_S4 * vx
        mag = math.sqrt(fx * fx + fy * fy)
        if mag > force_cap:
            fx, fy = fx * force_cap / mag, fy * force_cap / mag
        sandbox.apply_agent_force(fx, fy)
        return
    if dist < APPROACH_RADIUS:
        force_mag = min(force_cap, max(200.0, GAIN_APPROACH * 60.0 * dist))
        ux, uy = (dx / dist, dy / dist) if dist > 1e-6 else (0, 0)
        fx = force_mag * ux - HOLD_DAMP_S4 * 10.0 * vx
        fy = (force_mag * uy if y > 2.2 else 150.0) - HOLD_DAMP_S4 * 10.0 * vy
        mag = math.sqrt(fx * fx + fy * fy)
        if mag > force_cap:
            fx, fy = fx * force_cap / mag, fy * force_cap / mag
        sandbox.apply_agent_force(fx, fy)
        return
    gain = GAIN_NORMAL * 20.0
    force_mag = min(force_cap, gain * dist)
    ux, uy = (dx / dist, dy / dist) if dist > 1e-6 else (0, 0)
    sandbox.apply_agent_force(force_mag * ux, force_mag * uy)
