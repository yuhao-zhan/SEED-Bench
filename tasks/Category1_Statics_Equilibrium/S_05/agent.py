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
    d = 0.2
    p1 = sandbox.add_beam(8.0, 2.0, 0.1, 4.0, angle=0, density=d)
    p2 = sandbox.add_beam(12.0, 2.0, 0.1, 4.0, angle=0, density=d)
    sandbox.add_joint(p1, None, (8.0, 0.0), type='rigid')
    sandbox.add_joint(p2, None, (12.0, 0.0), type='rigid')
    roof = sandbox.add_beam(10.0, 4.05, 4.2, 0.1, angle=0, density=d)
    sandbox.add_joint(p1, roof, (8.0, 4.0), type='rigid')
    sandbox.add_joint(p2, roof, (12.0, 4.0), type='rigid')
    return p1

def build_agent_stage_2(sandbox):
    d = 0.5
    p1 = sandbox.add_beam(6.0, 2.0, 0.2, 4.0, angle=0, density=d)
    p2 = sandbox.add_beam(10.0, 2.0, 0.2, 4.0, angle=0, density=d)
    sandbox.add_joint(p1, None, (6.0, 0.0), type='rigid')
    sandbox.add_joint(p2, None, (10.0, 0.0), type='rigid')
    roof = sandbox.add_beam(8.0, 4.1, 4.4, 0.2, angle=0, density=d)
    sandbox.add_joint(p1, roof, (6.0, 4.0), type='rigid')
    sandbox.add_joint(p2, roof, (10.0, 4.0), type='rigid')
    return p1

def build_agent_stage_3(sandbox):
    d = 0.1
    p_l = sandbox.add_beam(7.0, 2.0, 0.2, 4.0, angle=0, density=d)
    p_r = sandbox.add_beam(13.0, 2.0, 0.2, 4.0, angle=0, density=d)
    sandbox.add_joint(p_l, None, (7.0, 0.0), type='rigid')
    sandbox.add_joint(p_r, None, (13.0, 0.0), type='rigid')
    roof = sandbox.add_beam(10.75, 4.1, 7.5, 0.2, angle=0, density=d)
    sandbox.add_joint(p_l, roof, (7.0, 4.0), type='rigid')
    sandbox.add_joint(p_r, roof, (13.0, 4.0), type='rigid')
    shield = sandbox.add_beam(14.5, 2.0, 0.2, 4.0, angle=0, density=d)
    sandbox.add_joint(shield, None, (14.5, 0.0), type='rigid')
    sandbox.add_joint(shield, roof, (14.5, 4.0), type='rigid')
    return p_l

def build_agent_stage_4(sandbox):
    d = 0.1
    p_l = sandbox.add_beam(11.0, 2.0, 0.2, 4.0, angle=0, density=d)
    p_r = sandbox.add_beam(15.0, 2.0, 0.2, 4.0, angle=0, density=d)
    sandbox.add_joint(p_l, None, (11.0, 0.0), type='rigid')
    sandbox.add_joint(p_r, None, (15.0, 0.0), type='rigid')
    roof_out = sandbox.add_beam(13.0, 4.5, 4.4, 0.2, angle=0, density=d)
    sandbox.add_joint(p_l, roof_out, (11.0, 4.5), type='rigid')
    sandbox.add_joint(p_r, roof_out, (15.0, 4.5), type='rigid')
    roof_in = sandbox.add_beam(13.0, 3.8, 3.0, 0.2, angle=0, density=d)
    sandbox.add_joint(p_l, roof_in, (11.5, 3.8), type='rigid')
    sandbox.add_joint(p_r, roof_in, (14.5, 3.8), type='rigid')
    shield = sandbox.add_beam(10.0, 2.0, 0.2, 4.0, angle=0, density=d)
    sandbox.add_joint(shield, None, (10.0, 0.0), type='rigid')
    sandbox.add_joint(shield, roof_out, (10.0, 4.5), type='rigid')
    return p_l

def agent_action_stage_1(sandbox, agent_body, step_count):
    pass

def agent_action_stage_2(sandbox, agent_body, step_count):
    pass

def agent_action_stage_3(sandbox, agent_body, step_count):
    pass

def agent_action_stage_4(sandbox, agent_body, step_count):
    pass
