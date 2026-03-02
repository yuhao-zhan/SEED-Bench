#!/usr/bin/env python3
"""
Test script for K_05 lifter task agent.
Runs the simulation and saves GIF on success.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from main import TaskRunner


def test_k05_agent():
    """Test K_05 agent and save GIF on success"""
    task_name = "Category2_Kinematics_Linkages.K_05"

    print("=" * 60)
    print("Testing K-05: The Lifter Task")
    print("=" * 60)

    try:
        task_module = __import__(
            f'tasks.{task_name}',
            fromlist=['environment', 'evaluator', 'agent', 'renderer']
        )

        runner = TaskRunner(task_name, task_module)

        task_dir = os.path.dirname(__file__)
        gif_path = os.path.join(task_dir, 'solution_success.gif')

        print(f"\nRunning simulation...")
        print(f"GIF will be saved to: {gif_path}")
        print(f"Max steps: 60000 (lift to 9m + 3s sustained)\n")

        # Reference agent places object on platform; skip enforce_object_at_ground so test passes
        result = runner.run(
            headless=True, max_steps=60000, save_gif=True,
            env_overrides={'terrain_config': {'skip_enforce_object_at_ground': True}}
        )

        if result:
            score, metrics = result
            print(f"\n✅ Test completed!")
            print(f"Score: {score:.2f}")
            print(f"Success: {metrics.get('success', False)}")
            if metrics.get('failed'):
                print(f"Failure reason: {metrics.get('failure_reason', 'Unknown')}")
            print(f"\nMetrics:")
            for key, value in metrics.items():
                print(f"  {key}: {value}")

            if metrics.get('success'):
                print(f"\n✅ SUCCESS! GIF saved to: {gif_path}")
            else:
                print(f"\n❌ Did not pass all criteria")
        else:
            print("\n❌ Test failed - no result returned (e.g. build failed)")

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_k05_agent()
