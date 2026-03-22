import math

from tasks.Category5_Cybernetics_Control.C_04.environment import (
    ACTIVATION_X_MAX,
    ACTIVATION_X_MIN,
    BACKWARD_FX_THRESHOLD,
    EXIT_X_MIN,
    ONEWAY_FORCE_RIGHT,
    ONEWAY_X,
    TIME_STEP,

)

class Memory:
    def __init__(self): self.data = {}
    def clear(self): self.data = {}

MEM = Memory()

def _weight_comp(sandbox):
    try:
        gy = float(sandbox.world.gravity[1])
    except (AttributeError, TypeError, IndexError):
        gy = -9.8
    return 5.0 * abs(gy)

def build_agent(sandbox):
    return sandbox.get_agent_body()

def agent_action(sandbox, agent_body, step_count):
    if not hasattr(agent_body, '_controller_state'):
        agent_body._controller_state = {'phase': 'APPROACH', 't': 0, 'lx': None, 'ly': None, 'vx': 0.0, 'vy': 0.0}
    state = agent_body._controller_state
    pd = sandbox.get_agent_position()
    dt = TIME_STEP
    if state['lx'] is not None:
        state['vx'] = (pd[0] - state['lx']) / dt
        state['vy'] = (pd[1] - state['ly']) / dt
    state['lx'], state['ly'] = pd[0], pd[1]
    vxd, vyd = state['vx'], state['vy']
    x, y = pd[0], pd[1]
    ty, w_comp = 1.4, _weight_comp(sandbox)
    if state['phase'] == 'APPROACH':
        fx = (15.0 if x < 5.0 else 10.0 * (7.0 - x) - 5.0 * vxd)
        fy = 50.0 * (ty - y) - 20.0 * vyd + w_comp
        if ACTIVATION_X_MIN <= x <= ACTIVATION_X_MAX and abs(vxd) < 0.5:
            state['phase'] = 'UNLOCK'
            state['t'] = 0
    elif state['phase'] == 'UNLOCK':
        fx, fy = BACKWARD_FX_THRESHOLD - 1.0, 50.0 * (ty - y) - 20.0 * vyd + w_comp
        state['t'] += 1
        if state['t'] > 60: state['phase'] = 'ESCAPE'
    elif state['phase'] == 'ESCAPE':
        fx, fy = 15.0, 50.0 * (ty - y) - 20.0 * vyd + w_comp
        if x > EXIT_X_MIN + 2.5: state['phase'] = 'HOLD'
    elif state['phase'] == 'HOLD':
        fx, fy = 0.0, w_comp
    sandbox.apply_agent_force(fx, fy)

def build_agent_stage_1(sandbox):
    MEM.clear()
    return sandbox.get_agent_body()

def agent_action_stage_1(sandbox, agent_body, step_count):
    p, v = sandbox.get_agent_position(), sandbox.get_agent_velocity()
    w_comp = _weight_comp(sandbox)
    ty = 1.4
    if 'phase1' not in MEM.data:
        MEM.data['phase1'] = 'APPROACH'
        MEM.data['t1'] = step_count
    phase = MEM.data['phase1']
    def creep_fx(f, lo=-0.8, hi=1.35): return max(lo, min(hi, f))
    def clamp_y_force(fy): return max(28, min(62, fy))
    speed = (v[0]**2 + v[1]**2)**0.5
    if phase != 'UNLOCK' and speed > 0.004:
        brake_fx = creep_fx(-2.5 * v[0] - 0.3 * (1.0 if v[0] > 0 else -1.0))
        if phase == 'ESCAPE' and p[0] > ONEWAY_X:
            fx = -ONEWAY_FORCE_RIGHT + brake_fx
        else:
            fx = brake_fx
        fy = clamp_y_force(w_comp - 2.5 * v[1] - 0.3 * (1.0 if v[1] > 0 else -1.0))
        sandbox.apply_agent_force(fx, fy)
        return
    if phase == 'APPROACH':
        fx = creep_fx(1.0 * (6.5 - p[0]) - 4.0 * v[0])
        fy = clamp_y_force(32.0 * (ty - p[1]) - 18.0 * v[1] + w_comp)
        if ACTIVATION_X_MIN <= p[0] <= ACTIVATION_X_MAX and abs(v[0]) < 0.06 and 1.1 <= p[1] <= 1.7:
            MEM.data['phase1'] = 'UNLOCK'
            MEM.data['t1'] = step_count
    elif phase == 'UNLOCK':
        steps_in_unlock = step_count - MEM.data['t1']
        fx = (BACKWARD_FX_THRESHOLD - 1.0) if steps_in_unlock < 35 else 0.0
        fy = clamp_y_force(32.0 * (ty - p[1]) - 18.0 * v[1] + w_comp)
        if steps_in_unlock >= 120:
            MEM.data['phase1'] = 'ESCAPE'
    elif phase == 'ESCAPE':
        raw_fx = 0.4 * (17.0 - p[0]) - 2.0 * v[0]
        if p[0] > ONEWAY_X:
            if speed > 0.005:
                fx = -ONEWAY_FORCE_RIGHT + creep_fx(-2.5 * v[0] - 0.5)
            else:
                creep = max(-0.8, min(0.06, raw_fx))
                fx = -ONEWAY_FORCE_RIGHT + creep
        elif p[0] > 5.0:
            if p[0] > 9.0 and speed > 0.01:
                fx = max(-3.0, -2.5 * v[0] - 1.0)
            elif speed > 0.005:
                fx = creep_fx(-2.5 * v[0] - 0.4)
            else:
                cap = 0.02 if p[0] <= ONEWAY_X else 0.06
                fx = max(-0.8, min(cap, raw_fx))
        elif p[0] > 3.0:
            if speed > 0.01:
                fx = creep_fx(-2.5 * v[0] - 0.5)
            else:
                cap = 0.5 - (0.5 - 0.06) * (p[0] - 3.0)
                fx = creep_fx(raw_fx, lo=-0.8, hi=cap)
        else:
            fx = creep_fx(1.3 * (17.0 - p[0]) - 4.0 * v[0])
        fy = clamp_y_force(32.0 * (ty - p[1]) - 18.0 * v[1] + w_comp)
        if p[0] > 17.0:
            MEM.data['phase1'] = 'HOLD'
    else:
        fx = -ONEWAY_FORCE_RIGHT if p[0] > ONEWAY_X else 0.0
        fy = w_comp
    sandbox.apply_agent_force(fx, fy)

