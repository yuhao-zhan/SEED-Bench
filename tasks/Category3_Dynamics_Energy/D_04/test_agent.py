#!/usr/bin/env python3
"""
Test script for D_04 Swing task agent.
Runs the simulation and saves GIF when successful.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from main import run_task


def test_d04_agent():
    """Test D_04 agent and save GIF on success."""
    task_name = "Category3_Dynamics_Energy.D_04"

    print("=" * 60)
    print("Testing D-04: The Swing Task")
    print("=" * 60)

    try:
        result = run_task(
            task_name,
            headless=True,
            max_steps=15000,
            save_gif=True,
        )

        if result:
            score, metrics = result
            print("\n✅ Test completed!")
            print(f"Score: {score:.2f}")
            print(f"Success: {metrics.get('success', False)}")
            if metrics.get("failed"):
                print(f"Failure reason: {metrics.get('failure_reason', 'Unknown')}")
            if metrics.get("success"):
                task_dir = os.path.dirname(__file__)
                print(f"\n✅ SUCCESS! GIF saved to: {os.path.join(task_dir, 'reference_solution_success.gif')}")
            else:
                print("\n❌ Did not pass all criteria")
        else:
            print("\n❌ Test failed - no result returned (build_agent may have raised)")

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_d04_agent()
