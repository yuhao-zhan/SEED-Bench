import math

def build_agent(sandbox):
    main_beam = sandbox.add_beam(x=0.0, y=5.0, width=7.0, height=0.2, density=10.0)
    pivot = sandbox._terrain_bodies.get("pivot")
    sandbox.add_joint(main_beam, pivot, (0.0, 5.0), type="rigid")
    platform = sandbox.add_beam(x=3.0, y=5.5, width=1.0, height=0.2, density=10.0)
    sandbox.add_joint(main_beam, platform, (3.0, 5.5), type="rigid")
    cw = sandbox.add_beam(x=-3.0, y=5.5, width=1.0, height=1.0, density=202.0)
    sandbox.add_joint(main_beam, cw, (-3.0, 5.5), type="rigid")
    return main_beam

def agent_action(sandbox, agent_body, step_count):
    pass

def build_agent_stage_1(sandbox):
    pivot = sandbox._terrain_bodies.get("pivot")
    arm = sandbox.add_beam(x=0.0, y=5.0, width=7.0, height=0.2, density=1.0)
    sandbox.add_joint(arm, pivot, (0.0, 5.0), type="pivot")
    platform = sandbox.add_beam(x=3.0, y=5.5, width=0.4, height=0.2, density=1.0)
    sandbox.add_joint(arm, platform, (3.0, 5.5), type="rigid")
    m_cw = 200.08
    cw = sandbox.add_beam(x=-3.0, y=3.0, width=0.5, height=0.5, density=m_cw/0.25)
    sandbox.add_joint(arm, cw, (-3.0, 5.0), type="rigid")
    return arm

def build_agent_stage_2(sandbox):
    return build_agent_stage_1(sandbox)

def build_agent_stage_3(sandbox):
    pivot = sandbox._terrain_bodies.get("pivot")
    arm = sandbox.add_beam(x=0.0, y=5.0, width=7.0, height=0.4, density=1000.0)
    sandbox.add_joint(arm, pivot, (0.0, 5.0), type="pivot")
    platform = sandbox.add_beam(x=3.0, y=5.5, width=0.4, height=0.2, density=1.0)
    sandbox.add_joint(arm, platform, (3.0, 5.5), type="rigid")
    m_cw = 200.08
    cw = sandbox.add_beam(x=-3.0, y=4.5, width=0.5, height=0.5, density=m_cw/0.25)
    sandbox.add_joint(arm, cw, (-3.0, 5.0), type="rigid")
    return arm

def build_agent_stage_4(sandbox):
    pivot = sandbox._terrain_bodies.get("pivot")
    arm = sandbox.add_beam(x=0.0, y=5.0, width=7.0, height=0.4, density=1000.0)
    sandbox.add_joint(arm, pivot, (0.0, 5.0), type="pivot")
    plat_x, plat_y = 4.5, 6.0
    platform = sandbox.add_beam(x=plat_x, y=plat_y, width=1.0, height=0.2, density=1.0)
    sandbox.add_joint(arm, platform, (plat_x, 5.0), type="rigid")
    m_cw = 200.08
    cw = sandbox.add_beam(x=-4.5, y=4.0, width=0.5, height=0.5, density=m_cw/0.25)
    sandbox.add_joint(arm, cw, (-4.5, 5.0), type="rigid")
    return arm

def agent_action_stage_1(sandbox, agent_body, step_count): pass

def agent_action_stage_2(sandbox, agent_body, step_count): pass

def agent_action_stage_3(sandbox, agent_body, step_count): pass

def agent_action_stage_4(sandbox, agent_body, step_count): pass
