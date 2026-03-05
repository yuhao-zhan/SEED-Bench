"""
K-03: The Gripper task — REFERENCE AGENT (for testing only).

Vertical gripper: base fixed on gantry, slider moves straight up/down (no rotation),
wrist + two fingers at bottom of slider for grasp. Sequence: lower → grasp → lift.
"""
import math
import Box2D

OBJ_X = 5.0
OBJ_REST_Y = 2.0
GANTRY_Y = 10.0


def build_agent(sandbox):
    """
    Reference gripper: base on gantry, vertical slider (prismatic), wrist + two fingers.
    No rotating arm — only vertical伸缩 (up/down).
    """
    gantry = sandbox.get_anchor_for_gripper()
    if gantry is None:
        raise ValueError("Gantry anchor not found. Use get_anchor_for_gripper() to attach base.")

    base_x, base_y = 5.0, GANTRY_Y - 0.2
    base_w, base_h = 0.6, 0.4
    base = sandbox.add_beam(x=base_x, y=base_y, width=base_w, height=base_h, angle=0, density=1.5)
    sandbox.set_material_properties(base, restitution=0.05, friction=0.6)
    sandbox.add_joint(gantry, base, (base_x, GANTRY_Y), type='rigid')

    pivot_y = base_y - base_h / 2

    slider_half_h = 2.0
    slider_center_y = pivot_y - slider_half_h
    stroke = 7.0
    slider = sandbox.add_beam(
        x=base_x, y=slider_center_y, width=0.35, height=slider_half_h, angle=0, density=0.6
    )
    slider.fixedRotation = True
    sandbox.set_material_properties(slider, restitution=0.05, friction=0.5)
    sandbox.add_joint(
        base, slider, (base_x, pivot_y), type='slider',
        axis=(0, -1),
        lower_translation=0.0,
        upper_translation=stroke,
        enable_motor=True,
        motor_speed=1.2,
        max_motor_force=10000.0,
    )
    wrist_y = slider_center_y - slider_half_h
    finger_w, finger_h = 0.28, 0.5
    finger_density = 0.5
    finger_offset_x = 0.28



    left_finger = sandbox.add_beam(
        x=base_x - finger_offset_x, y=wrist_y - finger_h / 2, width=finger_w, height=finger_h,
        angle=0.1 * math.pi, density=finger_density
    )
    sandbox.set_material_properties(left_finger, restitution=0.05, friction=0.95)
    sandbox.add_joint(slider, left_finger, (base_x, wrist_y), type='pivot', enable_motor=True, motor_speed=0.0, max_motor_torque=5000.0)

    right_finger = sandbox.add_beam(
        x=base_x + finger_offset_x, y=wrist_y - finger_h / 2, width=finger_w, height=finger_h,
        angle=-0.1 * math.pi, density=finger_density
    )
    sandbox.set_material_properties(right_finger, restitution=0.05, friction=0.95)
    sandbox.add_joint(slider, right_finger, (base_x, wrist_y), type='pivot', enable_motor=True, motor_speed=0.0, max_motor_torque=5000.0)

    slider_joint = left_finger_joint = right_finger_joint = None
    for joint in sandbox.joints:
        if type(joint).__name__ == 'b2PrismaticJoint':
            if joint.bodyA == base and joint.bodyB == slider:
                slider_joint = joint
        elif (joint.bodyA == slider and joint.bodyB == left_finger) or (joint.bodyB == slider and joint.bodyA == left_finger):
            left_finger_joint = joint
        elif (joint.bodyA == slider and joint.bodyB == right_finger) or (joint.bodyB == slider and joint.bodyA == right_finger):
            right_finger_joint = joint

    sandbox._gripper_joints = {
        'slider': slider_joint,
        'left_finger': left_finger_joint,
        'right_finger': right_finger_joint,
    }

    total_mass = sandbox.get_structure_mass()
    if total_mass > sandbox.MAX_STRUCTURE_MASS:
        raise ValueError(f"Structure mass {total_mass:.2f}kg exceeds limit {sandbox.MAX_STRUCTURE_MASS}kg")
    print(f"Gripper constructed: {len(sandbox.bodies)} beams, {len(sandbox.joints)} joints, {total_mass:.2f}kg (vertical slider, no rotation)")
    return base


def agent_action(sandbox, agent_body, step_count):
    """
    Lower → grasp → lift.
    """
    if not hasattr(sandbox, '_gripper_joints'):
        return
    joints = sandbox._gripper_joints
    t = step_count / 60.0
    slider_j = joints.get('slider')
    max_force = 10000.0

    obj_pos = sandbox.get_object_position()
    obj_y = obj_pos[1] if obj_pos else 0.0


    if t < 5.0:
        if slider_j is not None:
            sandbox.set_slider_motor(slider_j, 1.2, max_force)
        if joints.get('left_finger'):
            sandbox.set_motor(joints['left_finger'], 0.0, 100.0)
        if joints.get('right_finger'):
            sandbox.set_motor(joints['right_finger'], 0.0, 100.0)

    elif t < 7.0:
        if slider_j is not None:
            sandbox.set_slider_motor(slider_j, 0.0, max_force)

    elif t < 10.0:
        if slider_j is not None:
            sandbox.set_slider_motor(slider_j, 0.0, max_force)
        grip_torque = 5000.0
        if joints.get('left_finger'):
            sandbox.set_motor(joints['left_finger'], 4.0, grip_torque)
        if joints.get('right_finger'):
            sandbox.set_motor(joints['right_finger'], -4.0, grip_torque)

    else:
        if slider_j is not None:
            sandbox.set_slider_motor(slider_j, -2.0, max_force)
        finger_torque = 5000.0
        if joints.get('left_finger'):
            sandbox.set_motor(joints['left_finger'], 2.0, finger_torque)
        if joints.get('right_finger'):
            sandbox.set_motor(joints['right_finger'], -2.0, finger_torque)
