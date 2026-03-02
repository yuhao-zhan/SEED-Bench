"""
K-02: The Climber task Agent module
Reference solution: Climber with suction pads (stick to wall) + rotating legs (push up)
"""
import math


def build_agent(sandbox):
    """
    Build a climber using suction pads (add_pad) to stick to the wall and rotating legs to push up.
    """
    wall_x = 5.0
    start_x = 4.25
    start_y = 2.2   # Start BELOW red line (red line at y=3.5) — must climb up to it
    
    # Main body (torso)
    torso_width = 0.5
    torso_height = 0.8
    torso_density = 2.5
    
    torso = sandbox.add_beam(
        x=start_x,
        y=start_y,
        width=torso_width,
        height=torso_height,
        angle=0,
        density=torso_density
    )
    sandbox.set_material_properties(torso, restitution=0.1, friction=0.8)
    
    # Suction pads on the right side (toward wall) — when active they pull toward wall so we stick
    pad_radius = 0.12
    pad_y_positions = [start_y + 0.2, start_y - 0.2]  # Upper and lower pad
    pad_bodies = []
    for py in pad_y_positions:
        pad_x = start_x + torso_width / 2 + pad_radius  # Just right of torso
        pad = sandbox.add_pad(pad_x, py, radius=pad_radius, density=0.8)
        sandbox.add_joint(torso, pad, (start_x + torso_width / 2, py), type='rigid')
        pad_bodies.append(pad)
    sandbox._climber_pads = pad_bodies
    
    # Leg wheels - push against wall while pads hold us there
    num_legs_per_wheel = 8
    leg_length = 0.8
    leg_width = 0.1
    leg_density = 0.75
    
    # Upper wheel (8 legs)
    upper_wheel_legs = []
    wheel_center_x = start_x + torso_width/2
    wheel_center_y = start_y + torso_height/2
    
    for i in range(num_legs_per_wheel):
        angle = i * 2 * math.pi / num_legs_per_wheel
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
        sandbox.set_material_properties(leg, restitution=0.1, friction=1.0)  # High friction matching wall
        upper_wheel_legs.append(leg)
        
        # Connect to torso
        sandbox.add_joint(
            torso, leg,
            (wheel_center_x, wheel_center_y),
            type='pivot'
        )
    
    # Lower wheel (8 legs)
    lower_wheel_legs = []
    wheel_center_x = start_x + torso_width/2
    wheel_center_y = start_y - torso_height/2
    
    for i in range(num_legs_per_wheel):
        angle = i * 2 * math.pi / num_legs_per_wheel
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
        sandbox.set_material_properties(leg, restitution=0.1, friction=1.0)  # High friction matching wall
        lower_wheel_legs.append(leg)
        
        # Connect to torso
        sandbox.add_joint(
            torso, leg,
            (wheel_center_x, wheel_center_y),
            type='pivot'
        )
    
    # Store joints for motor control
    upper_joint = None
    lower_joint = None
    for joint in sandbox.joints:
        if (joint.bodyA == torso or joint.bodyB == torso):
            if upper_wheel_legs[0] in [joint.bodyA, joint.bodyB]:
                upper_joint = joint
            elif lower_wheel_legs[0] in [joint.bodyA, joint.bodyB]:
                lower_joint = joint
    
    sandbox._climber_joints = {
        'upper': upper_joint,
        'lower': lower_joint,
    }
    
    # Check mass
    total_mass = sandbox.get_structure_mass()
    if total_mass > sandbox.MAX_STRUCTURE_MASS:
        raise ValueError(f"Structure mass {total_mass:.2f}kg exceeds limit {sandbox.MAX_STRUCTURE_MASS}kg")
    
    print(f"Climber constructed: {len(sandbox.bodies)} bodies (beams+pads), {len(sandbox.joints)} joints, {total_mass:.2f}kg")
    
    return torso


def agent_action(sandbox, agent_body, step_count):
    """
    Agent control: keep pads active (stick to wall) and rotate legs to push upward.
    """
    # Pads active → pull toward wall so we stick; enables legs to grip and push up
    if hasattr(sandbox, '_climber_pads'):
        for pad in sandbox._climber_pads:
            sandbox.set_pad_active(pad, True)
    
    if not hasattr(sandbox, '_climber_joints'):
        return
    joints = sandbox._climber_joints
    if not joints:
        return
    
    rotation_speed = 5.0
    max_torque = 100.0
    if 'upper' in joints and joints['upper']:
        sandbox.set_motor(joints['upper'], rotation_speed, max_torque)
    if 'lower' in joints and joints['lower']:
        sandbox.set_motor(joints['lower'], rotation_speed, max_torque)
