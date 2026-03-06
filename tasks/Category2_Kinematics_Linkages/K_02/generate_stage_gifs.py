
import os
import sys
import importlib.util
import re

# Add scripts directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from evaluation.verifier import CodeVerifier

# Load stages from stages.py
stages_path = os.path.join(os.path.dirname(__file__), 'stages.py')
spec = importlib.util.spec_from_file_location("stages", stages_path)
stages_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stages_mod)
stages = stages_mod.get_k02_curriculum_stages()

def get_stage_code(stage_num):
    agent_path = os.path.join(os.path.dirname(__file__), 'agent.py')
    with open(agent_path, 'r') as f:
        code = f.read()
    
    # Append the renames at the end
    rename_code = f"\n\nprint('REDEFINING build_agent to stage {stage_num}')\nbuild_agent = build_agent_stage_{stage_num}\nagent_action = agent_action_stage_{stage_num}\n"
    return code + rename_code

passed = 0
for stage in stages:
    stage_id = stage['stage_id']
    num = stage_id.split("-")[1]
    gif_path = os.path.join(os.path.dirname(__file__), f'stage_{num}_solution_success.gif')
    
    print(f"Generating GIF for {stage_id}...")
    
    env_overrides = {
        "terrain_config": stage.get("terrain_config", {}),
        "physics_config": stage.get("physics_config", {}),
    }
    
    verifier = CodeVerifier(
        task_name="Category2_Kinematics_Linkages/K_02",
        max_steps=1000, # Just enough to pass
        env_overrides=env_overrides
    )
    
    code = get_stage_code(num)
    
    success, score, metrics, error = verifier.verify_code(
        code=code,
        headless=True,
        save_gif_path=gif_path
    )
    
    print(f"Result for {stage_id}: Success={success}, Score={score}")
    if success:
        passed += 1
    else:
        print(f"Error: {error}")
        print(f"Metrics: {metrics}")
    print("-" * 50)

print(f"Total passed: {passed}/{len(stages)}")
if passed < len(stages):
    sys.exit(1)
