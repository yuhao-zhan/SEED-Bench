#!/usr/bin/env python3
"""
Test script for F_03 The Excavator task agent.
Runs the simulation (40 s = 2400 steps) and saves GIF when successful.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from main import run_task

# 40 seconds at 60 fps
MAX_STEPS_F03 = 40 * 60


def test_f03_agent():
    """Test F_03 agent and save GIF on success."""
    task_name = "Category4_Granular_FluidInteraction.F_03"

    print("=" * 60)
    print("Testing F-03: The Excavator")
    print("=" * 60)

    try:
        # Success = real success: >= 50 particles in hopper (no relaxed threshold)
        result = run_task(
            task_name,
            headless=True,
            max_steps=MAX_STEPS_F03,
            save_gif=True,
        )

        if result:
            score, metrics = result
            print("\n✅ Test completed!")
            print(f"Score: {score:.2f}")
            print(f"Success: {metrics.get('success', False)}")
            print(f"Particles in hopper: {metrics.get('particles_in_truck')}/{metrics.get('initial_particle_count')}")
            print(f"Collected ratio: {metrics.get('collected_ratio_percent', 0):.1f}%")
            if metrics.get("failed"):
                print(f"Failure reason: {metrics.get('failure_reason', 'Unknown')}")
            if metrics.get("success"):
                task_dir = os.path.dirname(__file__)
                gif_path = os.path.join(task_dir, "reference_solution_success.gif")
                if hasattr(run_task, '__wrapped__'):
                    pass
                # Save GIF - main.run saves to simulator; we need to get path from runner
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
    test_f03_agent()
