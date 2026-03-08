#!/usr/bin/env python3
import os
import sys

# Add root directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from evaluation.verifier import CodeVerifier
from tasks.Category1_Statics_Equilibrium.S_01.stages import get_s01_curriculum_stages

def main():
    agent_path = os.path.join(os.path.dirname(__file__), 'agent.py')
    with open(agent_path, 'r') as f:
        code = f.read()
    
    # Replace build_agent with build_agent_stage_1
    code = code.replace('def build_agent(', 'def build_agent_original(')
    code = code.replace('def build_agent_stage_1(', 'def build_agent(')
    
    stages = get_s01_curriculum_stages()
    stage_1 = stages[0]
    
    env_overrides = {
        "terrain_config": stage_1.get("terrain_config", {}),
        "physics_config": stage_1.get("physics_config", {}),
    }
    
    verifier = CodeVerifier(
        task_name="Category1_Statics_Equilibrium/S_01",
        max_steps=10000,
        env_overrides=env_overrides
    )
    
    success, score, metrics, error = verifier.verify_code(
        code=code, 
        headless=True,
        save_gif_path=os.path.join(os.path.dirname(__file__), 'stage_1_solution_success.gif')
    )
    
    print(f"Stage 1 Result: Success={success}, Score={score}")
    if error:
        print(f"Error: {error}")
    if metrics:
        print(f"Failure Reason: {metrics.get('failure_reason')}")
        print(f"Vehicle reached target: {metrics.get('vehicle_reached_target')}")

if __name__ == "__main__":
    main()
