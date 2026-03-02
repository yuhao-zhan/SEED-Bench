#!/usr/bin/env python3
"""
Test script to verify how well the reference solution (agent.py) performs on mutated tasks.
Uses TaskRunner with env_overrides from each stage.
Reference solution should FAIL on all mutated stages (environment adaptability test).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from main import TaskRunner
from tasks.Category6_ExoticPhysics.E_01.stages import get_e01_curriculum_stages


def test_stage_with_reference_solution(stage_config):
    """Test a mutated stage with the reference agent (build_agent from agent.py)."""
    stage_id = stage_config["stage_id"]
    title = stage_config["title"]
    mutation_description = stage_config["mutation_description"]

    print(f"\n{'='*80}")
    print(f"Testing {stage_id}: {title}")
    print(f"Mutation: {mutation_description}")
    print(f"{'='*80}\n")

    env_overrides = {
        "terrain_config": stage_config.get("terrain_config", {}),
        "physics_config": stage_config.get("physics_config", {}),
    }

    task_name = "Category6_ExoticPhysics.E_01"
    task_module = __import__(f"tasks.{task_name}", fromlist=["environment", "evaluator", "agent", "renderer"])
    runner = TaskRunner(task_name, task_module)

    # Extended steps: 1200 (~20s) for negative damping stages to allow instability to develop
    max_steps = 1200
    result = runner.run(headless=True, max_steps=max_steps, save_gif=False, env_overrides=env_overrides)

    if result is None:
        return False, 0.0, {}, "Build agent failed"

    score, metrics = result
    success = metrics.get("success", False)
    failed = metrics.get("failed", False)
    failure_reason = metrics.get("failure_reason", "")

    return success, score, metrics, failure_reason


def main():
    """Run reference solution on all mutated stages."""
    print("=" * 80)
    print("Testing Reference Solution on E-01 Mutated Tasks")
    print("Expected: reference solution should FAIL on all mutated stages")
    print("=" * 80)

    stages = get_e01_curriculum_stages()
    results = []

    for stage in stages:
        success, score, metrics, failure_reason = test_stage_with_reference_solution(stage)
        results.append({
            "stage_id": stage["stage_id"],
            "title": stage["title"],
            "success": success,
            "score": score,
            "metrics": metrics,
            "failure_reason": failure_reason,
        })

    # Summary
    print(f"\n{'='*80}")
    print("Summary")
    print(f"{'='*80}\n")

    passed = sum(1 for r in results if r["success"])
    failed_count = sum(1 for r in results if not r["success"])

    for r in results:
        if r["success"]:
            print(f"⚠️  {r['stage_id']} ({r['title']}): PASSED (score {r['score']:.2f}) - need to make harder!")
        else:
            print(f"✅ {r['stage_id']} ({r['title']}): FAILED (score {r['score']:.2f}) - as expected")
            if r["failure_reason"]:
                print(f"   Reason: {r['failure_reason']}")

    print(f"\nTotal: {passed}/{len(results)} passed, {failed_count}/{len(results)} failed")
    print("Ideal: 0 passed (reference should fail on all mutated stages)")

    return passed, len(results)


if __name__ == "__main__":
    passed, total = main()
    print(f"\n{'='*80}\n")
    sys.exit(0 if passed == 0 else 1)
