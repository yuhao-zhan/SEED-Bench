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
    d = 0.6
    left_wall = sandbox.add_beam(8.0, 2.25, 0.4, 4.5, angle=0, density=d)
    right_wall = sandbox.add_beam(16.0, 2.25, 0.4, 4.5, angle=0, density=d)
    sandbox.add_joint(left_wall, None, (8.0, 0.0), type='rigid')
    sandbox.add_joint(right_wall, None, (16.0, 0.0), type='rigid')
    floor_l = sandbox.add_beam(9.5, 0.5, 2.5, 0.4, angle=0, density=d)
    floor_r = sandbox.add_beam(14.5, 0.5, 2.5, 0.4, angle=0, density=d)
    sandbox.add_joint(floor_l, left_wall, (8.0, 0.5), type='rigid')
    sandbox.add_joint(floor_r, right_wall, (16.0, 0.5), type='rigid')
    roof = sandbox.add_beam(12.0, 4.5, 8.0, 0.4, angle=0, density=d)
    sandbox.add_joint(roof, left_wall, (8.0, 4.5), type='rigid')
    sandbox.add_joint(roof, right_wall, (16.0, 4.5), type='rigid')
    sup_l = sandbox.add_beam(10.7, 2.5, 0.2, 3.6, angle=0, density=d)
    sup_r = sandbox.add_beam(13.3, 2.5, 0.2, 3.6, angle=0, density=d)
    sandbox.add_joint(sup_l, floor_l, (10.7, 0.7), type='rigid')
    sandbox.add_joint(sup_r, floor_r, (13.3, 0.7), type='rigid')
    sandbox.add_joint(sup_l, roof, (10.7, 4.3), type='rigid')
    sandbox.add_joint(sup_r, roof, (13.3, 4.3), type='rigid')
    return left_wall

def build_agent_stage_3(sandbox):
    density = 0.1
    col_l = sandbox.add_beam(7.5, 2.3, 0.5, 4.0, angle=0, density=density)
    col_r = sandbox.add_beam(12.5, 2.3, 0.5, 4.0, angle=0, density=density)
    sandbox.add_joint(col_l, None, (7.5, 0.3), type='rigid')
    sandbox.add_joint(col_r, None, (12.5, 0.3), type='rigid')
    roof_l = sandbox.add_beam(8.75, 4.8, 3.5, 0.4, angle=-math.pi/6, density=density)
    roof_r = sandbox.add_beam(11.25, 4.8, 3.5, 0.4, angle=math.pi/6, density=density)
    sandbox.add_joint(col_l, roof_l, (7.5, 4.3), type='rigid')
    sandbox.add_joint(col_r, roof_r, (12.5, 4.3), type='rigid')
    sandbox.add_joint(roof_l, roof_r, (10.0, 5.5), type='rigid')
    return col_l

def build_agent_stage_4(sandbox):
    density = 0.8
    col_l = sandbox.add_beam(5.5, 2.0, 0.4, 4.0, angle=0, density=density)
    col_r = sandbox.add_beam(10.5, 2.0, 0.4, 4.0, angle=0, density=density)
    sandbox.add_joint(col_l, None, (5.5, 0.0), type='rigid')
    sandbox.add_joint(col_r, None, (10.5, 0.0), type='rigid')
    roof = sandbox.add_beam(8.0, 4.2, 6.0, 0.4, angle=0, density=density)
    sandbox.add_joint(col_l, roof, (5.5, 4.0), type='rigid')
    sandbox.add_joint(col_r, roof, (10.5, 4.0), type='rigid')
    shield = sandbox.add_beam(6.5, 1.5, 0.2, 3.0, angle=0, density=density)
    sandbox.add_joint(shield, None, (6.5, 0.0), type='rigid')
    return col_l

def agent_action_stage_1(sandbox, agent_body, step_count):
    pass

def agent_action_stage_2(sandbox, agent_body, step_count):
    pass

def agent_action_stage_3(sandbox, agent_body, step_count):
    pass

def agent_action_stage_4(sandbox, agent_body, step_count):
    pass
