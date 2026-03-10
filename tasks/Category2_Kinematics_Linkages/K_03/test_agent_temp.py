import math
import Box2D

def build_agent_stage_1(sandbox):
    gantry = sandbox.get_anchor_for_gripper()
    base = sandbox.add_beam(x=5.0, y=9.8, width=0.6, height=0.4, angle=0, density=1.5)
    sandbox.add_joint(gantry, base, (5.0, 10.0), type='rigid')
    
    slider = sandbox.add_beam(x=5.0, y=8.0, width=0.2, height=1.0, angle=0, density=1.0)
    sandbox.set_fixed_rotation(slider, True)
    sandbox.add_joint(base, slider, (5.0, 9.6), type='slider', axis=(0,-1), 
                      lower_translation=-10.0, upper_translation=10.0, 
                      enable_motor=True, motor_speed=0.0, max_motor_force=100000.0)
    
    arm_h = 2.4
    wrist_y = 7.5
    l_arm = sandbox.add_beam(x=4.2, y=wrist_y - arm_h/2, width=0.1, height=arm_h, angle=0, density=1.0)
    sandbox.add_joint(slider, l_arm, (4.2, wrist_y), type='pivot', enable_motor=True, max_motor_torque=100000.0)
    l_foot = sandbox.add_beam(x=4.6, y=wrist_y - arm_h, width=0.8, height=0.1, angle=0, density=1.0)
    sandbox.add_joint(l_arm, l_foot, (4.2, wrist_y - arm_h), type='rigid')
    
    r_arm = sandbox.add_beam(x=5.8, y=wrist_y - arm_h/2, width=0.1, height=arm_h, angle=0, density=1.0)
    sandbox.add_joint(slider, r_arm, (5.8, wrist_y), type='pivot', enable_motor=True, max_motor_torque=100000.0)
    r_foot = sandbox.add_beam(x=5.4, y=wrist_y - arm_h, width=0.8, height=0.1, angle=0, density=1.0)
    sandbox.add_joint(r_arm, r_foot, (5.8, wrist_y - arm_h), type='rigid')
    
    pivots = [j for j in sandbox.joints if type(j).__name__ == 'b2RevoluteJoint']
    sliders = [j for j in sandbox.joints if type(j).__name__ == 'b2PrismaticJoint']
    sandbox._gripper_joints = {'slider': sliders[0], 'left_finger': pivots[0], 'right_finger': pivots[1]}
    return base

def agent_action_stage_1(sandbox, agent_body, step_count):
    if not hasattr(sandbox, '_gripper_joints'): return
    joints = sandbox._gripper_joints
    t = step_count / 60.0
    if t < 3.5:
        sandbox.set_slider_motor(joints['slider'], 1.2, 10000.0)
        sandbox.set_motor(joints['left_finger'], -3.0, 10000.0)
        sandbox.set_motor(joints['right_finger'], 3.0, 10000.0)
    elif t < 5.5:
        sandbox.set_slider_motor(joints['slider'], 0.0, 100000.0)
        sandbox.set_motor(joints['left_finger'], 15.0, 100000.0)
        sandbox.set_motor(joints['right_finger'], -15.0, 100000.0)
    else:
        sandbox.set_slider_motor(joints['slider'], -1.0, 100000.0)
        sandbox.set_motor(joints['left_finger'], 15.0, 100000.0)
        sandbox.set_motor(joints['right_finger'], -15.0, 100000.0)
