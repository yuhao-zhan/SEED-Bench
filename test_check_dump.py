import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from tasks.Category4_Granular_FluidInteraction.F_03.environment import Sandbox
from tasks.Category4_Granular_FluidInteraction.F_03.agent import build_agent, agent_action

sandbox = Sandbox()
agent_body = build_agent(sandbox)

for step in range(600):
    agent_action(sandbox, agent_body, step)
    
    bx, by = agent_body.position.x, agent_body.position.y
    ba = agent_body.angle
    over_hopper = (sandbox.HOPPER_X_MIN <= bx <= sandbox.HOPPER_X_MAX and by >= sandbox.HOPPER_Y_MIN)
    dumping = ba > 0.6 and over_hopper
    
    carried = 0
    dx, dy = 1.6, 1.35 # Approx for 1.5x1.0 scoop
    for p in sandbox._particles:
        px, py = p.position.x, p.position.y
        if abs(px - bx) <= dx and abs(py - by) <= dy:
            carried += 1
            
    sandbox.step(1/60.0)
    
    if step % 20 == 0:
        print(f"step {step} pos ({bx:.2f}, {by:.2f}), ba {ba:.2f}, over {over_hopper}, dump {dumping}, carried {carried}, in_hopper {sandbox.get_particles_in_hopper_count()}")

