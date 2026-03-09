import math

def build_agent(sandbox):
    sandbox.add_block(-1.0, 0.2, 4.0, 0.4)
    return None

def agent_action(sandbox, agent_body, step_count):
    pass

def build_agent_stage_1(sandbox):
    # Stage 1: The Slick Threshold (friction 0.05, overhang 1.2, spawn [-10, -0.8])
    # Single block at -0.8 reaches 1.2. High density for stability.
    sandbox.add_block(-0.8, 0.2, 4.0, 0.4, density=100.0)
    return None

def agent_action_stage_1(sandbox, agent_body, step_count):
    pass

def build_agent_stage_2(sandbox):
    # Stage 2: The Heavy Gale (wind -400, overhang 1.5, spawn [-10, -0.5])
    # Single block at -0.5 reaches 1.5. Needs mass > 50 to resist wind.
    sandbox.add_block(-0.5, 0.2, 4.0, 0.4, density=100.0)
    return None

def agent_action_stage_2(sandbox, agent_body, step_count):
    pass

def build_agent_stage_3(sandbox):
    # Stage 3: The Shaking Ceiling (ceiling 0.8, amp 0.02, freq 3.0, wind -100, overhang 1.8, spawn [-10, -0.2])
    # Single block at -0.2 reaches 1.8. Fits under ceiling. High density for stability.
    sandbox.add_block(-0.2, 0.2, 4.0, 0.4, density=200.0)
    return None

def agent_action_stage_3(sandbox, agent_body, step_count):
    pass

def build_agent_stage_4(sandbox):
    # Stage 4: The Tilted Titan (angle -5, friction 0.05, gravity -50, wind -800, overhang 1.8, spawn [-10, 0.0])
    # Use multiple blocks to ensure stability. COM should be well back from the edge.
    # Base block at -0.6 (right edge 1.4). Top block at -0.2 (right edge 1.8).
    # Total COM at -0.4.
    sandbox.add_block(-0.6, 0.2, 4.0, 0.4, density=500.0)
    sandbox.add_block(-0.2, 0.6, 4.0, 0.4, density=500.0)
    return None

def agent_action_stage_4(sandbox, agent_body, step_count):
    pass
