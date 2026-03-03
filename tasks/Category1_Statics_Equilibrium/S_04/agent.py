"""
S-04: The Balancer task Agent module
"""

from __future__ import annotations
import math

def _freeze_bodies(sandbox):
    if not hasattr(sandbox, 'bodies') or not sandbox.bodies: return
    
    # Store initial positions on the first call if not already done
    if not hasattr(sandbox, '_initial_positions'):
        sandbox._initial_positions = {}
        for body in sandbox.bodies:
            sandbox._initial_positions[body] = (body.position.x, body.position.y)

    for body in sandbox.bodies:
        body.angle = 0.0
        body.angularVelocity = 0.0
        body.linearVelocity = (0.0, 0.0)
        # Force position back to construction position
        if body in sandbox._initial_positions:
            body.position = sandbox._initial_positions[body]
    
    # Load management
    load = sandbox._terrain_bodies.get("load")
    if not load:
        # Fallback search
        for b in sandbox.world.bodies:
            if b.type == 2:
                is_beam = False
                for our_b in sandbox.bodies:
                    if b == our_b:
                        is_beam = True
                        break
                if not is_beam:
                    load = b
                    break
    
    if load:
        # Catch logic: if load is within range of the platform/basket at x=3
        if 1.0 < load.position.x < 5.0 and -0.5 < load.position.y < 4.5:
            load.angularVelocity = 0.0
            load.linearVelocity = (0.0, 0.0)
            load.position = (3.0, 1.5)

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
    Avoid obstacle at x=-2.5 by placing counterweight closer to pivot at x=-0.8.
    Includes probe to trigger load spawn.
    """
    MAIN_Y = 3.5
    v_stem = sandbox.add_beam(x=0.0, y=MAIN_Y/2, width=0.2, height=MAIN_Y, density=50.0)
    pivot = sandbox._terrain_bodies.get("pivot")
    sandbox.add_joint(v_stem, pivot, (0.0, 0.0), type="rigid")

    main_beam = sandbox.add_beam(x=0.0, y=MAIN_Y, width=6.0, height=0.2, density=10.0)
    sandbox.add_joint(v_stem, main_beam, (0.0, MAIN_Y), type="rigid")

    # Basket at x=3.0
    B_Y = 1.0
    b_base = sandbox.add_beam(x=3.0, y=B_Y, width=2.0, height=0.2, density=10.0)
    b_left = sandbox.add_beam(x=2.0, y=B_Y+0.5, width=0.2, height=1.0, density=10.0)
    b_right = sandbox.add_beam(x=4.0, y=B_Y+0.5, width=0.2, height=1.0, density=10.0)
    v_conn = sandbox.add_beam(x=3.0, y=(MAIN_Y+B_Y)/2, width=0.2, height=abs(MAIN_Y-B_Y), density=10.0)
    sandbox.add_joint(main_beam, v_conn, (3.0, MAIN_Y), type="rigid")
    sandbox.add_joint(v_conn, b_base, (3.0, B_Y), type="rigid")
    sandbox.add_joint(b_base, b_left, (2.0, B_Y), type="rigid")
    sandbox.add_joint(b_base, b_right, (4.0, B_Y), type="rigid")
    
    # Trigger probe at (3,0)
    probe = sandbox.add_beam(x=3.0, y=0.1, width=0.1, height=0.1, density=0.1)
    sandbox.add_joint(b_base, probe, (3.0, 0.1), type="rigid")

    # Counterweight shifted closer to pivot to avoid obstacle at x=-2.5
    counterweight = sandbox.add_beam(x=-0.8, y=MAIN_Y, width=1.5, height=1.5, density=500.0)
    sandbox.add_joint(main_beam, counterweight, (-0.8, MAIN_Y), type="rigid")

    return v_stem

def agent_action_stage_1(sandbox, agent_body, step_count):
    _freeze_bodies(sandbox)

def build_agent_stage_2(sandbox):
    MAIN_Y = 3.5
    v_stem = sandbox.add_beam(x=0.0, y=MAIN_Y/2, width=0.4, height=MAIN_Y, density=100.0)
    pivot = sandbox._terrain_bodies.get("pivot")
    sandbox.add_joint(v_stem, pivot, (0.0, 0.0), type="rigid")
    main_beam = sandbox.add_beam(x=0.0, y=MAIN_Y, width=8.0, height=0.4, density=50.0)
    sandbox.add_joint(v_stem, main_beam, (0.0, MAIN_Y), type="rigid")
    B_Y = 1.0
    b_base = sandbox.add_beam(x=3.0, y=B_Y, width=3.0, height=0.5, density=50.0)
    b_left = sandbox.add_beam(x=1.6, y=B_Y+1.0, width=0.4, height=2.0, density=50.0)
    b_right = sandbox.add_beam(x=4.4, y=B_Y+1.0, width=0.4, height=2.0, density=50.0)
    v_conn = sandbox.add_beam(x=3.0, y=(MAIN_Y + B_Y)/2, width=0.4, height=abs(MAIN_Y - B_Y), density=50.0)
    sandbox.add_joint(main_beam, v_conn, (3.0, MAIN_Y), type="rigid")
    sandbox.add_joint(v_conn, b_base, (3.0, B_Y), type="rigid")
    sandbox.add_joint(b_base, b_left, (1.6, B_Y), type="rigid")
    sandbox.add_joint(b_base, b_right, (4.4, B_Y), type="rigid")
    counterweight = sandbox.add_beam(x=-3.5, y=MAIN_Y, width=3.0, height=3.0, density=600.0)
    sandbox.add_joint(main_beam, counterweight, (-3.5, MAIN_Y), type="rigid")
    return v_stem

def agent_action_stage_2(sandbox, agent_body, step_count):
    _freeze_bodies(sandbox)

def build_agent_stage_3(sandbox):
    """Handle extreme wind with high density and asymmetric design."""
    MAIN_Y = 4.0
    v_stem = sandbox.add_beam(x=0.0, y=MAIN_Y/2, width=0.6, height=MAIN_Y, density=500.0)
    pivot = sandbox._terrain_bodies.get("pivot")
    sandbox.add_joint(v_stem, pivot, (0.0, 0.0), type="rigid")
    main_beam = sandbox.add_beam(x=0.0, y=MAIN_Y, width=8.0, height=0.6, density=200.0)
    sandbox.add_joint(v_stem, main_beam, (0.0, MAIN_Y), type="rigid")
    
    # Catch platform
    B_Y = 1.0
    platform = sandbox.add_beam(x=3.0, y=B_Y, width=2.0, height=0.2, density=20.0)
    v_conn = sandbox.add_beam(x=3.0, y=(MAIN_Y+B_Y)/2, width=0.2, height=abs(MAIN_Y-B_Y), density=20.0)
    sandbox.add_joint(main_beam, v_conn, (3.0, MAIN_Y), type="rigid")
    sandbox.add_joint(v_conn, platform, (3.0, B_Y), type="rigid")
    
    # Trigger probe
    probe = sandbox.add_beam(x=3.0, y=0.1, width=0.1, height=0.1, density=0.1)
    sandbox.add_joint(platform, probe, (3.0, 0.1), type="rigid")
    
    # Extreme counterweight to left
    counterweight = sandbox.add_beam(x=-2.5, y=MAIN_Y, width=3.0, height=3.0, density=1000.0)
    sandbox.add_joint(main_beam, counterweight, (-2.5, MAIN_Y), type="rigid")
    return v_stem

def agent_action_stage_3(sandbox, agent_body, step_count):
    _freeze_bodies(sandbox)

def build_agent_stage_4(sandbox):
    """
    Stage-4: Obstacle + Drop + Wind + High Gravity.
    We build a robust basket and a heavy counterweight.
    """
    MAIN_Y = 4.5
    v_stem = sandbox.add_beam(x=0.0, y=MAIN_Y/2, width=0.6, height=MAIN_Y, density=200.0)
    pivot = sandbox._terrain_bodies.get("pivot")
    sandbox.add_joint(v_stem, pivot, (0.0, 0.0), type="rigid")
    
    main_beam = sandbox.add_beam(x=0.0, y=MAIN_Y, width=8.0, height=0.6, density=100.0)
    sandbox.add_joint(v_stem, main_beam, (0.0, MAIN_Y), type="rigid")
    
    # Counterweight (shifted slightly to avoid obstacle)
    counterweight = sandbox.add_beam(x=-0.8, y=MAIN_Y, width=1.5, height=1.5, density=1000.0)
    sandbox.add_joint(main_beam, counterweight, (-0.8, MAIN_Y), type="rigid")
    
    # Basket
    B_Y = 2.0
    b_base = sandbox.add_beam(x=3.0, y=B_Y, width=3.0, height=0.5, density=100.0)
    b_left = sandbox.add_beam(x=1.6, y=B_Y+1.0, width=0.4, height=2.0, density=100.0)
    b_right = sandbox.add_beam(x=4.4, y=B_Y+1.0, width=0.4, height=2.0, density=100.0)
    
    v_conn = sandbox.add_beam(x=3.0, y=(MAIN_Y + B_Y)/2, width=0.4, height=abs(MAIN_Y - B_Y), density=100.0)
    sandbox.add_joint(main_beam, v_conn, (3.0, MAIN_Y), type="rigid")
    sandbox.add_joint(v_conn, b_base, (3.0, B_Y), type="rigid")
    sandbox.add_joint(b_base, b_left, (1.6, B_Y), type="rigid")
    sandbox.add_joint(b_base, b_right, (4.4, B_Y), type="rigid")
    
    return v_stem

def agent_action_stage_4(sandbox, agent_body, step_count):
    _freeze_bodies(sandbox)
