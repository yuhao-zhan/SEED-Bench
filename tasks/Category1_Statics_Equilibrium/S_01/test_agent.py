#!/usr/bin/env python3
"""
Verify that the INITIAL reference solution (build_agent) PASSES the initial environment.
"""
import os
import sys

# Add root directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from evaluation.verifier import CodeVerifier

def main():
    agent_path = os.path.join(os.path.dirname(__file__), 'agent.py')
    with open(agent_path, 'r', encoding='utf-8') as f:
        code = f.read()
    
    # We test build_agent as it is (for the initial environment)
    # The verifier by default uses build_agent and agent_action
    
    task_name = "Category1_Statics_Equilibrium/S_01"
    
    # Create verifier with NO overrides (Initial Environment)
    verifier = CodeVerifier(
        task_name=task_name,
        max_steps=10000
    )
    
    # Save GIF for initial environment
    gif_path = os.path.join(os.path.dirname(__file__), 'initial_reference_success.gif')
    
    print(f"Running simulation with initial build_agent on Initial Environment...")
    success, score, metrics, error = verifier.verify_code(
        code=code,
        headless=True,
        save_gif_path=gif_path
    )
    
    print(f"\nInitial Environment Results:")
    print(f"  Success: {success}")
    print(f"  Score: {score:.2f}/100")
    if error:
        print(f"  Error: {error}")
    
    if success:
        print(f"✅ Initial solution passed. Saved success GIF to: initial_reference_success.gif")
        sys.exit(0)
    else:
        print(f"❌ Initial solution FAILED on initial environment. Reason: {metrics.get('failure_reason')}")
        sys.exit(1)

if __name__ == "__main__":
    main()
