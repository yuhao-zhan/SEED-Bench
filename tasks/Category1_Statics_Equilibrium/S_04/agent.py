import math

def build_agent(sandbox):
    main_beam = sandbox.add_beam(x=0.0, y=5.0, width=8.0, height=0.2, density=10.0)
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
    arm = sandbox.add_beam(x=0.0, y=5.0, width=8.0, height=0.2, density=1000.0)
    sandbox.add_joint(arm, pivot, (0.0, 5.0), type="pivot")
    catcher = sandbox.add_beam(x=3.0, y=5.0, width=0.4, height=0.2, density=1000.0)
    sandbox.add_joint(arm, catcher, (3.0, 5.0), type="rigid")
    dummy = sandbox.add_beam(x=-3.0, y=5.0, width=0.4, height=0.2, density=1000.0)
    sandbox.add_joint(arm, dummy, (-3.0, 5.0), type="rigid")
    m_cw = 250.0
    cw = sandbox.add_beam(x=-3.0, y=5.5, width=1.0, height=1.0, density=m_cw)
    sandbox.add_joint(arm, cw, (-3.0, 5.5), type="rigid")
    return arm

def build_agent_stage_2(sandbox):
    pivot = sandbox._terrain_bodies.get("pivot")
    arm = sandbox.add_beam(x=0.0, y=5.0, width=8.0, height=0.2, density=1000.0)
    sandbox.add_joint(arm, pivot, (0.0, 5.0), type="pivot")
    catcher = sandbox.add_beam(x=3.0, y=5.0, width=0.4, height=0.2, density=1000.0)
    sandbox.add_joint(arm, catcher, (3.0, 5.0), type="rigid")
    dummy = sandbox.add_beam(x=-3.0, y=5.0, width=0.4, height=0.2, density=1000.0)
    sandbox.add_joint(arm, dummy, (-3.0, 5.0), type="rigid")
    m_cw = 69.56
    cw = sandbox.add_beam(x=-3.0, y=3.0, width=1.0, height=1.0, density=m_cw)
    sandbox.add_joint(arm, cw, (-3.0, 3.0), type="rigid")
    return arm

def build_agent_stage_3(sandbox):
    pivot = sandbox._terrain_bodies.get("pivot")
    arm = sandbox.add_beam(x=0.0, y=5.0, width=10.0, height=0.2, density=1000.0)
    sandbox.add_joint(arm, pivot, (0.0, 5.0), type="pivot")
    catcher = sandbox.add_beam(x=3.0, y=5.0, width=0.4, height=0.2, density=1000.0)
    sandbox.add_joint(arm, catcher, (3.0, 5.0), type="rigid")
    dummy = sandbox.add_beam(x=-3.0, y=5.0, width=0.4, height=0.2, density=1000.0)
    sandbox.add_joint(arm, dummy, (-3.0, 5.0), type="rigid")
    m_cw = 187.5
    cw = sandbox.add_beam(x=-4.0, y=5.0, width=1.0, height=1.0, density=m_cw)
    sandbox.add_joint(arm, cw, (-4.0, 5.0), type="rigid")
    return arm

def build_agent_stage_4(sandbox):
    pivot = sandbox._terrain_bodies.get("pivot")
    arm = sandbox.add_beam(x=0.0, y=5.0, width=12.0, height=0.4, density=1000.0)
    sandbox.add_joint(arm, pivot, (0.0, 5.0), type="pivot")
    catcher_x = 5.0
    base = sandbox.add_beam(x=catcher_x, y=8.0, width=6.0, height=0.4, density=1000.0)
    sandbox.add_joint(arm, base, (catcher_x, 8.0), type="rigid")
    side_l = sandbox.add_beam(x=catcher_x-2.9, y=9.0, width=0.2, height=2.0, density=1000.0)
    sandbox.add_joint(base, side_l, (catcher_x-2.9, 9.0), type="rigid")
    side_r = sandbox.add_beam(x=catcher_x+2.9, y=9.0, width=0.2, height=2.0, density=1000.0)
    sandbox.add_joint(base, side_r, (catcher_x+2.9, 9.0), type="rigid")
    m_cw = 225.0
    cw = sandbox.add_beam(x=-5.0, y=3.0, width=1.0, height=1.0, density=m_cw)
    sandbox.add_joint(arm, cw, (-5.0, 3.0), type="rigid")
    return arm

def agent_action_stage_1(sandbox, agent_body, step_count): pass

def agent_action_stage_2(sandbox, agent_body, step_count): pass

def agent_action_stage_3(sandbox, agent_body, step_count): pass

def agent_action_stage_4(sandbox, agent_body, step_count): pass
