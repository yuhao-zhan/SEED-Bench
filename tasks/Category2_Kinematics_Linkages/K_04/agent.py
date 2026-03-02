"""
K-04: The Pusher task Agent module
Reference solution: Low-center-of-gravity heavy pusher.
"""
import math

GROUND_TOP = 1.0
OBJECT_X = 8.0


def build_agent(sandbox):
    wheel_radius = 0.4
    wheel_y = GROUND_TOP + wheel_radius
    
    # Very low chassis
    chassis_h = 0.1
    chassis_w = 2.0
    chassis_cx = 6.0
    chassis_cy = wheel_y + 0.1
    
    chassis = sandbox.add_beam(x=chassis_cx, y=chassis_cy, width=chassis_w, height=chassis_h, density=5.0)
    if hasattr(sandbox, 'set_fixed_rotation'):
        sandbox.set_fixed_rotation(chassis, True)

    # Ballast
    ballast = sandbox.add_beam(x=chassis_cx, y=chassis_cy+0.2, width=2.0, height=0.2, density=10.0)
    sandbox.add_joint(chassis, ballast, (chassis_cx, chassis_cy), type='rigid')

    # Pusher plate
    plate = sandbox.add_beam(x=7.3, y=GROUND_TOP+0.4, width=0.4, height=0.6, density=5.0)
    sandbox.add_joint(chassis, plate, (7.1, chassis_cy), type='rigid')

    # 4 Heavy Wheels
    sandbox.my_drive_joints = []
    # pi * 0.16 * 15 = 7.5kg each. Total 4 wheels = 30kg.
    for x in [chassis_cx - 0.8, chassis_cx - 0.7, chassis_cx + 0.7, chassis_cx + 0.8]:
        w = sandbox.add_wheel(x=x, y=wheel_y, radius=wheel_radius, density=15.0)
        sandbox.set_material_properties(w, restitution=0.0, friction=10.0)
        j = sandbox.add_joint(chassis, w, (x, wheel_y), type='pivot')
        sandbox.my_drive_joints.append(j)
    
    if hasattr(sandbox, '_pusher_joints'):
        sandbox._pusher_joints = []
        
    return chassis


def agent_action(sandbox, agent_body, step_count):
    if not hasattr(sandbox, 'my_drive_joints'):
        return
    
    for joint in sandbox.my_drive_joints:
        if joint is not None:
            # High speed to overcome static friction
            sandbox.set_motor(joint, -50.0, 1000000.0)
