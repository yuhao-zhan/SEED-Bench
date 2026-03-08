import math

def build_agent(sandbox):
    return build_agent_raw(sandbox)

def build_agent_raw(sandbox):
    GROUND_TOP = 1.0
    WHEEL_RADIUS = 1.5
    wheel_y = GROUND_TOP + WHEEL_RADIUS
    chassis = sandbox.add_beam(x=5.0, y=wheel_y + 0.2, width=5.0, height=0.4, density=3.0)
    wheel1 = sandbox.add_wheel(x=3.2, y=wheel_y, radius=WHEEL_RADIUS, friction=4.0, density=1.0)
    wheel2 = sandbox.add_wheel(x=6.8, y=wheel_y, radius=WHEEL_RADIUS, friction=4.0, density=1.0)
    sandbox.connect(chassis, wheel1, anchor_x=3.2, anchor_y=wheel_y, motor_speed=-6.0, max_torque=1800.0)
    sandbox.connect(chassis, wheel2, anchor_x=6.8, anchor_y=wheel_y, motor_speed=-6.0, max_torque=1800.0)
    is_valid, errors = sandbox.validate_design(chassis)
    if not is_valid:
        raise ValueError(f"Design validation failed: {errors}")
    return chassis

def build_agent_ice_world(sandbox):
    GROUND_TOP = 1.0
    WHEEL_RADIUS = 1.8
    wheel_y = GROUND_TOP + WHEEL_RADIUS
    chassis = sandbox.add_beam(x=5.0, y=wheel_y + 0.0, width=7.5, height=0.2, density=1.5)
    wheel1 = sandbox.add_wheel(x=1.5, y=wheel_y, radius=WHEEL_RADIUS, friction=5.0, density=1.0)
    wheel2 = sandbox.add_wheel(x=8.5, y=wheel_y, radius=WHEEL_RADIUS, friction=5.0, density=1.0)
    sandbox.connect(chassis, wheel1, anchor_x=1.5, anchor_y=wheel_y, motor_speed=-3.2, max_torque=2000.0)
    sandbox.connect(chassis, wheel2, anchor_x=8.5, anchor_y=wheel_y, motor_speed=-3.2, max_torque=2000.0)
    is_valid, errors = sandbox.validate_design(chassis)
    if not is_valid:
        raise ValueError(f"Design validation failed: {errors}")
    return chassis

def build_agent_steep_canyon(sandbox):
    GROUND_TOP = 1.0
    WHEEL_RADIUS = 2.0
    wheel_y = GROUND_TOP + WHEEL_RADIUS
    chassis = sandbox.add_beam(x=5.0, y=wheel_y + 0.0, width=5.5, height=0.2, density=4.0)
    front_wheel = sandbox.add_wheel(x=2.5, y=wheel_y, radius=WHEEL_RADIUS, friction=5.0, density=1.5)
    rear_wheel = sandbox.add_wheel(x=7.5, y=wheel_y, radius=WHEEL_RADIUS, friction=5.0, density=4.0)
    front_joint = sandbox.connect(chassis, front_wheel, anchor_x=2.5, anchor_y=wheel_y, motor_speed=-3.0, max_torque=1500.0)
    rear_joint = sandbox.connect(chassis, rear_wheel, anchor_x=7.5, anchor_y=wheel_y, motor_speed=-2.8, max_torque=1500.0)
    sandbox._front_joint = front_joint
    sandbox._rear_joint = rear_joint
    is_valid, errors = sandbox.validate_design(chassis)
    if not is_valid:
        raise ValueError(f"Design validation failed: {errors}")
    return chassis

def build_agent_mud_pit(sandbox):
    GROUND_TOP = 1.0
    WHEEL_RADIUS = 1.8
    wheel_y = GROUND_TOP + WHEEL_RADIUS
    chassis = sandbox.add_beam(x=5.0, y=wheel_y + 0.0, width=7.5, height=0.2, density=1.5)
    front_wheel = sandbox.add_wheel(x=1.5, y=wheel_y, radius=WHEEL_RADIUS, friction=5.0, density=1.0)
    rear_wheel = sandbox.add_wheel(x=8.5, y=wheel_y, radius=WHEEL_RADIUS, friction=5.0, density=1.0)
    front_joint = sandbox.connect(chassis, front_wheel, anchor_x=1.5, anchor_y=wheel_y, motor_speed=-3.0, max_torque=2000.0)
    rear_joint = sandbox.connect(chassis, rear_wheel, anchor_x=8.5, anchor_y=wheel_y, motor_speed=-3.0, max_torque=2000.0)
    sandbox._mud_pit_front_joint = front_joint
    sandbox._mud_pit_rear_joint = rear_joint
    is_valid, errors = sandbox.validate_design(chassis)
    if not is_valid:
        raise ValueError(f"Design validation failed: {errors}")
    return chassis

def build_agent_heavy_planet(sandbox):
    GROUND_TOP = 1.0
    WHEEL_RADIUS = 1.5
    wheel_y = GROUND_TOP + WHEEL_RADIUS
    chassis = sandbox.add_beam(x=5.0, y=wheel_y + 0.15, width=5.0, height=0.3, density=1.0)
    wheel1 = sandbox.add_wheel(x=3.2, y=wheel_y, radius=WHEEL_RADIUS, friction=4.0, density=0.3)
    wheel2 = sandbox.add_wheel(x=6.8, y=wheel_y, radius=WHEEL_RADIUS, friction=4.0, density=0.3)
    sandbox.connect(chassis, wheel1, anchor_x=3.2, anchor_y=wheel_y, motor_speed=-5.0, max_torque=2000.0)
    sandbox.connect(chassis, wheel2, anchor_x=6.8, anchor_y=wheel_y, motor_speed=-5.0, max_torque=2000.0)
    is_valid, errors = sandbox.validate_design(chassis)
    if not is_valid:
        raise ValueError(f"Design validation failed: {errors}")
    return chassis

def agent_action(sandbox, agent_body, step_count):
    if hasattr(sandbox, '_front_joint') and hasattr(sandbox, '_rear_joint'):
        current_x = agent_body.position.x
        if current_x < 15.0:
            front_speed = -3.5
            rear_speed = -3.3
            torque = 2000.0
        elif current_x < 20.0:
            front_speed = -3.0
            rear_speed = -2.8
            torque = 2000.0
        elif current_x < 25.0:
            front_speed = -2.0
            rear_speed = -1.8
            torque = 1500.0
        else:
            front_speed = -1.2
            rear_speed = -1.0
            torque = 2000.0
        sandbox._front_joint.motorSpeed = front_speed
        sandbox._front_joint.maxMotorTorque = torque
        sandbox._rear_joint.motorSpeed = rear_speed
        sandbox._rear_joint.maxMotorTorque = torque
    elif hasattr(sandbox, '_mud_pit_front_joint') and hasattr(sandbox, '_mud_pit_rear_joint'):
        current_x = agent_body.position.x
        if current_x < 12.0:
            speed = -3.5
        elif current_x < 18.0:
            speed = -2.5
        elif current_x < 23.0:
            speed = -3.5
        elif current_x < 28.0:
            speed = -2.2
        else:
            speed = -3.5
        torque = 2000.0
        sandbox._mud_pit_front_joint.motorSpeed = speed
        sandbox._mud_pit_front_joint.maxMotorTorque = torque
        sandbox._mud_pit_rear_joint.motorSpeed = speed
        sandbox._mud_pit_rear_joint.maxMotorTorque = torque
