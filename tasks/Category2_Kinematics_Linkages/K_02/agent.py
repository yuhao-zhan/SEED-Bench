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
    dummy = sandbox.add_beam(start_x, 22.0, 0.1, 0.1, density=0.1)
    j = sandbox.add_joint(top, dummy, (start_x, 22.0), type='pivot')
    sandbox._climber_joints = {'tower_top': j}
    return top

def agent_action(sandbox, agent_body, step_count):
    joints = getattr(sandbox, '_climber_joints', {})
    if 'tower_top' in joints:
        sandbox.set_motor(joints['tower_top'], 0.5 * math.sin(step_count * 0.05), 1.0)

def build_agent_stage_1(sandbox):
    torso = sandbox.add_beam(4.5, 21.5, 0.2, 0.2, density=10.0)
    pads = []
    for i in range(50):
        py = 21.5 + (i / 49.0 - 0.5) * 2.5
        pad = sandbox.add_pad(4.8, py, radius=0.05, density=0.1)
        sandbox.add_joint(torso, pad, (4.8, py), type='rigid')
        pads.append(pad)
    sandbox._climber_pads = pads
    return torso

def agent_action_stage_1(sandbox, agent_body, step_count):
    pads = getattr(sandbox, '_climber_pads', [])
    for pad in pads:
        sandbox.set_pad_active(pad, True)

def build_agent_stage_2(sandbox):
    torso = sandbox.add_beam(4.5, 21.5, 0.4, 0.4, density=250.0)
    roof = sandbox.add_beam(4.0, 23.5, 2.0, 0.1, angle=math.pi/2.5, density=25.0)
    sandbox.add_joint(torso, roof, (4.5, 22.0), type='rigid')
    pads = []
    for i in range(400):
        py = 21.5 + (i / 399.0 - 0.5) * 2.0
        pad = sandbox.add_pad(4.9, py, radius=0.05, density=0.01)
        sandbox.add_joint(torso, pad, (4.9, py), type='rigid')
        pads.append(pad)
    sandbox._climber_pads = pads
    return torso

def agent_action_stage_2(sandbox, agent_body, step_count):
    pads = getattr(sandbox, '_climber_pads', [])
    for pad in pads:
        sandbox.set_pad_active(pad, True)

def build_agent_stage_3(sandbox):
    torso = sandbox.add_beam(4.5, 21.5, 0.4, 0.4, density=250.0)
    pads = []
    for i in range(100):
        py = 21.5 + (i - 49.5) * 0.04
        pad = sandbox.add_pad(4.9, py, radius=0.05, density=0.1)
        sandbox.add_joint(torso, pad, (4.9, py), type='rigid')
        pads.append(pad)
    sandbox._climber_pads = pads
    return torso

def agent_action_stage_3(sandbox, agent_body, step_count):
    pads = getattr(sandbox, '_climber_pads', [])
    for pad in pads:
        sandbox.set_pad_active(pad, True)

def build_agent_stage_4(sandbox):
    torso = sandbox.add_beam(4.8, 21.5, 0.4, 0.4, density=250.0)
    pads = []
    for i in range(150):
        py = 21.5 + (i - 74.5) * 0.03
        pad = sandbox.add_pad(4.95, py, radius=0.05, density=0.1)
        sandbox.add_joint(torso, pad, (4.95, py), type='rigid')
        pads.append(pad)
    sandbox._climber_pads = pads
    return torso

def agent_action_stage_4(sandbox, agent_body, step_count):
    pads = getattr(sandbox, '_climber_pads', [])
    for pad in pads:
        sandbox.set_pad_active(pad, True)
