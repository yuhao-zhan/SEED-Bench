#!/usr/bin/env python3
import sys
import os
import shutil

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from main import TaskRunner
from tasks.Category4_Granular_FluidInteraction.F_04.stages import get_f04_curriculum_stages
from evaluation.evaluate_cross_mutated import get_reference_solution

def generate_gifs():
    task_name = "Category4_Granular_FluidInteraction.F_04"
    agent_file = os.path.join(os.path.dirname(__file__), "agent.py")
    backup_file = agent_file + ".bak"
    
    shutil.copy(agent_file, backup_file)
    
    stages_config = get_f04_curriculum_stages()
    
    try:
        for stage in stages_config:
            shutil.copy(backup_file, agent_file)
            stage_id = stage['stage_id']
            print(f"Generating GIF for {stage_id}...")
            
            code = get_reference_solution("Category4_Granular_FluidInteraction/F_04", stage_id)
            with open(agent_file, "w") as f:
                f.write(code)
            
            # Reload module
            task_module = __import__(f"tasks.{task_name}", fromlist=["environment", "evaluator", "agent", "renderer"])
            import importlib
            importlib.reload(task_module.agent)
            
            runner = TaskRunner(task_name, task_module)
            env_overrides = {
                "terrain_config": stage.get("terrain_config", {}),
                "physics_config": stage.get("physics_config", {})
            }
            
            runner.run(headless=True, max_steps=10000, save_gif=True, env_overrides=env_overrides)
            
            # The GIF is saved as reference_solution_success.gif or reference_solution_fail.gif in the current dir
            if os.path.exists("reference_solution_success.gif"):
                os.rename("reference_solution_success.gif", f"tasks/Category4_Granular_FluidInteraction/F_04/stage_{stage_id}_solution_success.gif")
                print(f"Saved stage_{stage_id}_solution_success.gif")
            elif os.path.exists("reference_solution_fail.gif"):
                os.rename("reference_solution_fail.gif", f"tasks/Category4_Granular_FluidInteraction/F_04/stage_{stage_id}_solution_fail.gif")
                print(f"Failed to generate success GIF for {stage_id}, saved fail GIF instead.")
            
    finally:
        shutil.move(backup_file, agent_file)

if __name__ == "__main__":
    generate_gifs()
