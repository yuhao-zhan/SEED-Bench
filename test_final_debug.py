import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from tasks.Category4_Granular_FluidInteraction.F_03.environment import Sandbox
from tasks.Category4_Granular_FluidInteraction.F_03.agent import build_agent, agent_action

sandbox = Sandbox()
agent_body = build_agent(sandbox)

for step in range(1200):
    agent_action(sandbox, agent_body, step)
    sandbox.step(1/60.0)
    
    if step % 60 == 0:
        count = 0
        for p in sandbox._particles:
            x, y = p.position.x, p.position.y
            if -6.0 <= x <= -4.0 and 2.0 <= y <= 4.0:
                count += 1
        print(f"t={step/60.0:.1f}s, hopper_count={sandbox.get_particles_in_hopper_count()}, manual_count={count}")
        if count > 0:
            print(f"   Particle 0: {sandbox._particles[0].position}")

