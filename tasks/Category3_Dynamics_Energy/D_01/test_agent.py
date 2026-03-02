#!/usr/bin/env python3
"""
Test script for D_01 Launcher task agent.
Runs the simulation and saves GIF when successful.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from main import TaskRunner


def test_d01_agent():
    """Test D_01 agent and save GIF on success."""
    task_name = "Category3_Dynamics_Energy.D_01"

    print("=" * 60)
    print("Testing D-01: The Launcher Task")
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
        print(f"GIF will be saved to: {gif_path}\n")

        result = runner.run(headless=True, max_steps=6000, save_gif=True)

        if result:
            score, metrics = result
            print("\n✅ Test completed!")
            print(f"Score: {score:.2f}")
            print(f"Success: {metrics.get('success', False)}")
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


if __name__ == "__main__":
    test_d01_agent()
