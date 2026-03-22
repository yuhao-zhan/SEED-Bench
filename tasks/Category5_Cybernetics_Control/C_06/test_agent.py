#!/usr/bin/env python3
"""
Test script for C_06 The Governor task agent.
Runs the simulation and saves GIF when successful.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from main import run_task
from evaluation.utils import get_max_steps_for_task


def test_c06_agent():
    """Test C_06 agent and save GIF on success."""
    task_name = "Category5_Cybernetics_Control.C_06"
    max_steps = 15000

    print("=" * 60)
    print("Testing C-06: The Governor")
    print("=" * 60)

    try:
        result = run_task(
            task_name,
            headless=True,
            max_steps=max_steps,
            save_gif=True,
        )

        if result:
            score, metrics = result
            print("\n✅ Test completed!")
            print(f"Score: {score:.2f}")
            print(f"Success: {metrics.get('success', False)}")
            print(f"Wheel angular velocity (final): {metrics.get('wheel_angular_velocity', 0):.3f} rad/s")
            print(f"Target speed: {metrics.get('target_speed', 0):.2f} rad/s")
            print(f"Speed error: {metrics.get('speed_error', 0):.3f} rad/s")
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
    test_c06_agent()
