#!/usr/bin/env python3
"""
Test script to verify that the reference solution fails on mutated tasks.
If a mutated task still passes with the original solution, we need to adjust the environment parameters.
"""
import os
import sys
import importlib.util

# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from evaluation.verifier import CodeVerifier
from tasks.Category1_Statics_Equilibrium.S_03.stages import get_s03_curriculum_stages


def read_agent_code():
    """Read the reference agent code"""
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
    task_name = "Category1_Statics_Equilibrium/S_03"
    verifier = CodeVerifier(
        task_name=task_name,
        max_steps=15000,  # Need enough steps: 5s load attach + 10s hold = 15s = 900 steps at 60fps
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
        for key in ['failed', 'failure_reason', 'max_reach', 'target_reach', 'load_hold_time', 'load2_hold_time',
                   'anchor_broken', 'peak_joint_torque', 'max_anchor_torque_limit', 'structure_mass']:
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
    reference_code = read_agent_code()
    print(f"Reference code length: {len(reference_code)} characters")
    
    # Get all stages
    stages = get_s03_curriculum_stages()
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
            print(f"❌ {result['stage_id']} ({result['title']}): PASSED with score {result['score']:.2f}")
            print(f"   ⚠️  WARNING: Original solution still works! Need to adjust environment parameters.")
        else:
            failed_stages.append(result)
            print(f"✅ {result['stage_id']} ({result['title']}): FAILED with score {result['score']:.2f}")
            if result.get('error'):
                print(f"   Error: {result['error'][:100]}...")
            if result.get('metrics', {}).get('failure_reason'):
                print(f"   Reason: {result['metrics']['failure_reason']}")
    
    print(f"\nTotal: {len(passed_stages)} passed (need adjustment), {len(failed_stages)} failed (as expected)")
    
    # If any stages passed, provide guidance
    if passed_stages:
        print(f"\n{'='*80}")
        print("⚠️  ACTION REQUIRED: The following stages need environment parameter adjustments:")
        print(f"{'='*80}\n")
        for result in passed_stages:
            stage_idx = int(result['stage_id'].split('-')[1]) - 1
            stage_config = stages[stage_idx]
            print(f"{result['stage_id']}: {result['title']}")
            print(f"  Current terrain_config: {stage_config.get('terrain_config', {})}")
            print(f"  Current physics_config: {stage_config.get('physics_config', {})}")
            print(f"  Suggestion: Increase difficulty parameters (load_mass, target_reach, reduce max_anchor_torque, increase gravity, etc.)")
            print()
    
    return len(passed_stages) == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
