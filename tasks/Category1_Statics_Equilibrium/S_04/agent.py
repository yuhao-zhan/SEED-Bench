"""
S-04: The Balancer task Agent module
"""

from __future__ import annotations
import math

def build_agent(sandbox):
    """
    Build a balanced structure for the pivot.
    Symmetric design with catch platform and counterweight.
    """
    MAIN_Y = 2.2
    v_stem = sandbox.add_beam(x=0.0, y=MAIN_Y/2, width=0.2, height=MAIN_Y, density=50.0)
    pivot = sandbox._terrain_bodies.get("pivot")
    sandbox.add_joint(v_stem, pivot, (0.0, 0.0), type="rigid")
    
    main_beam = sandbox.add_beam(x=0.0, y=MAIN_Y, width=7.0, height=0.2, density=10.0)
    sandbox.add_joint(v_stem, main_beam, (0.0, MAIN_Y), type="rigid")
    
    # Catch platform at x=3
    h_link = sandbox.add_beam(x=3.0, y=0.4, width=2.2, height=0.2, density=2.0)
    v_conn = sandbox.add_beam(x=2.0, y=(MAIN_Y + 0.4)/2, width=0.2, height=abs(MAIN_Y - 0.4), density=2.0)
    sandbox.add_joint(main_beam, v_conn, (2.0, MAIN_Y), type="rigid")
    sandbox.add_joint(v_conn, h_link, (2.0, 0.4), type="rigid")
    
    # Counterweight at x=-3.5
    counterweight = sandbox.add_beam(x=-3.5, y=MAIN_Y, width=1.0, height=1.0, density=100.0)
    sandbox.add_joint(main_beam, counterweight, (-3.5, MAIN_Y), type="rigid")
    
    return v_stem

def agent_action(sandbox, agent_body, step_count):
    pass


# --- Mutated Task Solutions ---

def build_agent_stage_1(sandbox):
    """
    Stage 1: Structural Fragility.
    Requires extremely precise static balance to not exceed max_joint_torque=50.0.
    We use a precise Non-Overlapping Catcher to prevent Box2D collision snaps.
    """
    MAIN_Y = 1.5
    main_beam = sandbox.add_beam(x=0.0, y=MAIN_Y, width=8.0, height=0.4, density=100.0)
    pivot = sandbox._terrain_bodies.get("pivot")
    sandbox.add_joint(main_beam, pivot, (0.0, 0.0), type="pivot")
    
    v_conn = sandbox.add_beam(x=3.7, y=0.9, width=0.2, height=1.2, density=10.0)
    sandbox.add_joint(main_beam, v_conn, (3.7, MAIN_Y), type="rigid")
    
    probe = sandbox.add_beam(x=3.35, y=0.3, width=0.7, height=0.2, density=10.0)
    sandbox.add_joint(v_conn, probe, (3.7, 0.3), type="rigid")
    
    bodies_info = [
        (0.0, 8.0 * 0.4 * 100.0),
        (3.7, 0.2 * 1.2 * 10.0),
        (3.35, 0.7 * 0.2 * 10.0),
        (3.0, 200.0) 
    ]
    
    total_tau = sum(-10.0 * m * x for x, m in bodies_info)
    cw_x = -3.5
    cw_factor = -10.0 * cw_x
    req_m = -total_tau / cw_factor
    
    cw = sandbox.add_beam(x=cw_x, y=MAIN_Y, width=1.0, height=1.0, density=req_m)
    sandbox.add_joint(main_beam, cw, (cw_x, MAIN_Y), type="rigid")
    
    return main_beam

def agent_action_stage_1(sandbox, agent_body, step_count): pass


def build_agent_stage_2(sandbox):
    """
    Stage 2: Aerodynamic Overturning (Wind 50 right).
    Torque = m * (-10x - 50y). Counterweight must balance it.
    """
    MAIN_Y = 1.5
    main_beam = sandbox.add_beam(x=0.0, y=MAIN_Y, width=8.0, height=0.4, density=100.0)
    pivot = sandbox._terrain_bodies.get("pivot")
    sandbox.add_joint(main_beam, pivot, (0.0, 0.0), type="pivot")
    
    v_conn = sandbox.add_beam(x=3.7, y=0.9, width=0.2, height=1.2, density=10.0)
    sandbox.add_joint(main_beam, v_conn, (3.7, MAIN_Y), type="rigid")
    
    probe = sandbox.add_beam(x=3.35, y=0.3, width=0.7, height=0.2, density=10.0)
    sandbox.add_joint(v_conn, probe, (3.7, 0.3), type="rigid")
    
    bodies_info = [
        (0.0, MAIN_Y, 8.0 * 0.4 * 100.0),
        (3.7, 0.9, 0.2 * 1.2 * 10.0),
        (3.35, 0.3, 0.7 * 0.2 * 10.0),
        (3.0, 0.5, 200.0) 
    ]
    
    total_tau = sum(m * (-10*x - 50*y) for x, y, m in bodies_info)
    
    # CW far left and low
    cw_x, cw_y = -3.5, 0.5
    cw_factor = (-10*cw_x - 50*cw_y) # 35 - 25 = 10
    
    req_m = -total_tau / cw_factor
    
    cw = sandbox.add_beam(x=cw_x, y=cw_y, width=1.0, height=1.0, density=req_m)
    sandbox.add_joint(main_beam, cw, (cw_x, cw_y), type="rigid")
    
    return main_beam

