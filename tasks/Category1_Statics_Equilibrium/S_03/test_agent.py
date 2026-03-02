#!/usr/bin/env python3
"""
Test script for S_03 cantilever task agent
Runs the simulation and saves GIF when successful
"""
import os
import sys

# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from main import TaskRunner


def test_s03_agent():
    """Test S_03 agent and save GIF on success"""
    task_name = "Category1_Statics_Equilibrium.S_03"
    
    print("="*60)
    print("Testing S-03: The Cantilever Task")
    print("="*60)
    
    try:
        # Dynamically import task module
        task_module = __import__(f'tasks.{task_name}', 
                                fromlist=['environment', 'evaluator', 'agent', 'renderer'])
        
        # Create task runner
        runner = TaskRunner(task_name, task_module)
        
        # Create GIF path in task directory
        task_dir = os.path.dirname(__file__)
        gif_path = os.path.join(task_dir, 'cantilever_success.gif')
        
        print(f"\nRunning simulation...")
        print(f"GIF will be saved to: {gif_path}")
        print(f"Max steps: 15000 (need time for load attachment at t=5s and 10s hold)\n")
        
        # Run simulation (need enough steps: 5s load attach + 10s hold = 15s = 900 steps at 60fps)
        # Use 15000 steps to be safe
        result = runner.run(headless=True, max_steps=15000, save_gif=True)
        
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
    test_s03_agent()
