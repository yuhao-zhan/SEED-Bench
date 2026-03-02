#!/usr/bin/env python3
"""
Temporary script to test every agent.py against its corresponding task.
Run from scripts/ directory: python test_all_agents_temp.py

Reports which agent.py files FAIL their task test.

For headless environments (no display), run with:
  SDL_VIDEODRIVER=dummy DISPLAY= python test_all_agents_temp.py

Use --quick for faster testing (reduced steps; may produce false failures for
tasks that need long simulations).
"""
import os
import sys
import traceback
import io

# Ensure scripts/ is on path
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from main import run_task, TASK_ALIASES

# Task-specific config: (max_steps, env_overrides)
# Default: 10000 steps, no overrides
TASK_CONFIG = {
    # Category1
    "Category1_Statics_Equilibrium.S_01": (10000, None),
    "Category1_Statics_Equilibrium.S_02": (10000, None),
    "Category1_Statics_Equilibrium.S_03": (15000, None),
    "Category1_Statics_Equilibrium.S_04": (10000, None),
    "Category1_Statics_Equilibrium.S_05": (20000, {"terrain_config": {"random_seed": 123}}),
    "Category1_Statics_Equilibrium.S_06": (15000, None),
    # Category2
    "Category2_Kinematics_Linkages.K_01": (90000, None),
    "Category2_Kinematics_Linkages.K_02": (20000, None),
    "Category2_Kinematics_Linkages.K_03": (20000, None),
    "Category2_Kinematics_Linkages.K_04": (60000, {"terrain_config": {"random_seed": 42}}),
    "Category2_Kinematics_Linkages.K_05": (60000, {"terrain_config": {"skip_enforce_object_at_ground": True}}),
    "Category2_Kinematics_Linkages.K_06": (150000, None),
    # Category3
    "Category3_Dynamics_Energy.D_01": (6000, None),
    "Category3_Dynamics_Energy.D_02": (6000, None),
    "Category3_Dynamics_Energy.D_03": (20000, None),
    "Category3_Dynamics_Energy.D_04": (15000, None),
    "Category3_Dynamics_Energy.D_05": (10000, None),
    "Category3_Dynamics_Energy.D_06": (15000, None),
    # Category4
    "Category4_Granular_FluidInteraction.F_01": (10000, None),
    "Category4_Granular_FluidInteraction.F_02": (10000, None),
    "Category4_Granular_FluidInteraction.F_03": (2400, None),  # 40s at 60fps
    "Category4_Granular_FluidInteraction.F_04": (10000, None),
    "Category4_Granular_FluidInteraction.F_05": (10000, None),
    "Category4_Granular_FluidInteraction.F_06": (10000, None),
    # Category5
    "Category5_Cybernetics_Control.C_01": (10000, None),
    "Category5_Cybernetics_Control.C_02": (10000, None),
    "Category5_Cybernetics_Control.C_03": (10000, {"terrain_config": {"target_rng_seed": 42}}),
    "Category5_Cybernetics_Control.C_04": (10000, None),
    "Category5_Cybernetics_Control.C_05": (12000, None),
    "Category5_Cybernetics_Control.C_06": (10000, None),
    # Category6
    "Category6_ExoticPhysics.E_01": (600, None),
    "Category6_ExoticPhysics.E_02": (10000, None),
    "Category6_ExoticPhysics.E_03": (10000, None),
    "Category6_ExoticPhysics.E_04": (10000, None),
    "Category6_ExoticPhysics.E_05": (10000, None),
    "Category6_ExoticPhysics.E_06": (500, None),
    # Demo
    "demo.basic": (10000, None),
    "demo.classify_balls": (10000, None),
    "demo.control_aware": (10000, None),
}


