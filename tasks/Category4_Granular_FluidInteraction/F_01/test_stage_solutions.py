import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from main import TaskRunner

def main():
    task_name = "Category4_Granular_FluidInteraction.F_01"
    task_module = __import__(f"tasks.{task_name}", fromlist=["environment", "evaluator", "agent", "renderer"])
    stages_mod = __import__(f"tasks.{task_name}.stages", fromlist=["get_f01_curriculum_stages"])
    stages = stages_mod.get_f01_curriculum_stages()

    print("=" * 60)
    print("F-01: Verifying divergent reference solutions")
    print("=" * 60)

    for i, stage in enumerate(stages):
        stage_id = stage["stage_id"]
        title = stage.get("title", "")
        
        # Patch the agent module to use the stage-specific functions
        suffix = stage_id.lower().replace("-", "_")
        build_func_name = f"build_agent_{suffix}"
        action_func_name = f"agent_action_{suffix}"
        
        # Save original default functions
        orig_build = task_module.agent.build_agent
        orig_action = task_module.agent.agent_action
        
        if hasattr(task_module.agent, build_func_name):
            print(f"\n[Testing {stage_id}: {title}]")
            task_module.agent.build_agent = getattr(task_module.agent, build_func_name)
            task_module.agent.agent_action = getattr(task_module.agent, action_func_name)
        else:
            print(f"\n[Testing {stage_id}: {title} (using default)]")

        overrides = {
            "terrain_config": stage.get("terrain_config", {}),
            "physics_config": stage.get("physics_config", {}),
        }
        
        runner = TaskRunner(task_name, task_module)
        res = runner.run(headless=True, max_steps=10000, save_gif=False, env_overrides=overrides)
        
        # Restore original functions for next iteration
        task_module.agent.build_agent = orig_build
        task_module.agent.agent_action = orig_action
        
        if res:
            score, metrics = res
            success = metrics.get('success', False)
            reason = metrics.get('failure_reason', 'None')
            print(f"Result: score={score} success={success} reason={reason}")
            if not success:
                print(f"ERROR: {stage_id} failed!")
                sys.exit(1)
        else:
            print(f"ERROR: {stage_id} run failed (no result)!")
            sys.exit(1)

    print("\n" + "=" * 60)
    print("SUCCESS: All divergent stages passed!")
    print("=" * 60)

if __name__ == "__main__":
    main()