#!/usr/bin/env python3
"""
Test reference solution (agent.py) on all mutated stages for tasks that pass base test.
Expected: reference should FAIL on all mutated stages (mutated tasks should be harder).
If reference PASSES a mutated stage, that stage needs increased difficulty.
"""
import os
import sys
import io
import importlib.util

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import run_task, TASK_ALIASES
from test_all_agents_temp import TASK_CONFIG, discover_agent_tasks, run_single_test

# Tasks that fail base test - skip them
SKIP_BASE_FAIL = {"K_04"}


def get_stages_for_task(task_name):
    """Load curriculum stages for a task. Returns list of stage dicts or None."""
    short_name = task_name.split(".")[-1] if "." in task_name else task_name
    script_dir = os.path.dirname(os.path.abspath(__file__))
    task_path = task_name.replace(".", "/")
    stages_file = os.path.join(script_dir, "tasks", task_path, "stages.py")
    if not os.path.exists(stages_file):
        return None
    try:
        spec = importlib.util.spec_from_file_location("task_stages", stages_file)
        stages_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(stages_mod)
        for name in dir(stages_mod):
            if "curriculum_stages" in name.lower() and callable(getattr(stages_mod, name)):
                return getattr(stages_mod, name)()
    except Exception as e:
        print(f"  ⚠ load stages failed: {e}")
    return None


def run_mutated_stage(task_name, stage, max_steps, quick=False):
    """Run reference agent on one mutated stage. Returns (success, score, metrics)."""
    env_overrides = {
        "terrain_config": stage.get("terrain_config", {}),
        "physics_config": stage.get("physics_config", {}),
    }
    # Merge with TASK_CONFIG if any
    base_max, base_overrides = TASK_CONFIG.get(task_name, (10000, None))
    if base_overrides:
        tc = dict(env_overrides.get("terrain_config", {}))
        tc.update(base_overrides.get("terrain_config", {}))
        env_overrides["terrain_config"] = tc
        pc = dict(env_overrides.get("physics_config", {}))
        pc.update(base_overrides.get("physics_config", {}))
        env_overrides["physics_config"] = pc
    steps = max_steps or base_max
    if quick:
        quick_min = {
            "Category4_Granular_FluidInteraction.F_04": 5000,
            "Category3_Dynamics_Energy.D_04": 800,
            "Category2_Kinematics_Linkages.K_01": 50000,
            "Category2_Kinematics_Linkages.K_02": 15000,
            "Category2_Kinematics_Linkages.K_04": 40000,
            "Category2_Kinematics_Linkages.K_05": 40000,
            "Category2_Kinematics_Linkages.K_06": 120000,
            "Category6_ExoticPhysics.E_02": 6000,
            "Category5_Cybernetics_Control.C_03": 10000,
        }.get(task_name, 0)
        steps = max(quick_min, min(steps, 2000))
    _old_stdout, _old_stderr = sys.stdout, sys.stderr
    try:
        sys.stdout = io.StringIO()
        sys.stderr = io.StringIO()
        result = run_task(
            task_name,
            headless=True,
            max_steps=steps,
            save_gif=False,
            env_overrides=env_overrides,
        )
        sys.stdout, sys.stderr = _old_stdout, _old_stderr
    except Exception as e:
        sys.stdout, sys.stderr = _old_stdout, _old_stderr
        return False, 0.0, {"failure_reason": str(e)}
    if result is None:
        return False, 0.0, {"failure_reason": "Build failed"}
    score, metrics = result
    success = metrics.get("success", False)
    return success, score, metrics


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Test reference on mutated stages")
    parser.add_argument("--quick", action="store_true", help="Use reduced steps")
    parser.add_argument("--tasks", type=str, default=None, help="Comma-separated task IDs (e.g. S_01,C_01)")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    agents = discover_agent_tasks()
    agents = [(p, t) for p, t in agents if not t.startswith("demo.")]
    if args.tasks:
        want = set(s.strip() for s in args.tasks.split(","))
        agents = [(p, t) for p, t in agents if t.split(".")[-1] in want]

    # First: run base test to get passing tasks
    print("Running base tests to find passing tasks...")
    passing = []
    for agent_path, task_name in agents:
        short = task_name.split(".")[-1]
        if short in SKIP_BASE_FAIL:
            continue
        ok, _ = run_single_test(agent_path, task_name, verbose=args.verbose, quick=args.quick)
        if ok:
            passing.append(task_name)
    print(f"Passing base: {len(passing)} tasks\n")

    # For each passing task, test on mutated stages
    need_harder = []
    for task_name in passing:
        short = task_name.split(".")[-1]
        stages = get_stages_for_task(task_name)
        if not stages:
            continue
        base_max, _ = TASK_CONFIG.get(task_name, (10000, None))
        print(f"\n{'='*60}")
        print(f"{task_name} ({len(stages)} mutated stages)")
        print("=" * 60)
        for stage in stages:
            sid = stage["stage_id"]
            title = stage.get("title", sid)
            success, score, metrics = run_mutated_stage(task_name, stage, base_max, quick=args.quick)
            reason = metrics.get("failure_reason", "")
            if success:
                # Skip baseline/reference stages (empty config) - they're expected to pass
                is_baseline = (not stage.get("terrain_config") and not stage.get("physics_config")) or "baseline" in str(sid).lower() or "reference" in str(title).lower()
                if not is_baseline:
                    print(f"  ⚠ {sid} ({title}): PASSED (score {score:.1f}) - need to make harder!")
                    need_harder.append((task_name, sid, title, stage))
                else:
                    print(f"  ✓ {sid} ({title}): PASSED (baseline - expected)")
            else:
                print(f"  ✓ {sid} ({title}): FAILED (score {score:.1f}) - as expected")
                if args.verbose and reason:
                    print(f"      {reason[:80]}...")

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print("=" * 60)
    if need_harder:
        print(f"\n{len(need_harder)} mutated stage(s) where reference PASSED (should fail):")
        for task_name, sid, title, stage in need_harder:
            print(f"  - {task_name} {sid}: {title}")
        print("\nThese stages need increased difficulty in stages.py")
    else:
        print("\nAll mutated stages: reference passed 0 (expected). Good.")
    return 0 if not need_harder else 1


if __name__ == "__main__":
    sys.exit(main())
