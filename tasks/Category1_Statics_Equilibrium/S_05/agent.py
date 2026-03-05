"""
S-05: The Shelter task Agent module
"""

import math

def build_agent(sandbox):

    base_h = 1.0
    base_y = base_h / 2


    base_left = sandbox.add_beam(8.5, base_y, 1.0, base_h, angle=0, density=1.0)
    base_right = sandbox.add_beam(11.5, base_y, 1.0, base_h, angle=0, density=1.0)
    sandbox.add_joint(base_left, None, (8.5, 0.0), type='rigid')
    sandbox.add_joint(base_right, None, (11.5, 0.0), type='rigid')

    col_h = 4.0
    col_y = base_y + base_h/2 + col_h/2
    col_left = sandbox.add_beam(8.5, col_y, 0.5, col_h, angle=0, density=1.0)
    col_right = sandbox.add_beam(11.5, col_y, 0.5, col_h, angle=0, density=1.0)
    sandbox.add_joint(base_left, col_left, (8.5, 1.0), type='rigid')
    sandbox.add_joint(base_right, col_right, (11.5, 1.0), type='rigid')

    return base_left

def agent_action(sandbox, agent_body, step_count):
    pass



def build_agent_stage_1(sandbox):

    p1 = sandbox.add_beam(7.5, 2.0, 1.0, 4.0, angle=0, density=10.0)
    p2 = sandbox.add_beam(12.5, 2.0, 1.0, 4.0, angle=0, density=10.0)
    sandbox.add_joint(p1, None, (7.5, 0.0), type='rigid')
    sandbox.add_joint(p2, None, (12.5, 0.0), type='rigid')


    roof = sandbox.add_beam(10.0, 4.75, 8.0, 1.5, angle=0, density=15.0)
    sandbox.add_joint(p1, roof, (7.5, 4.0), type='rigid')
    sandbox.add_joint(p2, roof, (12.5, 4.0), type='rigid')



    return p1

def agent_action_stage_1(sandbox, agent_body, step_count):
    pass



def build_agent_stage_2(sandbox):


    p1_base_x, p2_base_x = 6.0, 14.0
    p1_top_x, p2_top_x = 8.5, 11.5


    p1 = sandbox.add_beam(7.25, 2.5, 0.5, 5.2, angle=-0.4, density=10.0)
    sandbox.add_joint(p1, None, (6.0, 0.0), type='rigid')


    p2 = sandbox.add_beam(12.75, 2.5, 0.5, 5.2, angle=0.4, density=10.0)
    sandbox.add_joint(p2, None, (14.0, 0.0), type='rigid')


    roof = sandbox.add_beam(10.0, 5.2, 8.0, 1.0, angle=0, density=10.0)
    sandbox.add_joint(p1, roof, (8.5, 5.0), type='rigid')
    sandbox.add_joint(p2, roof, (11.5, 5.0), type='rigid')


    brace = sandbox.add_beam(15.0, 2.0, 0.5, 4.0, angle=0, density=10.0)
    sandbox.add_joint(brace, None, (15.0, 0.0), type='rigid')
    sandbox.add_joint(brace, p2, (14.5, 4.0), type='rigid')

    return p1

def agent_action_stage_2(sandbox, agent_body, step_count):
    pass



def build_agent_stage_3(sandbox):

    p1 = sandbox.add_beam(7.5, 2.5, 1.0, 5.0, angle=0, density=10.0)
    p2 = sandbox.add_beam(12.5, 2.5, 1.0, 5.0, angle=0, density=10.0)
    sandbox.add_joint(p1, None, (7.5, 0.0), type='rigid')
    sandbox.add_joint(p2, None, (12.5, 0.0), type='rigid')



    slope_l = sandbox.add_beam(8.7, 6.0, 4.0, 0.5, angle=-0.5, density=15.0)
    sandbox.add_joint(p1, slope_l, (7.5, 5.0), type='rigid')


    slope_r = sandbox.add_beam(11.3, 6.0, 4.0, 0.5, angle=0.5, density=15.0)
    sandbox.add_joint(p2, slope_r, (12.5, 5.0), type='rigid')


    sandbox.add_joint(slope_l, slope_r, (10.0, 7.0), type='rigid')


    inner_roof = sandbox.add_beam(10.0, 4.0, 4.0, 0.3, angle=0, density=5.0)
    sandbox.add_joint(p1, inner_roof, (8.0, 4.0), type='rigid')
    sandbox.add_joint(p2, inner_roof, (12.0, 4.0), type='rigid')

    return p1

def agent_action_stage_3(sandbox, agent_body, step_count):
    pass



def build_agent_stage_4(sandbox):

    p1 = sandbox.add_beam(7.5, 2.5, 1.0, 5.0, angle=0, density=5.0)
    p2 = sandbox.add_beam(12.5, 2.5, 1.0, 5.0, angle=0, density=5.0)
    sandbox.add_joint(p1, None, (7.5, 0.0), type='rigid')
    sandbox.add_joint(p2, None, (12.5, 0.0), type='rigid')


    brace = sandbox.add_beam(13.5, 2.0, 0.5, 5.0, angle=0.5, density=5.0)
    sandbox.add_joint(brace, None, (15.0, 0.0), type='rigid')
    sandbox.add_joint(brace, p2, (12.5, 4.0), type='rigid')


    slope_l = sandbox.add_beam(8.7, 6.0, 4.0, 1.0, angle=-0.5, density=5.0)
    sandbox.add_joint(p1, slope_l, (7.5, 5.0), type='rigid')

    slope_r = sandbox.add_beam(11.3, 6.0, 4.0, 1.0, angle=0.5, density=5.0)
    sandbox.add_joint(p2, slope_r, (12.5, 5.0), type='rigid')

    sandbox.add_joint(slope_l, slope_r, (10.0, 7.0), type='rigid')


    inner = sandbox.add_beam(10.0, 4.0, 4.0, 0.5, angle=0, density=5.0)
    sandbox.add_joint(p1, inner, (8.0, 4.0), type='rigid')
    sandbox.add_joint(p2, inner, (12.0, 4.0), type='rigid')

    return p1

def agent_action_stage_4(sandbox, agent_body, step_count):
    pass
