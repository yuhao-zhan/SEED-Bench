#!/usr/bin/env python3
"""
Uniform script to systematically test reference solutions of each task environment.

Goals:
1. For each env (Initial + four mutated stages), its reference solution should PASS on its corresponding env.
2. The initial reference solution should FAIL on all four mutated envs (Stage-1 to Stage-4).

Execution: All tests use CodeVerifier + get_reference_solution(task_name, stage_id).
- Correct reference in correct env: ref_stage_id and env_stage are always matched (Initial ref on Initial env,
  Stage-k ref on Stage-k env). get_reference_solution extracts that stage's code; env_overrides come from that stage.

Usage:
  python test_reference_solutions.py --task all
  python test_reference_solutions.py --task S_01
  python test_reference_solutions.py --task Category1_Statics_Equilibrium
"""
import os
import sys
import argparse

# Script lives under scripts/tasks; add scripts dir to path
SCRIPTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from evaluation.verifier import CodeVerifier
from evaluation.evaluate_cross_mutated import get_all_stages, get_reference_solution


# Per-task max_steps overrides (task_id or full task name). Default used otherwise.
DEFAULT_MAX_STEPS = 15000
MAX_STEPS_OVERRIDES = {
    "K_04": 60000,
    "K_06": 150000,
    "K_02": 30000,
    "K_01": 200000,
    "F_06": 200000,
    "F_03": 2400,  # 40 s at 60 fps, same as F_03/test_stage_solutions.py
    "F_04": 10000,  # same as F_04/test_agent.py, test_stage_solutions.py
    "S_03": 1800,
    "D_05": 1000,
    "D_01": 6000,
    "D_02": 1000,
    "D_04": 15000,
    "D_06": 15000,
}


def discover_tasks(tasks_root: str):
    """Discover all tasks that have agent.py and stages with curriculum (Initial + mutated)."""
    tasks_root = os.path.abspath(tasks_root)
    task_list = []
    for cat in sorted(os.listdir(tasks_root)):
        cat_path = os.path.join(tasks_root, cat)
        if not os.path.isdir(cat_path) or cat.startswith('.') or cat == 'demo':
            continue
        for task_id in sorted(os.listdir(cat_path)):
            task_path = os.path.join(cat_path, task_id)
            if not os.path.isdir(task_path):
                continue
            agent_py = os.path.join(task_path, 'agent.py')
            stages_py = os.path.join(task_path, 'stages.py')
            if not os.path.isfile(agent_py) or not os.path.isfile(stages_py):
                continue
            task_name = f"{cat}/{task_id}"
            task_list.append(task_name)
    return task_list


def task_matches_filter(task_name: str, task_filter: str) -> bool:
    """Match --task filter: 'all', or category, or task_id (e.g. S_01)."""
    if task_filter == 'all':
        return True
    parts = task_name.split('/')
    for part in parts:
        if task_filter.lower().startswith('category_') and part.lower().startswith(task_filter.lower()):
            return True
        if part == task_filter:
            return True
    return False


def get_max_steps(task_name: str) -> int:
    """Return max_steps for this task (override or default)."""
    task_id = task_name.split('/')[-1] if '/' in task_name else task_name
    return MAX_STEPS_OVERRIDES.get(task_id, DEFAULT_MAX_STEPS)


def run_single_test(
    task_name: str,
    ref_stage_id: str,
    env_stage: dict,
    *,
    headless: bool = True,
) -> tuple[bool, float, str | None]:
    """
    Run one verification: reference solution for ref_stage_id on environment env_stage.
    Uses CodeVerifier + get_reference_solution so the correct ref runs in the correct env.
    """
    try:
        code = get_reference_solution(task_name, ref_stage_id)
    except Exception as e:
        return False, 0.0, str(e)
    env_overrides = {
        "terrain_config": env_stage.get("terrain_config", {}),
        "physics_config": env_stage.get("physics_config", {}),
    }
    max_steps = get_max_steps(task_name)
    try:
        verifier = CodeVerifier(
            task_name=task_name,
            max_steps=max_steps,
            env_overrides=env_overrides,
        )
        success, score, metrics, error = verifier.verify_code(code=code, headless=headless)
        return success, score, error
    except Exception as e:
        return False, 0.0, str(e)


