#!/usr/bin/env python3
"""Run C_03 reference agent on baseline (no mutation) and each mutated stage.

Expected: baseline may PASS (reference solution tuned for nominal env); Stage-1..4 should FAIL
(original solution not adapted to mutated physics). If any mutated stage PASSes, strengthen
that stage's terrain_config/physics_config until the reference solution fails.
"""
import importlib.util
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from evaluation.verifier import CodeVerifier

# Load stages from same task directory
_task_dir = os.path.dirname(os.path.abspath(__file__))
_stages_path = os.path.join(_task_dir, "stages.py")
spec = importlib.util.spec_from_file_location("c03_stages", _stages_path)
stages_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stages_mod)
get_c03_curriculum_stages = getattr(stages_mod, "get_c03_curriculum_stages")

# Fixed RNG seed for reproducibility (same across baseline and stages)
TARGET_RNG_SEED = 123


def main():
    task_name = "category_5_03"
    max_steps = 10000
    agent_path = os.path.join(os.path.dirname(__file__), "agent.py")
    with open(agent_path, "r") as f:
        code = f.read()

    results = []

    # 1) Baseline: same seed, no physics mutation (reference solution should pass in nominal env)
    env_baseline = {
        "terrain_config": {"target_rng_seed": TARGET_RNG_SEED},
        "physics_config": {},
    }
    verifier = CodeVerifier(task_name=task_name, max_steps=max_steps, env_overrides=env_baseline)
    success, score, metrics, error = verifier.verify_code(code, headless=True, save_gif_path=None)
    results.append(("Baseline", success, score, metrics.get("failure_reason"), error))
    print("Baseline (no mutation): success=%s, score=%s" % (success, score))
    if metrics.get("failure_reason"):
        print("  failure_reason: %s" % metrics["failure_reason"])
    if error:
        print("  error: %s" % error)

    # 2) Mutated stages: reference solution should fail (environment changed)
    stages = get_c03_curriculum_stages()
    for stage in stages:
        stage_id = stage["stage_id"]
        terrain = dict(stage.get("terrain_config", {}) or {})
        terrain.setdefault("target_rng_seed", TARGET_RNG_SEED)
        env_overrides = {
            "terrain_config": terrain,
            "physics_config": stage.get("physics_config", {}) or {},
        }
        verifier = CodeVerifier(task_name=task_name, max_steps=max_steps, env_overrides=env_overrides)
        success, score, metrics, error = verifier.verify_code(code, headless=True, save_gif_path=None)
        results.append((stage_id, success, score, metrics.get("failure_reason"), error))
        print("%s: success=%s, score=%s" % (stage_id, success, score))
        if metrics.get("failure_reason"):
            print("  failure_reason: %s" % metrics["failure_reason"])
        if error:
            print("  error: %s" % error)

    print("\n--- Summary (5 tasks: Baseline + Stage-1..4, difficulty ascending) ---")
    for label, success, score, reason, err in results:
        status = "PASS" if success else "FAIL"
        print("  %s: %s (score=%s)" % (label, status, score))
    mutated_results = [r for r in results if r[0] != "Baseline"]
    all_mutated_failed = all(not r[1] for r in mutated_results)
    if all_mutated_failed:
        print("Reference solution failed on all 4 mutated stages (expected).")
        return 0
    else:
        print("WARNING: Reference solution passed on some mutated stages; strengthen those mutations.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
