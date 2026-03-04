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
from tasks.Category1_Statics_Equilibrium.S_01.stages import get_s01_curriculum_stages


def read_agent_code():
    """Read the current agent code"""
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
    
    # Alias the stage-specific build and action functions
    stage_suffix = stage_id.lower().replace('-', '_') # e.g., stage_1
    modified_code = agent_code
    modified_code += f"\nbuild_agent = build_agent_{stage_suffix}"
    modified_code += f"\nagent_action = agent_action_{stage_suffix}"
    
    # Create verifier with environment overrides
    task_name = "Category1_Statics_Equilibrium/S_01"
    verifier = CodeVerifier(
        task_name=task_name,
        max_steps=10000,
        env_overrides=env_overrides
    )
    
    # Save GIF path
    gif_name = f"{stage_suffix}_solution_success.gif"
    gif_path = os.path.join(os.path.dirname(__file__), gif_name)
    
    # Test the agent code
    print(f"Running simulation with agent code for {stage_id}...")
    success, score, metrics, error = verifier.verify_code(
        code=modified_code,
        headless=True,
        save_gif_path=gif_path
    )
    
    print(f"\nResults:")
    print(f"  Success: {success}")
    print(f"  Score: {score:.2f}/100")
    if error:
        print(f"  Error: {error}")
    
    if success:
        print(f"✅ Saved success GIF to: {gif_name}")
    else:
        # If failed, we might want to keep the GIF for debugging but the prompt asks for success gifs
        if os.path.exists(gif_path):
            os.remove(gif_path)
            print(f"❌ Deleted failure GIF")
    
    # Print key metrics
    if metrics:
        print(f"\nKey metrics:")
        for key in ['failed', 'failure_reason', 'vehicle_reached_target', 'vehicle_max_x', 
                   'target_x', 'structure_mass', 'max_structure_mass']:
            if key in metrics:
                print(f"  {key}: {metrics[key]}")
    
    return success, score, metrics, error


def main():
    """Main test function"""
    print("="*80)
    print("Testing Overhauled Agent Code on New High-Difficulty Mutated Tasks")
    print("="*80)
    
    # Read agent code
    print("\nReading agent code from agent.py...")
    agent_code = read_agent_code()
    
    # Get all stages
    stages = get_s01_curriculum_stages()
    print(f"\nFound {len(stages)} mutated stages to test")
    
    # Test each stage
    results = []
    for stage in stages:
        success, score, metrics, error = test_stage_with_agent_code(stage, agent_code)
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
    
    print(f"\nTotal: {len(passed_stages)}/{len(results)} stages passed")
    if len(results) > 0:
        print(f"Pass rate: {len(passed_stages)/len(results)*100:.1f}%")
    
    return len(passed_stages), len(results)


if __name__ == "__main__":
    passed, total = main()
    print(f"\n{'='*80}")
    print(f"Final Result: {passed}/{total} mutated tasks passed")
    print(f"{'='*80}\n")
    sys.exit(0 if passed == total else 1)
