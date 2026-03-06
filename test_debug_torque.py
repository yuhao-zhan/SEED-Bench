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
        aj = sandbox._aj
        print(f"step {step} angle {aj.angle:.2f}, target {-1.6}, torque {aj.GetMotorTorque(60.0):.2f}")

