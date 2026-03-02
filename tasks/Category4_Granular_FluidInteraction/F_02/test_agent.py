#!/usr/bin/env python3
"""
Test script for F_02 Amphibian task agent.
Runs the simulation and saves GIF when successful.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from main import run_task


def test_f02_agent():
    """Test F_02 agent and save GIF on success."""
    task_name = "Category4_Granular_FluidInteraction.F_02"

    print("=" * 60)
    print("Testing F-02: The Amphibian Task")
    print("=" * 60)

    try:
        result = run_task(
            task_name,
            headless=True,
            max_steps=10000,
            save_gif=True,
        )

        if result:
            score, metrics = result
            print("\n✅ Test completed!")
            print(f"Score: {score:.2f}")
            print(f"Success: {metrics.get('success', False)}")
            print(f"Vehicle front x: {metrics.get('vehicle_front_x')}, target: {metrics.get('target_x')}")
            print(f"Vehicle lowest y: {metrics.get('vehicle_lowest_y')}")
            if metrics.get("failed"):
                print(f"Failure reason: {metrics.get('failure_reason', 'Unknown')}")
            if metrics.get("success"):
                task_dir = os.path.dirname(__file__)
                gif_path = os.path.join(task_dir, "reference_solution_success.gif")
                print(f"\n✅ SUCCESS! Save GIF to: {gif_path}")
            else:
                print("\n❌ Did not pass all criteria")
        else:
            print("\n❌ Test failed - no result returned (build_agent may have raised)")

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_f02_agent()
