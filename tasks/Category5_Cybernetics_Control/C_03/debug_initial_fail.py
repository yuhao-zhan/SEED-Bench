import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from evaluation.verifier import CodeVerifier
from tasks.Category5_Cybernetics_Control.C_03.agent import build_agent, agent_action

def main():
    verifier = CodeVerifier(
        task_name="Category5_Cybernetics_Control/C_03",
        max_steps=15000,
    )
    
    with open("tasks/Category5_Cybernetics_Control/C_03/agent.py", "r") as f:
        code = f.read()
        
    success, score, metrics, error = verifier.verify_code(code=code, headless=True)
    
    print(f"Success: {success}")
    print(f"Score: {score}")
    print(f"Metrics: {metrics}")
    if error:
        print(f"Error: {error}")

if __name__ == "__main__":
    main()
