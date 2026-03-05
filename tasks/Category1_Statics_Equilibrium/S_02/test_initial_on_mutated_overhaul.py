#!/usr/bin/env python3
"""
Verify that the INITIAL reference solution (build_agent) FAILS on overhauled mutated tasks.
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
    
    for stage in stages:
        stage_id = stage['stage_id']
        print(f"\nChecking INITIAL build_agent on {stage_id}...")
        
        env_overrides = {
            "terrain_config": stage.get("terrain_config", {}),
            "physics_config": stage.get("physics_config", {}),
        }
        
        verifier = CodeVerifier(
            task_name=task_name,
            max_steps=10000,
            env_overrides=env_overrides
        )
        
        # Test the code as-is (uses build_agent)
        success, score, metrics, error = verifier.verify_code(
            code=agent_code,
            headless=True
        )
        
        print(f"Result for {stage_id}: Success={success}, Score={score}")
        if not success:
            print(f"✅ Correct: Initial solution failed as expected. Reason: {metrics.get('failure_reason')}")
        else:
            print(f"❌ Error: Initial solution passed {stage_id} but it should have failed!")

if __name__ == "__main__":
    main()
