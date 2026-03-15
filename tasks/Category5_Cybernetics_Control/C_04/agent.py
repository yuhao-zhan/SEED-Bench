import math

class AgentState:
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AgentState, cls).__new__(cls)
            cls._instance.data = {}
        return cls._instance
    def reset(self): self.data = {}

def build_agent(sandbox):
    return sandbox.get_agent_body()

def agent_action(sandbox, agent_body, step_count):
    if not hasattr(agent_body, '_controller_state'):
        agent_body._controller_state = {
            'phase': 'APPROACH',
            'timer': 0,
            'prev_x': None,
            'prev_y': None,
            'vx': 0.0,
            'vy': 0.0
        }
    state = agent_body._controller_state
    pos = sandbox.get_agent_position()
    x, y = pos[0], pos[1]
    dt = 1.0/60.0
    if state['prev_x'] is not None:
        state['vx'] = (x - state['prev_x']) / dt
        state['vy'] = (y - state['prev_y']) / dt
    state['prev_x'], state['prev_y'] = x, y
    vx, vy = state['vx'], state['vy']
    fx, fy = 0.0, 0.0
    if step_count % 100 == 0:
        print(f"[BASE] {state['phase']} x={x:.2f} y={y:.2f} vx={vx:.2f} vy={vy:.2f}")
    if x < 4.0: target_y = 1.5
    elif x < 6.0: target_y = 1.9
    elif x < 8.5: target_y = 1.5
    elif x < 12.0: target_y = 1.3
    elif x < 15.5: target_y = 0.9
    else: target_y = 1.35
    if state['phase'] == 'APPROACH':
        target_y_act = 2.3
        if x < 6.2: fx = 45.0
        else: fx = 30.0 * (7.0 - x) - 15.0 * vx
        fy = 30.0 * (target_y_act - y) - 8.0 * vy + 50.0
        if 6.2 < x < 7.8 and y > 2.2 and abs(vx) < 0.5:
            state['phase'] = 'UNLOCK'
            state['timer'] = 0
    elif state['phase'] == 'UNLOCK':
        fx = -31.0
        fy = 100.0
        state['timer'] += 1
        if state['timer'] > 60: state['phase'] = 'ESCAPE'
    elif state['phase'] == 'ESCAPE':
        fx = 65.0
        fy = 40.0 * (target_y - y) - 10.0 * vy + 50.0
        if x > 18.5: state['phase'] = 'HOLD'
    elif state['phase'] == 'HOLD':
        fx = 50.0 * (19.0 - x) - 20.0 * vx
        fy = 80.0 * (1.35 - y) - 25.0 * vy + 50.0
    sandbox.apply_agent_force(fx, fy)

def _get_v_persistent(key, pos):
    dt = 1.0/60.0
    data = AgentState().data
    pk = f"{key}_pos"
    prev_pos = data.get(pk)
    if prev_pos is None:
        data[pk] = pos
        return (0.0, 0.0)
    v = ((pos[0] - prev_pos[0])/dt, (pos[1] - prev_pos[1])/dt)
    data[pk] = pos
    return v

def build_agent_stage_1(sandbox):
    AgentState().reset()
    return sandbox.get_agent_body()

def agent_action_stage_1(sandbox, agent_body, step_count):
    data = AgentState().data
    if 's1' not in data: data['s1'] = {'ph': 'APPROACH', 't': 0}
    s = data['s1']
    p = sandbox.get_agent_position()
    v = _get_v_persistent('s1', p)
    x, y, vx, vy = p[0], p[1], v[0], v[1]
    fx, fy = 0.0, 0.0
    if step_count % 100 == 0:
        print(f"[S] {s['ph']} x={x:.2f} y={y:.2f} vx={vx:.2f} vy={vy:.2f}")
    if s['ph'] == 'APPROACH':
        if x < 4.0: ty = 1.5
        elif x < 6.0: ty = 1.9
        else: ty = 0.5
        if x < 6.8: fx = 45.0
        else: fx = 30.0 * (7.0 - x) - 15.0 * vx
        fy = 50.0 * (ty - y) - 15.0 * vy + 75.0
        if 6.2 < x < 7.8 and y < 0.8 and abs(vx) < 0.4:
            s['ph'] = 'UNLOCK'
            s['t'] = 0
    elif s['ph'] == 'UNLOCK':
        fx, fy = -31.0, -100.0
        s['t'] += 1
        if s['t'] > 60: s['ph'] = 'ESCAPE'
    elif s['ph'] == 'ESCAPE':
        if x < 12.0: ty = 1.3
        elif x < 15.5: ty = 0.9
        else: ty = 1.35
        fx = 75.0
        fy = 80.0 * (ty - y) - 20.0 * vy + 75.0
        if x > 18.5: s['ph'] = 'HOLD'
    elif s['ph'] == 'HOLD':
        fx, fy = 60.0 * (19.2 - x) - 25.0 * vx, 150.0 * (1.35 - y) - 40.0 * vy + 75.0
    sandbox.apply_agent_force(fx, fy)

def build_agent_stage_2(sandbox):
    AgentState().reset()
    return sandbox.get_agent_body()

