
import sys
import os

# Add the project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from evaluation.verifier import CodeVerifier

def test_base():
    task_name = "Category1_Statics_Equilibrium/S_06"
    # Read reference solution
    agent_path = os.path.join(os.path.dirname(__file__), 'agent.py')
    with open(agent_path, 'r', encoding='utf-8') as f:
        code = f.read()
    
    verifier = CodeVerifier(task_name=task_name)
    success, score, metrics, error = verifier.verify_code(code)
    
    print(f"Base success: {success}, score: {score}")
    if not success:
        print(f"Failure reason: {metrics.get('failure_reason')}")
        print(f"Metrics: {metrics}")

if __name__ == "__main__":
    test_base()
