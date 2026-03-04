import sys
import os
import math
sys.path.insert(0, os.path.dirname(__file__))

from evaluation.verifier import CodeVerifier

code = """
import math

def build_agent(sandbox):
    start_x = 10.0
    start_y = 3.0
    
    torso = sandbox.add_beam(x=start_x, y=start_y, width=3.0, height=0.5, density=2.0)
    left_wheel = sandbox.add_wheel(x=start_x - 1.5, y=start_y - 0.5, radius=0.8, density=1.0)
    right_wheel = sandbox.add_wheel(x=start_x + 1.5, y=start_y - 0.5, radius=0.8, density=1.0)
    
    j1 = sandbox.add_joint(torso, left_wheel, (start_x - 1.5, start_y - 0.5), type='pivot')
    j2 = sandbox.add_joint(torso, right_wheel, (start_x + 1.5, start_y - 0.5), type='pivot')
    
    sandbox._walker_joints = [j1, j2]
    return torso

def agent_action(sandbox, agent_body, step_count):
    if not hasattr(sandbox, '_walker_joints'): return
    
    for j in sandbox._walker_joints:
        sandbox.set_motor(j, -15.0, 500.0)
        if step_count % 100 == 0:
            print(f"Step {step_count}: joint angle = {j.angle}")
"""

verifier = CodeVerifier(
    task_name="Category2_Kinematics_Linkages/K_01",
    max_steps=6000,
    env_overrides={}
)

success, score, metrics, error = verifier.verify_code(code=code, headless=True)
print("Initial Env:")
print("Success:", success, "Score:", score)
