#!/usr/bin/env python3
"""
Test script to verify how well the reference solution (agent.py) performs on mutated tasks.
Uses TaskRunner with env_overrides from each stage.
Reference solution should PASS on base (no mutation) and FAIL on all mutated stages.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from main import TaskRunner
from tasks.Category6_ExoticPhysics.E_02.stages import get_e02_curriculum_stages


def test_stage_with_reference_solution(stage_config, task_name="Category6_ExoticPhysics.E_02"):
    """Test a stage with the reference agent (agent_action from agent.py)."""
    stage_id = stage_config.get("stage_id", "base")
    title = stage_config.get("title", "Base (no mutation)")
    mutation_description = stage_config.get("mutation_description", "N/A")

    print(f"\n{'='*80}")
    print(f"Testing {stage_id}: {title}")
    print(f"Mutation: {mutation_description}")
    print(f"{'='*80}\n")

    env_overrides = {
        "terrain_config": stage_config.get("terrain_config", {}),
        "physics_config": stage_config.get("physics_config", {}),
    }

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
    """Run reference solution on base and all mutated stages."""
    print("=" * 80)
    print("Testing Reference Solution on E-02 Base + Mutated Tasks")
    print("Expected: PASS on base, FAIL on all mutated stages (Stage-1 to Stage-4)")
    print("=" * 80)

    # Base (no mutation)
    base_config = {
        "stage_id": "base",
        "title": "Base (no mutation)",
        "mutation_description": "Default physics",
        "terrain_config": {},
        "physics_config": {},
    }
    success, score, metrics, failure_reason = test_stage_with_reference_solution(base_config)
    results = [{
        "stage_id": "base",
        "title": base_config["title"],
        "success": success,
        "score": score,
        "metrics": metrics,
        "failure_reason": failure_reason,
    }]

    stages = get_e02_curriculum_stages()
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

    base_result = results[0]
    if base_result["success"]:
        print(f"✅ base (no mutation): PASSED (score {base_result['score']:.2f}) - as expected")
    else:
        print(f"⚠️  base (no mutation): FAILED (score {base_result['score']:.2f}) - reference should pass base!")

    mutated_passed = 0
    for r in results[1:]:
        if r["success"]:
            print(f"⚠️  {r['stage_id']} ({r['title']}): PASSED (score {r['score']:.2f}) - need to make harder!")
            mutated_passed += 1
        else:
            print(f"✅ {r['stage_id']} ({r['title']}): FAILED (score {r['score']:.2f}) - as expected")
            if r["failure_reason"]:
                print(f"   Reason: {r['failure_reason']}")

    print(f"\nBase: {'PASS' if base_result['success'] else 'FAIL'}")
    print(f"Mutated: {mutated_passed}/{len(results)-1} passed (ideal: 0)")

    return mutated_passed, len(results) - 1


if __name__ == "__main__":
    passed, total = main()
    print(f"\n{'='*80}\n")
    sys.exit(0 if passed == 0 else 1)
