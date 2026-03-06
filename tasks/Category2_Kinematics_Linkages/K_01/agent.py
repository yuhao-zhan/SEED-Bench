

import math





import math



def build_agent(sandbox):

    start_x = 10.0

    start_y = 2.0

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

        leg_x = wheel_center_x + math.cos(angle) * leg_length/2

        leg_y = wheel_center_y + math.sin(angle) * leg_length/2

        leg = sandbox.add_beam(x=leg_x, y=leg_y, width=leg_width, height=leg_length, angle=angle, density=leg_density)

        sandbox.set_material_properties(leg, restitution=0.1, friction=0.8)

                                                           

        pivot = sandbox.add_joint(torso, leg, (wheel_center_x, wheel_center_y), type='pivot')

        sandbox._walker_joints.append(pivot)



                      

    wheel_center_x = start_x + 1.0

    wheel_center_y = start_y

    for i in range(num_legs_per_wheel):

        angle = i * 2 * math.pi / num_legs_per_wheel

        leg_x = wheel_center_x + math.cos(angle) * leg_length/2

        leg_y = wheel_center_y + math.sin(angle) * leg_length/2

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

        rotation_speed = -15.0

        

    for j in sandbox._walker_joints:

        sandbox.set_motor(j, rotation_speed, 1000.0)













def build_agent_stage_1(sandbox):

    start_x = 15.0

    start_y = 2.0

    num_legs = 6

    length = 1.0

    torso = sandbox.add_beam(x=start_x, y=start_y, width=2.0, height=0.5, density=2.0)



    def create_wheel(cx, cy):

        legs = []

        leg0 = sandbox.add_beam(x=cx, y=cy, width=0.1, height=length, angle=0, density=1.0)

        legs.append(leg0)

        pivot = sandbox.add_joint(torso, leg0, (cx, cy), type='pivot', lower_limit=0)

        for i in range(1, num_legs):

            angle = i * math.pi / num_legs

            leg = sandbox.add_beam(x=cx, y=cy, width=0.1, height=length, angle=angle, density=1.0)

            sandbox.add_joint(leg0, leg, (cx, cy), type='rigid')

            legs.append(leg)

        return pivot



    sandbox._walker_joints = [create_wheel(start_x - 1.0, start_y), create_wheel(start_x + 1.0, start_y)]

    return torso



def agent_action_stage_1(sandbox, agent_body, step_count):

    if not hasattr(sandbox, '_walker_joints'): return

    for j in sandbox._walker_joints:

        sandbox.set_motor(j, -15.0, 1000.0)





def build_agent_stage_2(sandbox):

    start_x = 10.0

    start_y = 2.0

    num_legs = 6

    length = 1.0

    torso = sandbox.add_beam(x=start_x, y=start_y, width=2.0, height=0.5, density=2.0)



    def create_wheel(cx, cy):

        legs = []

        leg0 = sandbox.add_beam(x=cx, y=cy, width=0.1, height=length, angle=0, density=1.0)

        legs.append(leg0)

        pivot = sandbox.add_joint(torso, leg0, (cx, cy), type='pivot', lower_limit=0)

        for i in range(1, num_legs):

            angle = i * math.pi / num_legs

            leg = sandbox.add_beam(x=cx, y=cy, width=0.1, height=length, angle=angle, density=1.0)

            sandbox.add_joint(leg0, leg, (cx, cy), type='rigid')

            legs.append(leg)

        return pivot



    sandbox._walker_joints = [create_wheel(start_x - 1.0, start_y), create_wheel(start_x + 1.0, start_y)]

    return torso



def agent_action_stage_2(sandbox, agent_body, step_count):

    if not hasattr(sandbox, '_walker_joints'): return

    for j in sandbox._walker_joints:

        sandbox.set_motor(j, -10.0, 500.0)





def build_agent_stage_3(sandbox):

    start_x = 15.0

    start_y = 2.0

    num_legs = 6

    length = 1.0

    torso = sandbox.add_beam(x=start_x, y=start_y, width=2.0, height=0.5, density=2.0)



    def create_wheel(cx, cy):

        legs = []

        leg0 = sandbox.add_beam(x=cx, y=cy, width=0.1, height=length, angle=0, density=1.0)

        legs.append(leg0)

        pivot = sandbox.add_joint(torso, leg0, (cx, cy), type='pivot', lower_limit=0)

        for i in range(1, num_legs):

            angle = i * math.pi / num_legs

            leg = sandbox.add_beam(x=cx, y=cy, width=0.1, height=length, angle=angle, density=1.0)

            sandbox.add_joint(leg0, leg, (cx, cy), type='rigid')

            legs.append(leg)

        return pivot



    sandbox._walker_joints = [create_wheel(start_x - 1.0, start_y), create_wheel(start_x + 1.0, start_y)]

    return torso



def agent_action_stage_3(sandbox, agent_body, step_count):

    if not hasattr(sandbox, '_walker_joints'): return

    for j in sandbox._walker_joints:

        sandbox.set_motor(j, -10.0, 500.0)





def build_agent_stage_4(sandbox):

    start_x = 15.0

    start_y = 2.0

    num_legs = 12

    length = 1.2

    torso = sandbox.add_beam(x=start_x, y=start_y, width=2.0, height=0.5, density=2.0)



    def create_wheel(cx, cy):

        legs = []

        leg0 = sandbox.add_beam(x=cx, y=cy, width=0.1, height=length, angle=0, density=1.0)

        legs.append(leg0)

        pivot = sandbox.add_joint(torso, leg0, (cx, cy), type='pivot', lower_limit=0)

        for i in range(1, num_legs):

            angle = i * math.pi / num_legs

            leg = sandbox.add_beam(x=cx, y=cy, width=0.1, height=length, angle=angle, density=1.0)

            sandbox.add_joint(leg0, leg, (cx, cy), type='rigid')

            legs.append(leg)

        return pivot



    sandbox._walker_joints = [create_wheel(start_x - 1.0, start_y), create_wheel(start_x + 1.0, start_y)]

    return torso



def agent_action_stage_4(sandbox, agent_body, step_count):

    if not hasattr(sandbox, '_walker_joints'): return

    for j in sandbox._walker_joints:

        sandbox.set_motor(j, -18.0, 2000.0)

