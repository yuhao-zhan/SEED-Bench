import math

def build_agent(sandbox):
    start_x = 4.5
    top = sandbox.add_beam(start_x, 21.5, 0.4, 1.0, density=5.0)
    prev_b = top
    for i in range(6, -1, -1):
        y = 1.5 + i * 3.0
        b = sandbox.add_beam(start_x, y, 0.4, 3.0, density=5.0)
        joint_y = y + 1.5
        sandbox.add_joint(prev_b, b, (start_x, joint_y), type='rigid')
        prev_b = b
    return top

def agent_action(sandbox, agent_body, step_count):
    pass

def _apply_climb_action(sandbox, step_count):
    c = getattr(sandbox, '_climber_joints', {})
    if not c: return
    cycle = c['cycle']
    phase = step_count % (2 * cycle)
    overlap = c.get('overlap', 10)
    speed = c.get('speed', 10.0)
    torque = c.get('torque', 1000.0)
    if phase < cycle:
        for p in c['p_torso']: sandbox.set_pad_active(p, True)
        if phase > overlap:
            for p in c['p_arm']: sandbox.set_pad_active(p, False)
        else:
            for p in c['p_arm']: sandbox.set_pad_active(p, True)
        sandbox.set_motor(c['joint'], speed, torque)
    else:
        for p in c['p_arm']: sandbox.set_pad_active(p, True)
        if (phase - cycle) > overlap:
            for p in c['p_torso']: sandbox.set_pad_active(p, False)
        else:
            for p in c['p_torso']: sandbox.set_pad_active(p, True)
        sandbox.set_motor(c['joint'], -speed, torque)

def build_agent_stage_1(sandbox):
    x_pos = 4.85
    base_y = 2.0
    torso = sandbox.add_beam(x_pos, base_y, 0.05, 0.8, density=1.0)
    p1 = sandbox.add_pad(x_pos + 0.1, base_y - 0.2, radius=0.1, density=0.5)
    p2 = sandbox.add_pad(x_pos + 0.1, base_y + 0.2, radius=0.1, density=0.5)
    sandbox.add_joint(torso, p1, (x_pos + 0.1, base_y - 0.2), type='rigid')
    sandbox.add_joint(torso, p2, (x_pos + 0.1, base_y + 0.2), type='rigid')
    arm = sandbox.add_beam(x_pos, base_y + 1.0, 0.04, 1.2, density=0.5)
    p3 = sandbox.add_pad(x_pos + 0.1, base_y + 1.4, radius=0.1, density=0.5)
    p4 = sandbox.add_pad(x_pos + 0.1, base_y + 1.6, radius=0.1, density=0.5)
    sandbox.add_joint(arm, p3, (x_pos + 0.1, base_y + 1.4), type='rigid')
    sandbox.add_joint(arm, p4, (x_pos + 0.1, base_y + 1.6), type='rigid')
    joint = sandbox.add_joint(torso, arm, (x_pos, base_y + 0.4), type='pivot', lower_limit=-0.1, upper_limit=2.0)
    sandbox._climber_joints = {
        'p_torso': [p1, p2],
        'p_arm': [p3, p4],
        'joint': joint,
        'cycle': 60
    }
    return torso

def agent_action_stage_1(sandbox, agent_body, step_count):
    _apply_climb_action(sandbox, step_count)

