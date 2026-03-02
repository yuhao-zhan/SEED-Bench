#!/usr/bin/env python3
"""Debug F-06: run sim and print particle stats every N steps."""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))
from common.simulator import TIME_STEP
from environment import Sandbox
from agent import build_agent, agent_action

def main():
    env = Sandbox()
    agent_body = build_agent(env)
    n = env.get_initial_particle_count()
    print(f"Initial particles: {n}")
    for step in range(10001):
        agent_action(env, agent_body, step)
        env.step(TIME_STEP)
        if step % 2000 == 0 or step == 10000:
            in_t = env.get_particles_in_target_count()
            lost = n - sum(1 for p in env._fluid_particles if p is not None and p.active)
            xs = [p.position.x for p in env._fluid_particles if p is not None and p.active]
            ys = [p.position.y for p in env._fluid_particles if p is not None and p.active]
            mean_x = sum(xs) / len(xs) if xs else 0
            max_x = max(xs) if xs else 0
            min_x = min(xs) if xs else 0
            in_band = sum(1 for xi, yi in zip(xs, ys) if 19.5 <= xi <= 20.5 and 4.8 <= yi <= 5.2)
            near_x = sum(1 for xi in xs if xi >= 18)
            near_ys = [yi for xi, yi in zip(xs, ys) if xi >= 18]
            print(f"step {step}: in_target={in_t} lost={lost} max_x={max_x:.2f} near_x={near_x} in_band={in_band} y_at_near={near_ys[:5]} active={len(xs)}")
    print("Done")

if __name__ == "__main__":
    main()
