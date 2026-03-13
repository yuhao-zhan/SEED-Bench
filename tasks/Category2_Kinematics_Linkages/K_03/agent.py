import math

import Box2D

def build_agent(sandbox):
    gantry = sandbox.get_anchor_for_gripper()
    base = sandbox.add_beam(x=5.0, y=9.8, width=0.6, height=0.4, angle=0, density=1.5)
    sandbox.add_joint(gantry, base, (5.0, 10.0), type='rigid')
    slider = sandbox.add_beam(x=5.0, y=7.6, width=0.35, height=2.0, angle=0, density=0.6)
    sandbox.set_fixed_rotation(slider, True)
    sandbox.add_joint(base, slider, (5.0, 9.6), type='slider', axis=(0, -1), lower_translation=0.0, upper_translation=7.0, enable_motor=True, motor_speed=1.2, max_motor_force=10000.0)
    left_finger = sandbox.add_beam(x=4.72, y=5.35, width=0.28, height=0.5, angle=0.1 * math.pi, density=0.5)
    sandbox.set_material_properties(left_finger, restitution=0.05, friction=0.95)
    sandbox.add_joint(slider, left_finger, (5.0, 5.6), type='pivot', enable_motor=True, motor_speed=0.0, max_motor_torque=5000.0)
    right_finger = sandbox.add_beam(x=5.28, y=5.35, width=0.28, height=0.5, angle=-0.1 * math.pi, density=0.5)
    sandbox.set_material_properties(right_finger, restitution=0.05, friction=0.95)
    sandbox.add_joint(slider, right_finger, (5.0, 5.6), type='pivot', enable_motor=True, motor_speed=0.0, max_motor_torque=5000.0)
    s_j = [j for j in sandbox.joints if type(j).__name__ == 'b2PrismaticJoint'][0]
    pivots = [j for j in sandbox.joints if type(j).__name__ == 'b2RevoluteJoint']
    sandbox._gripper_joints = {'slider': s_j, 'left_finger': pivots[0], 'right_finger': pivots[1]}
    return base

def agent_action(sandbox, agent_body, step_count):
    if not hasattr(sandbox, '_gripper_joints'): return
    joints = sandbox._gripper_joints
    t = step_count / 60.0
    if t < 5.0:
        sandbox.set_slider_motor(joints['slider'], 1.2, 10000.0)
        sandbox.set_motor(joints['left_finger'], 0.0, 5000.0)
        sandbox.set_motor(joints['right_finger'], 0.0, 5000.0)
    elif t < 7.0:
        sandbox.set_slider_motor(joints['slider'], 0.0, 10000.0)
        sandbox.set_motor(joints['left_finger'], 2.0, 5000.0)
        sandbox.set_motor(joints['right_finger'], -2.0, 5000.0)
    elif t < 10.0:
        sandbox.set_slider_motor(joints['slider'], 0.0, 10000.0)
        sandbox.set_motor(joints['left_finger'], 4.0, 5000.0)
        sandbox.set_motor(joints['right_finger'], -4.0, 5000.0)
    else:
        sandbox.set_slider_motor(joints['slider'], -1.8, 10000.0)
        sandbox.set_motor(joints['left_finger'], 4.0, 5000.0)
        sandbox.set_motor(joints['right_finger'], -4.0, 5000.0)

def build_agent_stage_1(sandbox):
    gantry = sandbox.get_anchor_for_gripper()
    base = sandbox.add_beam(x=5.0, y=9.8, width=0.6, height=0.4, angle=0, density=2.0)
    sandbox.add_joint(gantry, base, (5.0, 10.0), type='rigid')
    slider = sandbox.add_beam(x=5.0, y=8.0, width=0.4, height=0.4, angle=0, density=2.0)
    sandbox.set_fixed_rotation(slider, True)
    sandbox.add_joint(base, slider, (5.0, 9.6), type='slider', axis=(0, -1), lower_translation=0.0, upper_translation=10.0, enable_motor=True, motor_speed=0.0, max_motor_force=100000.0)
    l_finger = sandbox.add_beam(x=4.7, y=6.0, width=0.15, height=2.0, angle=0, density=5.0)
    sandbox.set_material_properties(l_finger, friction=1.0)
    sandbox.add_joint(slider, l_finger, (4.7, 8.0), type='pivot', enable_motor=True, max_motor_torque=100000.0, lower_limit=-0.2*math.pi, upper_limit=0.2*math.pi)
    r_finger = sandbox.add_beam(x=5.3, y=6.0, width=0.15, height=2.0, angle=0, density=5.0)
    sandbox.set_material_properties(r_finger, friction=1.0)
    sandbox.add_joint(slider, r_finger, (5.3, 8.0), type='pivot', enable_motor=True, max_motor_torque=100000.0, lower_limit=-0.2*math.pi, upper_limit=0.2*math.pi)
    pivots = [j for j in sandbox.joints if type(j).__name__ == 'b2RevoluteJoint']
    sliders = [j for j in sandbox.joints if type(j).__name__ == 'b2PrismaticJoint']
    sandbox._gripper_joints = {'slider': sliders[0], 'left_finger': pivots[0], 'right_finger': pivots[1]}
    return base

