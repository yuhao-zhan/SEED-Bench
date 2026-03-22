import math

def _rendezvous_slot_intervals(sandbox):
    return sandbox.get_rendezvous_slots()

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
    slots = _rendezvous_slot_intervals(sandbox)
    in_slot = any(lo <= step_count <= hi for (lo, hi) in slots)
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
    slots = _rendezvous_slot_intervals(sandbox)
    in_slot = any(lo <= step_count <= hi for (lo, hi) in slots)
    if in_slot:
        gx, gy = m['tx_est'], m['ty_est']
        gx = max(c_lo + 2.5, min(c_hi - 2.5, gx))
    else:
        gx, gy = 15.5, 1.35
    if in_slot:
        fx = 2000.0 * (gx - sx) + 600.0 * (m['vx'] - vx)
        fy = 2000.0 * (gy - sy) + 600.0 * (m['vy'] - vy) + 300.0
    else:
        fx = 800.0 * (gx - sx) - 200.0 * vx
        fy = 800.0 * (gy - sy) - 200.0 * vy + 300.0
    mag = math.hypot(fx, fy)
    if mag > 190.0: fx, fy = fx * 190.0 / mag, fy * 190.0 / mag
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
    if not hasattr(agent_body, 's3'):
        agent_body.s3 = {'act': False, 'act_steps': 0}
    state = agent_body.s3
    tx, ty = sandbox.get_target_position()
    sx, sy = sandbox.get_seeker_position()
    vx, vy = sandbox.get_seeker_velocity()
    slots = _rendezvous_slot_intervals(sandbox)
    in_slot = any(lo <= step_count <= hi for (lo, hi) in slots)
    if not state['act']:
        gx, gy = 14.0, 2.4
        if 13.5 <= sx <= 14.5:
            state['act_steps'] += 1
            if state['act_steps'] >= 80: state['act'] = True
        else:
            state['act_steps'] = 0
    elif in_slot:
        gx, gy = tx, ty
        gx = max(13.0, min(17.0, gx))
        gy = max(2.2, min(3.5, gy))
    else:
        gx, gy = 14.0, 2.4
    kp, kd = 1200.0, 250.0
    fx = kp * (gx - sx) - kd * vx + 36.0 * vx - 24.0
    fy = kp * (gy - sy) - kd * vy + 36.0 * vy + 220.0
    mag = math.hypot(fx, fy)
    if mag > 450.0:
        fx, fy = fx * 450.0 / mag, fy * 450.0 / mag
    sandbox.apply_seeker_force(fx, fy)

def build_agent_stage_4(sandbox):
    return sandbox.get_seeker_body()

def agent_action_stage_4(sandbox, agent_body, step_count):
    tx, ty = sandbox.get_target_position()
    sx, sy = sandbox.get_seeker_position()
    vx, vy = sandbox.get_seeker_velocity()
    sh = sandbox.get_seeker_heading()
    slots = _rendezvous_slot_intervals(sandbox)
    in_slot = any(lo <= step_count <= hi for (lo, hi) in slots)
    if in_slot:
        dfx, dfy = 1200.0 * (tx - sx) - 150.0 * vx, 800.0 * (ty - sy) - 100.0 * vy
    else:
        gx, gy = 13.5, 1.35
        dfx, dfy = 200.0 * (gx - sx) - 50.0 * vx, 100.0 * (gy - sy) - 25.0 * vy
    mag = math.hypot(dfx, dfy)
    da = math.atan2(dfy, dfx)
    if mag > 120.0: mag = 120.0
    delta = da - sh
    while delta > math.pi: delta -= 2*math.pi
    while delta < -math.pi: delta += 2*math.pi
    if abs(delta) < 0.5 or mag > 20.0:
        sandbox.apply_seeker_force(mag * math.cos(da), mag * math.sin(da))
    else:
        sandbox.apply_seeker_force(0, 0)
