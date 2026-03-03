#!/usr/bin/env python3
"""
Test script to verify each stage-specific reference solution in agent.py.
"""
import os
import sys

# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from evaluation.verifier import CodeVerifier
import importlib.util

stages_path = os.path.join(os.path.dirname(__file__), 'stages.py')
spec = importlib.util.spec_from_file_location("stages", stages_path)
stages_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stages_mod)
get_s06_curriculum_stages = stages_mod.get_s06_curriculum_stages

def read_reference_solution():
    agent_path = os.path.join(os.path.dirname(__file__), 'agent.py')
    with open(agent_path, 'r', encoding='utf-8') as f:
        return f.read()

def test_stage_solution(stage_config, reference_code):
    stage_id = stage_config['stage_id']
    stage_num = stage_id.split('-')[-1]
    
    print(f"\n{'='*80}")
    print(f"Verifying Specialized Solution for {stage_id}")
    print(f"{'='*80}\n")
    
    env_overrides = {
        "terrain_config": stage_config.get("terrain_config", {}),
        "physics_config": stage_config.get("physics_config", {}),
    }
    
    # Alias the stage function to build_agent
    stage_code = reference_code
    stage_code += f"\n\n# Alias stage-specific functions\n"
    stage_code += f"build_agent = build_agent_stage_{stage_num}\n"
    stage_code += f"agent_action = agent_action_stage_{stage_num}\n"
    
    task_name = "Category1_Statics_Equilibrium/S_06"
    verifier = CodeVerifier(
        task_name=task_name,
        max_steps=10000,
        env_overrides=env_overrides
    )
    
    success, score, metrics, error = verifier.verify_code(
        code=stage_code,
        headless=True
    )
    
    print(f"DEBUG: verify_code returned success={success}")
    
    print(f"Results for {stage_id}:")
    print(f"  Success: {success}")
    print(f"  Score: {score:.2f}")
    if error:
        print(f"  Error: {error}")
    if metrics:
        print(f"  Reason: {metrics.get('failure_reason')}")
        print(f"  Metrics: max_x={metrics.get('max_x_position'):.2f}, target={metrics.get('target_overhang'):.2f}, stable={metrics.get('stable_duration'):.1f}s")
    
    return success

def main():
    reference_code = read_reference_solution()
    stages = get_s06_curriculum_stages()
    
    all_passed = True
    for stage in stages:
        if not test_stage_solution(stage, reference_code):
            all_passed = False
            print(f"❌ {stage['stage_id']} FAILED")
        else:
            print(f"✅ {stage['stage_id']} PASSED")
            
    if all_passed:
        print("\n🎉 All specialized stage solutions verified successfully!")
    else:
        print("\nSome stage solutions failed verification.")
    
    sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    main()
