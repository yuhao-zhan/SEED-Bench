#!/usr/bin/env python3
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from main import TaskRunner

def run_one(task_name, task_module, stage_id, env_overrides=None):
    runner = TaskRunner(task_name, task_module)
    # Patch agent functions to use stage-specific ones
    if stage_id != "Baseline":
        stage_num = stage_id.split("-")[1]
        build_func_name = f"build_agent_stage_{stage_num}"
        action_func_name = f"agent_action_stage_{stage_num}"
        if hasattr(task_module.agent, build_func_name):
            task_module.agent.build_agent = getattr(task_module.agent, build_func_name)
        if hasattr(task_module.agent, action_func_name):
            task_module.agent.agent_action = getattr(task_module.agent, action_func_name)
    
    result = runner.run(headless=True, max_steps=10000, save_gif=True, env_overrides=env_overrides)
    if result is None:
        return None, "build/run error"
        
    score, metrics = result
    success = metrics.get("success", False)
    
    # Rename the generated GIF
    src_gif = os.path.join(os.path.dirname(__file__), f"reference_solution_{'success' if success else 'failure'}.gif")
    stage_num = stage_id.split("-")[1]
    dst_gif = os.path.join(os.path.dirname(__file__), f"stage_{stage_num}_solution_success.gif")
    if os.path.exists(src_gif):
        os.rename(src_gif, dst_gif)
        
    return result, None

def main():
    task_name = "Category4_Granular_FluidInteraction.F_02"
    task_module = __import__(
        f"tasks.{task_name}",
        fromlist=["environment", "evaluator", "agent", "renderer"],
    )
    stages_mod = __import__(
        f"tasks.{task_name}.stages",
        fromlist=["get_f02_curriculum_stages"],
    )
    stages = stages_mod.get_f02_curriculum_stages()

    success_all = True
    for s in stages:
        stage_id = s["stage_id"]
        env_overrides = {
            "terrain_config": s.get("terrain_config", {}) or {},
            "physics_config": s.get("physics_config", {}) or {},
        }
        print(f"\nRunning {stage_id}...")
        res, err = run_one(task_name, task_module, stage_id, env_overrides)
        if err:
            print(f"  {stage_id}: {err}")
            success_all = False
            continue
        score, metrics = res
        success = metrics.get("success", False)
        reason = metrics.get("failure_reason", "")
        print(f"  {stage_id}: score={score:.1f} success={success}")
        if not success:
            print(f"  Reason: {reason}")
            success_all = False
    
    if success_all:
        print("\nAll stages passed!")
        sys.exit(0)
    else:
        print("\nSome stages failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
