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
    
    if step % 20 == 0:
        bx, by = agent_body.position.x, agent_body.position.y
        ba = agent_body.angle
        in_hopper = sandbox.get_particles_in_hopper_count()
        print(f"step {step} pos ({bx:.2f}, {by:.2f}), ba {ba:.2f}, in_hopper {in_hopper}")

