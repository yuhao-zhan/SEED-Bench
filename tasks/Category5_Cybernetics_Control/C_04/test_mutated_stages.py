#!/usr/bin/env python3
"""
Test C-04 reference solution on all mutated stages.
Expect failures on mutated tasks (original solution tuned for baseline).
"""
import os
import sys
import importlib.util

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from main import TaskRunner
from tasks.Category5_Cybernetics_Control.C_04.environment import MAX_STEPS


def main():
    task_name = "Category5_Cybernetics_Control.C_04"
    task_module = __import__(
        f"tasks.{task_name}",
        fromlist=["environment", "evaluator", "agent", "renderer", "stages", "prompt"],
    )
    stages_mod = getattr(task_module, "stages", None)
    prompt_mod = getattr(task_module, "prompt", None)
    if not stages_mod or not prompt_mod:
        print("Missing stages or prompt module")
        return
    curriculum = getattr(stages_mod, "get_c04_curriculum_stages", None)
    if not curriculum:
        print("No get_c04_curriculum_stages")
        return
    stages_list = curriculum()
    runner = TaskRunner(task_name, task_module)
    max_steps = MAX_STEPS

    # Baseline (no override)
    print("=" * 60)
    print("Baseline (no env override)")
    print("=" * 60)
    result = runner.run(headless=True, max_steps=max_steps, save_gif=False, env_overrides=None)
    if result:
        score, metrics = result
        print(f"Score: {score:.2f}  Success: {metrics.get('success', False)}  Failed: {metrics.get('failed', False)}")
        if metrics.get("failure_reason"):
            print(f"Failure: {metrics['failure_reason']}")
    else:
        print("No result (build_agent may have raised)")
    print()

    results = []
    base_prompt = prompt_mod.TASK_PROMPT["task_description"]
    base_success = prompt_mod.TASK_PROMPT["success_criteria"]
    
    for stage in stages_list:
        stage_id = stage.get("stage_id", "?")
        terrain_config = stage.get("terrain_config", {}) or {}
        physics_config = stage.get("physics_config", {}) or {}
        
        # Mutate the prompt description
        mutated_desc = stages_mod.update_task_description_for_visible_changes(
            base_prompt,
            terrain_config,
            {},
            physics_config,
            stages_mod.get_source_base_physics_config(),
        )
        
        env_overrides = {
            "terrain_config": terrain_config,
            "physics_config": physics_config,
        }
        # Inject the mutated description into physics_config so Evaluator picks it up
        env_overrides["physics_config"]["task_description"] = mutated_desc
        
        print("=" * 60)
        print(f"Mutated: {stage_id} — {stage.get('title', stage_id)}")
        print("=" * 60)
        runner = TaskRunner(task_name, task_module)
        result = runner.run(
            headless=True,
            max_steps=max_steps,
            save_gif=False,
            env_overrides=env_overrides,
        )
        if result:
            score, metrics = result
            success = metrics.get("success", False)
            results.append((stage_id, score, success, metrics.get("failure_reason")))
            print(f"Score: {score:.1f}  Success: {success}")
            if metrics.get("failed") and metrics.get("failure_reason"):
                print(f"Failure: {metrics['failure_reason']}")
        else:
            results.append((stage_id, None, False, "No result"))
            print("No result returned")
        print()

    print("=" * 60)
    print("Summary: reference solution on mutated tasks")
    print("=" * 60)
    for stage_id, score, success, reason in results:
        status = "PASS" if success else "FAIL"
        sc = f"{score:.1f}" if score is not None else "N/A"
        print(f"  {stage_id}: {status} (score={sc}) {reason or ''}")


if __name__ == "__main__":
    main()
