# EVOLVE-BLOCK-START
import math

def build_agent(sandbox):
    # Horizontal beam from x=0 to x=14m, y=0
    horizontal_beam = sandbox.add_beam(x=0, y=0, width=0.5, height=1.0, density=10.0)
    
    # Diagonal beam from tip (14m) to anchor at (0, 5)
    tip_angle = math.atan2(5, -14)
    diagonal_tip = sandbox.add_beam(x=14, y=0, width=0.1, height=0.1, angle=tip_angle, density=1.0)
    # Anchor joint at (0, 5)
    joint_tip = sandbox.add_joint(diagonal_tip, horizontal_beam, (14, 0), type='rigid')
    
    # Diagonal beam from mid-span (7.5m) to anchor at (0, 10)
    mid_angle = math.atan2(10, -7.5)
    diagonal_mid = sandbox.add_beam(x=7.5, y=0, width=0.1, height=0.1, angle=mid_angle, density=1.0)
    # Anchor joint at (0, 10)
    joint_mid = sandbox.add_joint(diagonal_mid, horizontal_beam, (7.5, 0), type='rigid')
    
    return horizontal_beam

def agent_action(sandbox, agent_body, step_count):
    pass
# EVOLVE-BLOCK-END