def test_task(task_name: str, verbose: bool = True) -> dict:
    """
    Run all reference-solution tests for one task.
    Returns dict with:
      - initial_on_initial: bool
      - initial_on_stage_1..4: bool
      - stage_k_on_stage_k: bool for k=1..4
      - mutated_stage_ids: list of stage ids (e.g. ["Stage-1", "Stage-2", "Stage-3", "Stage-4"])
    """
    all_stages = get_all_stages(task_name)
    if len(all_stages) < 2:
        return {
            "initial_on_initial": None,
            "initial_on_mutated": {},
            "ref_on_own_env": {},
            "mutated_stage_ids": [],
            "error": "No mutated stages",
        }
    initial_env = all_stages[0]  # Initial
    mutated = [s for s in all_stages[1:] if s["stage_id"] != "Initial"]
    mutated_stage_ids = [s["stage_id"] for s in mutated]

    result = {
        "initial_on_initial": None,
        "initial_on_mutated": {},
        "ref_on_own_env": {"Initial": None},
        "mutated_stage_ids": mutated_stage_ids,
        "error": None,
    }

    # 1) Initial reference on Initial env → expect PASS (correct ref in correct env)
    if verbose:
        print(f"  [Initial ref] on Initial env ... ", end="", flush=True)
    ok, score, err = run_single_test(task_name, "Initial", initial_env, headless=True)
    result["initial_on_initial"] = ok
    result["ref_on_own_env"]["Initial"] = ok
    if verbose:
        print("PASS" if ok else "FAIL", flush=True)

    # 2) Initial reference on each mutated env → expect FAIL
    for stage in mutated:
        sid = stage["stage_id"]
        if verbose:
            print(f"  [Initial ref] on {sid} env ... ", end="", flush=True)
        ok, _, _ = run_single_test(task_name, "Initial", stage, headless=True)
        result["initial_on_mutated"][sid] = ok
        if verbose:
            print("PASS" if ok else "FAIL (expected)", flush=True)

    # 3) Each stage's reference on its own env → expect PASS (correct ref in correct env)
    for stage in mutated:
        sid = stage["stage_id"]
        if verbose:
            print(f"  [{sid} ref] on {sid} env ... ", end="", flush=True)
        ok, _, _ = run_single_test(task_name, sid, stage, headless=True)
        result["ref_on_own_env"][sid] = ok
        if verbose:
            print("PASS" if ok else "FAIL", flush=True)

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Test reference solutions: initial must pass only on initial and fail on mutated; each stage ref must pass on its env."
    )
    parser.add_argument(
        "--task",
        type=str,
        default="all",
        help="Task filter: 'all', task id (e.g. S_01), or category (e.g. Category1_Statics_Equilibrium)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only print summary tables, not per-test lines",
    )
    args = parser.parse_args()

    tasks_root = os.path.join(SCRIPTS_DIR, "tasks")
    all_tasks = discover_tasks(tasks_root)
    task_list = [t for t in all_tasks if task_matches_filter(t, args.task)]
    if not task_list:
        print(f"No tasks found for filter: {args.task}")
        sys.exit(1)

    print(f"Testing {len(task_list)} task(s) for filter: {args.task}\n")
    verbose = not args.quiet
    results_by_task = {}

    for task_name in task_list:
        if verbose:
            print(f"[{task_name}]")
        try:
            res = test_task(task_name, verbose=verbose)
            results_by_task[task_name] = res
        except Exception as e:
            results_by_task[task_name] = {
                "initial_on_initial": None,
                "initial_on_mutated": {},
                "ref_on_own_env": {},
                "mutated_stage_ids": [],
                "error": str(e),
            }
            if verbose:
                print(f"  Error: {e}")
        if verbose:
            print()

    # Build two markdown tables
    # Table 1: Initial reference solution on the four mutated envs (expect ✗)
    # Table 2: Reference solution of each of the five envs on its corresponding env (expect ✓)
    stage_cols = ["Stage-1", "Stage-2", "Stage-3", "Stage-4"]
    env_cols = ["Initial", "Stage-1", "Stage-2", "Stage-3", "Stage-4"]

    def cell(success: bool | None) -> str:
        if success is None:
            return "—"
        return "✓" if success else "✗"

    lines1 = []
    lines1.append("## 1. Initial reference solution on mutated envs (expected: all ✗)")
    lines1.append("")
    lines1.append("| Task | Stage-1 | Stage-2 | Stage-3 | Stage-4 |")
    lines1.append("|------|---------|---------|---------|---------|")
    for task_name in sorted(results_by_task.keys()):
        res = results_by_task[task_name]
        row = [task_name]
        for col in stage_cols:
            val = res.get("initial_on_mutated", {}).get(col)
            row.append(cell(val))
        lines1.append("| " + " | ".join(row) + " |")
    lines1.append("")

    lines2 = []
    lines2.append("## 2. Reference solution of each env on its corresponding env (expected: all ✓)")
    lines2.append("")
    lines2.append("| Task | Initial | Stage-1 | Stage-2 | Stage-3 | Stage-4 |")
    lines2.append("|------|---------|---------|---------|---------|---------|")
    for task_name in sorted(results_by_task.keys()):
        res = results_by_task[task_name]
        row = [task_name]
        for col in env_cols:
            val = res.get("ref_on_own_env", {}).get(col)
            row.append(cell(val))
        lines2.append("| " + " | ".join(row) + " |")
    lines2.append("")

    print("\n".join(lines1))
    print("\n".join(lines2))

    # Exit code: 0 if all expectations met
    any_fail = False
    for task_name, res in results_by_task.items():
        if res.get("error"):
            any_fail = True
            continue
        if res.get("initial_on_initial") is False:
            any_fail = True
        for sid in res.get("initial_on_mutated", {}):
            if res["initial_on_mutated"][sid]:  # Initial should FAIL on mutated
                any_fail = True
        for sid, ok in res.get("ref_on_own_env", {}).items():
            if ok is False:  # Each ref should PASS on its env
                any_fail = True
    sys.exit(0 if not any_fail else 1)


if __name__ == "__main__":
    main()
