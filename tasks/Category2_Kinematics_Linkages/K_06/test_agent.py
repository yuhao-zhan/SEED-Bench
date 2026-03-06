#!/usr/bin/env python3
"""
Test script for K_06 wiper task agent.
Runs the simulation and saves GIF on success.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from main import TaskRunner


def test_k06_agent():
    """Test K_06 agent and save GIF on success"""
    task_name = "Category2_Kinematics_Linkages.K_06"

    print("=" * 60)
    print("Testing K-06: The Wiper Task")
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
        print(f"Max steps: 10000 (45 particles, 100%% removal, 12s motion, 15kg mass)\n")

        # Task defaults (seed 42, 45 particles); ref agent reaches 100% within 150k steps
        env_overrides = {}
        result = runner.run(headless=True, max_steps=10000, save_gif=True, env_overrides=env_overrides)

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
    test_k06_agent()
