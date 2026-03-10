import math
import sys
import os

# Add repo root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from evaluation.verifier import CodeVerifier

def test_stage_2():
    with open("tasks/Category2_Kinematics_Linkages/K_03/test_agent_temp.py", "r") as f:
        temp_code = f.read()
    
    code = temp_code.replace("build_agent_stage_1", "build_agent").replace("agent_action_stage_1", "agent_action")
    
    verifier = CodeVerifier(
        task_name="Category2_Kinematics_Linkages/K_03",
        max_steps=20000,
        env_overrides={
            "terrain_config": {'objects': {'shape': 'box', 'mass': 1.0, 'friction': 0.6, 'x': 5.0, 'y': 2.0}},
            "physics_config": {"gravity": (0, -17.0)}
        }
    )
    
    success, score, metrics, error = verifier.verify_code(code=code, headless=True)
    print(f"Stage 2 Result: Success={success}, Score={score:.2f}, Metrics={metrics}")

if __name__ == "__main__":
    test_stage_2()
