#!/usr/bin/env python3
"""
Test script for S_05 mutated tasks
Tests the reference solution against each mutated stage
"""
import os
import sys

# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from evaluation.verifier import CodeVerifier


def read_agent_code():
    """Read the reference agent code"""
    agent_path = os.path.join(os.path.dirname(__file__), 'agent.py')
    with open(agent_path, 'r', encoding='utf-8') as f:
        return f.read()


def test_stage_with_agent_code(stage_config, agent_code):
    """Test a mutated stage with the agent code"""
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
    task_name = "Category1_Statics_Equilibrium/S_05"
    verifier = CodeVerifier(
        task_name=task_name,
        max_steps=20000,  # Need enough time for all meteors
        env_overrides=env_overrides
    )
    
    # Test the agent code
    print("Running simulation with reference solution...")
    success, score, metrics, error = verifier.verify_code(
        code=agent_code,
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
        for key in ['failed', 'failure_reason', 'core_damage', 'max_core_force', 
                   'structure_stable', 'structure_mass', 'max_mass', 'meteor_count']:
            if key in metrics:
                print(f"  {key}: {metrics[key]}")
    
    return success, score, metrics, error


def main():
    """Main test function"""
    print("="*80)
    print("Testing S-05 Mutated Tasks with Reference Solution")
    print("="*80)
    
    # Import stages
    from tasks.Category1_Statics_Equilibrium.S_05.stages import get_s05_curriculum_stages
    
    stages = get_s05_curriculum_stages()
    agent_code = read_agent_code()
    
    results = []
    for stage in stages:
        success, score, metrics, error = test_stage_with_agent_code(stage, agent_code)
        results.append({
            'stage_id': stage['stage_id'],
            'title': stage['title'],
            'success': success,
            'score': score,
            'failed': metrics.get('failed', False) if metrics else False,
            'failure_reason': metrics.get('failure_reason', None) if metrics else None,
        })
    
    # Print summary
    print(f"\n{'='*80}")
    print("Summary")
    print(f"{'='*80}")
    for result in results:
        status = "✅ PASSED" if result['success'] else "❌ FAILED"
        print(f"{result['stage_id']}: {result['title']} - {status} (Score: {result['score']:.2f})")
        if result['failed'] and result['failure_reason']:
            print(f"  Failure reason: {result['failure_reason']}")
    
    # Check if all stages failed (ideal case)
    all_failed = all(not r['success'] for r in results)
    if all_failed:
        print(f"\n✅ All mutated tasks correctly fail with reference solution!")
        print("This is the expected behavior - the reference solution should not work in mutated environments.")
    else:
        print(f"\n⚠️  Some mutated tasks passed with reference solution.")
        print("Consider adjusting mutation parameters to make them more challenging.")
    
    return results


if __name__ == "__main__":
    main()
