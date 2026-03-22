#!/usr/bin/env python3
import os
import sys

# Add repo root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from evaluation.verifier import CodeVerifier
from tasks.Category4_Granular_FluidInteraction.F_05 import prompt as f05_prompt
from tasks.Category4_Granular_FluidInteraction.F_05.stages import (
    get_f05_curriculum_stages,
    update_success_criteria_for_visible_changes,
    update_task_description_for_visible_changes,
)


def assert_mutated_prompt_sync(stage: dict) -> None:
    """
    Same visible prompt updates as evaluation/evaluate_mutated.py (merged terrain/physics vs empty base).
    Catches drift between physics overrides and staged prompt strings.
    """
    base = f05_prompt.TASK_PROMPT
    tc = stage.get("terrain_config") or {}
    pc = stage.get("physics_config") or {}
    desc = update_task_description_for_visible_changes(
        base["task_description"], tc, {}, pc, {}
    )
    crit = update_success_criteria_for_visible_changes(base["success_criteria"], tc, {})
    cwy = float(tc.get("cargo_water_y", 1.98))
    if cwy > 1.98 + 1e-9 and f"{cwy:.2f}" not in crit:
        raise AssertionError(
            f"{stage['stage_id']}: cargo_water_y={cwy} not reflected in success_criteria text"
        )
    jmf = tc.get("joint_max_force", float("inf"))
    if jmf is not None and float(jmf) < float("inf"):
        if "Maximum joint reaction force" not in crit:
            raise AssertionError(f"{stage['stage_id']}: joint_max_force set but criteria lack weld limit text")
    mm = float(tc.get("max_structure_mass", 60.0))
    if mm < 60.0 - 1e-9 and f"{mm:.0f}" not in crit:
        raise AssertionError(f"{stage['stage_id']}: max_structure_mass={mm} not reflected in criteria")
    if "**Beam footprint**" not in base["task_description"]:
        raise AssertionError("Baseline prompt missing beam footprint line (prompt/stages regression)")
    assert "Build zone" in desc and "Success Criteria" in crit

def read_reference_solution():
    """Read the reference solution from F_05 agent.py"""
    agent_path = os.path.join(os.path.dirname(__file__), 'agent.py')
    with open(agent_path, 'r', encoding='utf-8') as f:
        return f.read()

def main():
    print("="*80)
    print("Testing Initial Reference Solution on Mutated Tasks (F-05)")
    print("="*80)

    reference_code = read_reference_solution()
    stages = get_f05_curriculum_stages()
    
    results = []
    passed_count = 0

    for stage in stages:
        stage_id = stage['stage_id']
        title = stage['title']
        print(f"\nTesting {stage_id}: {title}...")
        assert_mutated_prompt_sync(stage)

        env_overrides = {
            "terrain_config": stage.get("terrain_config", {}),
            "physics_config": stage.get("physics_config", {}),
        }

        verifier = CodeVerifier(
            task_name="Category4_Granular_FluidInteraction/F_05",
            max_steps=10000,  # Match prompt.py / standard verifier budget for F-05
            env_overrides=env_overrides
        )

        success, score, metrics, error = verifier.verify_code(
            code=reference_code,
            headless=True
        )

        print(f"  Result: Success={success}, Score={score:.2f}")
        if error:
            print(f"  Error: {error}")
        if metrics and metrics.get('failure_reason'):
            print(f"  Reason: {metrics['failure_reason']}")

        if success:
            passed_count += 1
        
        results.append((stage_id, success, score))

    print(f"\n{'='*80}")
    print("Summary")
    print(f"{'='*80}")
    for stage_id, success, score in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{stage_id}: {status} (Score: {score:.2f})")
    
    print(f"\nTotal passed: {passed_count}/{len(stages)}")
    
    if passed_count == 0:
        print("\n✅ Confirmed: Initial reference solution fails on all mutated environments.")
    else:
        print(f"\n⚠️  Warning: {passed_count} mutated task(s) passed. Mutation might be too weak.")

    sys.exit(0 if passed_count == 0 else 1)

if __name__ == "__main__":
    main()
