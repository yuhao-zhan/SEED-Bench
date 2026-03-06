

import math





def build_agent(sandbox):

    cabin = sandbox.get_vehicle_cabin()

    if cabin is None:

        raise ValueError("Cart not found")





    beams = []



    for (xx, yy) in [(4.8, 2.6), (4.9, 2.6), (5.0, 2.6), (5.1, 2.6)]:

        b = sandbox.add_beam(xx, yy, 0.08, 0.16, angle=0, density=5.0)

        sandbox.add_joint(cabin, b, (xx, yy), type="rigid")

        beams.append(b)



    return cabin





def agent_action(sandbox, agent_body, step_count):

    pass

