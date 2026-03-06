

import math



def build_agent(sandbox):



    MAIN_Y = 0.5

    main_beam = sandbox.add_beam(x=0.0, y=MAIN_Y, width=8.0, height=0.4, density=10.0)

    pivot = sandbox._terrain_bodies.get("pivot")

    sandbox.add_joint(main_beam, pivot, (0.0, 0.0), type="rigid")



    platform = sandbox.add_beam(x=3.0, y=0.3, width=1.0, height=0.2, density=10.0)

    sandbox.add_joint(main_beam, platform, (3.0, 0.3), type="rigid")



    cw = sandbox.add_beam(x=-3.0, y=MAIN_Y, width=1.0, height=1.0, density=202.0)

    sandbox.add_joint(main_beam, cw, (-3.0, MAIN_Y), type="rigid")



    return main_beam



def agent_action(sandbox, agent_body, step_count):

    pass







def build_agent_stage_1(sandbox):





    main_beam = sandbox.add_beam(x=0.0, y=0.0, width=8.0, height=1.0, density=100000.0)

    pivot = sandbox._terrain_bodies.get("pivot")

    sandbox.add_joint(main_beam, pivot, (0.0, 0.0), type="rigid")





    platform = sandbox.add_beam(x=3.0, y=0.0, width=1.0, height=0.5, density=10.0)

    sandbox.add_joint(main_beam, platform, (3.0, 0.0), type="rigid")



    return main_beam



def agent_action_stage_1(sandbox, agent_body, step_count): pass



def build_agent_stage_2(sandbox):





    main_beam = sandbox.add_beam(x=0.0, y=0.0, width=8.0, height=1.0, density=100000.0)

    pivot = sandbox._terrain_bodies.get("pivot")

    sandbox.add_joint(main_beam, pivot, (0.0, 0.0), type="rigid")





    platform = sandbox.add_beam(x=3.0, y=0.0, width=1.0, height=0.5, density=10.0)

    sandbox.add_joint(main_beam, platform, (3.0, 0.0), type="rigid")



    return main_beam



def agent_action_stage_2(sandbox, agent_body, step_count): pass



def build_agent_stage_3(sandbox):



    pivot = sandbox._terrain_bodies.get("pivot")



    base = sandbox.add_beam(x=0.0, y=0.5, width=1.0, height=1.0, density=5000.0)

    sandbox.add_joint(base, pivot, (0.0, 0.0), type="rigid")





    l_stem = sandbox.add_beam(x=-3.0, y=1.5, width=0.4, height=3.0, density=100.0)

    sandbox.add_joint(base, l_stem, (-3.0, 0.5), type="rigid")





    r_stem = sandbox.add_beam(x=3.0, y=1.5, width=0.4, height=3.0, density=100.0)

    sandbox.add_joint(base, r_stem, (3.0, 0.5), type="rigid")





    top_beam = sandbox.add_beam(x=0.0, y=3.0, width=6.4, height=0.4, density=10.0)

    sandbox.add_joint(l_stem, top_beam, (-3.0, 3.0), type="rigid")

    sandbox.add_joint(r_stem, top_beam, (3.0, 3.0), type="rigid")







    platform = sandbox.add_beam(x=3.0, y=0.3, width=1.0, height=0.2, density=10.0)

    sandbox.add_joint(r_stem, platform, (3.0, 0.3), type="rigid")





    c_platform = sandbox.add_beam(x=-3.0, y=0.3, width=1.0, height=0.2, density=10.0)

    sandbox.add_joint(l_stem, c_platform, (-3.0, 0.3), type="rigid")



    return base



def agent_action_stage_3(sandbox, agent_body, step_count): pass



def build_agent_stage_4(sandbox):





    main_beam = sandbox.add_beam(x=0.0, y=0.0, width=15.0, height=1.0, density=100000.0)

    pivot = sandbox._terrain_bodies.get("pivot")

    sandbox.add_joint(main_beam, pivot, (0.0, 0.0), type="rigid")





    target_x = 7.0

    platform = sandbox.add_beam(x=target_x, y=0.0, width=6.0, height=0.5, density=100.0)

    sandbox.add_joint(main_beam, platform, (target_x, 0.0), type="rigid")





    l_wall = sandbox.add_beam(x=target_x-3.0, y=2.0, width=0.4, height=4.0, density=100.0)

    r_wall = sandbox.add_beam(x=target_x+3.0, y=2.0, width=0.4, height=4.0, density=100.0)

    sandbox.add_joint(platform, l_wall, (target_x-3.0, 0.0), type="rigid")

    sandbox.add_joint(platform, r_wall, (target_x+3.0, 0.0), type="rigid")



    return main_beam



def agent_action_stage_4(sandbox, agent_body, step_count): pass

