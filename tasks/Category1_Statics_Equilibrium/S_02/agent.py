"""
S-02: The Skyscraper task Agent module
Build a tall tower that survives earthquake and wind.
Reference solutions for initial and mutated tasks are strictly independent.
"""
import math

def build_robust_tower(sandbox, levels=25, base_w=4.0, beam_h=1.5, base_density=200.0, top_density=5.0, joints_per_level=20, tmd=True):
    foundation_y = 1.0
    foundation = sandbox._terrain_bodies.get("foundation")
    
    # Base
    base = sandbox.add_beam(x=0, y=foundation_y + beam_h/2, width=base_w, height=beam_h, density=base_density)
    if foundation:
        # Use 4 joints distributed on the narrow foundation
        for i in range(4):
            ax = -1.5 + (i * 1.0) # [-1.5, -0.5, 0.5, 1.5]
            sandbox.add_joint(foundation, base, (ax, foundation_y), type='rigid')

    prev = base
    prev_y = foundation_y + beam_h/2
    beams = [base]
    for i in range(1, levels):
        curr_y = prev_y + beam_h
        progress = i / (levels - 1)
        # Taper the width and density to reduce top-heaviness and wind pressure
        curr_w = max(0.8, base_w * (1 - progress * 0.75))
        d = max(top_density, base_density * (1 - progress * 0.9))
        b = sandbox.add_beam(x=0, y=curr_y, width=curr_w, height=beam_h, density=d)
        
        anchor_y = curr_y - beam_h/2
        # Use two joints at the edges of the current beam width to distribute load without internal stress
        sandbox.add_joint(prev, b, (-curr_w/2 + 0.1, anchor_y), type='rigid')
        sandbox.add_joint(prev, b, (curr_w/2 - 0.1, anchor_y), type='rigid')
            
        prev = b
        prev_y = curr_y
        beams.append(b)

    if tmd:
        top = beams[-1]
        # Tuned Mass Damper: A heavy block suspended to absorb energy and reduce oscillation
        tmd_body = sandbox.add_beam(x=0, y=prev_y + 2.0, width=1.5, height=1.5, density=100.0)
        sandbox.add_spring(top, tmd_body, (0, prev_y + beam_h/2), (0, 0), stiffness=2.5, damping=0.9)
    
    return base

def build_agent(sandbox):
    return build_robust_tower(sandbox, levels=22, base_w=5.0)

def agent_action(sandbox, agent_body, step_count):
    pass

def build_agent_stage_1(sandbox):
    # Stage 1: Fragile joints. Needs wider base and lighter top to distribute load.
    return build_robust_tower(sandbox, levels=22, base_w=6.5, top_density=5.0)

def agent_action_stage_1(sandbox, agent_body, step_count):
    pass

def build_agent_stage_2(sandbox):
    # Stage 2: Wind Shear. Needs a low-profile, light-weight top and strong base.
    return build_robust_tower(sandbox, levels=23, base_w=5.5, top_density=2.0)

def agent_action_stage_2(sandbox, agent_body, step_count):
    pass

def build_agent_stage_3(sandbox):
    # Stage 3: Resonance. Needs TMD and light structure to shift natural frequency.
    return build_robust_tower(sandbox, levels=22, base_w=6.0, tmd=True)

def agent_action_stage_3(sandbox, agent_body, step_count):
    pass

def build_agent_stage_4(sandbox):
    # Stage 4: Chaos. Robust 5m base, heavy bottom, and TMD for oscillation control.
    return build_robust_tower(sandbox, levels=22, base_w=5.0, tmd=True, top_density=2.0, base_density=500.0)

def agent_action_stage_4(sandbox, agent_body, step_count):
    pass
