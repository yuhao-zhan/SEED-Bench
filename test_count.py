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
    
    in_hopper = sandbox.get_particles_in_hopper_count()
    if in_hopper > 0:
        print(f"step {step}, Particles in hopper: {in_hopper}")
    
    if step % 60 == 0:
        print(f"step {step}, scoop pos {agent_body.position.x:.2f}, {agent_body.position.y:.2f} | Angles: {sandbox._shoulder_joint.angle:.2f}, {sandbox._elbow_joint.angle:.2f}, {agent_body.angle:.2f}")

