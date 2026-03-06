import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from tasks.Category4_Granular_FluidInteraction.F_03.environment import Sandbox
from tasks.Category4_Granular_FluidInteraction.F_03.agent import build_agent, agent_action

sandbox = Sandbox()
agent_body = build_agent(sandbox)

for step in range(600):
    agent_action(sandbox, agent_body, step)
    sandbox.step(1/60.0)
    
    if step % 30 == 0:
        bx, by = agent_body.position.x, agent_body.position.y
        w, h = 0.65, 0.45
        dx = w / 2 + 0.85
        dy = h / 2 + 0.85
        count = sum(1 for p in sandbox._particles if abs(p.position.x - bx) <= dx and abs(p.position.y - by) <= dy)
        print(f"step {step}, arm {sandbox.agent_arm_joint.angle:.2f}, bucket y {by:.2f}, particles in AABB: {count}")

