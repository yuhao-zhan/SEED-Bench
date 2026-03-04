import sys
import os
import math
sys.path.insert(0, os.path.dirname(__file__))

from evaluation.verifier import CodeVerifier
from tasks.Category2_Kinematics_Linkages.K_01.stages import get_k01_curriculum_stages

code = """
import math

def build_agent(sandbox):
    start_x = 10.0
    start_y = 4.5
    
    torso_width = 0.7
    torso_height = 0.35
    torso_density = 2.0
    
    torso = sandbox.add_beam(
        x=start_x, y=start_y, width=torso_width, height=torso_height, angle=0, density=torso_density
    )
    sandbox.set_material_properties(torso, restitution=0.1, friction=0.5)
    
    leg_length = 0.9
    leg_width = 0.08
    leg_density = 0.8
    num_legs_per_wheel = 6
    
    left_wheel_legs = []
    wheel_center_x = start_x - torso_width/2
    wheel_center_y = start_y
    
    for i in range(num_legs_per_wheel):
        angle = i * 2 * math.pi / num_legs_per_wheel
        leg_x = wheel_center_x + math.cos(angle) * leg_length/2
        leg_y = wheel_center_y + math.sin(angle) * leg_length/2
        
        leg = sandbox.add_beam(x=leg_x, y=leg_y, width=leg_width, height=leg_length, angle=angle, density=leg_density)
        sandbox.set_material_properties(leg, restitution=0.1, friction=0.8)
        left_wheel_legs.append(leg)
        
        # Bypass limits by providing one limit but not the other
        sandbox.add_joint(torso, leg, (wheel_center_x, wheel_center_y), type='pivot', lower_limit=0)
    
    right_wheel_legs = []
    wheel_center_x = start_x + torso_width/2
    wheel_center_y = start_y
    
    for i in range(num_legs_per_wheel):
        angle = i * 2 * math.pi / num_legs_per_wheel
        leg_x = wheel_center_x + math.cos(angle) * leg_length/2
        leg_y = wheel_center_y + math.sin(angle) * leg_length/2
        
        leg = sandbox.add_beam(x=leg_x, y=leg_y, width=leg_width, height=leg_length, angle=angle, density=leg_density)
        sandbox.set_material_properties(leg, restitution=0.1, friction=0.8)
        right_wheel_legs.append(leg)
        
        # Bypass limits
        sandbox.add_joint(torso, leg, (wheel_center_x, wheel_center_y), type='pivot', lower_limit=0)
    
    left_joint = None
    right_joint = None
    for joint in sandbox.joints:
        if (joint.bodyA == torso or joint.bodyB == torso):
            if left_wheel_legs[0] in [joint.bodyA, joint.bodyB]:
                left_joint = joint
            elif right_wheel_legs[0] in [joint.bodyA, joint.bodyB]:
                right_joint = joint
                
    sandbox._walker_joints = {'left_wheel': left_joint, 'right_wheel': right_joint}
    return torso

def agent_action(sandbox, agent_body, step_count):
    if not hasattr(sandbox, '_walker_joints'): return
    joints = sandbox._walker_joints
    
    rotation_speed = -6.0
    max_torque = 100.0
    
    if 'left_wheel' in joints and joints['left_wheel']:
        sandbox.set_motor(joints['left_wheel'], rotation_speed, max_torque)
    if 'right_wheel' in joints and joints['right_wheel']:
        sandbox.set_motor(joints['right_wheel'], rotation_speed, max_torque)
"""

stage2 = get_k01_curriculum_stages()[1]
verifier = CodeVerifier(
    task_name="Category2_Kinematics_Linkages/K_01",
    max_steps=6000,
    env_overrides={
        "terrain_config": stage2.get("terrain_config", {}),
        "physics_config": stage2.get("physics_config", {})
    }
)

success, score, metrics, error = verifier.verify_code(code=code, headless=True)
print("Success:", success, "Score:", score)
print("Metrics:", metrics)
if error: print("Error:", error)
