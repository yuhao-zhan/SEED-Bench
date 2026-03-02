#!/usr/bin/env python3
"""
Run reference solution on baseline and on each mutated stage for F-06.
Expect: baseline passes; Stage-1..Stage-4 all fail (original solution should not pass in new environments).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from main import TaskRunner


def run_one(task_name, task_module, env_overrides=None, label="Baseline"):
    overrides = env_overrides or {}
    runner = TaskRunner(task_name, task_module)
    result = runner.run(headless=True, max_steps=10000, save_gif=False, env_overrides=overrides)
    if result is None:
        return None, f"{label}: build/run error (no result)"
    score, metrics = result
    success = metrics.get("success", False)
    failed = metrics.get("failed", False)
    reason = metrics.get("failure_reason", "")
    return (score, success, failed, reason), None


def main():
    task_name = "Category4_Granular_FluidInteraction.F_06"
    task_module = __import__(
        f"tasks.{task_name.replace('/', '.')}",
        fromlist=["environment", "evaluator", "agent", "renderer"],
    )
    stages_mod = __import__(
        f"tasks.{task_name.replace('/', '.')}.stages",
        fromlist=["get_f06_curriculum_stages"],
    )
    stages = stages_mod.get_f06_curriculum_stages()

    print("=" * 60)
    print("F-06: Reference solution on baseline and mutated stages")
    print("=" * 60)

    # Baseline (no overrides)
    res, err = run_one(task_name, task_module, None, "Baseline")
    if err:
        print(err)
        return 1
    score, success, failed, reason = res
    print(f"\nBaseline: score={score:.1f} success={success} failed={failed}")
    if reason:
        print(f"  reason: {reason}")
    if not success:
        print("  WARNING: Baseline should pass; fix initial task or ref solution.")
    baseline_ok = success

    # Mutated stages
    stage_results = []
    for s in stages:
        stage_id = s["stage_id"]
        env_overrides = {
            "terrain_config": s.get("terrain_config", {}) or {},
            "physics_config": s.get("physics_config", {}) or {},
        }
        res, err = run_one(task_name, task_module, env_overrides, stage_id)
        if err:
            print(f"\n{stage_id}: {err}")
            stage_results.append((stage_id, None, None, None, err))
            continue
        score, success, failed, reason = res
        stage_results.append((stage_id, score, success, failed, reason))
        print(f"\n{stage_id} ({s.get('title', '')}): score={score:.1f} success={success} failed={failed}")
        if reason:
            print(f"  reason: {reason}")
        if success:
            print(f"  WARNING: Ref solution passed; should fail. Strengthen mutation for {stage_id}.")

    print("\n" + "=" * 60)
    if baseline_ok and all(r[2] is False for r in stage_results if len(r) == 5 and r[1] is not None):
        print("OK: Baseline passes; all mutated stages fail with reference solution.")
    else:
        if not baseline_ok:
            print("FAIL: Baseline did not pass.")
        for r in stage_results:
            if len(r) == 5 and r[1] is not None and r[2] is True:
                print(f"FAIL: {r[0]} passed with ref solution (should fail).")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
