import os
import sys

# Add the root directory to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from main import TaskRunner
import tasks.Category4_Granular_FluidInteraction.F_06.agent as agent
from tasks.Category4_Granular_FluidInteraction.F_06.stages import get_f06_curriculum_stages

def main():
    task_name = "Category4_Granular_FluidInteraction.F_06"
    task_module = __import__(
        f"tasks.{task_name.replace('/', '.')}",
        fromlist=["environment", "evaluator", "agent", "renderer"],
    )
    
    stages = get_f06_curriculum_stages()
    stage_config = stages[3] # Stage 4
    
    env_overrides = {
        'terrain_config': stage_config.get('terrain_config', {}),
        'physics_config': stage_config.get('physics_config', {})
    }
    
    # Manually set the stage functions
    task_module.agent.build_agent = task_module.agent.build_agent_stage_4
    task_module.agent.agent_action = task_module.agent.agent_action_stage_4
    
    runner = TaskRunner(task_name, task_module)
    result = runner.run(headless=True, max_steps=2400, save_gif=False, env_overrides=env_overrides)
    
    if result:
        score, metrics = result
        print(f"Score: {score}")
        print(f"Metrics: {metrics}")
    else:
        print("No result returned")

if __name__ == "__main__":
    main()
