"""
S-02: The Skyscraper task Agent module
Build a tall tower that survives earthquake and wind.
Reference solutions for initial and mutated tasks are strictly independent.
"""
import math

def build_agent(sandbox):
    foundation_y = 1.0
    foundation = sandbox._terrain_bodies.get("foundation")
    levels = 25
    beam_h = 1.5
    base_w = 2.0
    density = 40.0
    tmd_f = 1.85
    
    base = sandbox.add_beam(x=0, y=foundation_y + 1.0, width=base_w, height=2.0, density=500.0)
    if foundation:
        for i in range(20):
            ax = -base_w/2 + (i * base_w / 19)
            sandbox.add_joint(foundation, base, (ax, foundation_y), type='rigid')

    prev = base
    prev_y = foundation_y + 1.0
    beams = [base]
    for i in range(1, levels):
        curr_y = prev_y + beam_h
        curr_w = max(0.8, base_w * (1 - curr_y/60.0))
        d = max(10.0, density * (1 - curr_y/70.0))
        b = sandbox.add_beam(x=0, y=curr_y, width=curr_w, height=beam_h, density=d)
        
        anchor_y = curr_y - beam_h/2
        num_j = 15
        for j in range(num_j):
            jx = -curr_w/2 + 0.05 + (j * (curr_w-0.1) / (num_j-1))
            sandbox.add_joint(prev, b, (jx, anchor_y), type='rigid')
            
        prev = b
        prev_y = curr_y
        beams.append(b)

    top = beams[-1]
    tmd = sandbox.add_beam(x=0, y=prev_y + 1.5, width=2.0, height=2.0, density=100.0)
    sandbox.add_spring(top, tmd, (0, prev_y + beam_h/2), (0, 0), stiffness=tmd_f, damping=0.95)
    return base

def agent_action(sandbox, agent_body, step_count):
    pass

def build_agent_stage_1(sandbox):
    foundation_y = 1.0
    foundation = sandbox._terrain_bodies.get("foundation")
    levels = 30
    beam_h = 1.5
    base_w = 3.8
    density = 80.0
    tmd_f = 1.85
    
    base = sandbox.add_beam(x=0, y=foundation_y + 1.0, width=base_w, height=2.0, density=500.0)
    if foundation:
        for i in range(20):
            ax = -base_w/2 + (i * base_w / 19)
            sandbox.add_joint(foundation, base, (ax, foundation_y), type='rigid')

    prev = base
    prev_y = foundation_y + 1.0
    beams = [base]
    for i in range(1, levels):
        curr_y = prev_y + beam_h
        curr_w = max(0.8, base_w * (1 - curr_y/60.0))
        d = max(10.0, density * (1 - curr_y/70.0))
        b = sandbox.add_beam(x=0, y=curr_y, width=curr_w, height=beam_h, density=d)
        
        anchor_y = curr_y - beam_h/2
        num_j = 15
        for j in range(num_j):
            jx = -curr_w/2 + 0.05 + (j * (curr_w-0.1) / (num_j-1))
            sandbox.add_joint(prev, b, (jx, anchor_y), type='rigid')
            
        prev = b
        prev_y = curr_y
        beams.append(b)

    top = beams[-1]
    tmd = sandbox.add_beam(x=0, y=prev_y + 1.5, width=2.0, height=2.0, density=100.0)
    sandbox.add_spring(top, tmd, (0, prev_y + beam_h/2), (0, 0), stiffness=tmd_f, damping=0.95)
    return base

def agent_action_stage_1(sandbox, agent_body, step_count):
    pass

