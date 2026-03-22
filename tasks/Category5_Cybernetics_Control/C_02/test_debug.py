import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from main import TaskRunner
from tasks.Category5_Cybernetics_Control.C_02 import environment, evaluator, agent, renderer, stages

def debug_stage_2():
    task_name = "Category5_Cybernetics_Control.C_02"
    task_module = sys.modules["tasks.Category5_Cybernetics_Control.C_02"]
    
    stages_list = stages.get_c02_curriculum_stages()
    stage = next(s for s in stages_list if s["stage_id"] == "Stage-2")
    
    env_overrides = {
        "terrain_config": dict(stage.get("terrain_config", {}) or {}),
        "physics_config": dict(stage.get("physics_config", {}) or {}),
    }

    agent.build_agent = agent.build_agent_Stage_2
    agent.agent_action = agent.agent_action_Stage_2

    runner = TaskRunner(task_name, task_module)
    result = runner.run(
        headless=True,
        max_steps=1000,
        save_gif=False,
        env_overrides=env_overrides,
    )
    
    if result:
        score, metrics = result
        print(f"Metrics: {metrics}")

if __name__ == "__main__":
    debug_stage_2()
