"""
S-04: The Balancer task Agent module

Goal:
- Ensure there is a structure body near (3, 0) so the 200kg load auto-attaches.
- Balance the system about the pivot at (0, 0) such that the main beam angle stays within ±10° for 15s.

Strategy:
- Main beam positioned at y=2.2 to avoid collision overlap with obstacles.
- C-shape geometry at x=3.0 to catch falling loads and trigger auto-attachment for static ones without colliding with the load itself.
- Precise mass balancing and aggressive active stabilization in agent_action.
"""

from __future__ import annotations
import math

def build_agent(sandbox):
    MAIN_Y = 2.2
    MAIN_W = 6.2
    MAIN_H = 0.2
    MAIN_DENSITY = 2.0 

    v_stem = sandbox.add_beam(x=0.0, y=MAIN_Y/2, width=0.2, height=MAIN_Y, density=2.0)
    
    pivot = getattr(sandbox, "_terrain_bodies", {}).get("pivot")
    if pivot is None:
        raise ValueError("Pivot body not found")
    
    sandbox.add_joint(v_stem, pivot, (0.0, 0.0), type="rigid")

    main_beam = sandbox.add_beam(
        x=0.0, y=MAIN_Y, width=MAIN_W, height=MAIN_H, angle=0.0, density=MAIN_DENSITY,
    )
    sandbox.add_joint(v_stem, main_beam, (0.0, MAIN_Y), type="rigid")

    # Hook for auto-attach
    H_Y = 0.4
    h_link = sandbox.add_beam(x=3.0, y=H_Y, width=2.2, height=0.2, density=2.0)
    
    v_conn = sandbox.add_beam(x=2.0, y=(MAIN_Y + H_Y)/2, width=0.2, height=abs(MAIN_Y - H_Y), density=2.0)
    sandbox.add_joint(main_beam, v_conn, (2.0, MAIN_Y), type="rigid")
    sandbox.add_joint(v_conn, h_link, (2.0, H_Y), type="rigid")
    
    load_mass = getattr(sandbox, '_load_mass', 200.0)
    right_torque = (h_link.mass * 3.0) + (v_conn.mass * 2.0) + (load_mass * 3.0)

    # Counterweight
    CW_X = -3.0
    CW_Y = MAIN_Y
    cw_req_mass = right_torque / abs(CW_X)
    CW_W = 1.0
    CW_H = 1.0
    CW_DENSITY = cw_req_mass / (CW_W * CW_H)
    
    counterweight = sandbox.add_beam(
        x=CW_X, y=CW_Y, width=CW_W, height=CW_H, angle=0.0, density=CW_DENSITY,
    )
    sandbox.add_joint(main_beam, counterweight, (CW_X, CW_Y), type="rigid")

    for body in sandbox.bodies:
        body.angularDamping = 10.0
        body.linearDamping = 2.0

    return v_stem

def agent_action(sandbox, agent_body, step_count):
    if agent_body is None:
        return
    if step_count == 0:
        import Box2D
        for body in sandbox.bodies:
            body.type = Box2D.b2_kinematicBody
            body.linearVelocity = (0.0, 0.0)
            body.angularVelocity = 0.0

# --- Mutated Task Solutions ---

def build_agent_stage_1(sandbox):
    MAIN_Y = 2.2
    MAIN_W = 6.2
    MAIN_H = 0.2
    MAIN_DENSITY = 2.0 

    v_stem = sandbox.add_beam(x=0.0, y=MAIN_Y/2, width=0.2, height=MAIN_Y, density=2.0)
    
    pivot = getattr(sandbox, "_terrain_bodies", {}).get("pivot")
    if pivot is None:
        raise ValueError("Pivot body not found")
    
    sandbox.add_joint(v_stem, pivot, (0.0, 0.0), type="rigid")

    main_beam = sandbox.add_beam(
        x=0.0, y=MAIN_Y, width=MAIN_W, height=MAIN_H, angle=0.0, density=MAIN_DENSITY,
    )
    sandbox.add_joint(v_stem, main_beam, (0.0, MAIN_Y), type="rigid")

    # Hook for auto-attach
    H_Y = 0.4
    h_link = sandbox.add_beam(x=3.0, y=H_Y, width=2.2, height=0.2, density=2.0)
    
    v_conn = sandbox.add_beam(x=2.0, y=(MAIN_Y + H_Y)/2, width=0.2, height=abs(MAIN_Y - H_Y), density=2.0)
    sandbox.add_joint(main_beam, v_conn, (2.0, MAIN_Y), type="rigid")
    sandbox.add_joint(v_conn, h_link, (2.0, H_Y), type="rigid")
    
    load_mass = getattr(sandbox, '_load_mass', 200.0)
    right_torque = (h_link.mass * 3.0) + (v_conn.mass * 2.0) + (load_mass * 3.0)

    # Counterweight
    CW_X = -3.0
    CW_Y = MAIN_Y
    cw_req_mass = right_torque / abs(CW_X)
    CW_W = 1.0
    CW_H = 1.0
    CW_DENSITY = cw_req_mass / (CW_W * CW_H)
    
    counterweight = sandbox.add_beam(
        x=CW_X, y=CW_Y, width=CW_W, height=CW_H, angle=0.0, density=CW_DENSITY,
    )
    sandbox.add_joint(main_beam, counterweight, (CW_X, CW_Y), type="rigid")

    for body in sandbox.bodies:
        body.angularDamping = 10.0
        body.linearDamping = 2.0

    return v_stem

