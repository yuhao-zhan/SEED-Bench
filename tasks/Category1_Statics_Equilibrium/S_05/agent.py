

import math



def build_agent(sandbox):

                                                                  

                  

    col_l = sandbox.add_beam(8.0, 2.0, 0.4, 4.0, angle=0, density=10.0)

    col_r = sandbox.add_beam(12.0, 2.0, 0.4, 4.0, angle=0, density=10.0)

    sandbox.add_joint(col_l, None, (8.0, 0.0), type='rigid')

    sandbox.add_joint(col_r, None, (12.0, 0.0), type='rigid')



          

    roof = sandbox.add_beam(10.0, 4.2, 6.0, 0.4, angle=0, density=10.0)

    sandbox.add_joint(col_l, roof, (8.0, 4.0), type='rigid')

    sandbox.add_joint(col_r, roof, (12.0, 4.0), type='rigid')



    return col_l



def agent_action(sandbox, agent_body, step_count):

    pass



def build_agent_stage_1(sandbox):

    
                                                                                              

    xs = [6.5, 7.0, 7.5, 8.0, 8.5, 11.5, 12.0, 12.5, 13.0, 13.5]

    pillars = []

    for x in xs:

        p = sandbox.add_beam(x, 2.0, 0.2, 4.0, angle=0, density=5.0)

        sandbox.add_joint(p, None, (x, 0.0), type='rigid')

        pillars.append(p)



                                      

    slope_l = sandbox.add_beam(8.5, 6.0, 5.5, 0.4, angle=-math.pi/3, density=5.0)

    for p in pillars[:5]:

        sandbox.add_joint(p, slope_l, (p.position.x, 4.0), type='rigid')



    slope_r = sandbox.add_beam(11.5, 6.0, 5.5, 0.4, angle=math.pi/3, density=5.0)

    for p in pillars[5:]:

        sandbox.add_joint(p, slope_r, (p.position.x, 4.0), type='rigid')



                     

    sandbox.add_joint(slope_l, slope_r, (10.0, 7.3), type='rigid')



                                                         

    wall_l = sandbox.add_beam(8.6, 1.5, 0.1, 3.0, angle=0, density=2.0)

    wall_r = sandbox.add_beam(11.4, 1.5, 0.1, 3.0, angle=0, density=2.0)

    sandbox.add_joint(pillars[4], wall_l, (8.5, 1.5), type='rigid')

    sandbox.add_joint(pillars[5], wall_r, (11.5, 1.5), type='rigid')



    return pillars[0]



def agent_action_stage_1(sandbox, agent_body, step_count):

    pass



def build_agent_stage_2(sandbox):

    
                                                                              

    xs = [6.0, 6.5, 7.5, 12.5, 13.5, 14.0]

    pillars = []

    for x in xs:

        p = sandbox.add_beam(x, 2.0, 0.2, 4.0, angle=0, density=5.0)

        sandbox.add_joint(p, None, (x, 0.0), type='rigid')

        pillars.append(p)



                                                               

    h1 = sandbox.add_beam(10.0, 2.5, 10.0, 0.2, angle=0, density=2.0)

    for p in pillars:

        sandbox.add_joint(p, h1, (p.position.x, 2.5), type='rigid')



          

    roof = sandbox.add_beam(10.0, 4.3, 11.0, 0.4, angle=0, density=5.0)

    for p in pillars:

        sandbox.add_joint(p, roof, (p.position.x, 4.0), type='rigid')



    return pillars[0]



def agent_action_stage_2(sandbox, agent_body, step_count):

    pass



def build_agent_stage_3(sandbox):

    
                                                                                    

    xs = [6.0, 7.0, 8.0, 8.8, 11.2, 12.0, 13.0, 14.0]

    pillars = []

    for x in xs:

        p = sandbox.add_beam(x, 2.5, 0.2, 5.0, angle=0, density=0.5)

        sandbox.add_joint(p, None, (x, 0.0), type='rigid')

        pillars.append(p)



                                          

    r1 = sandbox.add_beam(10.0, 5.1, 10.0, 0.2, angle=0, density=0.5)

    for p in pillars: sandbox.add_joint(p, r1, (p.position.x, 5.0), type='rigid')



    r2 = sandbox.add_beam(10.0, 5.5, 10.0, 0.2, angle=0, density=0.5)

    sandbox.add_joint(r1, r2, (10.0, 5.3), type='rigid')



    r3 = sandbox.add_beam(10.0, 6.0, 10.0, 0.4, angle=0, density=1.0)

    sandbox.add_joint(r2, r3, (10.0, 5.75), type='rigid')

    

                       

    s1 = sandbox.add_beam(8.9, 2.0, 0.1, 3.0, angle=0, density=0.5)

    s2 = sandbox.add_beam(11.1, 2.0, 0.1, 3.0, angle=0, density=0.5)

    sandbox.add_joint(pillars[3], s1, (8.8, 2.0), type='rigid')

    sandbox.add_joint(pillars[4], s2, (11.2, 2.0), type='rigid')



    return pillars[0]



def agent_action_stage_3(sandbox, agent_body, step_count):

    pass



def build_agent_stage_4(sandbox):

    
                                                

    xs = [7.2, 7.8, 8.4, 9.0, 11.0, 11.6, 12.2, 12.8]

    pillars = []

    for x in xs:

        p = sandbox.add_beam(x, 2.0, 0.15, 4.0, angle=0, density=1.0)

        sandbox.add_joint(p, None, (x, 0.0), type='rigid')

        pillars.append(p)



    roof = sandbox.add_beam(10.0, 4.1, 8.0, 0.2, angle=0, density=1.0)

    for p in pillars: sandbox.add_joint(p, roof, (p.position.x, 4.0), type='rigid')



    slope_l = sandbox.add_beam(8.5, 5.2, 4.0, 0.2, angle=-math.pi/4, density=1.0)

    sandbox.add_joint(pillars[3], slope_l, (9.0, 4.0), type='rigid')

    

    slope_r = sandbox.add_beam(11.5, 5.2, 4.0, 0.2, angle=math.pi/4, density=1.0)

    sandbox.add_joint(pillars[4], slope_r, (11.0, 4.0), type='rigid')



    return pillars[0]



def agent_action_stage_4(sandbox, agent_body, step_count):

    pass

