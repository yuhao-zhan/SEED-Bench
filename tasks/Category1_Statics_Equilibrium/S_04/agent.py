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
    # Stage 1: Glass Pivot. Load=250kg. Gravity=10.0. Torque limit=500.0.
    pivot = sandbox._terrain_bodies.get("pivot")
    core = sandbox.add_beam(x=0.0, y=0.0, width=0.4, height=0.4, density=100.0)
    sandbox.add_joint(core, pivot, (0.0, 0.0), type="pivot")
    arm = sandbox.add_beam(x=0.0, y=0.0, width=7.0, height=0.4, density=100.0)
    sandbox.add_joint(core, arm, (0.0, 0.0), type="rigid")
    catcher = sandbox.add_beam(x=3.0, y=0.0, width=0.4, height=0.4, density=100.0)
    sandbox.add_joint(arm, catcher, (3.0, 0.0), type="rigid")
    dummy = sandbox.add_beam(x=-3.0, y=0.0, width=0.4, height=0.4, density=100.0)
    sandbox.add_joint(arm, dummy, (-3.0, 0.0), type="rigid")
    # Load 250kg at y=0.5. Place CW at y=0.5.
    cw = sandbox.add_beam(x=-3.0, y=0.5, width=1.0, height=1.0, density=250.0)
    sandbox.add_joint(arm, cw, (-3.0, 0.5), type="rigid")
    return core

def build_agent_stage_2(sandbox):
    # Stage 2: Gale. Load=200kg. Wind=100.
    pivot = sandbox._terrain_bodies.get("pivot")
    core = sandbox.add_beam(x=0.0, y=0.0, width=0.4, height=0.4, density=100.0)
    sandbox.add_joint(core, pivot, (0.0, 0.0), type="pivot")
    arm = sandbox.add_beam(x=0.0, y=0.0, width=7.0, height=0.4, density=100.0)
    sandbox.add_joint(core, arm, (0.0, 0.0), type="rigid")
    catcher = sandbox.add_beam(x=3.0, y=0.0, width=0.4, height=0.4, density=100.0)
    sandbox.add_joint(arm, catcher, (3.0, 0.0), type="rigid")
    
    # Load at (3, 0.5): -10*200*3 - 100*200*0.5 = -6000 - 10000 = -16000
    # Structure torque (excl CW): -10*16*3 = -480.
    # Total to balance: -16480
    # CW at x=-3, y=-1: -10*m*-3 - 100*m*-1 = 30*m + 100*m = 130*m
    # m = 16480 / 130 = 126.77
    m_cw = 16480.0 / 130.0
    cw = sandbox.add_beam(x=-3.0, y=-1.0, width=1.0, height=1.0, density=m_cw)
    sandbox.add_joint(arm, cw, (-3.0, -1.0), type="rigid")
    return core

def build_agent_stage_3(sandbox):
    # Stage 3: Corridors. Load=300kg. Gravity=20.0.
    pivot = sandbox._terrain_bodies.get("pivot")
    core = sandbox.add_beam(x=0.0, y=0.0, width=0.4, height=0.4, density=100.0)
    sandbox.add_joint(core, pivot, (0.0, 0.0), type="pivot")
    arm = sandbox.add_beam(x=0.0, y=0.0, width=7.0, height=0.4, density=100.0)
    sandbox.add_joint(core, arm, (0.0, 0.0), type="rigid")
    catcher = sandbox.add_beam(x=3.0, y=0.0, width=0.4, height=0.4, density=100.0)
    sandbox.add_joint(arm, catcher, (3.0, 0.0), type="rigid")
    dummy = sandbox.add_beam(x=-3.0, y=0.0, width=0.4, height=0.4, density=100.0)
    sandbox.add_joint(arm, dummy, (-3.0, 0.0), type="rigid")
    # Load 300kg at y=0.5.
    cw = sandbox.add_beam(x=-3.0, y=0.5, width=1.0, height=1.0, density=300.0)
    sandbox.add_joint(arm, cw, (-3.0, 0.5), type="rigid")
    return core

def build_agent_stage_4(sandbox):
    # Stage 4: Storm. Load=400kg. Gravity=30.0. Wind=10.
    pivot = sandbox._terrain_bodies.get("pivot")
    core = sandbox.add_beam(x=0.0, y=0.0, width=1.0, height=1.0, density=100.0)
    sandbox.add_joint(core, pivot, (0.0, 0.0), type="pivot")
    arm = sandbox.add_beam(x=0.0, y=0.0, width=7.0, height=0.6, density=100.0)
    sandbox.add_joint(core, arm, (0.0, 0.0), type="rigid")
    # Catcher at x=3.5 to catch load at ~4.16
    catcher = sandbox.add_beam(x=3.5, y=0.0, width=3.0, height=0.4, density=100.0)
    sandbox.add_joint(arm, catcher, (3.5, 0.0), type="rigid")
    
    # Load 400kg at (4.16, 0.5): -30*400*4.16 - 10*400*0.5 = -51920
    # Catcher (120kg at 3.5,0): -30*120*3.5 = -12600
    # Total -64520
    # CW at x=-3, y=-2: 90*m + 20*m = 110*m
    # m = 64520 / 110 = 586.54
    m_cw = 64520.0 / 110.0
    cw = sandbox.add_beam(x=-3.0, y=-2.0, width=1.0, height=1.0, density=m_cw)
    sandbox.add_joint(arm, cw, (-3.0, -2.0), type="rigid")
    return core

def agent_action_stage_1(sandbox, agent_body, step_count): pass
def agent_action_stage_2(sandbox, agent_body, step_count): pass
def agent_action_stage_3(sandbox, agent_body, step_count): pass
def agent_action_stage_4(sandbox, agent_body, step_count): pass
