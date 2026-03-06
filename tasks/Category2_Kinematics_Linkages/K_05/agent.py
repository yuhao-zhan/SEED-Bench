

import math



CENTER_X = 4.0

BASE_Y = 1.15



def build_agent(sandbox):

                                         

    base = sandbox.add_beam(x=CENTER_X, y=BASE_Y, width=4.0, height=0.3, density=10.0)

    sandbox.weld_to_ground(base, (CENTER_X, BASE_Y))

    

                   

                                                                   

                           

                    

    arm = sandbox.add_beam(x=1.0, y=6.0, width=0.4, height=10.0, angle=0, density=2.0)

    j_motor = sandbox.add_joint(base, arm, (1.0, 1.3), type='pivot')

    

                                       

                                                 

                          

                                                            

    

    return build_simple_push(sandbox)



def build_simple_push(sandbox):

    base = sandbox.add_beam(x=CENTER_X, y=BASE_Y, width=4.0, height=0.2, density=10.0)

    sandbox.weld_to_ground(base, (CENTER_X, BASE_Y))

    

                                       

    plat = sandbox.add_beam(x=CENTER_X, y=1.5, width=4.0, height=0.2, density=5.0)

    

                             

    sandbox.add_joint(base, plat, (CENTER_X, 1.5), type='slider', axis=(0, 1), lower_translation=-10.0, upper_translation=10.0)

    

    sandbox.set_fixed_rotation(plat, True)

    sandbox._top_platform = plat

    

    return base



def agent_action(sandbox, agent_body, step_count):

    if not hasattr(sandbox, '_top_platform'): return

    

    plat = sandbox._top_platform

    target_y = 9.5

    

                                

    if plat.position.y < target_y:

                            

        sandbox.apply_force(plat, (0, 2000.0))

    else:

                 

        sandbox.apply_force(plat, (0, 40.0))

    

                                            

                        

