

import math



def build_agent(sandbox):





    sandbox.add_block(-1.0, 0.2, 4.0, 0.4)

    return None



def agent_action(sandbox, agent_body, step_count):

    pass



def build_agent_stage_1(sandbox):





    sandbox.add_block(-1.2, 0.2, 4.0, 0.4)



    for i in range(15):

        sandbox.add_block(-8.0, 0.6 + i*0.4, 4.0, 0.4)

    return None



def agent_action_stage_1(sandbox, agent_body, step_count):

    pass



def build_agent_stage_2(sandbox):





    sandbox.add_block(-0.8, 0.2, 4.0, 0.4)



    for i in range(15):

        sandbox.add_block(-8.0, 0.6 + i*0.4, 4.0, 0.4)

    return None



def agent_action_stage_2(sandbox, agent_body, step_count):

    pass



def build_agent_stage_3(sandbox):





    d = 200.0



    sandbox.add_block(-0.5, 0.2, 4.0, 0.4, density=d)



    for i in range(18):

        sandbox.add_block(-7.0, 0.6 + i*0.4, 4.0, 0.4, density=d)



    sandbox.add_block(-5.0, 0.2, 4.0, 0.4, density=d)

    return None



def agent_action_stage_3(sandbox, agent_body, step_count):

    pass



def build_agent_stage_4(sandbox):





    h = 0.1









    d = 100.0



    sandbox.add_block(-0.2, h/2, 4.0, h, density=d)



    for i in range(1, 4):

        sandbox.add_block(-2.2, h/2 + i*h, 4.0, h, density=d)



    for x_pos in [-4.0, -6.0, -8.0]:

        for i in range(4):

            sandbox.add_block(x_pos, h/2 + i*h, 4.0, h, density=d)

    return None



def agent_action_stage_4(sandbox, agent_body, step_count):

    pass

