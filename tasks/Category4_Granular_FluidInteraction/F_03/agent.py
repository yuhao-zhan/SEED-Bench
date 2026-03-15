import math

def _build_agent_internal(sandbox, torque=3000.0, arm_config=None, initial_angle=0.0):
    sandbox.add_anchored_base(-2.0, 0.2, 0.4, 0.4, angle=0, density=10.0)
    tower = sandbox.add_anchored_base(-2.0, 0.75, 0.4, 1.5, angle=0, density=400.0)
    if arm_config is None:
        arm_config = [1.5, 1.5, 1.0]
    prev_body = tower
    prev_anchor = (-2.0, 1.5)
    current_x, current_y = -2.0, 1.5
    for i, length in enumerate(arm_config):
        center_x = current_x + (length / 2.0) * math.cos(initial_angle)
        center_y = current_y + (length / 2.0) * math.sin(initial_angle)
        body = sandbox.add_beam(center_x, center_y, length, 0.2, angle=initial_angle, density=20.0)
        if i == 0:
            _aj = sandbox.add_revolute_joint(prev_body, body, prev_anchor, enable_motor=True, max_motor_torque=torque)
            sandbox._aj = _aj
            sandbox.agent_arm_joint = _aj
        else:
            sandbox.add_joint(prev_body, body, (current_x, current_y))
        prev_body = body
        current_x += length * math.cos(initial_angle)
        current_y += length * math.sin(initial_angle)
    scoop_w, scoop_h = 2.0, 1.0
    scoop = sandbox.add_scoop(current_x, current_y, scoop_w, scoop_h, angle=initial_angle, density=20.0)
    _bj = sandbox.add_revolute_joint(prev_body, scoop, (current_x, current_y), enable_motor=True, max_motor_torque=torque)
    sandbox._bj = _bj
    sandbox.agent_bucket_joint = _bj
    return scoop

def build_agent(sandbox):
    return _build_agent_internal(sandbox, torque=3000.0)

def agent_action(sandbox, agent_body, step_count):
    _aj = getattr(sandbox, '_aj', None)
    _bj = getattr(sandbox, '_bj', None)
    if not _aj or not _bj: return
    dt = 1.0 / 60.0
    t = step_count * dt
    phase_duration = 10.0
    phase = (t % phase_duration) / phase_duration
    arm_angle = _aj.angle
    bucket_world_angle = agent_body.angle
    if phase < 0.3:
        ta, tb = -0.2, 0.5
    elif phase < 0.5:
        ta, tb = 0.0, 0.0
    elif phase < 0.8:
        ta, tb = 2.4, 0.0
    elif phase < 0.9:
        ta, tb = 2.4, 1.2
    else:
        ta, tb = 0.5, 1.2
    _aj.motorSpeed = 1.0 * (ta - arm_angle)
    _bj.motorSpeed = 3.0 * (tb - bucket_world_angle)
    _aj.motorEnabled = True
    _bj.motorEnabled = True

def build_agent_stage_1(sandbox):
    return _build_agent_internal(sandbox, torque=3000.0)

def agent_action_stage_1(sandbox, agent_body, step_count):
    _aj = getattr(sandbox, '_aj', None)
    _bj = getattr(sandbox, '_bj', None)
    if not _aj or not _bj: return
    dt = 1.0 / 60.0
    t = step_count * dt
    phase_duration = 8.0
    phase = (t % phase_duration) / phase_duration
    arm_angle = _aj.angle
    bucket_world_angle = agent_body.angle
    if phase < 0.3:
        ta, tb = -0.4, 0.4
    elif phase < 0.45:
        ta, tb = 0.0, -0.2
    elif phase < 0.8:
        ta, tb = 2.4, -0.4
    elif phase < 0.9:
        ta, tb = 2.4, 1.2
    else:
        ta, tb = 0.5, 1.2
    _aj.motorSpeed = 1.5 * (ta - arm_angle)
    _bj.motorSpeed = 4.0 * (tb - bucket_world_angle)
    _aj.motorEnabled = True
    _bj.motorEnabled = True

def build_agent_stage_2(sandbox):
    return _build_agent_internal(sandbox, torque=10000.0)

def agent_action_stage_2(sandbox, agent_body, step_count):
    _aj = getattr(sandbox, '_aj', None)
    _bj = getattr(sandbox, '_bj', None)
    if not _aj or not _bj: return
    dt = 1.0 / 60.0
    t = step_count * dt
    phase_duration = 5.0
    phase = (t % phase_duration) / phase_duration
    arm_angle = _aj.angle
    bucket_world_angle = agent_body.angle
    if phase < 0.3:
        ta, tb = -0.3, 0.4
    elif phase < 0.5:
        ta, tb = 0.0, 0.1
    elif phase < 0.8:
        ta, tb = 2.4, 0.1
    elif phase < 0.9:
        ta, tb = 2.4, 1.2
    else:
        ta, tb = 0.5, 1.2
    _aj.motorSpeed = 4.0 * (ta - arm_angle)
    _bj.motorSpeed = 6.0 * (tb - bucket_world_angle)
    _aj.motorEnabled = True
    _bj.motorEnabled = True

def build_agent_stage_3(sandbox):
    return _build_agent_internal(sandbox, torque=8000.0)

def agent_action_stage_3(sandbox, agent_body, step_count):
    _aj = getattr(sandbox, '_aj', None)
    _bj = getattr(sandbox, '_bj', None)
    if not _aj or not _bj: return
    dt = 1.0 / 60.0
    t = step_count * dt
    phase_duration = 10.0
    phase = (t % phase_duration) / phase_duration
    arm_angle = _aj.angle
    bucket_world_angle = agent_body.angle
    if phase < 0.3:
        ta, tb = -0.2, 0.5
    elif phase < 0.5:
        ta, tb = 0.0, 0.0
    elif phase < 0.8:
        ta, tb = 2.4, 0.0
    elif phase < 0.9:
        ta, tb = 2.4, 1.2
    else:
        ta, tb = 0.5, 1.2
    _aj.motorSpeed = 1.4 * (ta - arm_angle)
    _bj.motorSpeed = 3.5 * (tb - bucket_world_angle)
    _aj.motorEnabled = True
    _bj.motorEnabled = True

def build_agent_stage_4(sandbox):
    return _build_agent_internal(sandbox, torque=18000.0)

def agent_action_stage_4(sandbox, agent_body, step_count):
    _aj = getattr(sandbox, '_aj', None)
    _bj = getattr(sandbox, '_bj', None)
    if not _aj or not _bj: return
    dt = 1.0 / 60.0
    t = step_count * dt
    phase_duration = 6.0
    phase = (t % phase_duration) / phase_duration
    arm_angle = _aj.angle
    bucket_world_angle = agent_body.angle
    if phase < 0.3:
        ta, tb = -0.5, 0.4
    elif phase < 0.45:
        ta, tb = 0.0, -0.2
    elif phase < 0.8:
        ta, tb = 2.4, -0.3
    elif phase < 0.9:
        ta, tb = 2.4, 1.2
    else:
        ta, tb = 0.5, 1.2
    _aj.motorSpeed = 3.5 * (ta - arm_angle)
    _bj.motorSpeed = 5.0 * (tb - bucket_world_angle)
    _aj.motorEnabled = True
    _bj.motorEnabled = True
