#!/usr/bin/env python3
"""
Test script for C_04 The Escaper task agent.
Runs the simulation and saves GIF when successful.
Use: python test_agent.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from main import TaskRunner
from tasks.Category5_Cybernetics_Control.C_04.environment import MAX_STEPS


def test_c04_agent():
    """Test C_04 agent and save GIF on success."""
    task_name = "Category5_Cybernetics_Control.C_04"
    print("=" * 60)
    print("Testing C-04: The Escaper")
    print("=" * 60)

    try:
        task_module = __import__(
            "tasks.Category5_Cybernetics_Control.C_04",
            fromlist=["environment", "evaluator", "agent", "renderer"],
        )
        runner = TaskRunner(task_name, task_module)
        task_dir = os.path.dirname(__file__)
        gif_path = os.path.join(task_dir, "reference_solution_success.gif")

        print("\nRunning simulation...")
        print(f"GIF will be saved to: {gif_path}\n")

        result = runner.run(
            headless=True,
            max_steps=MAX_STEPS,
            save_gif=True,
        )

        if result:
            score, metrics = result
            print("\n✅ Test completed!")
            print(f"Score: {score:.2f}")
            print(f"Success: {metrics.get('success', False)}")
            print(f"Reached exit: {metrics.get('reached_exit', False)}")
            print(f"Steps: {metrics.get('step_count')}")
            if metrics.get("failed"):
                print(f"Failure reason: {metrics.get('failure_reason', 'Unknown')}")
            if metrics.get("success"):
                print(f"\n✅ SUCCESS! GIF saved to: {gif_path}")
            else:
                print("\n❌ Did not pass (timeout or not reached exit)")
        else:
            print("\n❌ Test failed - no result returned (build_agent may have raised)")

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_c04_agent()
