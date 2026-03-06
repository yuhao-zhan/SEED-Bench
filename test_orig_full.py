import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from tasks.Category4_Granular_FluidInteraction.F_03.environment import Sandbox
from tasks.Category4_Granular_FluidInteraction.F_03.agent import build_agent, agent_action

sandbox = Sandbox()
agent_body = build_agent(sandbox)
base = sandbox._bodies[0]
arm = sandbox._bodies[1]

for step in range(720):
    agent_action(sandbox, agent_body, step)
    sandbox.step(1/60.0)
    if step % 60 == 0:
        print(f"step {step} arm angle={sandbox.agent_arm_joint.angle:.2f}, bucket angle={sandbox.agent_bucket_joint.angle:.2f}")
