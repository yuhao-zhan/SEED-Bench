#!/usr/bin/env python3
"""
Test D_05 reference solution (agent.py) on baseline and each mutated stage.
Expect: baseline passes (100); Stage-1..Stage-4 should fail (score 0 or low).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from main import TaskRunner


def get_stage_overrides(stage):
    return {
        "terrain_config": stage.get("terrain_config", {}) or {},
        "physics_config": stage.get("physics_config", {}) or {},
    }


def main():
    task_name = "Category3_Dynamics_Energy.D_05"
    task_module = __import__(
        f"tasks.{task_name}",
        fromlist=["environment", "evaluator", "agent", "renderer", "stages"],
    )
    stages_mod = getattr(task_module, "stages", None)
    if not stages_mod:
        print("No stages module")
        return
    curriculum = getattr(stages_mod, "get_d05_curriculum_stages", None)
    if not curriculum:
        print("No get_d05_curriculum_stages")
        return
    stages_list = curriculum()
    runner = TaskRunner(task_name, task_module)
    max_steps = 10000

    # Baseline (no override)
    print("=" * 60)
    print("Baseline (no env override)")
    print("=" * 60)
    result = runner.run(headless=True, max_steps=max_steps, save_gif=False, env_overrides=None)
    if result:
        score, metrics = result
        print(f"Score: {score:.2f}  Success: {metrics.get('success', False)}  Failed: {metrics.get('failed', False)}")
        if metrics.get("failure_reason"):
            print(f"Failure: {metrics['failure_reason']}")
        if metrics.get("shell_broken") is not None:
            print(f"Shell broken: {metrics['shell_broken']}")
    else:
        print("No result (build_agent may have raised)")
    print()

    for stage in stages_list:
        stage_id = stage.get("stage_id", "?")
        title = stage.get("title", "?")
        overrides = get_stage_overrides(stage)
        print("=" * 60)
        print(f"{stage_id}: {title}")
        print("=" * 60)
        result = runner.run(
            headless=True,
            max_steps=max_steps,
            save_gif=False,
            env_overrides=overrides,
        )
        if result:
            score, metrics = result
            print(f"Score: {score:.2f}  Success: {metrics.get('success', False)}  Failed: {metrics.get('failed', False)}")
            if metrics.get("failure_reason"):
                print(f"Failure: {metrics['failure_reason']}")
            if metrics.get("shell_broken") is not None:
                print(f"Shell broken: {metrics['shell_broken']}")
        else:
            print("No result (build_agent may have raised)")
        print()

    print("Done. Reference solution should pass baseline and fail all mutated stages.")


if __name__ == "__main__":
    main()
