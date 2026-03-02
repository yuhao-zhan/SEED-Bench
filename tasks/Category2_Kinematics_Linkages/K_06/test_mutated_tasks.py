#!/usr/bin/env python3
"""
Test script to verify how well the reference agent.py performs on mutated tasks.
Tests the reference solution against all curriculum stages defined in stages.py.
Expected: reference solution should FAIL on all mutated stages (original solution cannot adapt).
"""
import os
import sys
import importlib.util

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from evaluation.verifier import CodeVerifier

stages_path = os.path.join(os.path.dirname(__file__), 'stages.py')
spec = importlib.util.spec_from_file_location("stages", stages_path)
stages_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stages_mod)
get_k06_curriculum_stages = stages_mod.get_k06_curriculum_stages


def read_reference_solution():
    """Read the reference solution from K_06 agent.py"""
    agent_path = os.path.join(os.path.dirname(__file__), 'agent.py')
    with open(agent_path, 'r', encoding='utf-8') as f:
        return f.read()


def test_stage_with_reference_solution(stage_config, reference_code):
    """Test a mutated stage with the reference solution"""
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

    # K_06 base task uses 150000 steps for ref agent to reach 100%
    task_name = "Category2_Kinematics_Linkages/K_06"
    verifier = CodeVerifier(
        task_name=task_name,
        max_steps=150000,
        env_overrides=env_overrides
    )

    print("Running simulation with reference solution...")
    success, score, metrics, error = verifier.verify_code(
        code=reference_code,
        headless=True,
        save_gif_path=None
    )

    print(f"\nResults:")
    print(f"  Success: {success}")
    print(f"  Score: {score:.2f}/100")
    if error:
        print(f"  Error: {error}")

    if metrics:
        print(f"\nKey metrics:")
        for key in ['failed', 'failure_reason', 'current_particle_count', 'initial_particle_count',
                    'cleaning_percentage', 'residual_percentage', 'structure_mass', 'max_structure_mass']:
            if key in metrics:
                print(f"  {key}: {metrics[key]}")

    return success, score, metrics, error


def main():
    """Main test function"""
    print("="*80)
    print("K-06: Testing Reference Solution on Mutated Tasks")
    print("="*80)

    print("\nReading reference solution from agent.py...")
    reference_code = read_reference_solution()
    print(f"Reference solution code length: {len(reference_code)} characters")

    stages = get_k06_curriculum_stages()
    print(f"\nFound {len(stages)} mutated stages to test")

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
    for result in results:
        if result['success']:
            passed_stages.append(result)
            print(f"  {result['stage_id']} ({result['title']}): PASSED with score {result['score']:.2f}")
        else:
            print(f"  {result['stage_id']} ({result['title']}): FAILED with score {result['score']:.2f}")
            if result.get('error'):
                print(f"     Error: {result['error'][:120]}...")
            if result.get('metrics', {}).get('failure_reason'):
                print(f"     Reason: {result['metrics']['failure_reason']}")
            m = result.get('metrics', {})
            if m.get('current_particle_count') is not None:
                print(f"     Particles left: {m['current_particle_count']}/{m.get('initial_particle_count', '?')}")

    print(f"\nTotal: {len(passed_stages)}/{len(results)} stages passed")
    print(f"Pass rate: {len(passed_stages)/len(results)*100:.1f}%")

    if len(passed_stages) == 0:
        print("\nExpected result: All mutated tasks failed (original solution cannot adapt).")
    else:
        print(f"\nWarning: {len(passed_stages)} mutated task(s) passed. Consider making mutations more challenging.")

    return len(passed_stages), len(results)


if __name__ == "__main__":
    passed, total = main()
    print(f"\n{'='*80}")
    print(f"Final Result: {passed}/{total} mutated tasks passed")
    print(f"{'='*80}\n")
    sys.exit(0 if passed == 0 else 1)
