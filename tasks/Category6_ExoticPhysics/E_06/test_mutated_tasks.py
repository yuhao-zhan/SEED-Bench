#!/usr/bin/env python3
"""
Run E_06 reference solution on base task and on each mutated stage (Stage-1..Stage-4).
Expect: base passes; all mutated stages should fail (original solution not adapted to new physics).
"""
import os
import sys
import importlib.util

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from evaluation.verifier import CodeVerifier


def load_stages():
    stages_file = os.path.join(os.path.dirname(__file__), "stages.py")
    spec = importlib.util.spec_from_file_location("e06_stages", stages_file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, "get_e06_curriculum_stages")()


def main():
    task_name = "Category6_ExoticPhysics/E_06"
    max_steps = 500  # same as test_agent.py
    agent_path = os.path.join(os.path.dirname(__file__), "agent.py")
    with open(agent_path, "r") as f:
        code = f.read()

    # 1) Base task (no overrides) — should pass
    verifier_base = CodeVerifier(task_name=task_name, max_steps=max_steps, env_overrides=None)
    success_base, score_base, metrics_base, error_base = verifier_base.verify_code(
        code, headless=True, save_gif_path=None
    )
    print("=== Base task (initial) ===")
    print("Success:", success_base, "| Score:", score_base)
    if error_base:
        print("Error:", error_base)
    print()

    stages = load_stages()
    results = []
    for stage in stages:
        stage_id = stage["stage_id"]
        env_overrides = {
            "terrain_config": stage.get("terrain_config") or {},
            "physics_config": stage.get("physics_config") or {},
        }
        verifier = CodeVerifier(task_name=task_name, max_steps=max_steps, env_overrides=env_overrides)
        success, score, metrics, error = verifier.verify_code(code, headless=True, save_gif_path=None)
        results.append((stage_id, success, score, metrics, error))
        print(f"=== {stage_id}: {stage.get('title', '')} ===")
        print("Success:", success, "| Score:", score)
        if metrics.get("failure_reason"):
            print("Failure reason:", metrics["failure_reason"])
        if error:
            print("Error:", error)
        print()

    # Summary
    print("=== Summary ===")
    print("Base:  ", "PASS" if success_base else "FAIL", "| Score:", score_base)
    for stage_id, success, score, _, _ in results:
        print(f"{stage_id}: ", "PASS" if success else "FAIL", "| Score:", score)
    mutated_passed = sum(1 for r in results if r[1])
    if success_base and mutated_passed == 0:
        print("\nOK: Base passes, all mutated stages fail (reference solution does not adapt).")
        return 0
    if not success_base:
        print("\nWARN: Base task failed; fix reference solution or environment.")
        return 1
    print(f"\nWARN: {mutated_passed} mutated stage(s) still pass; tighten physics_config so reference fails.")
    return 2


if __name__ == "__main__":
    sys.exit(main())
