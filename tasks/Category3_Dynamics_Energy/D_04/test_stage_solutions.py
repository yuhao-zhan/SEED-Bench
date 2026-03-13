#!/usr/bin/env python3
import os
import sys

# Add the root directory to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from main import TaskRunner

def get_stage_overrides(stage):
    return {
        "terrain_config": stage.get("terrain_config", {}) or {},
        "physics_config": stage.get("physics_config", {}) or {},
    }

def test_stage(stage_index):
    task_name = "Category3_Dynamics_Energy.D_04"
    task_module = __import__(
        f"tasks.{task_name}",
        fromlist=["environment", "evaluator", "agent", "renderer", "stages"],
    )
    stages_mod = getattr(task_module, "stages", None)
    stages_list = stages_mod.get_d04_curriculum_stages()
    stage = stages_list[stage_index]
    stage_id = stage["stage_id"]
    
    # Override agent functions
    agent_mod = task_module.agent
    build_func_name = f"build_agent_{stage_id.lower().replace('-', '_')}"
    action_func_name = f"agent_action_{stage_id.lower().replace('-', '_')}"
    
    print(f"--- Testing {stage_id}: {stage['title']} ---")
    
    if hasattr(agent_mod, build_func_name) and hasattr(agent_mod, action_func_name):
        print(f"Using reference solution: {action_func_name}")
        # Monkey patch for the runner
        original_build = agent_mod.build_agent
        original_action = agent_mod.agent_action
        agent_mod.build_agent = getattr(agent_mod, build_func_name)
        agent_mod.agent_action = getattr(agent_mod, action_func_name)
    else:
        print(f"Reference solution for {stage_id} not found, using default agent functions.")

    runner = TaskRunner(task_name, task_module)
    max_steps = 15000
    overrides = get_stage_overrides(stage)
    
    result = runner.run(
        headless=True,
        max_steps=max_steps,
        save_gif=True,
        env_overrides=overrides,
    )
    
    # Restore original functions if they were patched
    if hasattr(agent_mod, build_func_name) and hasattr(agent_mod, action_func_name):
        agent_mod.build_agent = original_build
        agent_mod.agent_action = original_action

    if result:
        score, metrics = result
        print(f"Stage {stage_id} Score: {score:.2f} Success: {metrics.get('success', False)}")
        if metrics.get("max_seat_y_reached"):
            print(f"Max y reached: {metrics['max_seat_y_reached']:.2f} m")
        return metrics.get('success', False)
    return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_stage(int(sys.argv[1]) - 1)
    else:
        success_count = 0
        for i in range(4):
            if test_stage(i):
                success_count += 1
            print("-" * 40)
        print(f"Summary: {success_count}/4 stages passed.")
