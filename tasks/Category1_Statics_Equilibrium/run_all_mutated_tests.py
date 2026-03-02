#!/usr/bin/env python3
"""
Run all Category1_Statics_Equilibrium tasks: for each task, run its agent.py (initial-environment
solution) on all 4 mutated-task environments and collect pass/fail. Output a table report.
Must be run from scripts/ directory: python tasks/Category1_Statics_Equilibrium/run_all_mutated_tests.py
"""
import os
import sys
import importlib.util

# Ensure scripts/ is on path (run from repo root or scripts/)
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_SCRIPTS_DIR = os.path.join(_SCRIPT_DIR, '../..')
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from evaluation.verifier import CodeVerifier


# Task config: (task_folder_name, task_name_for_verifier, max_steps)
# task_name_for_verifier must match folder (S_01, S_02, ..., S_06)
TASK_CONFIGS = [
    ("S_01", "Category1_Statics_Equilibrium/S_01", 10000),
    ("S_02", "Category1_Statics_Equilibrium/S_02", 10000),
    ("S_03", "Category1_Statics_Equilibrium/S_03", 15000),
    ("S_04", "Category1_Statics_Equilibrium/S_04", 20000),
    ("S_05", "Category1_Statics_Equilibrium/S_05", 20000),
    ("S_06", "Category1_Statics_Equilibrium/S_06", 10000),
]


def get_stages_for_task(task_folder: str):
    """Return list of stage configs for the task. S_01..S_06 use standard import."""
    if task_folder == "S_06":
        stages_path = os.path.join(_SCRIPT_DIR, "S_06", "stages.py")
        spec = importlib.util.spec_from_file_location("stages_s06", stages_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.get_s06_curriculum_stages()
    # S_01 .. S_05: use standard import
    mod_name = f"tasks.Category1_Statics_Equilibrium.{task_folder}.stages"
    stages_mod = __import__(mod_name, fromlist=["stages"])
    # e.g. S_01 -> get_s01_curriculum_stages, S-06 -> get_s06_curriculum_stages
    key = task_folder.replace("-", "").replace("_", "").lower()
    getter = getattr(stages_mod, f"get_{key}_curriculum_stages")
    return getter()


def read_agent_code(task_folder: str) -> str:
    """Read agent.py for the task."""
    agent_path = os.path.join(_SCRIPT_DIR, task_folder, "agent.py")
    with open(agent_path, "r", encoding="utf-8") as f:
        return f.read()


def run_one_stage(task_name: str, max_steps: int, stage: dict, agent_code: str, verbose: bool = False):
    """Run verifier for one (task, stage). Return (success, score)."""
    env_overrides = {
        "terrain_config": stage.get("terrain_config", {}),
        "physics_config": stage.get("physics_config", {}),
    }
    verifier = CodeVerifier(
        task_name=task_name,
        max_steps=max_steps,
        env_overrides=env_overrides,
    )
    success, score, metrics, error = verifier.verify_code(
        code=agent_code,
        headless=True,
        save_gif_path=None,
    )
    if verbose:
        print(f"    {stage['stage_id']} {stage['title']}: {'PASS' if success else 'FAIL'} score={score:.2f}")
    return success, score


def main():
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    print("Category1 Statics & Equilibrium: Initial agent.py vs 4 mutated tasks per task")
    print("=" * 100)

    all_results = []  # list of (task_folder, stage_id, title, success, score)

    for task_folder, task_name, max_steps in TASK_CONFIGS:
        task_dir = os.path.join(_SCRIPT_DIR, task_folder)
        if not os.path.isdir(task_dir):
            print(f"Skip {task_folder}: directory not found")
            continue
        try:
            stages = get_stages_for_task(task_folder)
        except Exception as e:
            print(f"Skip {task_folder}: failed to load stages: {e}")
            continue
        try:
            agent_code = read_agent_code(task_folder)
        except Exception as e:
            print(f"Skip {task_folder}: failed to read agent.py: {e}")
            continue

        if verbose:
            print(f"\nTask {task_folder} ({len(stages)} stages)")
        for stage in stages:
            success, score = run_one_stage(task_name, max_steps, stage, agent_code, verbose=verbose)
            all_results.append((task_folder, stage["stage_id"], stage["title"], success, score))

    # Table report
    print("\n" + "=" * 100)
    print("REPORT: Initial solution (agent.py) run on mutated environments")
    print("=" * 100)

    # Header: Task | Stage-1 | Stage-2 | Stage-3 | Stage-4 | Pass/Total
    tasks_seen = []
    for task_folder, task_name, max_steps in TASK_CONFIGS:
        if task_folder not in tasks_seen:
            tasks_seen.append(task_folder)
    stage_ids = ["Stage-1", "Stage-2", "Stage-3", "Stage-4"]

    # Build rows
    col_width = 12
    header = "Task".ljust(8) + "".join(s.ljust(col_width) for s in stage_ids) + "  Pass/Total"
    print(header)
    print("-" * len(header))

    for task_folder in tasks_seen:
        row_results = [r for r in all_results if r[0] == task_folder]
        if not row_results:
            continue
        cells = [task_folder.ljust(8)]
        passed = 0
        for sid in stage_ids:
            r = next((x for x in row_results if x[1] == sid), None)
            if r is None:
                cells.append("-".ljust(col_width))
            else:
                status = "PASS" if r[3] else "FAIL"
                cells.append(status.ljust(col_width))
                if r[3]:
                    passed += 1
        total = len(row_results)
        cells.append(f"  {passed}/{total}")
        print("".join(cells))

    print("-" * len(header))
    total_passed = sum(1 for r in all_results if r[3])
    total_runs = len(all_results)
    print(f"\nTotal: {total_passed}/{total_runs} mutated tasks passed ({100 * total_passed / total_runs:.1f}%)")
    return all_results


if __name__ == "__main__":
    main()
