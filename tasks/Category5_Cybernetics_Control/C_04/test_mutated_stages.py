#!/usr/bin/env python3
"""
Test C-04 reference solution on all mutated stages.
Expect failures on mutated tasks (original solution tuned for baseline).
"""
import os
import sys
import importlib.util

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from main import TaskRunner


def main():
    task_name = "Category5_Cybernetics_Control.C_04"
    task_module = __import__(
        f"tasks.{task_name}",
        fromlist=["environment", "evaluator", "agent", "renderer", "stages"],
    )
    stages_mod = getattr(task_module, "stages", None)
    if not stages_mod:
        print("No stages module")
        return
    curriculum = getattr(stages_mod, "get_c04_curriculum_stages", None)
    if not curriculum:
        print("No get_c04_curriculum_stages")
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
    else:
        print("No result (build_agent may have raised)")
    print()

    results = []
    for stage in stages_list:
        stage_id = stage.get("stage_id", "?")
        env_overrides = {
            "terrain_config": stage.get("terrain_config", {}) or {},
            "physics_config": stage.get("physics_config", {}) or {},
        }
        print("=" * 60)
        print(f"Mutated: {stage_id} — {stage.get('title', stage_id)}")
        print("=" * 60)
        runner = TaskRunner(task_name, task_module)
        result = runner.run(
            headless=True,
            max_steps=max_steps,
            save_gif=False,
            env_overrides=env_overrides,
        )
        if result:
            score, metrics = result
            success = metrics.get("success", False)
            results.append((stage_id, score, success, metrics.get("failure_reason")))
            print(f"Score: {score:.1f}  Success: {success}")
            if metrics.get("failed") and metrics.get("failure_reason"):
                print(f"Failure: {metrics['failure_reason']}")
        else:
            results.append((stage_id, None, False, "No result"))
            print("No result returned")
        print()

    print("=" * 60)
    print("Summary: reference solution on mutated tasks")
    print("=" * 60)
    for stage_id, score, success, reason in results:
        status = "PASS" if success else "FAIL"
        sc = f"{score:.1f}" if score is not None else "N/A"
        print(f"  {stage_id}: {status} (score={sc}) {reason or ''}")


if __name__ == "__main__":
    main()
