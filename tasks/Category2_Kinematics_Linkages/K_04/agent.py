"""
K-04: The Pusher task Agent module
Reference solution: Heavy rear ballast + front wheels. Ballast keeps front wheels grounded when pushing.
"""
import math

GROUND_TOP = 1.0
OBJECT_LEFT = 7.5   # object left face (object center at 8.0, width 1.0)


def build_agent(sandbox):
    """
    Build a pusher: chassis + heavy rear ballast + front wheels.
    Ballast counteracts push reaction torque to keep wheels on ground.
    """
    if hasattr(sandbox, 'remove_initial_template'):
        sandbox.remove_initial_template()

    wheel_radius = 0.22
    wheel_y = GROUND_TOP + wheel_radius
    chassis_h = 0.2

    chassis_w = 2.2
    chassis_right = 4.6
    chassis_cx = chassis_right - chassis_w / 2
    chassis_cy = wheel_y + chassis_h / 2 + 0.05
    chassis = sandbox.add_beam(
        x=chassis_cx, y=chassis_cy,
        width=chassis_w, height=chassis_h,
        angle=0, density=2.0
    )
    sandbox.set_material_properties(chassis, restitution=0.0, friction=0.9)

    # Heavy rear ballast to keep front wheels down when pushing
    ballast_cx = chassis_cx - chassis_w / 2 + 0.5
    ballast = sandbox.add_beam(
        x=ballast_cx, y=chassis_cy + 0.3,
        width=0.6, height=0.5,
        angle=0, density=8.0
    )
    sandbox.set_material_properties(ballast, restitution=0.0, friction=0.9)
    sandbox.add_joint(chassis, ballast, (ballast_cx, chassis_cy), type='rigid')

    gap = 0.15
    plate_w = max(0.5, min(OBJECT_LEFT - chassis_right - gap, 3.0))
    plate_cx = chassis_right + plate_w / 2
    pusher_plate = sandbox.add_beam(
        x=plate_cx, y=GROUND_TOP + 0.3,
        width=plate_w, height=0.15,
        angle=0, density=1.0
    )
    sandbox.set_material_properties(pusher_plate, restitution=0.0, friction=0.8)
    sandbox.add_joint(chassis, pusher_plate, (chassis_right, chassis_cy), type='rigid')

    # Front wheels - ballast keeps them pressed to ground
    wheel_x = chassis_right - 0.3
    left_wheel = sandbox.add_wheel(x=wheel_x - 0.22, y=wheel_y, radius=wheel_radius, density=1.0)
    right_wheel = sandbox.add_wheel(x=wheel_x + 0.22, y=wheel_y, radius=wheel_radius, density=1.0)
    sandbox.set_material_properties(left_wheel, restitution=0.0, friction=1.0)
    sandbox.set_material_properties(right_wheel, restitution=0.0, friction=1.0)

    j1 = sandbox.add_joint(chassis, left_wheel, (wheel_x - 0.22, wheel_y), type='pivot')
    j2 = sandbox.add_joint(chassis, right_wheel, (wheel_x + 0.22, wheel_y), type='pivot')
    sandbox._pusher_joints = [j1, j2]

    total_mass = sandbox.get_structure_mass()
    if total_mass > sandbox.MAX_STRUCTURE_MASS:
        raise ValueError(f"Structure mass {total_mass:.2f}kg exceeds limit {sandbox.MAX_STRUCTURE_MASS}kg")
    print(f"Pusher constructed: {len(sandbox.bodies)} bodies, {len(sandbox.joints)} joints, {total_mass:.2f}kg")
    return chassis


def agent_action(sandbox, agent_body, step_count):
    """Drive both wheels: negative speed => chassis moves right (positive x)."""
    if not hasattr(sandbox, '_pusher_joints'):
        return
    for joint in sandbox._pusher_joints:
        if joint is not None:
            sandbox.set_motor(joint, -75.0, 600.0)
