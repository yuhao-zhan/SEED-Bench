"""
Basic task Agent module
Contains Agent construction logic and control logic
"""
import math


def build_agent(sandbox):
    """
    Standard entry point for the benchmark.
    Uses build_agent_raw as the default.
    """
    return build_agent_raw(sandbox)


def build_agent_raw(sandbox):
    """
    Minimal design: chassis + 2 wheels + 2 motors
    """
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
    """
    Stage-1: The Ice World - Low friction (0.1)
    Solution: Larger wheels for better obstacle clearance, wide wheelbase, safe speed
    """
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
    """
    Stage-2: The Steep Canyon - Extreme obstacle angles
    Solution: Maximum wheels + ultra-low chassis + asymmetric weight + dynamic speed control
    """
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
    """
    Stage-3: The Mud Pit - Moderate damping (2.0, reduced from 5.0)
    Physics-based solution: Symmetric design with optimized speed control
    Key insight: Lower damping allows faster speeds, but still need to slow on obstacles
    """
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
    """
    Stage-4: The Heavy Planet - High gravity (-30.0)
    Solution: Reduce density significantly, slower speed to prevent rotation, maximum torque
    """
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
    """
    Agent control logic - called by simulation loop at each step

    For Stage-2 (Steep Canyon): Dynamic speed/torque control based on position
    - Phase 1 (x < 15): High speed + high torque - overcome first obstacle
    - Phase 2 (15 < x < 20): Maximum torque - climb steep upward slope (40°)
    - Phase 3 (20 < x < 25): Reduce speed - prepare for steep descent
    - Phase 4 (x > 25): Very low speed - prevent flip on -46° descent

    For Stage-3 (Mud Pit): Dynamic speed control to prevent rotation at obstacles
    - Phase 1 (x < 13): High speed - overcome damping on flat ground
    - Phase 2 (13 < x < 18): Low speed - approach and pass first obstacle safely
    - Phase 3 (18 < x < 23): Moderate speed - between obstacles
    - Phase 4 (23 < x < 28): Low speed - approach and pass second obstacle safely
    - Phase 5 (x > 28): High speed - final push to target

    For other stages (raw, ice_world, etc.): No-op (purely passive control)
    """

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

