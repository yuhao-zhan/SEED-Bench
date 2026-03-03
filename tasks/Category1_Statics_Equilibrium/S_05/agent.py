"""
S-05: The Shelter task Agent module
"""

import math

def build_agent(sandbox):
    # BASE AGENT: Extremely weak, no roof.
    base_h = 1.0
    base_y = base_h / 2 # 0.5
    
    # Just two separate columns, NO ROOF to protect the core.
    base_left = sandbox.add_beam(8.5, base_y, 1.0, base_h, angle=0, density=1.0)
    base_right = sandbox.add_beam(11.5, base_y, 1.0, base_h, angle=0, density=1.0)
    sandbox.add_joint(base_left, None, (8.5, 0.0), type='rigid')
    sandbox.add_joint(base_right, None, (11.5, 0.0), type='rigid')
    
    col_h = 4.0
    col_y = base_y + base_h/2 + col_h/2 # 3.0
    col_left = sandbox.add_beam(8.5, col_y, 0.5, col_h, angle=0, density=1.0)
    col_right = sandbox.add_beam(11.5, col_y, 0.5, col_h, angle=0, density=1.0)
    sandbox.add_joint(base_left, col_left, (8.5, 1.0), type='rigid')
    sandbox.add_joint(base_right, col_right, (11.5, 1.0), type='rigid')
    
    return base_left

def agent_action(sandbox, agent_body, step_count):
    pass


# Stage 1: Increased Gravity (-40)
def build_agent_stage_1(sandbox):
    if 'core' in sandbox._terrain_bodies:
        sandbox._terrain_bodies['core'].position = (10.0, 0.5)
        
    base_h = 1.0
    base_y = base_h / 2
    base_left = sandbox.add_beam(7.0, base_y, 3.0, base_h, angle=0, density=5.0)
    base_right = sandbox.add_beam(13.0, base_y, 3.0, base_h, angle=0, density=5.0)
    sandbox.add_joint(base_left, None, (7.0, 0.0), type='rigid')
    sandbox.add_joint(base_right, None, (13.0, 0.0), type='rigid')
    
    col_h = 4.5
    col_y = base_y + base_h/2 + col_h/2
    col_left = sandbox.add_beam(7.0, col_y, 1.5, col_h, angle=0, density=5.0)
    col_right = sandbox.add_beam(13.0, col_y, 1.5, col_h, angle=0, density=5.0)
    sandbox.add_joint(base_left, col_left, (7.0, 1.0), type='rigid')
    sandbox.add_joint(base_right, col_right, (13.0, 1.0), type='rigid')
    
    roof_w = 10.0
    roof_h = 1.5
    roof_y = col_y + col_h/2 + roof_h/2
    roof = sandbox.add_beam(10.0, roof_y, roof_w, roof_h, angle=0, density=10.0)
    sandbox.add_joint(col_left, roof, (7.0, 5.5), type='rigid')
    sandbox.add_joint(col_right, roof, (13.0, 5.5), type='rigid')
    
    return base_left

def agent_action_stage_1(sandbox, agent_body, step_count):
    pass


# Stage 2: Endless Bombardment (128 meteors)
def build_agent_stage_2(sandbox):
    return build_agent_stage_1(sandbox)

def agent_action_stage_2(sandbox, agent_body, step_count):
    pass


# Stage 3: Stricter Core (10.0N)
def build_agent_stage_3(sandbox):
    if 'core' in sandbox._terrain_bodies:
        sandbox._terrain_bodies['core'].position = (10.0, 0.5)
        
    base_h = 1.0
    base_y = base_h / 2
    base_left = sandbox.add_beam(6.5, base_y, 4.0, base_h, angle=0, density=5.0)
    base_right = sandbox.add_beam(13.5, base_y, 4.0, base_h, angle=0, density=5.0)
    sandbox.add_joint(base_left, None, (6.5, 0.0), type='rigid')
    sandbox.add_joint(base_right, None, (13.5, 0.0), type='rigid')
    
    col_h = 4.5
    col_y = base_y + base_h/2 + col_h/2
    col_left = sandbox.add_beam(6.5, col_y, 2.0, col_h, angle=0, density=5.0)
    col_right = sandbox.add_beam(13.5, col_y, 2.0, col_h, angle=0, density=5.0)
    sandbox.add_joint(base_left, col_left, (6.5, 1.0), type='rigid')
    sandbox.add_joint(base_right, col_right, (13.5, 1.0), type='rigid')
    
    roof_w = 11.0
    roof_h = 2.0
    roof_y = col_y + col_h/2 + roof_h/2
    roof = sandbox.add_beam(10.0, roof_y, roof_w, roof_h, angle=0, density=15.0)
    sandbox.add_joint(col_left, roof, (6.5, 5.5), type='rigid')
    sandbox.add_joint(col_right, roof, (13.5, 5.5), type='rigid')
    
    return base_left

def agent_action_stage_3(sandbox, agent_body, step_count):
    pass


# Stage 4: Extreme Challenge
def build_agent_stage_4(sandbox):
    if 'core' in sandbox._terrain_bodies:
        sandbox._terrain_bodies['core'].position = (10.0, 0.5)
        
    base_h = 1.0
    base_y = base_h / 2
    base_left = sandbox.add_beam(7.5, base_y, 2.0, base_h, angle=0, density=4.0)
    base_right = sandbox.add_beam(12.5, base_y, 2.0, base_h, angle=0, density=4.0)
    sandbox.add_joint(base_left, None, (7.5, 0.0), type='rigid')
    sandbox.add_joint(base_right, None, (12.5, 0.0), type='rigid')
    
    col_h = 4.5
    col_y = base_y + base_h/2 + col_h/2
    col_left = sandbox.add_beam(7.5, col_y, 1.0, col_h, angle=0, density=4.0)
    col_right = sandbox.add_beam(12.5, col_y, 1.0, col_h, angle=0, density=4.0)
    sandbox.add_joint(base_left, col_left, (7.5, 1.0), type='rigid')
    sandbox.add_joint(base_right, col_right, (12.5, 1.0), type='rigid')
    
    roof_w = 8.0
    roof_h = 1.5
    roof_y = col_y + col_h/2 + roof_h/2
    roof = sandbox.add_beam(10.0, roof_y, roof_w, roof_h, angle=0, density=6.0)
    sandbox.add_joint(col_left, roof, (7.5, 5.5), type='rigid')
    sandbox.add_joint(col_right, roof, (12.5, 5.5), type='rigid')
    
    return base_left

def agent_action_stage_4(sandbox, agent_body, step_count):
    pass
