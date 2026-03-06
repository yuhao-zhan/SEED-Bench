import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from tasks.Category4_Granular_FluidInteraction.F_03.environment import Sandbox
from tasks.Category4_Granular_FluidInteraction.F_03.agent import build_agent, agent_action

sandbox = Sandbox()
agent_body = build_agent(sandbox)

for step in range(30):
    agent_action(sandbox, agent_body, step)
    sandbox.step(1/60.0)
    if step % 10 == 0:
        arm = sandbox.agent_arm_joint.bodyB
        print(f"step {step} arm y={arm.position.y:.2f}, angle={sandbox.agent_arm_joint.angle:.2f}")
