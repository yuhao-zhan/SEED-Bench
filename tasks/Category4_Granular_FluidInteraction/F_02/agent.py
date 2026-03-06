

import math



THRUST_PER_BODY = 520.0

STOP_X = 26.0

MAX_VX = 3.0

MAX_VY = 4.0



PILLAR_ZONE_1 = (11.5, 16.0)

PILLAR_ZONE_2 = (16.0, 22.0)

LIFT_FY = 175.0

LIFT_FX = 400.0





def build_agent(sandbox):



    beam_w = 0.62

    beam_h = 0.35

    density = 55.0

    y_center = 0.5 + beam_h / 2



    centers_x = [2.31 + i * 0.62 for i in range(9)]



    bodies = []

    for x in centers_x:

        b = sandbox.add_beam(x, y_center, beam_w, beam_h, angle=0, density=density)

        sandbox.set_material_properties(b, restitution=0.05)

        bodies.append(b)

    for i in range(8):

        anchor_x = (centers_x[i] + centers_x[i + 1]) / 2

        sandbox.add_joint(bodies[i], bodies[i + 1], (anchor_x, y_center), type='rigid')



    total_mass = sandbox.get_structure_mass()

    if total_mass > sandbox.MAX_STRUCTURE_MASS:

        raise ValueError(f"Structure mass {total_mass:.2f} kg exceeds limit {sandbox.MAX_STRUCTURE_MASS} kg")



    return bodies[-1]





def agent_action(sandbox, agent_body, step_count):



    if agent_body is None or not agent_body.active:

        return

    front_x = sandbox.get_vehicle_front_x() or agent_body.position.x

    vx = agent_body.linearVelocity.x

    vy = agent_body.linearVelocity.y



    if front_x >= STOP_X:

        for b in sandbox.bodies:

            if b.active:

                b.linearVelocity = (0.0, b.linearVelocity.y)

        return



    for b in sandbox.bodies:

        if b.active:

            vbx, vby = b.linearVelocity.x, b.linearVelocity.y

            speed = math.sqrt(vbx * vbx + vby * vby)

            if speed > MAX_VX:

                scale = MAX_VX / speed

                b.linearVelocity = (vbx * scale, vby * scale)



    in_pillar_zone = (PILLAR_ZONE_1[0] <= front_x <= PILLAR_ZONE_1[1] or

                      PILLAR_ZONE_2[0] <= front_x <= PILLAR_ZONE_2[1])

    if in_pillar_zone:

        fx, fy = LIFT_FX, LIFT_FY

    else:

        fx, fy = THRUST_PER_BODY, 0.0

        if vx > 2.2:

            fx *= 0.3

        elif vx > 1.5:

            fx *= 0.6



    for body in sandbox.bodies:

        if body.active:

            sandbox.apply_force(body, fx, fy, step_count=step_count)

