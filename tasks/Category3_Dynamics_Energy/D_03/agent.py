import math

def build_agent(sandbox):
    cabin = sandbox.get_vehicle_cabin()
    if cabin is None:
        raise ValueError("Cart not found")
    beams = []
    for (xx, yy) in [(4.8, 2.6), (4.9, 2.6), (5.0, 2.6), (5.1, 2.6)]:
        b = sandbox.add_beam(xx, yy, 0.08, 0.16, angle=0, density=5.0)
        sandbox.add_joint(cabin, b, (xx, yy), type="rigid")
        beams.append(b)
    return cabin

def agent_action(sandbox, agent_body, step_count):
    pass

def build_agent_stage_1(sandbox):
    cabin = sandbox.get_vehicle_cabin()
    beams = []
    for (xx, yy) in [(4.8, 2.6), (4.9, 2.6), (5.0, 2.6), (5.1, 2.6)]:
        b = sandbox.add_beam(xx, yy, 0.08, 0.16, angle=0, density=14.2)
        sandbox.add_joint(cabin, b, (xx, yy), type="rigid")
        beams.append(b)
    return cabin

def agent_action_stage_1(sandbox, agent_body, step_count):
    pass

def build_agent_stage_2(sandbox):
    cabin = sandbox.get_vehicle_cabin()
    beams = []
    for i in range(5):
        xx, yy = 4.8 + i*0.1, 2.5
        b = sandbox.add_beam(xx, yy, 1.2, 1.2, angle=0, density=0.1)
        sandbox.add_joint(cabin, b, (xx, yy), type="rigid")
        beams.append(b)
    return cabin

def agent_action_stage_2(sandbox, agent_body, step_count):
    if agent_body:
        pos = sandbox.get_vehicle_position()
        vel = sandbox.get_vehicle_velocity()
        if pos is None or vel is None:
            return
        x, v = pos[0], vel[0]
        t = step_count * 0.01
        if x < 9.0:
            target_v = 10.0
        elif x < 11.3:
            target_v = 2.5
        elif x < 11.45:
            if t < 3.8:
                target_v = 0.0
            else:
                target_v = 2.0
        else:
            target_v = 1.0
        force_mag = (target_v - v) * 400.0
        sandbox.apply_force(agent_body, (force_mag, 0.0))

def build_agent_stage_3(sandbox):
    cabin = sandbox.get_vehicle_cabin()
    beams = []
    for (xx, yy) in [(4.8, 2.6), (4.9, 2.6), (5.0, 2.6), (5.1, 2.6)]:
        b = sandbox.add_beam(xx, yy, 0.08, 0.16, angle=0, density=15.0)
        sandbox.add_joint(cabin, b, (xx, yy), type="rigid")
        beams.append(b)
    return cabin

def agent_action_stage_3(sandbox, agent_body, step_count):
    pass

def build_agent_stage_4(sandbox):
    cabin = sandbox.get_vehicle_cabin()
    beams = []
    for (xx, yy) in [(4.8, 2.6), (4.9, 2.6), (5.0, 2.6), (5.1, 2.6), (5.2, 2.6)]:
        b = sandbox.add_beam(xx, yy, 0.08, 0.16, angle=0, density=1.0)
        sandbox.add_joint(cabin, b, (xx, yy), type="rigid")
        beams.append(b)
    return cabin

def agent_action_stage_4(sandbox, agent_body, step_count):
    if agent_body:
        pos = sandbox.get_vehicle_position()
        vel = sandbox.get_vehicle_velocity()
        if pos is None or vel is None:
            return
        x, v = pos[0], vel[0]
        if x < 9.0:
            target_v = 10.0
        elif x < 11.0:
            target_v = 2.0
        else:
            target_v = 1.5
        force_mag = (target_v - v) * 500.0
        sandbox.apply_force(agent_body, (force_mag, 0.0))
