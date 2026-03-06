import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from tasks.Category4_Granular_FluidInteraction.F_03.environment import Sandbox
from tasks.Category4_Granular_FluidInteraction.F_03.agent import build_agent, agent_action

sandbox = Sandbox()
agent_body = build_agent(sandbox)

for step in range(120):
    agent_action(sandbox, agent_body, step)
    sandbox.step(1/60.0)
    
    if step % 20 == 0:
        arm = sandbox._arm_joint
        bucket = sandbox._bucket_joint
        print(f"step {step} arm angle {arm.angle:.2f}, speed {arm.speed:.2f}, torque {arm.GetMotorTorque(60.0):.2f}")
        print(f"         bucket angle {bucket.angle:.2f}, ba {agent_body.angle:.2f}")

