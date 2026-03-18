import math

def build_agent(sandbox):
    col_l = sandbox.add_beam(8.0, 2.0, 0.4, 4.0, angle=0, density=10.0)
    col_r = sandbox.add_beam(12.0, 2.0, 0.4, 4.0, angle=0, density=10.0)
    sandbox.add_joint(col_l, None, (8.0, 0.0), type='rigid')
    sandbox.add_joint(col_r, None, (12.0, 0.0), type='rigid')
    roof = sandbox.add_beam(10.0, 4.2, 6.0, 0.4, angle=0, density=10.0)
    sandbox.add_joint(col_l, roof, (8.0, 4.0), type='rigid')
    sandbox.add_joint(col_r, roof, (12.0, 4.0), type='rigid')
    return col_l

def agent_action(sandbox, agent_body, step_count):
    pass

def build_agent_stage_1(sandbox):
    d = 0.06
    p1 = sandbox.add_beam(8.0, 2.0, 0.2, 3.5, angle=0, density=d)
    p2 = sandbox.add_beam(12.0, 2.0, 0.2, 3.5, angle=0, density=d)
    sandbox.add_joint(p1, None, (8.0, 0.0), type='rigid')
    sandbox.add_joint(p2, None, (12.0, 0.0), type='rigid')
    r1 = sandbox.add_beam(8.5, 3.9, 1.0, 0.15, angle=0, density=d)
    r2 = sandbox.add_beam(9.5, 3.9, 1.0, 0.15, angle=0, density=d)
    r3 = sandbox.add_beam(10.5, 3.9, 1.0, 0.15, angle=0, density=d)
    r4 = sandbox.add_beam(11.5, 3.9, 1.0, 0.15, angle=0, density=d)
    sandbox.add_joint(p1, r1, (8.0, 3.5), type='rigid')
    sandbox.add_joint(r1, r2, (9.0, 3.5), type='rigid')
    sandbox.add_joint(r2, r3, (10.0, 3.5), type='rigid')
    sandbox.add_joint(r3, r4, (11.0, 3.5), type='rigid')
    sandbox.add_joint(p2, r4, (12.0, 3.5), type='rigid')
    return p1

def build_agent_stage_2(sandbox):
    d = 10.0
    p1 = sandbox.add_beam(6.5, 2.0, 0.4, 4.0, angle=0, density=d)
    p2 = sandbox.add_beam(8.5, 2.0, 0.4, 4.0, angle=0, density=d)
    sandbox.add_joint(p1, None, (6.5, 0.0), type='rigid')
    sandbox.add_joint(p2, None, (8.5, 0.0), type='rigid')
    roof = sandbox.add_beam(7.5, 4.2, 5.5, 0.4, angle=0, density=d)
    sandbox.add_joint(p1, roof, (6.5, 4.0), type='rigid')
    sandbox.add_joint(p2, roof, (8.5, 4.0), type='rigid')
    return p1

def build_agent_stage_3(sandbox):
    d = 0.05
    p_l = sandbox.add_beam(7.5, 2.0, 0.15, 3.5, angle=0, density=d)
    p_r = sandbox.add_beam(12.5, 2.0, 0.15, 3.5, angle=0, density=d)
    sandbox.add_joint(p_l, None, (7.5, 0.0), type='rigid')
    sandbox.add_joint(p_r, None, (12.5, 0.0), type='rigid')
    xs = [7.5 + i * (5.0 / 8) for i in range(9)]
    beams = [sandbox.add_beam((xs[i]+xs[i+1])/2, 3.52, xs[i+1]-xs[i], 0.12, angle=0, density=d) for i in range(8)]
    sandbox.add_joint(p_l, beams[0], (7.5, 3.5), type='rigid')
    for i in range(7):
        sandbox.add_joint(beams[i], beams[i + 1], (xs[i + 1], 3.5), type='rigid')
    sandbox.add_joint(p_r, beams[7], (12.5, 3.5), type='rigid')
    return p_l

def build_agent_stage_4(sandbox):
    d = 0.06
    p_l = sandbox.add_beam(11.0, 2.0, 0.18, 4.0, angle=0, density=d)
    p_r = sandbox.add_beam(15.0, 2.0, 0.18, 4.0, angle=0, density=d)
    sandbox.add_joint(p_l, None, (11.0, 0.0), type='rigid')
    sandbox.add_joint(p_r, None, (15.0, 0.0), type='rigid')
    xs = [11.0 + i * (4.0 / 8) for i in range(9)]
    beams = [sandbox.add_beam((xs[i]+xs[i+1])/2, 4.1, xs[i+1]-xs[i], 0.18, angle=0, density=d) for i in range(8)]
    sandbox.add_joint(p_l, beams[0], (11.0, 4.0), type='rigid')
    for i in range(7):
        sandbox.add_joint(beams[i], beams[i+1], (xs[i+1], 4.0), type='rigid')
    sandbox.add_joint(p_r, beams[7], (15.0, 4.0), type='rigid')
    return p_l

def agent_action_stage_1(sandbox, agent_body, step_count):
    pass

def agent_action_stage_2(sandbox, agent_body, step_count):
    pass

def agent_action_stage_3(sandbox, agent_body, step_count):
    pass

def agent_action_stage_4(sandbox, agent_body, step_count):
    pass
