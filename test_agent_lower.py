import sys
import os
import math
sys.path.insert(0, os.path.dirname(__file__))

from evaluation.verifier import CodeVerifier

with open("tasks/Category2_Kinematics_Linkages/K_01/agent.py", "r") as f:
    code = f.read()

# Modify starting position
code = code.replace("start_y = 4.5", "start_y = 1.6")

verifier = CodeVerifier(
    task_name="Category2_Kinematics_Linkages/K_01",
    max_steps=6000,
    env_overrides={}
)

success, score, metrics, error = verifier.verify_code(code=code, headless=True)
print("Initial Env with lower start_y:")
print("Success:", success, "Score:", score)
print("Metrics:", metrics)
