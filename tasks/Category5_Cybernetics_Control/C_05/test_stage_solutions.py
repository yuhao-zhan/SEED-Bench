#!/usr/bin/env python3
"""
Test each C_05 stage reference solution in its corresponding mutated environment.
Uses get_reference_solution + CodeVerifier so behavior matches test_reference_solutions.py.
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from evaluation.verifier import CodeVerifier
from evaluation.evaluate_cross_mutated import get_reference_solution
from tasks.Category5_Cybernetics_Control.C_05.stages import get_c05_curriculum_stages

TASK_NAME = "Category5_Cybernetics_Control/C_05"
# Must be >= C05_MAX_EPISODE_STEPS (35000 in prompt); extra headroom for slow refs
MAX_STEPS = 50000


def main():
    stages_config = get_c05_curriculum_stages()
    all_stages = [
        {
            "stage_id": "Initial",
            "title": "Initial Task",
            "terrain_config": {},
            "physics_config": {},
        }
    ] + stages_config

    print("Testing C_05 reference solutions on their respective environments...")
    print("-" * 60)

    passed_count = 0
    total_stages = len(all_stages)

    for stage in all_stages:
        stage_id = stage["stage_id"]
        title = stage.get("title", stage_id)
        print(f"Testing {stage_id}: {title}...")

        try:
            code = get_reference_solution(TASK_NAME, stage_id)
            verifier = CodeVerifier(
                task_name=TASK_NAME,
                max_steps=MAX_STEPS,
                env_overrides={
                    "terrain_config": stage.get("terrain_config", {}),
                    "physics_config": stage.get("physics_config", {}),
                },
            )
            success, score, metrics, error = verifier.verify_code(code=code, headless=True)
            print(f"  Result: Success={success}, Score={score:.2f}, Steps={metrics.get('step_count', 'unknown')}")
            if error:
                print(f"  Error: {error}")
            if success:
                passed_count += 1
            else:
                if metrics.get("failure_reason"):
                    print(f"  Reason: {metrics['failure_reason']}")
                elif not success:
                    print(f"  Note: Metrics: {metrics}")
        except Exception as e:
            print(f"  Failed to test {stage_id}: {e}")

        print("-" * 60)

    print(f"\nFinal Result: {passed_count}/{total_stages} stages passed.")
    sys.exit(0 if passed_count == total_stages else 1)


if __name__ == "__main__":
    main()
