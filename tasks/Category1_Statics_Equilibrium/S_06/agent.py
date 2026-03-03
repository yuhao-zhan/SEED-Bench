"""
S-06: The Overhang task Agent module
Highly robust reference solutions for refined difficulty progression tasks.
"""
import math

def build_agent(sandbox):
    """Initial Baseline: Standard cantilever."""
    # center -1.0, width 4.0 -> edge 1.0. 
    # Fails Stage 1 (Spawn Zone x < -1.5)
    # Fails Stage 2 (Target Reach 1.2)
    # Fails Stage 3 (Target Reach 1.5)
    # Fails Stage 4 (Spawn Zone x < -1.5)
    sandbox.add_block(-1.0, 0.2, 4.0, 0.4)
    return None

def agent_action(sandbox, agent_body, step_count):
    pass

def build_agent_stage_1(sandbox):
    """Stage 1: The Edge Restriction. Spawn x < -1.5, reach 0.5."""
    # center -1.5, width 4.0 -> edge 0.5. Exactly on target.
    sandbox.add_block(-1.5, 0.25, 4.0, 0.4)
    # Counter-weight to ensure absolute stability
    for i in range(5):
        sandbox.add_block(-9.0, 0.25 + i*0.4, 1.0, 0.4)
    return None

def agent_action_stage_1(sandbox, agent_body, step_count):
    pass

def build_agent_stage_2(sandbox):
    """Stage 2: The Slick cantilever. Friction 0.05, reach 1.2."""
    # Center -0.8, width 4.0 -> edge 1.2.
    # To stabilize 0.05 friction, we need a massive base anchor.
    sandbox.add_block(-0.8, 0.25, 4.0, 0.4)
    # Stack multiple to increase normal force
    sandbox.add_block(-0.8, 0.65, 4.0, 0.4)
    # Anchor at the back
    for i in range(15):
        sandbox.add_block(-9.5, 0.25 + i*0.4, 1.0, 0.4)
    return None

def agent_action_stage_2(sandbox, agent_body, step_count):
    pass

def build_agent_stage_3(sandbox):
    """Stage 3: The Low-Clearance Stretch. Ceiling 0.45, reach 1.5."""
    # Center -0.5, width 4.0 -> edge 1.5.
    # Single layer only.
    sandbox.add_block(-0.5, 0.2, 4.0, 0.4)
    # Horizontal counter-weights
    for x in range(10):
        sandbox.add_block(-9.5 + x*0.5, 0.2, 0.5, 0.4)
    return None

def agent_action_stage_3(sandbox, agent_body, step_count):
    pass

def build_agent_stage_4(sandbox):
    """Stage 4: The Seismic Abyss. Oscillation, Spawn x < -1.5, reach 0.5."""
    # center -1.5, width 4.0 -> edge 0.5.
    sandbox.add_block(-1.5, 0.2, 4.0, 0.4)
    # Massive side-by-side stabilization
    for x in range(15):
        sandbox.add_block(-9.5 + x*0.5, 0.2, 0.5, 0.4)
    return None

def agent_action_stage_4(sandbox, agent_body, step_count):
    pass
