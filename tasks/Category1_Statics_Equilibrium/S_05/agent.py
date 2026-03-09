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
    p_density = 0.01
    xs = [7.5, 12.5]
    pillars = []
    for x in xs:
        p = sandbox.add_beam(x, 2.0, 0.1, 4.0, angle=0, density=p_density)
        sandbox.add_joint(p, None, (x, 0.0), type='rigid')
        pillars.append(p)
    roof_l = sandbox.add_beam(8.5, 4.8, 3.5, 0.1, angle=-math.pi/6, density=p_density)
    roof_r = sandbox.add_beam(11.5, 4.8, 3.5, 0.1, angle=math.pi/6, density=p_density)
    sandbox.add_joint(pillars[0], roof_l, (7.5, 4.0), type='rigid')
    sandbox.add_joint(pillars[1], roof_r, (12.5, 4.0), type='rigid')
    sandbox.add_joint(roof_l, roof_r, (10.0, 5.5), type='rigid')
    return pillars[0]

def build_agent_stage_2(sandbox):
    col_l = sandbox.add_beam(7.0, 2.0, 0.3, 4.0, angle=0, density=10.0)
    col_r = sandbox.add_beam(13.0, 2.0, 0.3, 4.0, angle=0, density=10.0)
    sandbox.add_joint(col_l, None, (7.0, 0.0), type='rigid')
    sandbox.add_joint(col_r, None, (13.0, 0.0), type='rigid')
    roof_l = sandbox.add_beam(8.5, 5.0, 5.0, 0.3, angle=-math.pi/6, density=10.0)
    roof_r = sandbox.add_beam(11.5, 5.0, 5.0, 0.3, angle=math.pi/6, density=10.0)
    sandbox.add_joint(col_l, roof_l, (7.0, 4.0), type='rigid')
    sandbox.add_joint(col_r, roof_r, (13.0, 4.0), type='rigid')
    sandbox.add_joint(roof_l, roof_r, (10.0, 5.8), type='rigid')
    side_l = sandbox.add_beam(8.5, 1.2, 0.1, 2.4, angle=0, density=5.0)
    side_r = sandbox.add_beam(11.5, 1.2, 0.1, 2.4, angle=0, density=5.0)
    sandbox.add_joint(side_l, None, (8.5, 0.0), type='rigid')
    sandbox.add_joint(side_r, None, (11.5, 0.0), type='rigid')
    return col_l

def agent_action_stage_2(sandbox, agent_body, step_count):
    pass

def build_agent_stage_3(sandbox):
    density = 0.01
    xs = [7.5, 12.5]
    pillars = []
    for x in xs:
        p = sandbox.add_beam(x, 2.0, 0.1, 4.0, angle=0, density=density)
        sandbox.add_joint(p, None, (x, 0.0), type='rigid')
        pillars.append(p)
    roof_l = sandbox.add_beam(8.5, 4.8, 3.0, 0.1, angle=-math.pi/6, density=density)
    roof_r = sandbox.add_beam(11.5, 4.8, 3.0, 0.1, angle=math.pi/6, density=density)
    sandbox.add_joint(pillars[0], roof_l, (7.5, 4.0), type='rigid')
    sandbox.add_joint(pillars[1], roof_r, (12.5, 4.0), type='rigid')
    sandbox.add_joint(roof_l, roof_r, (10.0, 5.5), type='rigid')
    return pillars[0]

def agent_action_stage_3(sandbox, agent_body, step_count):
    pass

def build_agent_stage_4(sandbox):
    density = 0.01
    col_l = sandbox.add_beam(7.5, 2.0, 0.1, 4.0, angle=-0.2, density=density)
    col_r = sandbox.add_beam(12.5, 2.0, 0.1, 4.0, angle=0.2, density=density)
    sandbox.add_joint(col_l, None, (7.5, 0.0), type='rigid')
    sandbox.add_joint(col_r, None, (12.5, 0.0), type='rigid')
    roof_l = sandbox.add_beam(8.5, 4.5, 3.0, 0.1, angle=-math.pi/4, density=density)
    roof_r = sandbox.add_beam(11.5, 4.5, 3.0, 0.1, angle=math.pi/4, density=density)
    sandbox.add_joint(col_l, roof_l, (7.5, 4.0), type='rigid')
    sandbox.add_joint(col_r, roof_r, (12.5, 4.0), type='rigid')
    sandbox.add_joint(roof_l, roof_r, (10.0, 5.5), type='rigid')
    wall_l = sandbox.add_beam(8.6, 1.0, 0.1, 2.0, angle=0, density=density)
    wall_r = sandbox.add_beam(11.4, 1.0, 0.1, 2.0, angle=0, density=density)
    sandbox.add_joint(wall_l, None, (8.6, 0.0), type='rigid')
    sandbox.add_joint(wall_r, None, (11.4, 0.0), type='rigid')
    return col_l

def agent_action_stage_4(sandbox, agent_body, step_count):
    pass

def agent_action_stage_1(sandbox, agent_body, step_count):
    pass
