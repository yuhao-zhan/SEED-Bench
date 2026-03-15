#!/usr/bin/env python3
"""
Test reference solutions for F_03 on each stage env (Initial + Stage-1..4).
Uses get_reference_solution + CodeVerifier so behavior matches test_reference_solutions.py.
"""
import sys
import os

# Add repo root (scripts) to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from evaluation.verifier import CodeVerifier
from evaluation.evaluate_cross_mutated import get_reference_solution, get_all_stages

# F-03: 40 s at 60 fps, same as test_reference_solutions.py MAX_STEPS_OVERRIDES["F_03"]
MAX_STEPS_F03 = 40 * 60


def main():
    task_name = "Category4_Granular_FluidInteraction/F_03"
    all_stages = get_all_stages(task_name)
    if len(all_stages) < 2:
        print("No mutated stages found for F_03")
        sys.exit(1)

    print("Starting verification of all stages (Initial + mutated)...")
    passed = 0
    total = len(all_stages)

    for stage in all_stages:
        stage_id = stage["stage_id"]
        print(f"\n--- Testing {stage_id} ---")
        try:
            code = get_reference_solution(task_name, stage_id)
            verifier = CodeVerifier(
                task_name=task_name,
                max_steps=MAX_STEPS_F03,
                env_overrides={
                    "terrain_config": stage.get("terrain_config", {}),
                    "physics_config": stage.get("physics_config", {}),
                },
            )
            success, score, metrics, error = verifier.verify_code(code=code, headless=True)
            print(f"Stage {stage_id} metrics: {metrics}")
            if success:
                print(f"Stage {stage_id} Passed!")
                passed += 1
            else:
                print(f"Stage {stage_id} FAILED: {error or metrics.get('failure_reason', 'unknown')}")
        except Exception as e:
            print(f"Stage {stage_id} ERROR: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 30)
    if passed == total:
        print("ALL STAGES VERIFIED SUCCESSFULLY")
        print("=" * 30)
        sys.exit(0)
    else:
        print(f"VERIFICATION FAILED: {passed}/{total} passed")
        print("=" * 30)
        sys.exit(1)


if __name__ == "__main__":
    main()
