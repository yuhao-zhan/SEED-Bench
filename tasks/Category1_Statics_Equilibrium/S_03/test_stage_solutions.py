#!/usr/bin/env python3
import os
import sys
import importlib.util

# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from evaluation.verifier import CodeVerifier
from tasks.Category1_Statics_Equilibrium.S_03.stages import get_s03_curriculum_stages

def test_stage_solution(stage_config, build_func_name, action_func_name):
    stage_id = stage_config['stage_id']
    title = stage_config['title']
    
    print(f"\n{'='*80}")
    print(f"Testing {stage_id}: {title}")
    print(f"Functions: {build_func_name}, {action_func_name}")
    print(f"{'='*80}\n")
    
    env_overrides = {
        "terrain_config": stage_config.get("terrain_config", {}),
        "physics_config": stage_config.get("physics_config", {}),
    }
    
    task_name = "Category1_Statics_Equilibrium/S_03"
    verifier = CodeVerifier(
        task_name=task_name,
        max_steps=1800,
        env_overrides=env_overrides
    )
    
    # Read agent.py and append calls to the specific functions
    agent_path = os.path.join(os.path.dirname(__file__), 'agent.py')
    with open(agent_path, 'r', encoding='utf-8') as f:
        code = f.read()
    
    # We need to call the specific functions instead of the default build_agent/agent_action
    wrapper_code = f"""
{code}

def build_agent(sandbox):
    return {build_func_name}(sandbox)

def agent_action(sandbox, agent_body, step_count):
    return {action_func_name}(sandbox, agent_body, step_count)
"""
    
    success, score, metrics, error = verifier.verify_code(
        code=wrapper_code,
        headless=True,
        save_gif_path=os.path.join(os.path.dirname(__file__), f"stage_{stage_id}_success.gif")
    )
    
    print(f"\nResults for {stage_id}:")
    print(f"  Success: {success}")
    print(f"  Score: {score:.2f}/100")
    if error:
        print(f"  Error: {error}")
    if metrics and metrics.get('failure_reason'):
        print(f"  Failure Reason: {metrics['failure_reason']}")
    
    return success

def main():
    stages = get_s03_curriculum_stages()
    
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', type=int, help='Stage number to test (1-4)')
    args = parser.parse_args()
    
    if args.stage:
        stage_indices = [args.stage - 1]
    else:
        stage_indices = range(len(stages))
        
    all_success = True
    for i in stage_indices:
        stage = stages[i]
        sid = stage['stage_id'].split('-')[1]
        success = test_stage_solution(stage, f"build_agent_stage_{sid}", f"agent_action_stage_{sid}")
        if not success:
            all_success = False
            
    return all_success

if __name__ == "__main__":
    main()
