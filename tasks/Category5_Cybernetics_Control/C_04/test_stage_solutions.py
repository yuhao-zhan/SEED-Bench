#!/usr/bin/env python3
"""
Detailed verification script for C-04.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from main import TaskRunner

def run_test(task_name, task_module, orig_build, orig_action, stage_num, use_mutated):
    stages_mod = task_module.stages
    stages_list = stages_mod.get_c04_curriculum_stages()
    stage = stages_list[stage_num - 1]
    
    env_overrides = {
        "terrain_config": stage.get("terrain_config", {}) or {},
        "physics_config": stage.get("physics_config", {}) or {},
    }
    
    if use_mutated:
        task_module.agent.build_agent = getattr(task_module.agent, f"build_agent_stage_{stage_num}")
        task_module.agent.agent_action = getattr(task_module.agent, f"agent_action_stage_{stage_num}")
        mode = "MUTATED"
    else:
        task_module.agent.build_agent = orig_build
        task_module.agent.agent_action = orig_action
        mode = "BASELINE"

    print(f"--- Testing Stage-{stage_num} [{mode}] ---")
    runner = TaskRunner(task_name, task_module)
    result = runner.run(headless=True, max_steps=20000, env_overrides=env_overrides)
    if result:
        score, metrics = result
        success = metrics.get("success", False)
        print(f"Result: {'PASS' if success else 'FAIL'} (Score: {score})")
        if not success:
            print(f"Final Pos: {metrics.get('final_pos')}, Steps: {metrics.get('steps')}")
        return success
    return False

def main():
    task_name = "Category5_Cybernetics_Control.C_04"
    task_module = __import__(f"tasks.{task_name}", fromlist=["agent", "stages", "environment", "evaluator", "renderer"])
    task_module.environment = __import__(f"tasks.{task_name}.environment", fromlist=["Sandbox"])
    task_module.evaluator = __import__(f"tasks.{task_name}.evaluator", fromlist=["Evaluator"])
    task_module.renderer = __import__(f"tasks.{task_name}.renderer", fromlist=["Renderer"])
    
    orig_build = task_module.agent.build_agent
    orig_action = task_module.agent.agent_action

    all_correct = True
    for i in range(1, 5):
        if not run_test(task_name, task_module, orig_build, orig_action, i, use_mutated=True):
            print(f"Error: Mutated solution for Stage {i} failed!")
            all_correct = False
        if run_test(task_name, task_module, orig_build, orig_action, i, use_mutated=False):
            print(f"Error: Baseline solution for Stage {i} passed, but should have failed!")
            all_correct = False
        print()

    if all_correct:
        print("Verification successful: Mutated solutions PASS, Baseline FAILS.")
        sys.exit(0)
    else:
        print("Verification failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