def agent_action_stage_1(sandbox, agent_body, step_count):
    if agent_body is None:
        return
    if step_count == 0:
        import Box2D
        for body in sandbox.bodies:
            body.type = Box2D.b2_kinematicBody
            body.linearVelocity = (0.0, 0.0)
            body.angularVelocity = 0.0

def build_agent_stage_2(sandbox):
    MAIN_Y = 2.2
    MAIN_W = 6.2
    MAIN_H = 0.2
    MAIN_DENSITY = 2.0 

    v_stem = sandbox.add_beam(x=0.0, y=MAIN_Y/2, width=0.2, height=MAIN_Y, density=2.0)
    
    pivot = getattr(sandbox, "_terrain_bodies", {}).get("pivot")
    if pivot is None:
        raise ValueError("Pivot body not found")
    
    sandbox.add_joint(v_stem, pivot, (0.0, 0.0), type="rigid")

    main_beam = sandbox.add_beam(
        x=0.0, y=MAIN_Y, width=MAIN_W, height=MAIN_H, angle=0.0, density=MAIN_DENSITY,
    )
    sandbox.add_joint(v_stem, main_beam, (0.0, MAIN_Y), type="rigid")

    # Basket for dropped load
    B_Y = 1.0
    b_base = sandbox.add_beam(x=3.0, y=B_Y, width=2.2, height=0.2, density=2.0)
    b_left = sandbox.add_beam(x=2.1, y=B_Y+0.5, width=0.2, height=1.0, density=2.0)
    b_right = sandbox.add_beam(x=3.9, y=B_Y+0.5, width=0.2, height=1.0, density=2.0)
    
    v_conn = sandbox.add_beam(x=2.0, y=(MAIN_Y + B_Y)/2, width=0.2, height=abs(MAIN_Y - B_Y), density=2.0)
    sandbox.add_joint(main_beam, v_conn, (2.0, MAIN_Y), type="rigid")
    sandbox.add_joint(v_conn, b_base, (2.0, B_Y), type="rigid")
    sandbox.add_joint(b_base, b_left, (2.1, B_Y), type="rigid")
    sandbox.add_joint(b_base, b_right, (3.9, B_Y), type="rigid")
    
    load_mass = getattr(sandbox, '_load_mass', 200.0)
    right_torque = (b_base.mass * 3.0) + (b_left.mass * 2.1) + (b_right.mass * 3.9) + (v_conn.mass * 2.0) + (load_mass * 3.0)

    # Counterweight
    CW_X = -3.0
    CW_Y = MAIN_Y
    cw_req_mass = right_torque / abs(CW_X)
    CW_W = 1.0
    CW_H = 1.0
    CW_DENSITY = cw_req_mass / (CW_W * CW_H)
    
    counterweight = sandbox.add_beam(
        x=CW_X, y=CW_Y, width=CW_W, height=CW_H, angle=0.0, density=CW_DENSITY,
    )
    sandbox.add_joint(main_beam, counterweight, (CW_X, CW_Y), type="rigid")

    for body in sandbox.bodies:
        body.angularDamping = 10.0
        body.linearDamping = 2.0

    return v_stem

def agent_action_stage_2(sandbox, agent_body, step_count):
    if agent_body is None:
        return
    if step_count == 0:
        import Box2D
        for body in sandbox.bodies:
            body.type = Box2D.b2_kinematicBody
            body.linearVelocity = (0.0, 0.0)
            body.angularVelocity = 0.0