def discover_agent_tasks():
    """Find all agent.py files and map to task module names."""
    tasks_dir = os.path.join(_SCRIPT_DIR, "tasks")
    results = []
    for root, _dirs, files in os.walk(tasks_dir):
        if "agent.py" in files:
            rel = os.path.relpath(root, tasks_dir)
            # rel is e.g. "Category1_Statics_Equilibrium/S_01" or "demo/basic"
            task_name = rel.replace("/", ".").replace("-", "_")
            results.append((os.path.join(root, "agent.py"), task_name))
    return results


def run_single_test(agent_path: str, task_name: str, verbose: bool = False, quick: bool = False) -> tuple[bool, str | None]:
    """
    Run one agent test. Returns (passed, error_message).
    passed=True means metrics.get('success') and result is not None.
    """
    max_steps, env_overrides = TASK_CONFIG.get(task_name, (10000, None))
    if quick:
        # Some tasks need more steps even in quick mode (e.g. F_04 particles need time to settle)
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
        max_steps = max(quick_min, min(max_steps, 2000))
    _old_stdout, _old_stderr = sys.stdout, sys.stderr
    try:
        # Suppress verbose output when not in verbose mode
        if not verbose:
            sys.stdout = io.StringIO()
            sys.stderr = io.StringIO()
        result = run_task(
            task_name,
            headless=True,
            max_steps=max_steps,
            save_gif=False,
            env_overrides=env_overrides,
        )
        if not verbose:
            sys.stdout, sys.stderr = _old_stdout, _old_stderr
        if result is None:
            return False, "run_task returned None (build_agent may have failed)"
        score, metrics = result
        success = metrics.get("success", False)
        if success:
            return True, None
        failure_reason = metrics.get("failure_reason", "Unknown")
        return False, f"success=False, failure_reason={failure_reason}"
    except Exception as e:
        if not verbose:
            sys.stdout, sys.stderr = _old_stdout, _old_stderr
        return False, f"{type(e).__name__}: {e}"


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Test all agent.py files")
    parser.add_argument("-v", "--verbose", action="store_true", help="Print each task result")
    parser.add_argument("--skip-demo", action="store_true", help="Skip demo tasks")
    parser.add_argument("--quick", action="store_true",
                        help="Use reduced steps (max 2000) for faster run; may cause false failures")
    parser.add_argument("--tasks", type=str, default=None,
                        help="Comma-separated task IDs to test (e.g. S_01,S_02,E_06). Tests only these.")
    args = parser.parse_args()

    agents = discover_agent_tasks()
    if args.skip_demo:
        agents = [(p, t) for p, t in agents if not t.startswith("demo.")]
    if args.tasks:
        want = set(s.strip() for s in args.tasks.split(","))
        agents = [(p, t) for p, t in agents if t.split(".")[-1] in want]

    print(f"Testing {len(agents)} agent(s)...")
    print("=" * 70)

    passed = []
    failed = []

    for agent_path, task_name in agents:
        short_name = task_name.split(".")[-1] if "." in task_name else task_name
        if args.verbose:
            print(f"  Testing {task_name} ... ", end="", flush=True)
        ok, err = run_single_test(agent_path, task_name, verbose=args.verbose, quick=args.quick)
        if ok:
            passed.append((task_name, None))
            if args.verbose:
                print("PASS")
        else:
            failed.append((task_name, err))
            if args.verbose:
                print("FAIL")
                print(f"    {err}")

    # Summary
    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Passed: {len(passed)}/{len(agents)}")
    print(f"Failed: {len(failed)}/{len(agents)}")
    print()

    if args.quick:
        print("(Note: --quick mode used; some failures may be due to insufficient simulation steps.)")
        print()
    if failed:
        print("FAILED agent.py (cannot pass their task test):")
        print("-" * 70)
        for task_name, err in failed:
            rel_path = task_name.replace(".", "/")
            agent_path = os.path.join(_SCRIPT_DIR, "tasks", rel_path, "agent.py")
            print(f"  {agent_path}")
            print(f"    Task: {task_name}")
            print(f"    Error: {err}")
            print()
    else:
        print("All agents passed.")

    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
