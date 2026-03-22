#!/usr/bin/env python3
import sys
import os

# Add repo root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from evaluation.verifier import CodeVerifier
from evaluation.evaluate_cross_mutated import get_reference_solution
from evaluation.utils import get_max_steps_for_task
from tasks.Category5_Cybernetics_Control.C_06.stages import get_c06_curriculum_stages


def main():
    # Test all stages including Initial
    stages_config = get_c06_curriculum_stages()

    all_stages = [
        {
            "stage_id": "Initial",
            "title": "Initial Task",
            "terrain_config": {},
            "physics_config": {},
        }
    ] + stages_config

    task_name = "Category5_Cybernetics_Control/C_06"
    max_steps = get_max_steps_for_task(task_name)

    print(f"Testing C_06 reference solutions on their respective environments...")
    print("-" * 60)

    passed_count = 0
    total_stages = len(all_stages)

    for stage in all_stages:
        stage_id = stage["stage_id"]
        title = stage.get("title", stage_id)
        print(f"Testing {stage_id}: {title}...")

        try:
            code = get_reference_solution(task_name, stage_id)

            verifier = CodeVerifier(
                task_name=task_name,
                max_steps=max_steps,
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
            import traceback
            traceback.print_exc()

        print("-" * 60)

    print(f"\nFinal Result: {passed_count}/{total_stages} stages passed.")
    sys.exit(0 if passed_count == total_stages else 1)


if __name__ == "__main__":
    main()
