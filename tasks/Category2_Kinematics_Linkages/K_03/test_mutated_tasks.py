#!/usr/bin/env python3
"""
Test script to verify how well the reference agent.py performs on mutated tasks.
Tests the reference solution against all curriculum stages defined in stages.py.
Expected: baseline passes; Stage-1 through Stage-4 should fail (original solution cannot adapt).
"""
import os
import sys
import importlib.util

# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from evaluation.verifier import CodeVerifier

stages_path = os.path.join(os.path.dirname(__file__), 'stages.py')
spec = importlib.util.spec_from_file_location("stages", stages_path)
stages_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stages_mod)
get_k03_curriculum_stages = stages_mod.get_k03_curriculum_stages


def read_reference_solution():
    """Read the reference solution from K_03 agent.py"""
    agent_path = os.path.join(os.path.dirname(__file__), 'agent.py')
    with open(agent_path, 'r', encoding='utf-8') as f:
        return f.read()


def test_stage_with_reference_solution(stage_config, reference_code):
    """Test a stage with the reference solution"""
    stage_id = stage_config['stage_id']
    title = stage_config['title']
    mutation_description = stage_config['mutation_description']

    print(f"\n{'='*80}")
    print(f"Testing {stage_id}: {title}")
    print(f"Mutation: {mutation_description}")
    print(f"{'='*80}\n")

    env_overrides = {
        "terrain_config": stage_config.get("terrain_config", {}),
        "physics_config": stage_config.get("physics_config", {}),
    }

    print("Environment config:")
    print(f"  Terrain config: {env_overrides['terrain_config']}")
    print(f"  Physics config: {env_overrides['physics_config']}")
    print()

    task_name = "Category2_Kinematics_Linkages/K_03"
    verifier = CodeVerifier(
        task_name=task_name,
        max_steps=20000,  # Match test_agent.py (grasp + lift + hold)
        env_overrides=env_overrides
    )

    print("Running simulation with reference solution...")
    success, score, metrics, error = verifier.verify_code(
        code=reference_code,
        headless=True,
        save_gif_path=None
    )

    print("\nResults:")
    print(f"  Success: {success}")
    print(f"  Score: {score:.2f}/100")
    if error:
        print(f"  Error: {error}")

    if metrics:
        print("\nKey metrics:")
        for key in ['failed', 'failure_reason', 'object_y', 'target_object_y', 'height_gained',
                    'max_object_y_reached', 'object_grasped', 'object_fell',
                    'gripper_bodies_touching_object', 'steps_with_object_above_target']:
            if key in metrics:
                print(f"  {key}: {metrics[key]}")

    return success, score, metrics, error


def main():
    """Main test function"""
    print("="*80)
    print("Testing Reference Solution on K-03 Mutated Tasks")
    print("="*80)

    print("\nReading reference solution from agent.py...")
    reference_code = read_reference_solution()
    print(f"Reference solution code length: {len(reference_code)} characters")

    stages = get_k03_curriculum_stages()
    print(f"\nFound {len(stages)} stages to test (baseline + Stage-1..4)")

    results = []
    for stage in stages:
        success, score, metrics, error = test_stage_with_reference_solution(stage, reference_code)
        results.append({
            'stage_id': stage['stage_id'],
            'title': stage['title'],
            'success': success,
            'score': score,
            'metrics': metrics,
            'error': error
        })

    print(f"\n{'='*80}")
    print("Summary")
    print(f"{'='*80}\n")

    passed_stages = []
    failed_stages = []

    for result in results:
        if result['success']:
            passed_stages.append(result)
            print(f"  PASSED  {result['stage_id']} ({result['title']}): score {result['score']:.2f}")
        else:
            failed_stages.append(result)
            print(f"  FAILED  {result['stage_id']} ({result['title']}): score {result['score']:.2f}")
            if result.get('error'):
                print(f"           Error: {result['error'][:80]}...")
            if result.get('metrics', {}).get('failure_reason'):
                print(f"           Reason: {result['metrics']['failure_reason']}")

    print(f"\nTotal: {len(passed_stages)}/{len(results)} stages passed")
    if len(results) > 0:
        print(f"Pass rate: {len(passed_stages)/len(results)*100:.1f}%")

    # Expected: baseline passes; Stage-1..4 should fail
    baseline_passed = any(r['stage_id'] == 'baseline' and r['success'] for r in results)
    mutated_passed = [r for r in results if r['stage_id'] != 'baseline' and r['success']]

    if baseline_passed and len(mutated_passed) == 0:
        print("\n  Expected: baseline PASSED, all mutated tasks (Stage-1..4) FAILED.")
    elif not baseline_passed:
        print("\n  Warning: baseline did not pass; check reference solution or environment.")
    else:
        print(f"\n  Warning: {len(mutated_passed)} mutated task(s) passed. Consider making those mutations harder.")

    return results


if __name__ == "__main__":
    results = main()
    passed = sum(1 for r in results if r['success'])
    total = len(results)
    mutated_passed = [r for r in results if r['stage_id'] != 'baseline' and r['success']]
    print(f"\n{'='*80}")
    print(f"Final: {passed}/{total} stages passed")
    print(f"{'='*80}\n")
    # Exit 1 if any mutated stage (Stage-1..4) passed — should tune env so original solution fails
    sys.exit(1 if len(mutated_passed) > 0 else 0)
