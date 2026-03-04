#!/usr/bin/env python3
"""
Test script to verify each stage-specific reference solution and SAVE GIFs.
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
    print(f"Verifying and Saving GIF for {stage_id}")
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
    
    # Correct path to the task directory for saving GIFs
    task_dir = os.path.dirname(__file__)
    gif_path = os.path.join(task_dir, f"stage_{stage_num}_solution_success.gif")
    
    task_name = "Category1_Statics_Equilibrium/S_06"
    verifier = CodeVerifier(
        task_name=task_name,
        max_steps=10000,
        env_overrides=env_overrides
    )
    
    success, score, metrics, error = verifier.verify_code(
        code=stage_code,
        headless=True,
        save_gif_path=gif_path
    )
    
    print(f"Results for {stage_id}:")
    print(f"  Success: {success}")
    print(f"  Score: {score:.2f}")
    if success:
        print(f"  ✅ GIF saved to: {gif_path}")
    
    return success

def main():
    reference_code = read_reference_solution()
    stages = get_s06_curriculum_stages()
    
    for stage in stages:
        test_stage_solution(stage, reference_code)

if __name__ == "__main__":
    main()
