import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from tasks.Category4_Granular_FluidInteraction.F_03.environment import Sandbox
from tasks.Category4_Granular_FluidInteraction.F_03.agent import build_agent, agent_action

sandbox = Sandbox()
agent_body = build_agent(sandbox)

for step in range(1200):
    agent_action(sandbox, agent_body, step)
    
    carried = 0
    bx, by = agent_body.position.x, agent_body.position.y
    dx, dy = 1.6, 1.35
    for p in sandbox._particles:
        px, py = p.position.x, p.position.y
        if abs(px - bx) <= dx and abs(py - by) <= dy:
            carried += 1
            
    sandbox.step(1/60.0)
    
    if step % 60 == 0:
        print(f"t={step/60.0:.1f}s carried={carried}, pos=({bx:.2f}, {by:.2f}), ba={agent_body.angle:.2f}, in_h={sandbox.get_particles_in_hopper_count()}")

