#!/usr/bin/env python3
"""
Run C_02 reference agent on each mutated stage.
Expect reference solution to FAIL on all mutated stages (environment changes break the original controller).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from main import TaskRunner

# Load stages from same task directory
_task_dir = os.path.dirname(os.path.abspath(__file__))
_stages_module = __import__("tasks.Category5_Cybernetics_Control.C_02.stages", fromlist=["get_c02_curriculum_stages"])
get_c02_curriculum_stages = _stages_module.get_c02_curriculum_stages


def main():
    task_name = "Category5_Cybernetics_Control.C_02"
    max_steps = 10000

    task_module = __import__(
        f"tasks.{task_name}",
        fromlist=["environment", "evaluator", "agent", "renderer"],
    )

    stages = get_c02_curriculum_stages()
    results = []

    for stage in stages:
        stage_id = stage["stage_id"]
        title = stage.get("title", stage_id)
        env_overrides = {
            "terrain_config": dict(stage.get("terrain_config", {}) or {}),
            "physics_config": dict(stage.get("physics_config", {}) or {}),
        }

        print("=" * 60)
        print(f"Testing {stage_id}: {title}")
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
            results.append((stage_id, success, score, metrics.get("failure_reason"), None))
            print(f"  Score: {score:.2f}, Success: {success}")
            if metrics.get("failure_reason"):
                print(f"  Failure: {metrics['failure_reason']}")
        else:
            results.append((stage_id, False, 0.0, None, "No result (build_agent may have failed)"))
            print("  No result returned")

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    all_failed = all(not r[1] for r in results)
    for stage_id, success, score, reason, err in results:
        status = "PASS" if success else "FAIL"
        print(f"  {stage_id}: {status} (score={score:.2f})")
        if reason:
            print(f"    -> {reason[:80]}...")
    if all_failed:
        print("\nReference solution failed on all mutated stages (expected).")
        return 0
    else:
        passed = [r[0] for r in results if r[1]]
        print(f"\nWARNING: Reference solution PASSED on: {passed}")
        print("Strengthen those stage mutations so the original controller fails.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
