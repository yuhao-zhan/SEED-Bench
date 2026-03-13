#!/usr/bin/env python3
"""
Test D_05 reference solutions for each mutated stage.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from main import TaskRunner

def get_stage_overrides(stage):
    return {
        "terrain_config": stage.get("terrain_config", {}) or {},
        "physics_config": stage.get("physics_config", {}) or {},
    }

def main():
    task_name = "Category3_Dynamics_Energy.D_05"
    task_module = __import__(
        f"tasks.{task_name}",
        fromlist=["environment", "evaluator", "agent", "renderer", "stages"],
    )
    stages_mod = getattr(task_module, "stages", None)
    if not stages_mod:
        print("No stages module")
        return
    curriculum = getattr(stages_mod, "get_d05_curriculum_stages", None)
    if not curriculum:
        print("No get_d05_curriculum_stages")
        return
    stages_list = curriculum()
    runner = TaskRunner(task_name, task_module)
    max_steps = 1000

    for i, stage in enumerate(stages_list):
        stage_num = i + 1
        stage_id = stage.get("stage_id", "?")
        title = stage.get("title", "?")
        overrides = get_stage_overrides(stage)
        
        print("=" * 60)
        print(f"Testing {stage_id}: {title}")
        print("=" * 60)
        
        # Swap agent functions
        original_build = task_module.agent.build_agent
        original_action = task_module.agent.agent_action
        
        stage_build = getattr(task_module.agent, f"build_agent_stage_{stage_num}", None)
        stage_action = getattr(task_module.agent, f"agent_action_stage_{stage_num}", None)
        
        if not stage_build or not stage_action:
            print(f"Missing build/action for stage {stage_num}")
            continue
            
        task_module.agent.build_agent = stage_build
        task_module.agent.agent_action = stage_action
        
        try:
            result = runner.run(
                headless=True,
                max_steps=max_steps,
                save_gif=False,
                env_overrides=overrides,
            )
            if result:
                score, metrics = result
                print(f"Score: {score:.2f}  Success: {metrics.get('success', False)}  Failed: {metrics.get('failed', False)}")
                if metrics.get("failure_reason"):
                    print(f"Failure: {metrics['failure_reason']}")
                print(f"Shell broken: {metrics.get('shell_broken')}")
                print(f"Kinetic Energy: {metrics.get('kinetic_energy', 'N/A')}")
                print(f"Hit Slot Bar: {metrics.get('hammer_hit_slot_bar')}")
                print(f"Hit Slot Wall: {metrics.get('hammer_hit_slot_wall')}")
                print(f"Hammer Final Pos: ({metrics.get('hammer_x', 'N/A')}, {metrics.get('hammer_y', 'N/A')})")
            else:
                print("No result (build_agent may have raised)")
        finally:
            # Restore original functions
            task_module.agent.build_agent = original_build
            task_module.agent.agent_action = original_action
        print()

if __name__ == "__main__":
    main()
