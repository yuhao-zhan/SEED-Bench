#!/usr/bin/env python3
"""
Test script to verify each stage's reference solution in its corresponding mutated environment.
"""
import os
import sys

# Add project root to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from main import TaskRunner
from tasks.Category6_ExoticPhysics.E_01.stages import get_e01_curriculum_stages
import tasks.Category6_ExoticPhysics.E_01.agent as agent

def test_stage_solution(stage_idx, stage_config):
    """Test a specific stage solution in its mutated environment."""
    stage_id = stage_config["stage_id"]
    title = stage_config["title"]
    
    print(f"\n{'='*80}")
    print(f"Testing Solution for {stage_id}: {title}")
    print(f"{'='*80}\n")

    env_overrides = {
        "terrain_config": stage_config.get("terrain_config", {}),
        "physics_config": stage_config.get("physics_config", {}),
    }

    task_name = "Category6_ExoticPhysics.E_01"
    task_module = __import__(f"tasks.{task_name}", fromlist=["environment", "evaluator", "agent", "renderer"])
    
    # Override build_agent and agent_action with stage-specific versions
    stage_num = stage_id.split("-")[-1]
    build_func_name = f"build_agent_stage_{stage_num}"
    action_func_name = f"agent_action_stage_{stage_num}"
    
    if hasattr(agent, build_func_name):
        task_module.agent.build_agent = getattr(agent, build_func_name)
    else:
        print(f"❌ Error: {build_func_name} not found in agent.py")
        return False

    if hasattr(agent, action_func_name):
        task_module.agent.agent_action = getattr(agent, action_func_name)
    else:
        print(f"❌ Error: {action_func_name} not found in agent.py")
        return False

    runner = TaskRunner(task_name, task_module)
    
    # Steps: 1200 (~20s) as in test_mutated_tasks.py
    max_steps = 1200
    result = runner.run(headless=True, max_steps=max_steps, save_gif=True, env_overrides=env_overrides)

    if result is None:
        return False

    score, metrics = result
    success = metrics.get("success", False)
    failure_reason = metrics.get("failure_reason", "")

    if success:
        print(f"✅ {stage_id} PASSED (score {score:.2f})")
        # Rename gif to stage_n_solution_success.gif
        gif_path = os.path.join(os.path.dirname(__file__), "reference_solution_success.gif")
        if os.path.exists(gif_path):
            new_gif_path = os.path.join(os.path.dirname(__file__), f"stage_{stage_num}_solution_success.gif")
            os.rename(gif_path, new_gif_path)
    else:
        print(f"❌ {stage_id} FAILED (score {score:.2f})")
        if failure_reason:
            print(f"   Reason: {failure_reason}")

    return success

def main():
    stages = get_e01_curriculum_stages()
    results = []

    for i, stage in enumerate(stages):
        success = test_stage_solution(i, stage)
        results.append((stage["stage_id"], success))

    print(f"\n{'='*80}")
    print("Final Summary")
    print(f"{'='*80}")
    for stage_id, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{stage_id}: {status}")

if __name__ == "__main__":
    main()
