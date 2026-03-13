#!/usr/bin/env python3
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from main import TaskRunner

def run_one(task_name, task_module, env_overrides=None, label="Stage"):
    overrides = env_overrides or {}
    runner = TaskRunner(task_name, task_module)
    result = runner.run(headless=True, max_steps=15000, save_gif=False, env_overrides=overrides)
    if result is None:
        return None, f"{label}: build/run error (no result)"
    score, metrics = result
    success = metrics.get("success", False)
    failed = metrics.get("failed", False)
    reason = metrics.get("failure_reason", "")
    return (score, success, failed, reason), None

def main():
    task_name = "Category3_Dynamics_Energy.D_06"
    import tasks.Category3_Dynamics_Energy.D_06.agent as agent_mod
    
    stages_mod = __import__(
        "tasks.Category3_Dynamics_Energy.D_06.stages",
        fromlist=["get_d06_curriculum_stages"],
    )
    stages = stages_mod.get_d06_curriculum_stages()

    print("=" * 60)
    print("D-06: Testing specific reference solutions for mutated stages")
    print("=" * 60)

    all_ok = True
    for s in stages:
        stage_id = s["stage_id"]
        # Extract stage number (e.g., "Stage-1" -> "stage_1")
        stage_suffix = stage_id.lower().replace("-", "_")
        build_func_name = f"build_agent_{stage_suffix}"
        action_func_name = f"agent_action_{stage_suffix}"

        if not hasattr(agent_mod, build_func_name):
            print(f"Missing {build_func_name} in agent.py")
            all_ok = False
            continue

        # Override agent module functions temporarily
        original_build = agent_mod.build_agent
        original_action = agent_mod.agent_action

        agent_mod.build_agent = getattr(agent_mod, build_func_name)
        agent_mod.agent_action = getattr(agent_mod, action_func_name, lambda *args: None)

        task_module = __import__(
            f"tasks.{task_name}",
            fromlist=["environment", "evaluator", "agent", "renderer"],
        )

        env_overrides = {
            "terrain_config": s.get("terrain_config", {}) or {},
            "physics_config": s.get("physics_config", {}) or {},
        }

        res, err = run_one(task_name, task_module, env_overrides, stage_id)
        
        # Restore
        agent_mod.build_agent = original_build
        agent_mod.agent_action = original_action

        if err:
            print(f"\n{stage_id}: {err}")
            all_ok = False
            continue

        score, success, failed, reason = res
        print(f"\n{stage_id} ({s.get('title', '')}) with {build_func_name}: score={score:.1f} success={success} failed={failed}")
        if reason:
            print(f"  reason: {reason}")
            
        if not success:
            all_ok = False
            print(f"  FAIL: {build_func_name} did not solve {stage_id}.")
        else:
            print(f"  PASS: {build_func_name} solved {stage_id}.")

    return 0 if all_ok else 1

if __name__ == "__main__":
    sys.exit(main())
