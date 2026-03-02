#!/usr/bin/env python3
"""
Run the reference agent across the C_06 mutated stages defined in `stages.py`.
The script uses `run_task` to execute the environment with `physics_config` overrides
provided by each stage entry and prints the resulting score/metrics.
"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from main import run_task
from stages import get_c06_curriculum_stages


def run_all_stages():
    stages = get_c06_curriculum_stages()
    task_name = "Category5_Cybernetics_Control.C_06"
    print("Running reference solution across mutated stages for C_06\n")

    for st in stages:
        sid = st.get("stage_id")
        title = st.get("title")
        phys = st.get("physics_config") or {}
        terr = st.get("terrain_config") or {}
        print("=" * 60)
        print(f"Stage: {sid} - {title}")
        print(f"Physics overrides: {phys}")
        print("Starting run...")
        start = time.time()
        # Use run_task env_overrides to pass physics/terrain configs
        result = run_task(task_name, headless=True, max_steps=10000, save_gif=False, env_overrides={
            "physics_config": phys,
            "terrain_config": terr,
        })
        elapsed = time.time() - start
        if result:
            score, metrics = result
            print(f"-> Score: {score:.2f}, success: {metrics.get('success', False)}, final_wheel_omega: {metrics.get('wheel_angular_velocity', 0):.3f}")
            if metrics.get('failed'):
                print(f"   Failure reason: {metrics.get('failure_reason', 'Unknown')}")
        else:
            print("-> No result returned (agent may have failed to build)")
        print(f"Elapsed: {elapsed:.1f}s")
        print("\n")


if __name__ == '__main__':
    run_all_stages()
