"""
S-06: The Overhang task Agent module
Highly robust reference solutions for refined difficulty progression tasks.
"""
import math

def build_agent(sandbox):
    """Initial Baseline: Standard cantilever."""
    # center -1.0, width 4.0 -> edge 1.0. 
    sandbox.add_block(-1.0, 0.2, 4.0, 0.4)
    return None

def agent_action(sandbox, agent_body, step_count):
    pass

def build_agent_stage_1(sandbox):
    """Stage 1: The Slick Anchor. Friction 0.05, Spawn x < -1.2, reach 0.8."""
    # Main cantilever block
    sandbox.add_block(-1.2, 0.2, 4.0, 0.4)
    # Massive anchor stack to overcome 0.05 friction
    for i in range(15):
        sandbox.add_block(-8.0, 0.6 + i*0.4, 4.0, 0.4)
    return None

def agent_action_stage_1(sandbox, agent_body, step_count):
    pass

def build_agent_stage_2(sandbox):
    """Stage 2: The Inclined Gale. Tilt -10, Spawn x < -0.8, reach 1.2."""
    # Main cantilever block
    sandbox.add_block(-0.8, 0.2, 4.0, 0.4)
    # Heavy anchor stack at the back to prevent sliding down the 10 degree slope
    for i in range(15):
        sandbox.add_block(-8.0, 0.6 + i*0.4, 4.0, 0.4)
    return None

def agent_action_stage_2(sandbox, agent_body, step_count):
    pass

def build_agent_stage_3(sandbox):
    """Stage 3: The Seismic Squeeze. Oscillation, Wind 20, Spawn x < -0.5, reach 1.5."""
    # Use higher density for stability
    d = 200.0
    # Main cantilever block
    sandbox.add_block(-0.5, 0.2, 4.0, 0.4, density=d)
    # Extremely heavy base to resist wind and seismic vibrations
    for i in range(18):
        sandbox.add_block(-7.0, 0.6 + i*0.4, 4.0, 0.4, density=d)
    # Add some wide blocks at the bottom for more friction contact
    sandbox.add_block(-5.0, 0.2, 4.0, 0.4, density=d)
    return None

def agent_action_stage_3(sandbox, agent_body, step_count):
    pass

def build_agent_stage_4(sandbox):
    """Stage 4: The Titan's Overhang. Gravity 60, Wind 30, Friction 0.02, Ceiling 0.5, Spawn x < -0.2, reach 1.8."""
    # We must use thin, high-density blocks to fit under the 0.5m ceiling and resist the wind on slick table.
    h = 0.1
    # Use density=100.0 to ensure F_friction (mu * m * g) > F_wind.
    # mu=0.02, g=60 -> mu*g = 1.2.
    # wind=30, m=density*area = 100*0.4 = 40 -> wind/m = 0.75.
    # 1.2 > 0.75, so it will stay on the table.
    d = 100.0
    # Main cantilever block (reaches 1.8m)
    sandbox.add_block(-0.2, h/2, 4.0, h, density=d)
    # Stack blocks on top of the base of the cantilever to anchor it.
    for i in range(1, 4):
        sandbox.add_block(-2.2, h/2 + i*h, 4.0, h, density=d)
    # Add more blocks behind it to increase total mass and friction.
    for x_pos in [-4.0, -6.0, -8.0]:
        for i in range(4):
            sandbox.add_block(x_pos, h/2 + i*h, 4.0, h, density=d)
    return None

def agent_action_stage_4(sandbox, agent_body, step_count):
    pass
