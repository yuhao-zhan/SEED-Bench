#!/usr/bin/env python3
"""
Test script for S_05 shelter task agent
Runs the simulation and saves GIF when successful
"""
import os
import sys

# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from main import TaskRunner


def test_s05_agent():
    """Test S_05 agent and save GIF on success"""
    task_name = "Category1_Statics_Equilibrium.S_05"
    
    print("="*60)
    print("Testing S-05: The Shelter Task")
    print("="*60)
    
    try:
        # Dynamically import task module
        task_module = __import__(f'tasks.{task_name}', 
                                fromlist=['environment', 'evaluator', 'agent', 'renderer'])
        
        # Create task runner
        runner = TaskRunner(task_name, task_module)
        
        # Create GIF path in task directory
        task_dir = os.path.dirname(__file__)
        gif_path = os.path.join(task_dir, 'solution_success.gif')
        
        print(f"\nRunning simulation...")
        print(f"GIF will be saved to: {gif_path} (and reference_solution_success.gif on success)\n")
        print(f"Max steps: 20000 (need time for 24 meteors to spawn and fall)\n")
        
        # Run simulation - use fixed seed 123 for deterministic reference solution test
        env_overrides = {"terrain_config": {"seed": 123}}
        result = runner.run(headless=True, max_steps=20000, save_gif=True, env_overrides=env_overrides)
        
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
        else:
            print("\n❌ Test failed - no result returned")
            
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    test_s05_agent()
