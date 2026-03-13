import math

def build_agent(sandbox):
    return sandbox.get_seeker_body()

def agent_action(sandbox, agent_body, step_count):
    if not hasattr(agent_body, '_state'):
        agent_body._state = {'last_tx': 0.0, 'last_ty': 0.0, 'tvx': 0.0, 'tvy': 0.0}
    state = agent_body._state
    tx, ty = sandbox.get_target_position()
    sx, sy = sandbox.get_seeker_position()
    svx, svy = sandbox.get_seeker_velocity()
    if step_count % 5 == 0 and step_count > 5:
        dt = 5.0 / 60.0
        state['tvx'] = 0.5 * state['tvx'] + 0.5 * (tx - state['last_tx']) / dt
        state['tvy'] = 0.5 * state['tvy'] + 0.5 * (ty - state['last_ty']) / dt
        state['last_tx'], state['last_ty'] = tx, ty
    elif step_count <= 5:
        state['last_tx'], state['last_ty'] = tx, ty
    in_slot = any(lo <= step_count <= hi for (lo, hi) in [(3700, 3800), (4200, 4300), (4700, 4800), (6200, 6300), (6700, 6800), (7200, 7300)])
    if step_count < 110: gx, gy = 11.95, 1.35
    elif in_slot: gx, gy = tx, ty
    else:
        gx = 13.1 if (step_count // 120) % 2 == 0 else 13.5
        gy = 1.35
    if in_slot:
        fx = 300.0 * (gx - sx) + 60.0 * (state['tvx'] - svx)
        fy = 300.0 * (gy - sy) + 60.0 * (state['tvy'] - svy)
    else:
        fx = 300.0 * (gx - sx) - 60.0 * svx
        fy = 180.0 * (gy - sy) - 45.0 * svy
    if step_count >= 110 and abs(gx - sx) > 0.05:
        if abs(fx) < 110.0: fx = 110.0 if (gx - sx) > 0 else -110.0
    mag = math.sqrt(fx*fx + fy*fy)
    if mag > 119.0: fx, fy = fx * 119.0 / mag, fy * 119.0 / mag
    sandbox.apply_seeker_force(fx, fy)

def build_agent_stage_1(sandbox):
    return sandbox.get_seeker_body()

def agent_action_stage_1(sandbox, agent_body, step_count):
    if not hasattr(agent_body, 's1'):
        tx_init, ty_init = sandbox.get_target_position()
        agent_body.s1 = {'ltx': tx_init, 'lty': ty_init, 'vx': 0.0, 'vy': 0.0, 'tx_est': tx_init, 'ty_est': ty_init}
    m = agent_body.s1
    tx, ty = sandbox.get_target_position()
    sx, sy = sandbox.get_seeker_position()
    vx, vy = sandbox.get_seeker_velocity()
    c_lo, c_hi = sandbox.get_corridor_bounds()
    if (tx, ty) != (m['ltx'], m['lty']):
        dt = 5.0 / 60.0
        m['vx'] = 0.5 * m['vx'] + 0.5 * (tx - m['ltx']) / dt
        m['vy'] = 0.5 * m['vy'] + 0.5 * (ty - m['lty']) / dt
        m['ltx'], m['lty'] = tx, ty
        m['tx_est'], m['ty_est'] = tx, ty
    else:
        m['tx_est'] += m['vx'] * (1.0/60.0)
        m['ty_est'] += m['vy'] * (1.0/60.0)
    slots = [(3700, 3800), (4200, 4300), (4700, 4800), (6200, 6300), (6700, 6800), (7200, 7300)]
    in_slot = any((lo - 60) <= step_count <= hi for (lo, hi) in slots)
    if in_slot:
        gx, gy = m['tx_est'], m['ty_est']
        gx = max(c_lo + 2.5, min(c_hi - 2.5, gx))
    else:
        gx, gy = 15.5, 1.35
    if in_slot:
        fx = 1500.0 * (gx - sx) + 400.0 * (m['vx'] - vx)
        fy = 1500.0 * (gy - sy) + 400.0 * (m['vy'] - vy) + 200.0
    else:
        fx = 400.0 * (gx - sx) - 100.0 * vx
        fy = 400.0 * (gy - sy) - 100.0 * vy + 200.0
    mag = math.hypot(fx, fy)
    if mag > 119.0: fx, fy = fx * 119.0 / mag, fy * 119.0 / mag
    sandbox.apply_seeker_force(fx, fy)

def build_agent_stage_2(sandbox):
    return sandbox.get_seeker_body()

def agent_action_stage_2(sandbox, agent_body, step_count):
    tx, ty = sandbox.get_target_position()
    sx, sy = sandbox.get_seeker_position()
    vx, vy = sandbox.get_seeker_velocity()
    c_lo, c_hi = sandbox.get_corridor_bounds()
    gx = max(16.5, tx)
    gx = min(c_hi - 2.5, gx)
    gy = 1.35
    fx = 1500.0 * (gx - sx) - 200.0 * vx + 100.0
    fy = 1500.0 * (gy - sy) - 200.0 * vy + 200.0
    mag = math.hypot(fx, fy)
    if mag > 119.0: fx, fy = fx * 119.0 / mag, fy * 119.0 / mag
    sandbox.apply_seeker_force(fx, fy)

def build_agent_stage_3(sandbox):
    return sandbox.get_seeker_body()

def agent_action_stage_3(sandbox, agent_body, step_count):
    tx, ty = sandbox.get_target_position()
    sx, sy = sandbox.get_seeker_position()
    c_lo, c_hi = sandbox.get_corridor_bounds()
    gx = max(c_lo + 1.5, min(c_hi - 1.5, tx))
    if step_count < 150: gx = 15.0
    fx = 8000.0 * (gx - sx)
    fy = 6000.0 * (1.35 - sy)
    mag = math.hypot(fx, fy)
    if mag > 199.0: fx, fy = fx * 199.0 / mag, fy * 199.0 / mag
    sandbox.apply_seeker_force(fx, fy)

def build_agent_stage_4(sandbox):
    return sandbox.get_seeker_body()

def agent_action_stage_4(sandbox, agent_body, step_count):
    tx, ty = sandbox.get_target_position()
    sx, sy = sandbox.get_seeker_position()
    vx, vy = sandbox.get_seeker_velocity()
    sh = sandbox.get_seeker_heading()
    slots = [(3700, 3800), (4200, 4300), (4700, 4800), (6200, 6300), (6700, 6800), (7200, 7300)]
    in_slot = any(lo <= step_count <= hi for (lo, hi) in slots)
    if in_slot:
        dfx, dfy = 1500.0 * (tx - sx) - 200.0 * vx, 1200.0 * (ty - sy) - 150.0 * vy
        dfx += 1200.0 if (tx - sx) > 0 else -1200.0
    else:
        gx = 13.5
        if step_count < 40: dfx, dfy = 100.0, 0.0
        elif abs(sx - gx) > 0.5: dfx, dfy = 150.0 * (gx - sx) - 50.0 * vx, 0.0
        else: dfx, dfy = -40.0 * vx if abs(vx) > 0.02 else 0.0, 0.0
    mag = math.hypot(dfx, dfy)
    da = math.atan2(dfy, dfx)
    delta = da - sh
    while delta > math.pi: delta -= 2*math.pi
    while delta < -math.pi: delta += 2*math.pi
    if abs(delta) > 0.4 and mag > 5.0: mag = 10.0
    if mag > 110.0: mag = 110.0
    sandbox.apply_seeker_force(mag * math.cos(da), mag * math.sin(da))
