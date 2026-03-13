#!/usr/bin/env python3
"""
Verify reference solutions for all stages of D-02.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from main import TaskRunner

def test_all_stages():
    task_name = "Category3_Dynamics_Energy.D_02"
    task_module = __import__(f"tasks.{task_name}", fromlist=["environment", "evaluator", "agent"])
    stages_mod = __import__(f"tasks.{task_name}.stages", fromlist=["get_d02_curriculum_stages"])
    stages = stages_mod.get_d02_curriculum_stages()

    print("=" * 60)
    print("D-02: Verifying all stage solutions")
    print("=" * 60)

    # Initial
    runner = TaskRunner(task_name, task_module)
    res = runner.run(headless=True, max_steps=1000)
    if res:
        score, metrics = res
        print(f"Initial: success={metrics.get('success')}")
        if not metrics.get('success'):
            print(f"  Failure reason: {metrics.get('failure_reason')}")
    else:
        print("Initial: Failed to run (no result)")

    for i, s in enumerate(stages):
        stage_id = s["stage_id"]
        # Override agent functions for this stage
        build_func = getattr(task_module.agent, f"build_agent_stage_{i+1}")
        action_func = getattr(task_module.agent, f"agent_action_stage_{i+1}")
        
        # We need to temporarily patch the task_module.agent functions
        orig_build = task_module.agent.build_agent
        orig_action = task_module.agent.agent_action
        task_module.agent.build_agent = build_func
        task_module.agent.agent_action = action_func
        
        env_overrides = {
            "terrain_config": s.get("terrain_config", {}) or {},
            "physics_config": s.get("physics_config", {}) or {},
        }
        
        runner = TaskRunner(task_name, task_module)
        res = runner.run(headless=True, max_steps=1000, env_overrides=env_overrides)
        if res:
            score, metrics = res
            print(f"{stage_id}: success={metrics.get('success')}")
            if not metrics.get('success'):
                print(f"  Failure reason: {metrics.get('failure_reason')}")
        else:
            print(f"{stage_id}: Failed to run (no result)")
            
        # Restore original functions
        task_module.agent.build_agent = orig_build
        task_module.agent.agent_action = orig_action

if __name__ == "__main__":
    test_all_stages()
