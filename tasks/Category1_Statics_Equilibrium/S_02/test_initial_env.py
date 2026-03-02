#!/usr/bin/env python3
import os
import sys

# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from evaluation.verifier import CodeVerifier

def main():
    task_name = "Category1_Statics_Equilibrium/S_02"
    verifier = CodeVerifier(
        task_name=task_name,
        max_steps=10000
    )
    
    agent_path = os.path.join(os.path.dirname(__file__), 'agent.py')
    with open(agent_path, 'r', encoding='utf-8') as f:
        code = f.read()
    
    print("Testing Initial Environment...")
    success, score, metrics, error = verifier.verify_code(
        code=code,
        headless=True,
        save_gif_path=os.path.join(os.path.dirname(__file__), "initial_reference_success.gif")
    )
    
    print(f"\nResults for Initial Environment:")
    print(f"  Success: {success}")
    print(f"  Score: {score:.2f}/100")
    if error:
        print(f"  Error: {error}")
    if metrics and metrics.get('failure_reason'):
        print(f"  Failure Reason: {metrics['failure_reason']}")
    
    return success

if __name__ == "__main__":
    main()
