"""
K-01: The Walker task Agent module
Reference solution: Stable walker with rotating leg wheels
"""
import math


def build_agent(sandbox):
    """
    Build a stable walker with rotating leg wheels that can move forward.
    
    Design:
    - Torso (main body)
    - Two leg wheels on each side, each with 6 legs for smooth rotation
    - Motors rotate the leg wheels to create forward motion
    """
    # Starting position - higher for stability
    start_x = 10.0
    start_y = 4.5
    
    # Torso dimensions - wider and heavier for better stability
    torso_width = 0.7
    torso_height = 0.35
    torso_density = 2.0  # Heavier torso for stability
    
    # Create torso
    torso = sandbox.add_beam(
        x=start_x,
        y=start_y,
        width=torso_width,
        height=torso_height,
        angle=0,
        density=torso_density
    )
    sandbox.set_material_properties(torso, restitution=0.1, friction=0.5)
    
    # Leg wheel parameters
    leg_length = 0.9  # Moderate length for stability
    leg_width = 0.08
    leg_density = 0.8
    num_legs_per_wheel = 6  # More legs for smoother rotation
    
    # Create left leg wheel
    left_wheel_legs = []
    wheel_center_x = start_x - torso_width/2
    wheel_center_y = start_y
    
    for i in range(num_legs_per_wheel):
        angle = i * 2 * math.pi / num_legs_per_wheel  # Evenly spaced
        leg_x = wheel_center_x + math.cos(angle) * leg_length/2
        leg_y = wheel_center_y + math.sin(angle) * leg_length/2
        
        leg = sandbox.add_beam(
            x=leg_x,
            y=leg_y,
            width=leg_width,
            height=leg_length,
            angle=angle,
            density=leg_density
        )
        sandbox.set_material_properties(leg, restitution=0.1, friction=0.8)
        left_wheel_legs.append(leg)
        
        # Connect to torso at wheel center
        sandbox.add_joint(
            torso, leg,
            (wheel_center_x, wheel_center_y),
            type='pivot'
        )
    
    # Create right leg wheel
    right_wheel_legs = []
    wheel_center_x = start_x + torso_width/2
    wheel_center_y = start_y
    
    for i in range(num_legs_per_wheel):
        angle = i * 2 * math.pi / num_legs_per_wheel  # Evenly spaced
        leg_x = wheel_center_x + math.cos(angle) * leg_length/2
        leg_y = wheel_center_y + math.sin(angle) * leg_length/2
        
        leg = sandbox.add_beam(
            x=leg_x,
            y=leg_y,
            width=leg_width,
            height=leg_length,
            angle=angle,
            density=leg_density
        )
        sandbox.set_material_properties(leg, restitution=0.1, friction=0.8)
        right_wheel_legs.append(leg)
        
        # Connect to torso at wheel center
        sandbox.add_joint(
            torso, leg,
            (wheel_center_x, wheel_center_y),
            type='pivot'
        )
    
    # Store joints for motor control
    left_joint = None
    right_joint = None
    for joint in sandbox.joints:
        if (joint.bodyA == torso or joint.bodyB == torso):
            if left_wheel_legs[0] in [joint.bodyA, joint.bodyB]:
                left_joint = joint
            elif right_wheel_legs[0] in [joint.bodyA, joint.bodyB]:
                right_joint = joint
    
    sandbox._walker_joints = {
        'left_wheel': left_joint,
        'right_wheel': right_joint,
    }
    
    # Check mass
    total_mass = sandbox.get_structure_mass()
    if total_mass > sandbox.MAX_STRUCTURE_MASS:
        raise ValueError(f"Structure mass {total_mass:.2f}kg exceeds limit {sandbox.MAX_STRUCTURE_MASS}kg")
    
    print(f"Walker constructed: {len(sandbox.bodies)} beams, {len(sandbox.joints)} joints, {total_mass:.2f}kg")
    
    return torso


def agent_action(sandbox, agent_body, step_count):
    """
    Agent control logic - rotate leg wheels to create forward motion.
    
    Strategy:
    - Rotate both leg wheels continuously in clockwise direction (negative speed)
    - When legs contact ground and rotate clockwise, they push backward against ground
    - This reaction force pushes the walker forward
    - Use moderate speed for stability
    """
    if not hasattr(sandbox, '_walker_joints'):
        return
    
    joints = sandbox._walker_joints
    if not joints:
        return
    
    # Continuous rotation speed (rad/s)
    # Clockwise rotation (negative) - when leg is below center, it pushes backward
    # This creates forward propulsion
    rotation_speed = -6.0  # Moderate speed for stability
    
    # Set motor speeds on wheel joints
    max_torque = 100.0
    
    # Rotate both wheels clockwise to move forward
    if 'left_wheel' in joints and joints['left_wheel']:
        sandbox.set_motor(joints['left_wheel'], rotation_speed, max_torque)
    if 'right_wheel' in joints and joints['right_wheel']:
        sandbox.set_motor(joints['right_wheel'], rotation_speed, max_torque)
