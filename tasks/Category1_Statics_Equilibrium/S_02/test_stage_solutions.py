#!/usr/bin/env python3
"""
Test script to verify that each stage-specific agent function passes its corresponding mutated task.
"""
import os
import sys

# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from evaluation.verifier import CodeVerifier
from tasks.Category1_Statics_Equilibrium.S_02.stages import get_s02_curriculum_stages

def read_agent_code():
    agent_path = os.path.join(os.path.dirname(__file__), 'agent.py')
    with open(agent_path, 'r', encoding='utf-8') as f:
        return f.read()

def main():
    agent_code = read_agent_code()
    stages = get_s02_curriculum_stages()
    
    task_name = "Category1_Statics_Equilibrium/S_02"
    all_success = True
    
    for stage in stages:
        stage_id = stage['stage_id']
        stage_suffix = stage_id.lower().replace('-', '_') # e.g., stage_1
        
        print(f"\n{'='*80}")
        print(f"Testing {stage_id} with build_agent_{stage_suffix}")
        print(f"{'='*80}\n")
        
        env_overrides = {
            "terrain_config": stage.get("terrain_config", {}),
            "physics_config": stage.get("physics_config", {}),
        }
        
        # Alias the stage-specific build and action functions
        modified_code = agent_code
        modified_code += f"\nbuild_agent = build_agent_{stage_suffix}"
        modified_code += f"\nagent_action = agent_action_{stage_suffix}"
        
        verifier = CodeVerifier(
            task_name=task_name,
            max_steps=10000,
            env_overrides=env_overrides
        )
        
        success, score, metrics, error = verifier.verify_code(
            code=modified_code,
            headless=True
        )
        
        print(f"Result for {stage_id}: Success={success}, Score={score}")
        if not success:
            all_success = False
            if metrics:
                print(f"Failure Reason: {metrics.get('failure_reason')}")
            if error:
                print(f"Error: {error}")
        else:
            print(f"✅ PASSED {stage_id}")

    return all_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
