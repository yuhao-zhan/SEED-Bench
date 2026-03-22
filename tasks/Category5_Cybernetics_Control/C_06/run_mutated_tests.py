#!/usr/bin/env python3
"""
Run the per-stage reference solution across C_06 curriculum stages.

Passes curriculum_stage_id to main.run_task so each Stage-N uses
build_agent_stage_N / agent_action_stage_N with matching physics_config.
"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from main import run_task
from evaluation.utils import get_max_steps_for_task
from stages import get_c06_curriculum_stages


def run_all_stages():
    stages = get_c06_curriculum_stages()
    task_name = "Category5_Cybernetics_Control.C_06"
    # Slash form so utils maps to category_5_06 → 15000 (dot form falls through to 10k)
    max_steps = get_max_steps_for_task("Category5_Cybernetics_Control/C_06")
    print("Running per-stage reference solutions across C_06 mutated stages\n")

    for st in stages:
        sid = st.get("stage_id")
        title = st.get("title")
        phys = st.get("physics_config") or {}
        terr = st.get("terrain_config") or {}
        print("=" * 60)
        print(f"Stage: {sid} - {title}")
        print("Starting run...")
        start = time.time()
        result = run_task(
            task_name,
            headless=True,
            max_steps=max_steps,
            save_gif=False,
            env_overrides={
                "physics_config": phys,
                "terrain_config": terr,
            },
            curriculum_stage_id=sid,
        )
        elapsed = time.time() - start
        if result:
            score, metrics = result
            print(
                f"-> Score: {score:.2f}, success: {metrics.get('success', False)}, "
                f"final_wheel_omega: {metrics.get('wheel_angular_velocity', 0):.3f}"
            )
            if metrics.get("failed"):
                print(
                    f"   Failure reason: {metrics.get('failure_reason', 'Unknown')}"
                )
        else:
            print("-> No result returned (agent may have failed to build)")
        print(f"Elapsed: {elapsed:.1f}s")
        print("\n")


if __name__ == "__main__":
    run_all_stages()