def build_agent_stage_2(sandbox):
    x_pos = 4.85
    base_y = 1.5
    torso = sandbox.add_beam(x_pos, base_y, 0.05, 0.6, density=1.0)
    p1 = sandbox.add_pad(x_pos + 0.1, base_y - 0.2, radius=0.1, density=0.5)
    p2 = sandbox.add_pad(x_pos + 0.1, base_y + 0.2, radius=0.1, density=0.5)
    sandbox.add_joint(torso, p1, (x_pos + 0.1, base_y - 0.2), type='rigid')
    sandbox.add_joint(torso, p2, (x_pos + 0.1, base_y + 0.2), type='rigid')
    arm = sandbox.add_beam(x_pos, base_y + 2.8, 0.06, 5.0, density=1.0)
    p3 = sandbox.add_pad(x_pos + 0.1, base_y + 5.0, radius=0.1, density=0.5)
    p4 = sandbox.add_pad(x_pos + 0.1, base_y + 5.2, radius=0.1, density=0.5)
    sandbox.add_joint(arm, p3, (x_pos + 0.1, base_y + 5.0), type='rigid')
    sandbox.add_joint(arm, p4, (x_pos + 0.1, base_y + 5.2), type='rigid')
    joint = sandbox.add_joint(torso, arm, (x_pos, base_y + 0.4), type='pivot', lower_limit=-0.1, upper_limit=2.8)
    sandbox._climber_joints = {
        'p_torso': [p1, p2],
        'p_arm': [p3, p4],
        'joint': joint,
        'cycle': 80,
        'speed': 8.0,
        'torque': 5000.0,
        'overlap': 10
    }
    return torso

def agent_action_stage_2(sandbox, agent_body, step_count):
    _apply_climb_action(sandbox, step_count)

def build_agent_stage_3(sandbox):
    x_pos = 4.8
    base_y = 2.0
    torso = sandbox.add_beam(x_pos, base_y, 0.2, 1.2, density=60.0)
    p1 = sandbox.add_pad(x_pos + 0.15, base_y - 0.4, radius=0.15, density=20.0)
    p2 = sandbox.add_pad(x_pos + 0.15, base_y + 0.4, radius=0.15, density=20.0)
    sandbox.add_joint(torso, p1, (x_pos + 0.15, base_y - 0.4), type='rigid')
    sandbox.add_joint(torso, p2, (x_pos + 0.15, base_y + 0.4), type='rigid')
    arm = sandbox.add_beam(x_pos, base_y + 1.5, 0.2, 1.8, density=60.0)
    p3 = sandbox.add_pad(x_pos + 0.15, base_y + 2.2, radius=0.15, density=20.0)
    p4 = sandbox.add_pad(x_pos + 0.15, base_y + 2.6, radius=0.15, density=20.0)
    sandbox.add_joint(arm, p3, (x_pos + 0.15, base_y + 2.2), type='rigid')
    sandbox.add_joint(arm, p4, (x_pos + 0.15, base_y + 2.6), type='rigid')
    joint = sandbox.add_joint(torso, arm, (x_pos, base_y + 0.6), type='pivot', lower_limit=-0.1, upper_limit=2.0)
    sandbox._climber_joints = {
        'p_torso': [p1, p2],
        'p_arm': [p3, p4],
        'joint': joint,
        'cycle': 100,
        'speed': 8.0,
        'torque': 20000.0
    }
    return torso

def agent_action_stage_3(sandbox, agent_body, step_count):
    _apply_climb_action(sandbox, step_count)

def build_agent_stage_4(sandbox):
    x_pos = 4.9
    base_y = 0.5
    torso = sandbox.add_beam(x_pos, base_y, 0.05, 0.4, density=1.0)
    p1 = sandbox.add_pad(x_pos + 0.05, base_y, radius=0.05, density=0.5)
    sandbox.add_joint(torso, p1, (x_pos + 0.05, base_y), type='rigid')
    arm = sandbox.add_beam(x_pos, base_y + 0.5, 0.04, 0.6, density=0.5)
    p2 = sandbox.add_pad(x_pos + 0.05, base_y + 0.8, radius=0.05, density=0.5)
    sandbox.add_joint(arm, p2, (x_pos + 0.05, base_y + 0.8), type='rigid')
    joint = sandbox.add_joint(torso, arm, (x_pos, base_y + 0.2), type='pivot', lower_limit=-0.1, upper_limit=2.0)
    sandbox._climber_joints = {
        'p_torso': [p1],
        'p_arm': [p2],
        'joint': joint,
        'cycle': 30,
        'speed': 25.0,
        'torque': 5000.0,
        'overlap': 4
    }
    return torso

def agent_action_stage_4(sandbox, agent_body, step_count):
    _apply_climb_action(sandbox, step_count)
