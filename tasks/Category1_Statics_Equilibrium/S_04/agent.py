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
    arm = sandbox.add_beam(x=0.0, y=5.0, width=7.0, height=0.2, density=1000.0)
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
    arm = sandbox.add_beam(x=0.0, y=5.0, width=7.0, height=0.2, density=1000.0)
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
    arm = sandbox.add_beam(x=0.0, y=5.0, width=7.0, height=0.2, density=1000.0)
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
    arm = sandbox.add_beam(x=0.0, y=5.0, width=7.0, height=0.4, density=1000.0)
    sandbox.add_joint(arm, pivot, (0.0, 5.0), type="pivot")
    catcher_x = 3.0
    conn_lo = sandbox.add_beam(x=catcher_x, y=6.0, width=0.2, height=2.0, density=1000.0)
    sandbox.add_joint(arm, conn_lo, (catcher_x, 5.0), type="rigid")
    conn_hi = sandbox.add_beam(x=catcher_x, y=7.75, width=0.2, height=1.5, density=1000.0)
    sandbox.add_joint(conn_lo, conn_hi, (catcher_x, 7.0), type="rigid")
    base = sandbox.add_beam(x=catcher_x, y=8.5, width=0.8, height=0.4, density=1000.0)
    sandbox.add_joint(conn_hi, base, (catcher_x, 8.5), type="rigid")
    bumper = sandbox.add_beam(x=catcher_x, y=8.93, width=0.4, height=0.24, density=1000.0)
    sandbox.add_joint(base, bumper, (catcher_x, 8.93), type="rigid")
    bumper2 = sandbox.add_beam(x=catcher_x, y=8.97, width=0.3, height=0.12, density=1000.0)
    sandbox.add_joint(bumper, bumper2, (catcher_x, 8.97), type="rigid")
    ext1 = sandbox.add_beam(x=3.6, y=8.5, width=0.6, height=0.4, density=1000.0)
    sandbox.add_joint(base, ext1, (3.3, 8.5), type="rigid")
    ext2 = sandbox.add_beam(x=4.2, y=8.5, width=0.6, height=0.4, density=1000.0)
    sandbox.add_joint(ext1, ext2, (3.9, 8.5), type="rigid")
    m_cw = 800.0
    cw = sandbox.add_beam(x=-3.0, y=4.0, width=1.0, height=1.0, density=m_cw)
    sandbox.add_joint(arm, cw, (-3.0, 5.0), type="rigid")
    return arm

def agent_action_stage_1(sandbox, agent_body, step_count): pass

def agent_action_stage_2(sandbox, agent_body, step_count): pass

def agent_action_stage_3(sandbox, agent_body, step_count): pass

def agent_action_stage_4(sandbox, agent_body, step_count): pass
