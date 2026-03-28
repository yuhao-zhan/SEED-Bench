#!/usr/bin/env python3
import os
import sys

# Add root directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from evaluation.verifier import CodeVerifier
from tasks.Category1_Statics_Equilibrium.S_01.stages import get_s01_curriculum_stages

def test_stage(stage_idx):
    agent_path = os.path.join(os.path.dirname(__file__), 'agent.py')
    with open(agent_path, 'r') as f:
        code = f.read()
    
    # Replace build_agent and agent_action with stage-specific ones
    code = code.replace('def build_agent(', 'def build_agent_original(')
    code = code.replace(f'def build_agent_stage_{stage_idx+1}(', 'def build_agent(')
    
    code = code.replace('def agent_action(', 'def agent_action_original(')
    code = code.replace(f'def agent_action_stage_{stage_idx+1}(', 'def agent_action(')
    
    stages = get_s01_curriculum_stages()
    stage = stages[stage_idx]
    
    env_overrides = {
        "terrain_config": stage.get("terrain_config", {}),
        "physics_config": stage.get("physics_config", {}),
    }
    
    verifier = CodeVerifier(
        task_name="Category1_Statics_Equilibrium/S_01",
        max_steps=10000,
        env_overrides=env_overrides
    )
    
    success, score, metrics, error = verifier.verify_code(code=code, headless=True)
    
    print(f"Stage {stage_idx+1} Result: Success={success}, Score={score}")
    if error:
        print(f"Error: {error}")
    return success

def main():
    all_success = True
    for i in range(4):
        success = test_stage(i)
        if not success:
            all_success = False
    
    if all_success:
        print("\nAll mutated stages passed with their respective solutions!")
        sys.exit(0)
    else:
        print("\nSome stages failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