def agent_action_stage_1(sandbox, agent_body, step_count):
    if not hasattr(sandbox, '_gripper_joints'): return
    joints = sandbox._gripper_joints
    t = step_count / 60.0
    if t < 3.0:
        sandbox.set_slider_motor(joints['slider'], 1.2, 50000.0)
        sandbox.set_motor(joints['left_finger'], -0.5, 20000.0)
        sandbox.set_motor(joints['right_finger'], 0.5, 20000.0)
    elif t < 6.0:
        sandbox.set_slider_motor(joints['slider'], 0.0, 50000.0)
        sandbox.set_motor(joints['left_finger'], 1.5, 100000.0)
        sandbox.set_motor(joints['right_finger'], -1.5, 100000.0)
    else:
        sandbox.set_slider_motor(joints['slider'], -2.0, 100000.0)
        sandbox.set_motor(joints['left_finger'], 1.0, 100000.0)
        sandbox.set_motor(joints['right_finger'], -1.0, 100000.0)

def build_agent_stage_2(sandbox):
    gantry = sandbox.get_anchor_for_gripper()
    base = sandbox.add_beam(x=5.0, y=9.8, width=0.6, height=0.4, angle=0, density=2.0)
    sandbox.add_joint(gantry, base, (5.0, 10.0), type='rigid')
    slider = sandbox.add_beam(x=5.0, y=8.0, width=0.4, height=0.4, angle=0, density=2.0)
    sandbox.set_fixed_rotation(slider, True)
    sandbox.add_joint(base, slider, (5.0, 9.6), type='slider', axis=(0,-1), lower_translation=0.0, upper_translation=10.0, enable_motor=True, motor_speed=0.0, max_motor_force=100000.0)
    l_finger = sandbox.add_beam(x=4.7, y=6.0, width=0.15, height=2.0, angle=0, density=5.0)
    sandbox.set_material_properties(l_finger, friction=1.0)
    sandbox.add_joint(slider, l_finger, (4.7, 8.0), type='pivot', enable_motor=True, max_motor_torque=100000.0, lower_limit=-0.2*math.pi, upper_limit=0.2*math.pi)
    r_finger = sandbox.add_beam(x=5.3, y=6.0, width=0.15, height=2.0, angle=0, density=5.0)
    sandbox.set_material_properties(r_finger, friction=1.0)
    sandbox.add_joint(slider, r_finger, (5.3, 8.0), type='pivot', enable_motor=True, max_motor_torque=100000.0, lower_limit=-0.2*math.pi, upper_limit=0.2*math.pi)
    pivots = [j for j in sandbox.joints if type(j).__name__ == 'b2RevoluteJoint']
    sliders = [j for j in sandbox.joints if type(j).__name__ == 'b2PrismaticJoint']
    sandbox._gripper_joints = {'slider': sliders[0], 'left_finger': pivots[0], 'right_finger': pivots[1]}
    return base

def agent_action_stage_2(sandbox, agent_body, step_count):
    if not hasattr(sandbox, '_gripper_joints'): return
    joints = sandbox._gripper_joints
    t = step_count / 60.0
    if t < 3.0:
        sandbox.set_slider_motor(joints['slider'], 1.2, 50000.0)
        sandbox.set_motor(joints['left_finger'], -0.5, 20000.0)
        sandbox.set_motor(joints['right_finger'], 0.5, 20000.0)
    elif t < 6.0:
        sandbox.set_slider_motor(joints['slider'], 0.0, 50000.0)
        sandbox.set_motor(joints['left_finger'], 1.5, 100000.0)
        sandbox.set_motor(joints['right_finger'], -1.5, 100000.0)
    else:
        sandbox.set_slider_motor(joints['slider'], -2.0, 100000.0)
        sandbox.set_motor(joints['left_finger'], 1.0, 100000.0)
        sandbox.set_motor(joints['right_finger'], -1.0, 100000.0)