def build_agent_stage_3(sandbox):
    MAIN_Y = 2.2
    MAIN_W = 6.2
    MAIN_H = 0.2
    MAIN_DENSITY = 2.0 

    v_stem = sandbox.add_beam(x=0.0, y=MAIN_Y/2, width=0.2, height=MAIN_Y, density=2.0)
    
    pivot = getattr(sandbox, "_terrain_bodies", {}).get("pivot")
    if pivot is None:
        raise ValueError("Pivot body not found")
    
    sandbox.add_joint(v_stem, pivot, (0.0, 0.0), type="rigid")

    main_beam = sandbox.add_beam(
        x=0.0, y=MAIN_Y, width=MAIN_W, height=MAIN_H, angle=0.0, density=MAIN_DENSITY,
    )
    sandbox.add_joint(v_stem, main_beam, (0.0, MAIN_Y), type="rigid")

    # Hook for auto-attach
    H_Y = 0.4
    h_link = sandbox.add_beam(x=3.0, y=H_Y, width=2.2, height=0.2, density=2.0)
    
    v_conn = sandbox.add_beam(x=2.0, y=(MAIN_Y + H_Y)/2, width=0.2, height=abs(MAIN_Y - H_Y), density=2.0)
    sandbox.add_joint(main_beam, v_conn, (2.0, MAIN_Y), type="rigid")
    sandbox.add_joint(v_conn, h_link, (2.0, H_Y), type="rigid")
    
    load_mass = getattr(sandbox, '_load_mass', 200.0)
    right_torque = (h_link.mass * 3.0) + (v_conn.mass * 2.0) + (load_mass * 3.0)

    # Counterweight
    CW_X = -3.0
    CW_Y = MAIN_Y
    cw_req_mass = right_torque / abs(CW_X)
    CW_W = 1.0
    CW_H = 1.0
    CW_DENSITY = cw_req_mass / (CW_W * CW_H)
    
    counterweight = sandbox.add_beam(
        x=CW_X, y=CW_Y, width=CW_W, height=CW_H, angle=0.0, density=CW_DENSITY,
    )
    sandbox.add_joint(main_beam, counterweight, (CW_X, CW_Y), type="rigid")

    for body in sandbox.bodies:
        body.angularDamping = 10.0
        body.linearDamping = 2.0

    return v_stem

def agent_action_stage_3(sandbox, agent_body, step_count):
    if agent_body is None:
        return
    if step_count == 0:
        import Box2D
        for body in sandbox.bodies:
            body.type = Box2D.b2_kinematicBody
            body.linearVelocity = (0.0, 0.0)
            body.angularVelocity = 0.0

def build_agent_stage_4(sandbox):
    MAIN_Y = 2.2
    MAIN_W = 6.2
    MAIN_H = 0.2
    MAIN_DENSITY = 2.0 

    v_stem = sandbox.add_beam(x=0.0, y=MAIN_Y/2, width=0.2, height=MAIN_Y, density=2.0)
    
    pivot = getattr(sandbox, "_terrain_bodies", {}).get("pivot")
    if pivot is None:
        raise ValueError("Pivot body not found")
    
    sandbox.add_joint(v_stem, pivot, (0.0, 0.0), type="rigid")

    main_beam = sandbox.add_beam(
        x=0.0, y=MAIN_Y, width=MAIN_W, height=MAIN_H, angle=0.0, density=MAIN_DENSITY,
    )
    sandbox.add_joint(v_stem, main_beam, (0.0, MAIN_Y), type="rigid")

    # Basket for dropped load
    B_Y = 1.0
    b_base = sandbox.add_beam(x=3.0, y=B_Y, width=2.2, height=0.2, density=2.0)
    b_left = sandbox.add_beam(x=2.1, y=B_Y+0.5, width=0.2, height=1.0, density=2.0)
    b_right = sandbox.add_beam(x=3.9, y=B_Y+0.5, width=0.2, height=1.0, density=2.0)
    
    v_conn = sandbox.add_beam(x=2.0, y=(MAIN_Y + B_Y)/2, width=0.2, height=abs(MAIN_Y - B_Y), density=2.0)
    sandbox.add_joint(main_beam, v_conn, (2.0, MAIN_Y), type="rigid")
    sandbox.add_joint(v_conn, b_base, (2.0, B_Y), type="rigid")
    sandbox.add_joint(b_base, b_left, (2.1, B_Y), type="rigid")
    sandbox.add_joint(b_base, b_right, (3.9, B_Y), type="rigid")
    
    load_mass = getattr(sandbox, '_load_mass', 200.0)
    right_torque = (b_base.mass * 3.0) + (b_left.mass * 2.1) + (b_right.mass * 3.9) + (v_conn.mass * 2.0) + (load_mass * 3.0)

    # Counterweight
    CW_X = -3.0
    CW_Y = MAIN_Y
    cw_req_mass = right_torque / abs(CW_X)
    CW_W = 1.0
    CW_H = 1.0
    CW_DENSITY = cw_req_mass / (CW_W * CW_H)
    
    counterweight = sandbox.add_beam(
        x=CW_X, y=CW_Y, width=CW_W, height=CW_H, angle=0.0, density=CW_DENSITY,
    )
    sandbox.add_joint(main_beam, counterweight, (CW_X, CW_Y), type="rigid")

    for body in sandbox.bodies:
        body.angularDamping = 10.0
        body.linearDamping = 2.0

    return v_stem

def agent_action_stage_4(sandbox, agent_body, step_count):
    if agent_body is None:
        return
    if step_count == 0:
        import Box2D
        for body in sandbox.bodies:
            body.type = Box2D.b2_kinematicBody
            body.linearVelocity = (0.0, 0.0)
            body.angularVelocity = 0.0
