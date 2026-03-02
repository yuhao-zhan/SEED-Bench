#!/usr/bin/env python3
"""
Test script for D_03 Phase-Locked Gate task agent.
Runs the simulation and saves GIF when successful.
Use: python test_agent.py           — baseline (initial task)
     python test_agent.py --mutated — run reference solution on all 4 mutated stages.
"""
import argparse
import importlib.util
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from main import TaskRunner


def test_d03_agent(env_overrides=None):
    """Test D_03 agent and save GIF on success. env_overrides: optional dict with terrain_config/physics_config."""
    task_name = "Category3_Dynamics_Energy.D_03"
    label = " (mutated)" if env_overrides else ""

    print("=" * 60)
    print("Testing D-03: Phase-Locked Gate" + label)
    print("=" * 60)

    try:
        task_module = __import__(
            f"tasks.{task_name}",
            fromlist=["environment", "evaluator", "agent", "renderer"],
        )
        runner = TaskRunner(task_name, task_module)
        task_dir = os.path.dirname(__file__)
        gif_path = os.path.join(task_dir, "reference_solution_success.gif")

        print("\nRunning simulation...")
        if not env_overrides:
            print(f"GIF will be saved to: {gif_path}\n")

        result = runner.run(
            headless=True,
            max_steps=20000,
            save_gif=bool(not env_overrides),
            env_overrides=env_overrides,
        )

        if result:
            score, metrics = result
            print("\n✅ Test completed!")
            print(f"Score: {score:.2f}")
            print(f"Success: {metrics.get('success', False)}")
            print(f"Gate open when crossed: {metrics.get('gate_was_open_when_crossed', False)}; Final speed: {metrics.get('final_speed')}; Target reached: {metrics.get('target_reached', False)}")
            if metrics.get("failed"):
                print(f"Failure reason: {metrics.get('failure_reason', 'Unknown')}")
            if metrics.get("success"):
                print(f"\n✅ SUCCESS! GIF saved to: {gif_path}")
            else:
                print("\n❌ Did not pass all criteria")
        else:
            print("\n❌ Test failed - no result returned (build_agent may have raised)")

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


def test_d03_mutated_stages():
    """Run reference solution on all 4 mutated stages; expect failures (original tuned for baseline)."""
    task_name = "Category3_Dynamics_Energy.D_03"
    task_dir = os.path.dirname(__file__)
    stages_file = os.path.join(task_dir, "stages.py")
    if not os.path.exists(stages_file):
        print("stages.py not found")
        return
    spec = importlib.util.spec_from_file_location("task_stages", stages_file)
    stages_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(stages_mod)
    curriculum_func = getattr(stages_mod, "get_d03_curriculum_stages", None)
    if not curriculum_func:
        print("get_d03_curriculum_stages not found")
        return
    stages = curriculum_func()
    task_module = __import__(
        f"tasks.{task_name}",
        fromlist=["environment", "evaluator", "agent", "renderer"],
    )
    results = []
    for stage in stages:
        stage_id = stage["stage_id"]
        env_overrides = {
            "terrain_config": stage.get("terrain_config", {}) or {},
            "physics_config": stage.get("physics_config", {}) or {},
        }
        print("\n" + "=" * 60)
        print(f"Mutated task: {stage_id} — {stage.get('title', stage_id)}")
        print("=" * 60)
        runner = TaskRunner(task_name, task_module)
        result = runner.run(
            headless=True, max_steps=20000, save_gif=False, env_overrides=env_overrides
        )
        if result:
            score, metrics = result
            success = metrics.get("success", False)
            results.append((stage_id, score, success, metrics.get("failure_reason")))
            print(f"Score: {score:.1f}  Success: {success}")
            if metrics.get("failed") and metrics.get("failure_reason"):
                print(f"Failure: {metrics['failure_reason']}")
        else:
            results.append((stage_id, None, False, "No result (build/run error)"))
            print("No result returned")
    print("\n" + "=" * 60)
    print("Summary: reference solution on mutated tasks")
    print("=" * 60)
    for stage_id, score, success, reason in results:
        status = "PASS" if success else "FAIL"
        print(f"  {stage_id}: {status}  score={score}")
        if reason and not success:
            print(f"    -> {(reason or '')[:80]}{'...' if len(reason or '') > 80 else ''}")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="D_03 Phase-Locked Gate agent test")
    parser.add_argument(
        "--mutated",
        action="store_true",
        help="Run reference solution on all 4 mutated stages (expect failures)",
    )
    args = parser.parse_args()
    if args.mutated:
        test_d03_mutated_stages()
    else:
        test_d03_agent()
