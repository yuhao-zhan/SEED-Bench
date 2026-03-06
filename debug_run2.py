import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from main import Simulator
from tasks.Category4_Granular_FluidInteraction.F_03.environment import Sandbox
from tasks.Category4_Granular_FluidInteraction.F_03.agent import build_agent, agent_action

sandbox = Sandbox()
agent_body = build_agent(sandbox)

for step in range(1200):
    agent_action(sandbox, agent_body, step)
    sandbox.step(1/60.0)
    
    if step % 60 == 0:
        t = step / 60.0
        arm_a = sandbox.agent_arm_joint.angle
        ba = agent_body.angle
        carried = 0
        for p in sandbox._particles:
            if p.linearVelocity == agent_body.linearVelocity:
                carried += 1
        print(f"t={t:.2f}s, arm={arm_a:.2f}, ba={ba:.2f}, carried={carried}, y={agent_body.position.y:.2f}")

