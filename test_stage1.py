import sys
import os
import math
sys.path.insert(0, os.path.dirname(__file__))

from evaluation.verifier import CodeVerifier
from tasks.Category2_Kinematics_Linkages.K_01.stages import get_k01_curriculum_stages

code = """
import math

def build_agent(sandbox):
    start_x = 25.0
    start_y = 2.0
    torso_width = 2.0
    torso_height = 0.5
    torso = sandbox.add_beam(x=start_x, y=start_y, width=torso_width, height=torso_height, density=2.0)
    
    def create_wheel(cx, cy):
        legs = []
        num_legs = 6
        length = 1.0
        leg0 = sandbox.add_beam(x=cx, y=cy, width=0.1, height=length, angle=0, density=1.0)
        legs.append(leg0)
        pivot = sandbox.add_joint(torso, leg0, (cx, cy), type='pivot', lower_limit=0)
        for i in range(1, num_legs):
            angle = i * math.pi / num_legs
            leg = sandbox.add_beam(x=cx, y=cy, width=0.1, height=length, angle=angle, density=1.0)
            sandbox.add_joint(leg0, leg, (cx, cy), type='rigid')
            legs.append(leg)
        return pivot
        
    sandbox._walker_joints = [create_wheel(start_x - 1.0, start_y), create_wheel(start_x + 1.0, start_y)]
    return torso

def agent_action(sandbox, agent_body, step_count):
    if not hasattr(sandbox, '_walker_joints'): return
    for j in sandbox._walker_joints:
        sandbox.set_motor(j, -10.0, 500.0)
"""

stage = get_k01_curriculum_stages()[0]
verifier = CodeVerifier(
    task_name="Category2_Kinematics_Linkages/K_01",
    max_steps=6000,
    env_overrides={
        "terrain_config": stage.get("terrain_config", {}),
        "physics_config": stage.get("physics_config", {})
    }
)

success, score, metrics, error = verifier.verify_code(code=code, headless=True)
print("Stage 1:")
print("Success:", success, "Score:", score)
print("Metrics:", metrics)
if error: print("Error:", error)
