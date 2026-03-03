#!/usr/bin/env python3
"""
Test script to verify how well the current agent.py performs on mutated tasks.
Tests the agent code against all curriculum stages defined in stages.py.
"""
import os
import sys

# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from evaluation.verifier import CodeVerifier
# Import stages - handle directory name with hyphen
import sys
import os
stages_path = os.path.join(os.path.dirname(__file__), 'stages.py')
import importlib.util
spec = importlib.util.spec_from_file_location("stages", stages_path)
stages_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stages_mod)
get_s06_curriculum_stages = stages_mod.get_s06_curriculum_stages


def read_reference_solution():
    """Read the reference solution from S-06 agent.py"""
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
    
    # Prepare environment overrides
    env_overrides = {
        "terrain_config": stage_config.get("terrain_config", {}),
        "physics_config": stage_config.get("physics_config", {}),
    }
    
    print(f"Environment config:")
    print(f"  Terrain config: {env_overrides['terrain_config']}")
    print(f"  Physics config: {env_overrides['physics_config']}")
    print()
    
    # Create verifier with environment overrides
    # Use path format for task name
    task_name = "Category1_Statics_Equilibrium/S_06"
    verifier = CodeVerifier(
        task_name=task_name,
        max_steps=10000,  # 10s stability check at 60fps = 600 steps, but need more for settling
        env_overrides=env_overrides
    )
    
    # Test the reference code
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
    
    # Print key metrics
    if metrics:
        print(f"\nKey metrics:")
        for key in ['failed', 'failure_reason', 'max_x_position', 'target_overhang', 
                   'stable_duration', 'target_stability_time', 'stability_ok', 'overhang_ok',
                   'structure_mass', 'block_count', 'center_of_mass_x', 'total_kinetic_energy']:
            if key in metrics:
                print(f"  {key}: {metrics[key]}")
    
    return success, score, metrics, error


def main():
    """Main test function"""
    print("="*80)
    print("Testing Reference Solution on Mutated Tasks")
    print("="*80)
    
    # Read reference solution
    print("\nReading reference solution from agent.py...")
    reference_code = read_reference_solution()
    print(f"Reference solution code length: {len(reference_code)} characters")
    
    # Get all stages
    stages = get_s06_curriculum_stages()
    print(f"\nFound {len(stages)} mutated stages to test")
    
    # Test each stage
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
    
    # Print summary
    print(f"\n{'='*80}")
    print("Summary")
    print(f"{'='*80}\n")
    
    passed_stages = []
    failed_stages = []
    
    for result in results:
        if result['success']:
            passed_stages.append(result)
            print(f"✅ {result['stage_id']} ({result['title']}): PASSED with score {result['score']:.2f}")
        else:
            failed_stages.append(result)
            print(f"❌ {result['stage_id']} ({result['title']}): FAILED with score {result['score']:.2f}")
            if result.get('error'):
                print(f"   Error: {result['error'][:100]}...")
            if result.get('metrics', {}).get('failure_reason'):
                print(f"   Reason: {result['metrics']['failure_reason']}")
            # Print why it failed
            metrics = result.get('metrics', {})
            if not metrics.get('stability_ok', True):
                print(f"   → Structure not stable: {metrics.get('stable_duration', 0):.2f}s / {metrics.get('target_stability_time', 10):.1f}s")
            if not metrics.get('overhang_ok', True):
                print(f"   → Overhang insufficient: {metrics.get('max_x_position', 0):.2f}m < {metrics.get('target_overhang', 0.1):.2f}m")
    
    print(f"\nTotal: {len(passed_stages)}/{len(results)} stages passed")
    print(f"Pass rate: {len(passed_stages)/len(results)*100:.1f}%")
    
    # Expected: All should fail (original solution should not work in mutated environments)
    if len(passed_stages) == 0:
        print("\n✅ Expected result: All mutated tasks failed (original solution cannot adapt)")
    else:
        print(f"\n⚠️  Warning: {len(passed_stages)} mutated task(s) passed. Consider making mutations more challenging.")
    
    return len(passed_stages), len(results)


if __name__ == "__main__":
    passed, total = main()
    print(f"\n{'='*80}")
    print(f"Final Result: {passed}/{total} mutated tasks passed")
    print(f"{'='*80}\n")
    # Exit with 0 if all failed (expected), 1 if any passed (unexpected)
    sys.exit(0 if passed == 0 else 1)