def build_agent_stage_2(sandbox):
    MEM.clear()
    return sandbox.get_agent_body()

def agent_action_stage_2(sandbox, agent_body, step_count):
    px, py = sandbox.get_agent_position()
    vx, vy = sandbox.get_agent_velocity()
    fy = 60.0 * (2.2 - py) - 30.0 * vy + _weight_comp(sandbox)
    if px < 5.0: fx = 20.0
    elif px < 10.0:
        if 'u2' not in MEM.data:
            fx = -60.0
            if 's2' not in MEM.data: MEM.data['s2'] = 0
            MEM.data['s2'] += 1
            if MEM.data['s2'] > 80: MEM.data['u2'] = True
        else: fx = 40.0
    else: fx = 40.0 if px < 18.0 else -10.0 * vx
    sandbox.apply_agent_force(fx, fy)

def build_agent_stage_3(sandbox):
    MEM.clear()
    return sandbox.get_agent_body()

def agent_action_stage_3(sandbox, agent_body, step_count):
    p, v = sandbox.get_agent_position(), sandbox.get_agent_velocity()
    w_comp = _weight_comp(sandbox)
    speed = (v[0]**2 + v[1]**2)**0.5
    if speed > 16.0:
        fx = -3.0 * v[0] - 80.0 * (1.0 if v[0] > 0 else -1.0)
        fy = w_comp - 3.0 * v[1] - 80.0 * (1.0 if v[1] > 0 else -1.0)
        mag = (fx**2 + fy**2)**0.5
        if mag > 400.0:
            fx, fy = fx * 400.0 / mag, fy * 400.0 / mag
        sandbox.apply_agent_force(fx, fy)
        return
    if p[0] < 5.5:
        ty = 2.0
    elif p[0] < 10.0:
        ty = 0.75
    else:
        ty = 1.2
    if p[0] < 5.0:
        fx = 350.0
    elif p[0] < 10.0:
        if 'u3' not in MEM.data:
            fx = -200.0
            if 's3' not in MEM.data: MEM.data['s3'] = 0
            MEM.data['s3'] += 1
            if MEM.data['s3'] > 120: MEM.data['u3'] = True
        else:
            fx = min(900.0, 400.0 + 200.0 * (1.0 - speed / 18.0))
    else:
        fx = min(900.0, 400.0 + 200.0 * (1.0 - speed / 18.0))
    fy = 500.0 * (ty - p[1]) - 120.0 * v[1] + w_comp
    mag = (fx**2 + fy**2)**0.5
    if mag > 550.0:
        fx, fy = fx * 550.0 / mag, fy * 550.0 / mag
    sandbox.apply_agent_force(fx, fy)

def build_agent_stage_4(sandbox):
    MEM.clear()
    return sandbox.get_agent_body()

def agent_action_stage_4(sandbox, agent_body, step_count):
    p, v = sandbox.get_agent_position(), sandbox.get_agent_velocity()
    w_comp = _weight_comp(sandbox)
    ty = 1.4
    mag_comp = 80.0 if p[1] < 1.5 else 0.0
    fy = 500.0 * (ty - p[1]) - 120.0 * v[1] + w_comp + mag_comp
    if 'u4' not in MEM.data:
        MEM.data['u4'] = False
        MEM.data['steps4'] = 0
    if not MEM.data['u4']:
        fx_cmd = -60.0
        speed = (v[0]**2 + v[1]**2)**0.5
        if ACTIVATION_X_MIN <= p[0] <= ACTIVATION_X_MAX and fx_cmd < BACKWARD_FX_THRESHOLD and speed < 100.0:
            MEM.data['steps4'] += 1
        else:
            MEM.data['steps4'] = 0
        if MEM.data['steps4'] >= 5:
            MEM.data['u4'] = True
        if p[0] > 11.0:
            fx_cmd = 60.0
    else:
        if p[0] < 17.5:
            fx_cmd = -100.0
        else:
            fx_cmd = 40.0 * v[0]
    mag = (fx_cmd**2 + fy**2)**0.5
    limit = 950.0
    if mag > limit:
        fx_cmd, fy = fx_cmd * limit / mag, fy * limit / mag
    sandbox.apply_agent_force(fx_cmd, fy)