def build_agent_stage_3(sandbox):
    gantry = sandbox.get_anchor_for_gripper()
    base = sandbox.add_beam(x=5.0, y=9.8, width=0.6, height=0.4, angle=0, density=2.0)
    sandbox.add_joint(gantry, base, (5.0, 10.0), type='rigid')
    slider = sandbox.add_beam(x=5.0, y=8.0, width=0.4, height=0.4, angle=0, density=2.0)
    sandbox.set_fixed_rotation(slider, True)
    sandbox.add_joint(base, slider, (5.0, 9.6), type='slider', axis=(0,-1), lower_translation=0.0, upper_translation=10.0, enable_motor=True, motor_speed=0.0, max_motor_force=100000.0)
    l_finger = sandbox.add_beam(x=4.7, y=6.0, width=0.15, height=2.0, angle=0, density=5.0)
    sandbox.set_material_properties(l_finger, friction=1.0)
    sandbox.add_joint(slider, l_finger, (4.7, 8.0), type='pivot', enable_motor=True, max_motor_torque=100000.0, lower_limit=-0.2*math.pi, upper_limit=0.2*math.pi)
    r_finger = sandbox.add_beam(x=5.3, y=6.0, width=0.15, height=2.0, angle=0, density=5.0)
    sandbox.set_material_properties(r_finger, friction=1.0)
    sandbox.add_joint(slider, r_finger, (5.3, 8.0), type='pivot', enable_motor=True, max_motor_torque=100000.0, lower_limit=-0.2*math.pi, upper_limit=0.2*math.pi)
    pivots = [j for j in sandbox.joints if type(j).__name__ == 'b2RevoluteJoint']
    sliders = [j for j in sandbox.joints if type(j).__name__ == 'b2PrismaticJoint']
    sandbox._gripper_joints = {'slider': sliders[0], 'left_finger': pivots[0], 'right_finger': pivots[1]}
    return base

def agent_action_stage_3(sandbox, agent_body, step_count):
    if not hasattr(sandbox, '_gripper_joints'): return
    joints = sandbox._gripper_joints
    t = step_count / 60.0
    if t < 3.0:
        sandbox.set_slider_motor(joints['slider'], 1.2, 50000.0)
        sandbox.set_motor(joints['left_finger'], -0.5, 20000.0)
        sandbox.set_motor(joints['right_finger'], 0.5, 20000.0)
    elif t < 6.0:
        sandbox.set_slider_motor(joints['slider'], 0.0, 50000.0)
        sandbox.set_motor(joints['left_finger'], 1.5, 100000.0)
        sandbox.set_motor(joints['right_finger'], -1.5, 100000.0)
    else:
        sandbox.set_slider_motor(joints['slider'], -2.0, 100000.0)
        sandbox.set_motor(joints['left_finger'], 1.0, 100000.0)
        sandbox.set_motor(joints['right_finger'], -1.0, 100000.0)

def build_agent_stage_4(sandbox):
    gantry = sandbox.get_anchor_for_gripper()
    base = sandbox.add_beam(x=5.0, y=9.8, width=0.6, height=0.4, angle=0, density=2.0)
    sandbox.add_joint(gantry, base, (5.0, 10.0), type='rigid')
    slider = sandbox.add_beam(x=5.0, y=8.0, width=0.4, height=0.4, angle=0, density=2.0)
    sandbox.set_fixed_rotation(slider, True)
    sandbox.add_joint(base, slider, (5.0, 9.6), type='slider', axis=(0,-1), lower_translation=0.0, upper_translation=10.0, enable_motor=True, motor_speed=0.0, max_motor_force=100000.0)
    l_finger = sandbox.add_beam(x=4.7, y=6.0, width=0.15, height=2.0, angle=0, density=5.0)
    sandbox.set_material_properties(l_finger, friction=1.0)
    sandbox.add_joint(slider, l_finger, (4.7, 8.0), type='pivot', enable_motor=True, max_motor_torque=100000.0, lower_limit=-0.2*math.pi, upper_limit=0.2*math.pi)
    r_finger = sandbox.add_beam(x=5.3, y=6.0, width=0.15, height=2.0, angle=0, density=5.0)
    sandbox.set_material_properties(r_finger, friction=1.0)
    sandbox.add_joint(slider, r_finger, (5.3, 8.0), type='pivot', enable_motor=True, max_motor_torque=100000.0, lower_limit=-0.2*math.pi, upper_limit=0.2*math.pi)
    pivots = [j for j in sandbox.joints if type(j).__name__ == 'b2RevoluteJoint']
    sliders = [j for j in sandbox.joints if type(j).__name__ == 'b2PrismaticJoint']
    sandbox._gripper_joints = {'slider': sliders[0], 'left_finger': pivots[0], 'right_finger': pivots[1]}
    return base

def agent_action_stage_4(sandbox, agent_body, step_count):
    if not hasattr(sandbox, '_gripper_joints'): return
    joints = sandbox._gripper_joints
    t = step_count / 60.0
    if t < 3.0:
        sandbox.set_slider_motor(joints['slider'], 1.2, 50000.0)
        sandbox.set_motor(joints['left_finger'], -0.5, 20000.0)
        sandbox.set_motor(joints['right_finger'], 0.5, 20000.0)
    elif t < 6.0:
        sandbox.set_slider_motor(joints['slider'], 0.0, 50000.0)
        sandbox.set_motor(joints['left_finger'], 1.5, 100000.0)
        sandbox.set_motor(joints['right_finger'], -1.5, 100000.0)
    else:
        sandbox.set_slider_motor(joints['slider'], -2.0, 100000.0)
        sandbox.set_motor(joints['left_finger'], 1.0, 100000.0)
        sandbox.set_motor(joints['right_finger'], -1.0, 100000.0)
