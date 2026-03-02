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
from tasks.Category6_ExoticPhysics.E_03.stages import get_e03_curriculum_stages


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

    task_name = "Category6_ExoticPhysics.E_03"
    task_module = __import__(f"tasks.{task_name}", fromlist=["environment", "evaluator", "agent", "renderer"])
    runner = TaskRunner(task_name, task_module)

    result = runner.run(headless=True, max_steps=10000, save_gif=False, env_overrides=env_overrides)

    if result is None:
        return False, 0.0, {}, "Build agent failed"

    score, metrics = result
    success = metrics.get("success", False)
    failed = metrics.get("failed", False)
    failure_reason = metrics.get("failure_reason", "")

    return success, score, metrics, failure_reason


def main():
    """Run reference solution on baseline (no overrides) and all mutated stages."""
    print("=" * 80)
    print("Testing Reference Solution on E-03 Mutated Tasks")
    print("Expected: reference solution should PASS on baseline, FAIL on all mutated stages")
    print("=" * 80)

    # Baseline (no env_overrides)
    print(f"\n{'='*80}")
    print("Testing Baseline (no mutation)")
    print(f"{'='*80}\n")
    task_name = "Category6_ExoticPhysics.E_03"
    task_module = __import__(f"tasks.{task_name}", fromlist=["environment", "evaluator", "agent", "renderer"])
    runner = TaskRunner(task_name, task_module)
    result = runner.run(headless=True, max_steps=10000, save_gif=False, env_overrides=None)
    if result is None:
        baseline_success, baseline_score, baseline_metrics, baseline_reason = False, 0.0, {}, "Build agent failed"
    else:
        baseline_score, baseline_metrics = result
        baseline_success = baseline_metrics.get("success", False)
        baseline_reason = baseline_metrics.get("failure_reason", "")
    print(f"Baseline: success={baseline_success}, score={baseline_score:.1f}")

    stages = get_e03_curriculum_stages()
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

    print(f"Baseline: {'PASS' if baseline_success else 'FAIL'} (score {baseline_score:.1f})")
    if not baseline_success and baseline_reason:
        print(f"   Reason: {baseline_reason}")

    passed_mutated = sum(1 for r in results if r["success"])
    failed_mutated = sum(1 for r in results if not r["success"])

    for r in results:
        if r["success"]:
            print(f"⚠️  {r['stage_id']} ({r['title']}): PASSED (score {r['score']:.2f}) - need to make harder!")
        else:
            print(f"✅ {r['stage_id']} ({r['title']}): FAILED (score {r['score']:.2f}) - as expected")
            if r["failure_reason"]:
                print(f"   Reason: {r['failure_reason']}")

    print(f"\nMutated: {passed_mutated}/{len(results)} passed, {failed_mutated}/{len(results)} failed")
    print("Ideal: 0 passed on mutated (reference should fail on all mutated stages)")

    return passed_mutated, len(results), baseline_success


if __name__ == "__main__":
    passed, total, baseline_ok = main()
    print(f"\n{'='*80}\n")
    # Exit 0 if baseline passes and all mutated fail; else 1
    sys.exit(0 if (baseline_ok and passed == 0) else 1)
