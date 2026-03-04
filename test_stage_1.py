import sys
import os
from evaluation.verifier import CodeVerifier
sys.path.insert(0, os.path.dirname(__file__))

import stages
st = stages.get_k01_curriculum_stages()[0]

with open('tasks/Category2_Kinematics_Linkages/K_01/agent.py', 'r') as f:
    code = f.read()

verifier = CodeVerifier(
    task_name="Category2_Kinematics_Linkages/K_01",
    max_steps=6000,
    env_overrides={
        "terrain_config": st.get("terrain_config", {}),
        "physics_config": st.get("physics_config", {})
    }
)

success, score, metrics, error = verifier.verify_code(code=code, headless=True)
print("Stage 1 original code success:", success)
print("Score:", score)
print("Metrics:", metrics)
if error: print("Error:", error)
