#!/usr/bin/env python3
"""Run C_01 reference agent on each mutated stage; expect failures (original solution not adapted)."""
import importlib.util
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from evaluation.verifier import CodeVerifier

# Load stages from same task directory
_task_dir = os.path.dirname(os.path.abspath(__file__))
_stages_path = os.path.join(_task_dir, "stages.py")
spec = importlib.util.spec_from_file_location("c01_stages", _stages_path)
stages_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stages_mod)
get_c01_curriculum_stages = getattr(stages_mod, "get_c01_curriculum_stages")


def main():
    task_name = "category_5_01"
    max_steps = 10000
    agent_path = os.path.join(os.path.dirname(__file__), "agent.py")
    with open(agent_path, "r") as f:
        code = f.read()

    stages = get_c01_curriculum_stages()
    results = []

    for stage in stages:
        stage_id = stage["stage_id"]
        env_overrides = {
            "terrain_config": dict(stage.get("terrain_config", {}) or {}),
            "physics_config": dict(stage.get("physics_config", {}) or {}),
        }
        verifier = CodeVerifier(task_name=task_name, max_steps=max_steps, env_overrides=env_overrides)
        success, score, metrics, error = verifier.verify_code(code, headless=True, save_gif_path=None)
        results.append((stage_id, success, score, metrics.get("failure_reason"), error))
        print(f"{stage_id}: success={success}, score={score}")
        if metrics.get("failure_reason"):
            print(f"  failure_reason: {metrics['failure_reason']}")
        if error:
            print(f"  error: {error}")

    print("\n--- Summary ---")
    all_failed = all(not r[1] for r in results)
    for stage_id, success, score, reason, err in results:
        status = "PASS" if success else "FAIL"
        print(f"  {stage_id}: {status} (score={score})")
    if all_failed:
        print("Reference solution failed on all mutated stages (expected).")
        return 0
    else:
        print("WARNING: Reference solution passed on some stages; strengthen those mutations.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
