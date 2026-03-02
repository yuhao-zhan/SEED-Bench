#!/usr/bin/env python3
"""
Test script for K_04 pusher task agent
Runs the simulation and saves GIF when successful
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from main import TaskRunner


def test_k04_agent():
    """Test K_04 agent and save GIF on success"""
    task_name = "Category2_Kinematics_Linkages.K_04"

    print("=" * 60)
    print("Testing K-04: The Pusher Task")
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
        print(f"Max steps: 60000 (push 8m + 5s sustained motion)\n")

        # Moderate difficulty: heavier than trivial, higher friction, reduced kick vs trivial
        env_overrides = {
            'terrain_config': {
                'object': {'mass': 0.12, 'friction': 0.1},   # 6x trivial 0.02
                'ground_friction': 0.22,                      # higher than trivial 0.15
                'pusher_initial_velocity_x': 3.0             # reduced from trivial 4.0
            },
            'physics_config': {'do_sleep': False}
        }
        result = runner.run(headless=True, max_steps=60000, save_gif=True, env_overrides=env_overrides)

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
            print("\n❌ Test failed - no result returned")

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_k04_agent()
