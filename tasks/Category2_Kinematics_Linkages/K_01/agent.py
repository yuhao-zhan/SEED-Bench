import math

def build_agent(sandbox):
    start_x = 10.0
    start_y = 2.5
    torso_width = 2.0
    torso_height = 0.5
    torso_density = 2.0
    torso = sandbox.add_beam(
        x=start_x, y=start_y, width=torso_width, height=torso_height, angle=0, density=torso_density
    )
    sandbox.set_material_properties(torso, restitution=0.1, friction=0.5)
    leg_length = 1.0
    leg_width = 0.1
    leg_density = 1.0
    num_legs_per_wheel = 6
    sandbox._walker_joints = []
    wheel_center_x = start_x - 1.0
    wheel_center_y = start_y
    for i in range(num_legs_per_wheel):
        angle = i * 2 * math.pi / num_legs_per_wheel
        leg_x = wheel_center_x + math.cos(angle) * leg_length / 2
        leg_y = wheel_center_y + math.sin(angle) * leg_length / 2
        leg = sandbox.add_beam(x=leg_x, y=leg_y, width=leg_width, height=leg_length, angle=angle, density=leg_density)
        sandbox.set_material_properties(leg, restitution=0.1, friction=0.8)
        pivot = sandbox.add_joint(torso, leg, (wheel_center_x, wheel_center_y), type='pivot')
        sandbox._walker_joints.append(pivot)
    wheel_center_x = start_x + 1.0
    wheel_center_y = start_y
    for i in range(num_legs_per_wheel):
        angle = i * 2 * math.pi / num_legs_per_wheel
        leg_x = wheel_center_x + math.cos(angle) * leg_length / 2
        leg_y = wheel_center_y + math.sin(angle) * leg_length / 2
        leg = sandbox.add_beam(x=leg_x, y=leg_y, width=leg_width, height=leg_length, angle=angle, density=leg_density)
        sandbox.set_material_properties(leg, restitution=0.1, friction=0.8)
        pivot = sandbox.add_joint(torso, leg, (wheel_center_x, wheel_center_y), type='pivot')
        sandbox._walker_joints.append(pivot)
    return torso

def agent_action(sandbox, agent_body, step_count):
    if not hasattr(sandbox, '_walker_joints'): return
    if agent_body and agent_body.position.x > 28.0:
        rotation_speed = 0.0
    else:
        rotation_speed = -25.0
    for j in sandbox._walker_joints:
        sandbox.set_motor(j, rotation_speed, 2000.0)

def build_agent_stage_1(sandbox):
    start_x = 10.0
    start_y = 2.4
    num_legs_per_wheel = 6
    leg_length = 0.8
    leg_width = 0.1
    torso = sandbox.add_beam(x=start_x, y=start_y, width=1.8, height=0.45, density=1.2)
    sandbox.set_material_properties(torso, restitution=0.05, friction=0.6)
    sandbox._walker_joints = []
    for cx in (start_x - 0.85, start_x + 0.85):
        for i in range(num_legs_per_wheel):
            angle = i * 2 * math.pi / num_legs_per_wheel
            lx = cx + math.cos(angle) * leg_length / 2
            ly = start_y + math.sin(angle) * leg_length / 2
            leg = sandbox.add_beam(x=lx, y=ly, width=leg_width, height=leg_length, angle=angle, density=0.7)
            sandbox.set_material_properties(leg, restitution=0.05, friction=0.8)
            pivot = sandbox.add_joint(torso, leg, (cx, start_y), type='pivot')
            sandbox._walker_joints.append(pivot)
    return torso

def agent_action_stage_1(sandbox, agent_body, step_count):
    if not hasattr(sandbox, '_walker_joints'): return
    for j in sandbox._walker_joints:
        sandbox.set_motor(j, -25.0, 2200.0)