def agent_action_stage_2(sandbox, agent_body, step_count): pass


def build_agent_stage_3(sandbox):
    """
    Stage 3: The Labyrinth.
    Wall from 0.5 to 2.5, height 2.0. Must arch over it.
    """
    stem = sandbox.add_beam(x=0.0, y=1.25, width=0.4, height=2.5, density=100.0)
    pivot = sandbox._terrain_bodies.get("pivot")
    sandbox.add_joint(stem, pivot, (0.0, 0.0), type="pivot")
    
    over_beam = sandbox.add_beam(x=0.0, y=2.5, width=8.0, height=0.4, density=100.0)
    sandbox.add_joint(stem, over_beam, (0.0, 2.5), type="rigid")
    
    v_conn = sandbox.add_beam(x=3.7, y=1.4, width=0.2, height=2.2, density=10.0)
    sandbox.add_joint(over_beam, v_conn, (3.7, 2.5), type="rigid")
    
    probe = sandbox.add_beam(x=3.35, y=0.3, width=0.7, height=0.2, density=10.0)
    sandbox.add_joint(v_conn, probe, (3.7, 0.3), type="rigid")
    
    bodies_info = [
        (0.0, 0.4*2.5*100.0),
        (0.0, 8.0*0.4*100.0),
        (3.7, 0.2*2.2*10.0),
        (3.35, 0.7*0.2*10.0),
        (3.0, 200.0)
    ]
    
    total_tau = sum(-10.0 * m * x for x, m in bodies_info)
    cw_x = -3.5
    cw_factor = -10.0 * cw_x
    req_m = -total_tau / cw_factor
    
    cw = sandbox.add_beam(x=cw_x, y=2.5, width=1.0, height=1.0, density=req_m)
    sandbox.add_joint(over_beam, cw, (cw_x, 2.5), type="rigid")
    
    return stem

def agent_action_stage_3(sandbox, agent_body, step_count): pass


def build_agent_stage_4(sandbox):
    """
    Stage 4: Planetary Kinetic Storm.
    Moving obstacle (-1 to 1, y=1 to 2). Drop load (300kg from 4.0). Wind 20, Grav -20.
    The dropped load forms a parabolic arc due to wind, landing at x=5.8.
    """
    # Base beam at y=0.3 to easily pass under the sweeping obstacle.
    beam = sandbox.add_beam(x=3.0, y=0.3, width=7.0, height=0.4, density=100.0)
    pivot = sandbox._terrain_bodies.get("pivot")
    sandbox.add_joint(beam, pivot, (0.0, 0.0), type="pivot")
    
    # Catch basket at x=5.8, base at y=0.5
    plat = sandbox.add_beam(x=5.8, y=0.5, width=2.0, height=0.4, density=100.0)
    sandbox.add_joint(beam, plat, (5.8, 0.3), type="rigid")
    
    # Left wall at 5.0, Right wall at 6.6.
    wall_l = sandbox.add_beam(x=5.0, y=1.2, width=0.4, height=1.8, density=100.0)
    sandbox.add_joint(plat, wall_l, (5.0, 0.5), type="rigid")
    
    wall_r = sandbox.add_beam(x=6.6, y=1.2, width=0.4, height=1.8, density=100.0)
    sandbox.add_joint(plat, wall_r, (6.6, 0.5), type="rigid")
    
    # CW arm extending left
    cw_arm = sandbox.add_beam(x=-4.0, y=0.3, width=7.0, height=0.4, density=100.0)
    sandbox.add_joint(beam, cw_arm, (-0.5, 0.3), type="rigid")
    
    bodies_info = [
        (3.0, 0.3, 7.0*0.4*100.0),
        (5.8, 0.5, 2.0*0.4*100.0),
        (5.0, 1.2, 0.4*1.8*100.0),
        (6.6, 1.2, 0.4*1.8*100.0),
        (-4.0, 0.3, 7.0*0.4*100.0),
        (5.8, 1.2, 300.0) # Dropped load rests around y=1.2
    ]
    
    total_tau = sum(m * (-20*x - 20*y) for x, y, m in bodies_info)
    
    cw_x, cw_y = -7.0, 0.3
    cw_factor = -20*cw_x - 20*cw_y # 140 - 6 = 134
    
    req_m = -total_tau / cw_factor
    cw = sandbox.add_beam(x=cw_x, y=cw_y, width=1.0, height=1.0, density=req_m)
    sandbox.add_joint(cw_arm, cw, (cw_x, cw_y), type="rigid")
    
    # Extra anchor mass near pivot for dropping stability
    anchor = sandbox.add_beam(x=0.0, y=0.3, width=1.0, height=0.4, density=10000.0)
    sandbox.add_joint(beam, anchor, (0.0, 0.3), type="rigid")
    
    return beam

def agent_action_stage_4(sandbox, agent_body, step_count): pass