def agent_action_stage_2(sandbox, agent_body, step_count):
    data = AgentState().data
    if 's2' not in data: data['s2'] = {'ph': 'APPROACH', 't': 0}
    s = data['s2']
    p = sandbox.get_agent_position()
    v = _get_v_persistent('s2', p)
    x, y, vx, vy = p[0], p[1], v[0], v[1]
    fx, fy = 0.0, 0.0
    if step_count % 100 == 0:
        print(f"[S] {s['ph']} x={x:.2f} y={y:.2f} vx={vx:.2f} vy={vy:.2f}")
    if s['ph'] == 'APPROACH':
        if x < 4.0: ty = 1.5
        elif x < 6.0: ty = 1.9
        else: ty = 2.45
        if x < 7.0: fx = 45.0
        else: fx = 30.0 * (7.0 - x) - 15.0 * vx
        fy = 50.0 * (ty - y) - 15.0 * vy - 25.0
        if 6.2 < x < 7.8 and y > 2.2 and abs(vx) < 0.4:
            s['ph'] = 'UNLOCK'
            s['t'] = 0
    elif s['ph'] == 'UNLOCK':
        fx, fy = -31.0, 100.0
        s['t'] += 1
        if s['t'] > 60: s['ph'] = 'ESCAPE'
    elif s['ph'] == 'ESCAPE':
        if x < 12.0: ty = 1.3
        elif x < 15.5: ty = 0.9
        else: ty = 1.35
        fx = 80.0
        fy = 120.0 * (ty - y) - 30.0 * vy - 25.0
        if x > 18.5: s['ph'] = 'HOLD'
    elif s['ph'] == 'HOLD':
        fx, fy = 60.0 * (19.2 - x) - 25.0 * vx, 200.0 * (1.35 - y) - 50.0 * vy - 25.0
    sandbox.apply_agent_force(fx, fy)

def build_agent_stage_3(sandbox):
    AgentState().reset()
    return sandbox.get_agent_body()

def agent_action_stage_3(sandbox, agent_body, step_count):
    data = AgentState().data
    if 's3' not in data: data['s3'] = {'ph': 'APPROACH', 't': 0}
    s = data['s3']
    p = sandbox.get_agent_position()
    v = _get_v_persistent('s3', p)
    x, y, vx, vy = p[0], p[1], v[0], v[1]
    fx, fy = 0.0, 0.0
    if step_count % 100 == 0:
        print(f"[S] {s['ph']} x={x:.2f} y={y:.2f} vx={vx:.2f} vy={vy:.2f}")
    if s['ph'] == 'APPROACH':
        if x < 4.0: ty = 1.5
        elif x < 6.0: ty = 1.9
        else: ty = 2.45
        if x < 6.8: fx = 45.0
        else: fx = 30.0 * (7.0 - x) - 15.0 * vx
        fy = 50.0 * (ty - y) - 15.0 * vy + 50.0
        if 6.2 < x < 7.8 and y > 2.2 and abs(vx) < 0.4:
            s['ph'] = 'UNLOCK'
            s['t'] = 0
    elif s['ph'] == 'UNLOCK':
        fx, fy = -31.0, 100.0
        s['t'] += 1
        if s['t'] > 60: s['ph'] = 'ESCAPE'
    elif s['ph'] == 'ESCAPE':
        if x < 12.0: ty = 1.3
        elif x < 15.5: ty = 0.9
        else: ty = 1.35
        fx = 75.0
        fy = 80.0 * (ty - y) - 25.0 * vy + 50.0
        if x > 18.5: s['ph'] = 'HOLD'
    elif s['ph'] == 'HOLD':
        fx, fy = 60.0 * (19.2 - x) - 25.0 * vx, 150.0 * (1.35 - y) - 40.0 * vy + 50.0
    sandbox.apply_agent_force(fx, fy)

def build_agent_stage_4(sandbox):
    AgentState().reset()
    return sandbox.get_agent_body()

def agent_action_stage_4(sandbox, agent_body, step_count):
    data = AgentState().data
    if 's4' not in data: data['s4'] = {'ph': 'APPROACH', 't': 0}
    s = data['s4']
    p = sandbox.get_agent_position()
    v = _get_v_persistent('s4', p)
    x, y, vx, vy = p[0], p[1], v[0], v[1]
    fx, fy = 0.0, 0.0
    if step_count % 100 == 0:
        print(f"[S] {s['ph']} x={x:.2f} y={y:.2f} vx={vx:.2f} vy={vy:.2f}")
    if s['ph'] == 'APPROACH':
        if x < 4.0: ty = 1.5
        elif x < 6.0: ty = 1.9
        else: ty = 2.45
        if x < 7.0: fx = 45.0
        else: fx = 30.0 * (7.0 - x) - 15.0 * vx
        fy = 50.0 * (ty - y) - 15.0 * vy + 50.0
        if 6.2 < x < 7.8 and y > 2.2 and abs(vx) < 0.4:
            s['ph'] = 'UNLOCK'
            s['t'] = 0
    elif s['ph'] == 'UNLOCK':
        fx, fy = -31.0, 100.0
        s['t'] += 1
        if s['t'] > 60: s['ph'] = 'CLIMB'
    elif s['ph'] == 'CLIMB':
        ty, fx = 2.5, 80.0
        fy = 120.0 * (ty - y) - 30.0 * vy + 50.0
        if x > 15.5: s['ph'] = 'DIVE'
    elif s['ph'] == 'DIVE':
        ty, fx = 1.35, 80.0
        fy = 400.0 * (ty - y) - 80.0 * vy + 50.0
        if x > 18.5: s['ph'] = 'HOLD'
    elif s['ph'] == 'HOLD':
        fx, fy = 60.0 * (19.2 - x) - 25.0 * vx, 200.0 * (1.35 - y) - 50.0 * vy + 50.0
    sandbox.apply_agent_force(fx, fy)
