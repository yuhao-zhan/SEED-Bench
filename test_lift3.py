import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from tasks.Category4_Granular_FluidInteraction.F_03.environment import Sandbox
from tasks.Category4_Granular_FluidInteraction.F_03.agent import build_agent, agent_action

sandbox = Sandbox()
agent_body = build_agent(sandbox)
_arm_joint = sandbox.agent_arm_joint

for step in range(30):
    _arm_joint.motorSpeed = 3.0  # Force it to lift!
    sandbox.step(1/60.0)
    print(f"step {step}, arm angle {_arm_joint.angle:.3f}, speed {_arm_joint.motorSpeed}, speed_real {_arm_joint.speed}")
