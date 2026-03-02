#!/usr/bin/env python3
"""
Test script for control_aware task agent (speed-controlled slider)
Runs the simulation and saves GIF when successful
"""
import os
import sys

# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from main import TaskRunner


def test_control_aware_agent():
    """Test control_aware agent and save GIF on success"""
    task_name = "demo.control_aware"
    
    print("="*60)
    print("Testing Control-Aware Task: Speed-Controlled Slider")
    print("="*60)
    
    try:
        # Dynamically import task module
        task_module = __import__(f'tasks.{task_name}', 
                                fromlist=['environment', 'evaluator', 'agent', 'renderer'])
        
        # Create task runner
        runner = TaskRunner(task_name, task_module)
        
        # Create GIF path in task directory
        task_dir = os.path.dirname(__file__)
        gif_path = os.path.join(task_dir, 'control_aware_success.gif')
        
        print(f"\nRunning simulation...")
        print(f"GIF will be saved to: {gif_path}")
        print(f"Max steps: 10000\n")
        
        # Run simulation
        result = runner.run(headless=True, max_steps=10000, save_gif=True)
        
        if result:
            score, metrics = result
            print(f"\n{'='*60}")
            print(f"Simulation completed!")
            print(f"Final score: {score:.2f}")
            print(f"Success: {metrics.get('success', False)}")
            print(f"Distance traveled: {metrics.get('distance_traveled', 0):.2f}m")
            print(f"Max distance: {metrics.get('max_distance', 0):.2f}m")
            print(f"Speed violations: {metrics.get('speed_violation_count', 0)}")
            if metrics.get('failed'):
                print(f"Failure reason: {metrics.get('failure_reason', 'Unknown')}")
            print(f"{'='*60}\n")
            
            if metrics.get('success'):
                print(f"✅ Task completed successfully!")
                print(f"GIF saved to: {gif_path}")
            else:
                print(f"❌ Task failed")
        else:
            print("❌ Simulation returned no result")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    test_control_aware_agent()
