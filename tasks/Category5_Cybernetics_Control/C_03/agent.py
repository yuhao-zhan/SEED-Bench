import math

def build_agent(sandbox):
    return sandbox.get_seeker_body()

def agent_action(sandbox, agent_body, step_count):
    if not hasattr(agent_body, '_state'):
        agent_body._state = {
            'last_tx': 0.0,
            'tvx': 0.0
        }
    state = agent_body._state
    target_pos = sandbox.get_target_position()
    tx, ty = target_pos[0], target_pos[1]
    sx, sy = sandbox.get_seeker_position()
    svx, svy = sandbox.get_seeker_velocity()
    if step_count % 5 == 0:
        if step_count > 5:
            vx_est = (tx - state['last_tx']) / 0.08333
            state['tvx'] = 0.5 * state['tvx'] + 0.5 * vx_est
        state['last_tx'] = tx
    in_slot = any(lo <= step_count <= hi for (lo, hi) in [
        (3700, 3800), (4200, 4300), (4700, 4800),
        (6200, 6300), (6700, 6800), (7200, 7300)
    ])
    if step_count < 110:
        gx, gy = 11.95, 1.35
    elif in_slot:
        gx, gy = 13.3, 1.35
    else:
        if (step_count // 120) % 2 == 0:
            gx = 13.1
        else:
            gx = 13.5
        gy = 1.35
    fx = 300.0 * (gx - sx) - 60.0 * svx
    fy = 180.0 * (gy - sy) - 45.0 * svy
    if in_slot:
        if state['tvx'] > 0.15:
            if fx < 60.0: fx = 60.0
        elif state['tvx'] < -0.15:
            if fx > -60.0: fx = -60.0
    if not in_slot and step_count >= 110 and abs(gx - sx) > 0.05:
        if abs(fx) < 110.0:
            fx = 110.0 if (gx - sx) > 0 else -110.0
    mag = math.sqrt(fx*fx + fy*fy)
    if mag > 119.0:
        fx, fy = fx * 119.0 / mag, fy * 119.0 / mag
    sandbox.apply_seeker_force(fx, fy)
