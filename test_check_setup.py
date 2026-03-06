import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from tasks.Category4_Granular_FluidInteraction.F_03.environment import Sandbox
from tasks.Category4_Granular_FluidInteraction.F_03.agent import build_agent, agent_action

sandbox = Sandbox()
scoop = build_agent(sandbox)

print(f"Scoop position: {scoop.position}")
for i, body in enumerate(sandbox._bodies):
    print(f"Body {i}: {body.position}, type: {body.type}")

