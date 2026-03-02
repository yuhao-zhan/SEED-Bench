#!/usr/bin/env python3
"""Quick debug: run a few steps and print bucket + particle positions and truck count."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from tasks.Category4_Granular_FluidInteraction.F_03.environment import Sandbox
from tasks.Category4_Granular_FluidInteraction.F_03.agent import build_agent, agent_action
from common.simulator import TIME_STEP

def main():
    env = Sandbox()
    bucket = build_agent(env)
    print("Truck zone: x=[20, 24], y=[0, 1.5]")
    print("Pit: x=[3, 10], y=[0, 2.5]")
    print("Initial particles:", env.get_initial_particle_count())
    for step in range(10000):
        agent_action(env, bucket, step)
        env.step(TIME_STEP)
        if step % 1000 == 0 or step in (0, 500, 800, 2000, 4000, 5500):
            in_truck = env.get_particles_in_truck_count()
            bx, by = bucket.position.x, bucket.position.y
            xs = [p.position.x for p in env._particles if p.active][:5]
            print(f"step {step:5d}  bucket=({bx:.2f}, {by:.2f})  in_truck= {in_truck}  sample_x= {[round(x,2) for x in xs]}")
    print("Final in_truck:", env.get_particles_in_truck_count())

if __name__ == "__main__":
    main()
