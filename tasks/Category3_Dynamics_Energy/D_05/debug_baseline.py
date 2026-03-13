#!/usr/bin/env python3
"""
Debug D_05 baseline.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from main import TaskRunner

def main():
    task_name = "Category3_Dynamics_Energy.D_05"
    task_module = __import__(
        f"tasks.{task_name}",
        fromlist=["environment", "evaluator", "agent", "renderer", "stages"],
    )
    runner = TaskRunner(task_name, task_module)
    max_steps = 1000

    print("=" * 60)
    print("Debugging Baseline")
    print("=" * 60)
    
    # We'll modify the agent_action to print info
    original_action = task_module.agent.agent_action
    
    def debug_action(sandbox, agent_body, step_count):
        original_action(sandbox, agent_body, step_count)
        if step_count >= 370 and step_count <= 420:
            print(f"Step {step_count}: Pos ({agent_body.position.x:.2f}, {agent_body.position.y:.2f}) Angle {agent_body.angle:.2f} Omega {agent_body.angularVelocity:.2f}")

    task_module.agent.agent_action = debug_action
    
    try:
        runner.run(headless=True, max_steps=max_steps, save_gif=False)
    finally:
        task_module.agent.agent_action = original_action

if __name__ == "__main__":
    main()