def build_agent_stage_2(sandbox):
    start_x = 10.0
    start_y = 2.8
    leg_length = 0.9
    leg_width = 0.1
    torso = sandbox.add_beam(x=start_x, y=start_y, width=2.0, height=0.5, density=2.0)
    sandbox.set_material_properties(torso, restitution=0.1, friction=0.6)
    sandbox._walker_joints = []
    for cx in (start_x - 1.0, start_x + 1.0):
        for i in range(6):
            angle = i * 2 * math.pi / 6
            lx = cx + math.cos(angle) * leg_length / 2
            ly = start_y + math.sin(angle) * leg_length / 2
            leg = sandbox.add_beam(x=lx, y=ly, width=leg_width, height=leg_length, angle=angle, density=1.0)
            sandbox.set_material_properties(leg, restitution=0.1, friction=0.7)
            pivot = sandbox.add_joint(torso, leg, (cx, start_y), type='pivot')
            sandbox._walker_joints.append(pivot)
    return torso

def agent_action_stage_2(sandbox, agent_body, step_count):
    if not hasattr(sandbox, '_walker_joints'): return
    limit_lo, limit_hi = -math.pi / 6, math.pi / 6
    margin = 0.08
    speed, torque = 18.0, 3500.0
    for j in sandbox._walker_joints:
        a = j.angle
        if a >= limit_hi - margin:
            sandbox.set_motor(j, -speed, torque)
        else:
            sandbox.set_motor(j, speed, torque)

def build_agent_stage_3(sandbox):
    start_x = 10.0
    start_y = 2.8
    leg_length = 0.9
    leg_width = 0.1
    torso = sandbox.add_beam(x=start_x, y=start_y, width=2.0, height=0.5, density=2.0)
    sandbox.set_material_properties(torso, restitution=0.05, friction=0.6)
    sandbox._walker_joints = []
    for cx in (start_x - 1.0, start_x + 1.0):
        for i in range(6):
            angle = i * 2 * math.pi / 6
            lx = cx + math.cos(angle) * leg_length / 2
            ly = start_y + math.sin(angle) * leg_length / 2
            leg = sandbox.add_beam(x=lx, y=ly, width=leg_width, height=leg_length, angle=angle, density=1.0)
            sandbox.set_material_properties(leg, restitution=0.05, friction=0.8)
            pivot = sandbox.add_joint(torso, leg, (cx, start_y), type='pivot')
            sandbox._walker_joints.append(pivot)
    return torso

def agent_action_stage_3(sandbox, agent_body, step_count):
    if not hasattr(sandbox, '_walker_joints'): return
    limit_lo, limit_hi = -math.pi / 6, math.pi / 6
    margin = 0.08
    speed, torque = 18.0, 3800.0
    for j in sandbox._walker_joints:
        a = j.angle
        if a >= limit_hi - margin:
            sandbox.set_motor(j, -speed, torque)
        else:
            sandbox.set_motor(j, speed, torque)

def build_agent_stage_4(sandbox):
    start_x = 10.0
    start_y = 2.8
    leg_length = 0.85
    leg_width = 0.1
    torso = sandbox.add_beam(x=start_x, y=start_y, width=1.6, height=0.45, density=1.2)
    sandbox.set_material_properties(torso, restitution=0.05, friction=0.5)
    sandbox._walker_joints = []
    for cx in (start_x - 0.85, start_x + 0.85):
        for i in range(6):
            angle = i * 2 * math.pi / 6
            lx = cx + math.cos(angle) * leg_length / 2
            ly = start_y + math.sin(angle) * leg_length / 2
            leg = sandbox.add_beam(x=lx, y=ly, width=leg_width, height=leg_length, angle=angle, density=0.5)
            sandbox.set_material_properties(leg, restitution=0.05, friction=0.5)
            pivot = sandbox.add_joint(torso, leg, (cx, start_y), type='pivot')
            sandbox._walker_joints.append(pivot)
    return torso

def agent_action_stage_4(sandbox, agent_body, step_count):
    if not hasattr(sandbox, '_walker_joints'): return
    limit_lo, limit_hi = -math.pi / 6, math.pi / 6
    margin = 0.08
    speed, torque = 28.0, 8000.0
    for j in sandbox._walker_joints:
        a = j.angle
        if a >= limit_hi - margin:
            sandbox.set_motor(j, -speed, torque)
        else:
            sandbox.set_motor(j, speed, torque)
