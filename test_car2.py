import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from evaluation.verifier import CodeVerifier

code = """
import math

def build_agent(sandbox):
    start_x = 10.0
    start_y = 2.0
    
    torso = sandbox.add_beam(x=start_x, y=start_y, width=2.5, height=0.4, density=2.0)
    
    # Square wheels!
    w1 = sandbox.add_beam(x=start_x - 1.0, y=start_y - 0.5, width=0.8, height=0.8, density=1.0)
    w2 = sandbox.add_beam(x=start_x + 1.0, y=start_y - 0.5, width=0.8, height=0.8, density=1.0)
    
    j1 = sandbox.add_joint(torso, w1, (start_x - 1.0, start_y - 0.5), type='pivot', lower_limit=0)
    j2 = sandbox.add_joint(torso, w2, (start_x + 1.0, start_y - 0.5), type='pivot', lower_limit=0)
    
    sandbox._walker_joints = [j1, j2]
    return torso

def agent_action(sandbox, agent_body, step_count):
    if not hasattr(sandbox, '_walker_joints'): return
    
    for j in sandbox._walker_joints:
        sandbox.set_motor(j, -15.0, 800.0)
"""

verifier = CodeVerifier(
    task_name="Category2_Kinematics_Linkages/K_01",
    max_steps=6000,
    env_overrides={}
)

success, score, metrics, error = verifier.verify_code(code=code, headless=True)
print("Initial Env:")
print("Success:", success, "Score:", score)
print("Metrics:", metrics)
