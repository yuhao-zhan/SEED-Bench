import math

def build_agent(sandbox):
    main_beam = sandbox.add_beam(x=0.0, y=0.5, width=8.0, height=0.4, density=10.0)
    pivot = sandbox._terrain_bodies.get("pivot")
    sandbox.add_joint(main_beam, pivot, (0.0, 0.0), type="rigid")
    platform = sandbox.add_beam(x=3.0, y=0.3, width=1.0, height=0.2, density=10.0)
    sandbox.add_joint(main_beam, platform, (3.0, 0.3), type="rigid")
    cw = sandbox.add_beam(x=-3.0, y=0.5, width=1.0, height=1.0, density=202.0)
    sandbox.add_joint(main_beam, cw, (-3.0, 0.5), type="rigid")
    return main_beam

def agent_action(sandbox, agent_body, step_count):
    pass

def build_agent_stage_1(sandbox):
    pivot = sandbox._terrain_bodies.get("pivot")
    core = sandbox.add_beam(x=0.0, y=0.0, width=0.4, height=0.4, density=100.0)
    sandbox.add_joint(core, pivot, (0.0, 0.0), type="pivot")
    arm = sandbox.add_beam(x=0.0, y=0.0, width=7.0, height=0.4, density=100.0)
    sandbox.add_joint(core, arm, (0.0, 0.0), type="rigid")
    catcher = sandbox.add_beam(x=3.0, y=0.0, width=0.4, height=0.4, density=100.0)
    sandbox.add_joint(arm, catcher, (3.0, 0.0), type="rigid")
    dummy = sandbox.add_beam(x=-3.0, y=0.0, width=0.4, height=0.4, density=100.0)
    sandbox.add_joint(arm, dummy, (-3.0, 0.0), type="rigid")
    cw = sandbox.add_beam(x=-3.0, y=0.0, width=1.0, height=1.0, density=200.0)
    sandbox.add_joint(arm, cw, (-3.0, 0.0), type="rigid")
    return core

def build_agent_stage_2(sandbox):
    pivot = sandbox._terrain_bodies.get("pivot")
    core = sandbox.add_beam(x=0.0, y=0.0, width=0.2, height=0.2, density=100.0)
    sandbox.add_joint(core, pivot, (0.0, 0.0), type="pivot")
    arm = sandbox.add_beam(x=0.0, y=0.1, width=7.0, height=0.2, density=100.0)
    sandbox.add_joint(core, arm, (0.0, 0.1), type="rigid")
    catcher = sandbox.add_beam(x=3.0, y=0.25, width=0.4, height=0.1, density=100.0)
    sandbox.add_joint(arm, catcher, (3.0, 0.1), type="rigid")
    cw = sandbox.add_beam(x=-3.0, y=0.0, width=2.0, height=2.0, density=175.0)
    sandbox.add_joint(arm, cw, (-3.0, 0.1), type="rigid")
    return core

def build_agent_stage_3(sandbox):
    pivot = sandbox._terrain_bodies.get("pivot")
    core = sandbox.add_beam(x=0.0, y=0.0, width=0.4, height=0.4, density=1000.0)
    sandbox.add_joint(core, pivot, (0.0, 0.0), type="pivot")
    mast = sandbox.add_beam(x=0.0, y=0.0, width=0.4, height=8.0, density=100.0)
    sandbox.add_joint(core, mast, (0.0, 0.0), type="rigid")
    r_top = sandbox.add_beam(x=1.5, y=3.0, width=3.0, height=0.4, density=100.0)
    sandbox.add_joint(mast, r_top, (0.0, 3.0), type="rigid")
    r_down = sandbox.add_beam(x=3.0, y=1.8, width=0.4, height=3.4, density=100.0)
    sandbox.add_joint(r_top, r_down, (3.0, 3.5), type="rigid")
    catcher = sandbox.add_beam(x=3.0, y=0.25, width=0.4, height=0.5, density=100.0)
    sandbox.add_joint(r_down, catcher, (3.0, 0.25), type="rigid")
    l_bot = sandbox.add_beam(x=-1.5, y=-1.5, width=3.0, height=0.4, density=100.0)
    sandbox.add_joint(mast, l_bot, (0.0, -1.5), type="rigid")
    cw = sandbox.add_beam(x=-3.0, y=-1.5, width=1.0, height=1.0, density=215.0)
    sandbox.add_joint(l_bot, cw, (-3.0, -1.5), type="rigid")
    return core

def build_agent_stage_4(sandbox):
    pivot = sandbox._terrain_bodies.get("pivot")
    core = sandbox.add_beam(x=0.0, y=0.0, width=1.0, height=1.0, density=1000.0)
    sandbox.add_joint(core, pivot, (0.0, 0.0), type="rigid")
    platform = sandbox.add_beam(x=3.0, y=0.0, width=4.0, height=1.0, density=100.0)
    sandbox.add_joint(core, platform, (0.0, 0.0), type="rigid")
    cw = sandbox.add_beam(x=-3.0, y=0.0, width=2.0, height=2.0, density=175.0)
    sandbox.add_joint(core, cw, (0.0, 0.0), type="rigid")
    return core

def agent_action_stage_1(sandbox, agent_body, step_count): pass

def agent_action_stage_2(sandbox, agent_body, step_count): pass

def agent_action_stage_3(sandbox, agent_body, step_count): pass

def agent_action_stage_4(sandbox, agent_body, step_count): pass