def build_agent_stage_2(sandbox):
    foundation_y = 1.0
    foundation = sandbox._terrain_bodies.get("foundation")
    levels = 25
    beam_h = 1.5
    base_w = 3.8
    density = 120.0
    tmd_f = 1.85
    
    base = sandbox.add_beam(x=0, y=foundation_y + 1.0, width=base_w, height=2.0, density=500.0)
    if foundation:
        for i in range(20):
            ax = -base_w/2 + (i * base_w / 19)
            sandbox.add_joint(foundation, base, (ax, foundation_y), type='rigid')

    prev = base
    prev_y = foundation_y + 1.0
    beams = [base]
    for i in range(1, levels):
        curr_y = prev_y + beam_h
        curr_w = max(0.8, base_w * (1 - curr_y/60.0))
        d = max(10.0, density * (1 - curr_y/70.0))
        b = sandbox.add_beam(x=0, y=curr_y, width=curr_w, height=beam_h, density=d)
        
        anchor_y = curr_y - beam_h/2
        num_j = 15
        for j in range(num_j):
            jx = -curr_w/2 + 0.05 + (j * (curr_w-0.1) / (num_j-1))
            sandbox.add_joint(prev, b, (jx, anchor_y), type='rigid')
            
        prev = b
        prev_y = curr_y
        beams.append(b)

    top = beams[-1]
    tmd = sandbox.add_beam(x=0, y=prev_y + 1.5, width=2.0, height=2.0, density=100.0)
    sandbox.add_spring(top, tmd, (0, prev_y + beam_h/2), (0, 0), stiffness=tmd_f, damping=0.95)
    return base

def agent_action_stage_2(sandbox, agent_body, step_count):
    pass

def build_agent_stage_3(sandbox):
    foundation_y = 1.0
    foundation = sandbox._terrain_bodies.get("foundation")
    levels = 6
    beam_h = 5.5
    base_w = 3.8
    
    base = sandbox.add_beam(x=0, y=foundation_y + beam_h/2, width=base_w, height=beam_h, density=500.0)
    if foundation:
        for i in range(10):
            ax = -base_w/2 + (i * base_w / 9)
            sandbox.add_joint(foundation, base, (ax, foundation_y), type='rigid')

    prev = base
    prev_y = foundation_y + beam_h/2
    for i in range(1, levels):
        curr_y = prev_y + beam_h
        curr_w = max(1.5, base_w * (1 - i/10.0))
        b = sandbox.add_beam(x=0, y=curr_y, width=curr_w, height=beam_h, density=100.0)
        
        anchor_y = curr_y - beam_h/2
        num_j = 5
        for j in range(num_j):
            jx = -curr_w/2 + 0.1 + (j * (curr_w-0.2) / (num_j-1))
            sandbox.add_joint(prev, b, (jx, anchor_y), type='rigid')
        
        prev = b
        prev_y = curr_y
        
    return base

def agent_action_stage_3(sandbox, agent_body, step_count):
    pass

def build_agent_stage_4(sandbox):
    foundation_y = 1.0
    foundation = sandbox._terrain_bodies.get("foundation")
    levels = 6
    beam_h = 5.5
    base_w = 3.8
    
    base = sandbox.add_beam(x=0, y=foundation_y + beam_h/2, width=base_w, height=beam_h, density=500.0)
    if foundation:
        for i in range(10):
            ax = -base_w/2 + (i * base_w / 9)
            sandbox.add_joint(foundation, base, (ax, foundation_y), type='rigid')

    prev = base
    prev_y = foundation_y + beam_h/2
    for i in range(1, levels):
        curr_y = prev_y + beam_h
        curr_w = max(1.5, base_w * (1 - i/10.0))
        b = sandbox.add_beam(x=0, y=curr_y, width=curr_w, height=beam_h, density=100.0)
        
        anchor_y = curr_y - beam_h/2
        num_j = 5
        for j in range(num_j):
            jx = -curr_w/2 + 0.1 + (j * (curr_w-0.2) / (num_j-1))
            sandbox.add_joint(prev, b, (jx, anchor_y), type='rigid')
        
        prev = b
        prev_y = curr_y
        
    return base

def agent_action_stage_4(sandbox, agent_body, step_count):
    pass
