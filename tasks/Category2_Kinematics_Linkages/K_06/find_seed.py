#!/usr/bin/env python3
"""Try different particle seeds to find one where ref agent clears 100%."""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))
from main import TaskRunner

def main():
    task_name = "Category2_Kinematics_Linkages.K_06"
    task_module = __import__(f'tasks.{task_name}', fromlist=['environment', 'evaluator', 'agent', 'renderer'])
    max_steps = 60000  # faster per run
    for seed in range(0, 60):
        runner = TaskRunner(task_name, task_module)
        overrides = {"terrain_config": {"particles": {"seed": seed, "count": 45}}}
        result = runner.run(headless=True, max_steps=max_steps, save_gif=False, env_overrides=overrides)
        if result is None:
            print(f"Seed {seed}: build failed")
            continue
        score, metrics = result
        n_rem = metrics.get('current_particle_count', 45)
        residual = metrics.get('residual_percentage', 100)
        if n_rem == 0:
            print(f"Seed {seed}: SUCCESS 0 particles left")
            return seed
        print(f"Seed {seed}: {n_rem} left ({residual:.1f}%)")
    print("No seed found with 0 particles in 0..59")
    return None

if __name__ == "__main__":
    main()
