# EVOLVE-BLOCK-START
def build_agent(sandbox):
    '''Evolve this function to solve the task.'''
    # Attach base to gantry at (5.0, 10.0)
    gantry = sandbox.get_anchor_for_gripper()
    base = sandbox.add_beam(x=5.0, y=10.0, width=0.5, height=0.2, density=1.0)
    sandbox.add_joint(gantry, base, (5.0, 10.0), type='rigid')
    
    # Create arm as vertical slider joint
    arm = sandbox.add_beam(x=5.0, y=10.0, width=0.1, height=0.1, density=1.0)
    slider_joint = sandbox.add_joint(base, arm, (5.0, 10.0), 
                                    type='slider', 
                                    axis=(0, -1), 
                                    lower_translation=0, 
                                    upper_translation=8.0, 
                                    enable_motor=True, 
                                    motor_speed=0.0, 
                                    max_motor_force=5000.0)
    
    # Create fingers with pivot joints
    finger1 = sandbox.add_beam(x=5.0, y=8.0, width=0.1, height=0.1, density=1.0)
    finger2 = sandbox.add_beam(x=5.0, y=8.0, width=0.1, height=0.1, density=1.0)
    
    # Connect fingers to arm end
    joint1 = sandbox.add_joint(arm, finger1, (5.0, 8.0), type='pivot', 
                              lower_limit=-1.57, upper_limit=1.57, 
                              enable_motor=True, motor_speed=0.0, 
                              max_motor_torque=100.0)
    joint2 = sandbox.add_joint(arm, finger2, (5.0, 8.0), type='pivot', 
                              lower_limit=-1.57, upper_limit=1.57, 
                              enable_motor=True, motor_speed=0.0, 
                              max_motor_torque=100.0)
    
    # Set high friction for fingers
    sandbox.set_material_properties(finger1, friction=0.9)
    sandbox.set_material_properties(finger2, friction=0.9)
    
    return {
        'base': base,
        'arm': arm,
        'slider_joint': slider_joint,
        'finger1': finger1,
        'finger2': finger2,
        'joint1': joint1,
        'joint2': joint2
    }

def agent_action(sandbox, agent_body, step_count):
    # Phase 1: Reach - lower arm to object level
    if step_count < 100:
        sandbox.set_slider_motor(agent_body['slider_joint'], speed=0.5, max_force=5000.0)
    # Phase 2: Grasp - close fingers
    elif step_count < 200:
        sandbox.set_motor(agent_body['joint1'], motor_speed=1.0, max_torque=100.0)
        sandbox.set_motor(agent_body['joint2'], motor_speed=-1.0, max_torque=100.0)
    # Phase 3: Lift - raise arm
    else:
        sandbox.set_slider_motor(agent_body['slider_joint'], speed=-0.5, max_force=5000.0)
# EVOLVE-BLOCK-END
