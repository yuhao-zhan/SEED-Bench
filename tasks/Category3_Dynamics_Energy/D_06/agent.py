import math

GROUND_TOP = 0.5

def build_agent(sandbox):
    density = 0.05
    pillar_w = 0.1
    rest = 0.0
    slab_y = 2.65
    p1 = sandbox.add_beam(7.08, 1.75, pillar_w, 2.5, 0, density)
    sandbox.set_material_properties(p1, restitution=rest)
    sandbox.add_joint(p1, None, (7.08, GROUND_TOP), type="rigid")
    p2 = sandbox.add_beam(7.16, 1.75, pillar_w, 2.5, 0, density)
    sandbox.set_material_properties(p2, restitution=rest)
    sandbox.add_joint(p2, None, (7.16, GROUND_TOP), type="rigid")
    slab_left = sandbox.add_beam(7.12, slab_y, 0.2, 0.22, 0, density)
    sandbox.set_material_properties(slab_left, restitution=0.0)
    sandbox.add_joint(p1, slab_left, (7.08, slab_y), type="rigid")
    sandbox.add_joint(p2, slab_left, (7.16, slab_y), type="rigid")
    p5 = sandbox.add_beam(9.75, 1.75, pillar_w, 2.0, 0, density)
    sandbox.set_material_properties(p5, restitution=rest)
    sandbox.add_joint(p5, None, (9.75, GROUND_TOP), type="rigid")
    slab_right_a = sandbox.add_beam(9.75, slab_y, 0.35, 0.25, 0, density)
    sandbox.set_material_properties(slab_right_a, restitution=0.0)
    sandbox.add_joint(p5, slab_right_a, (9.75, slab_y), type="rigid")
    slab_right_b = sandbox.add_beam(10.75, 1.7, 0.45, 0.3, 0, density)
    sandbox.set_material_properties(slab_right_b, restitution=0.0)
    sandbox.add_joint(slab_right_b, None, (10.75, GROUND_TOP), type="rigid")
    n = len(sandbox.bodies)
    if n > sandbox.MAX_BEAM_COUNT:
        raise ValueError(f"Beam count {n} > {sandbox.MAX_BEAM_COUNT}")
    mass = sandbox.get_structure_mass()
    if mass >= sandbox.MAX_STRUCTURE_MASS:
        raise ValueError(f"Mass {mass:.2f} must be < {sandbox.MAX_STRUCTURE_MASS} kg")
    return slab_right_a

def agent_action(sandbox, agent_body, step_count):
    pass

def _horizontal_grid_absorber(
    sandbox,
    *,
    density: float,
    damping: float,
    x_inner: float,
    x_outer: float,
    anchor_density: float = 1.0,

):
    anchor = sandbox.add_beam(7.1, 5.4, 0.1, 0.1, 0, anchor_density)
    sandbox.add_joint(anchor, None, (7.1, 5.5), type="rigid")
    y_safe = [0.75, 1.75, 2.75, 3.85]
    for y in y_safe:
        b_out = sandbox.add_beam(x_outer, y, 0.4, 0.1, 0, density)
        sandbox.set_damping(b_out, damping, damping)
        sandbox.set_material_properties(b_out, restitution=0.0)
        b_in = sandbox.add_beam(x_inner, y, 0.4, 0.1, 0, density)
        sandbox.set_damping(b_in, damping, damping)
        sandbox.set_material_properties(b_in, restitution=0.0)
    return anchor

def _dual_column_absorber(sandbox, *, right_x: float, density: float, damping: float):
    anchor = sandbox.add_beam(7.12, 5.42, 0.1, 0.1, 0, max(0.12, density * 0.02))
    sandbox.add_joint(anchor, None, (7.12, 5.52), type="rigid")
    sandbox.set_material_properties(anchor, restitution=0.0)
    y_safe = [0.78, 1.72, 2.78, 3.82]
    for y in y_safe:
        br = sandbox.add_beam(right_x, y, 0.1, 0.88, 0, density)
        sandbox.set_damping(br, damping, damping)
        sandbox.set_material_properties(br, restitution=0.0)
        bl = sandbox.add_beam(7.14, y, 0.1, 0.88, 0, density)
        sandbox.set_damping(bl, damping, damping)
        sandbox.set_material_properties(bl, restitution=0.0)
    return anchor

def build_agent_stage_1(sandbox):
    return _horizontal_grid_absorber(
        sandbox, density=30.0, damping=100.0, x_inner=9.75, x_outer=10.75
    )

def build_agent_stage_2(sandbox):
    return _horizontal_grid_absorber(
        sandbox, density=26.0, damping=128.0, x_inner=7.77, x_outer=9.98
    )

def build_agent_stage_3(sandbox):
    return _horizontal_grid_absorber(
        sandbox, density=22.0, damping=60.0, x_inner=9.52, x_outer=10.62
    )

def build_agent_stage_4(sandbox):
    return _horizontal_grid_absorber(
        sandbox,
        density=30.0,
        damping=210.0,
        x_inner=9.52,
        x_outer=10.62,
        anchor_density=1.0,
    )

def agent_action_stage_1(sandbox, agent_body, step_count):
    pass

def _d06_impulse_scale_linear_vel(body, k: float) -> None:
    vx, vy = body.linearVelocity.x, body.linearVelocity.y
    m = body.mass
    if m <= 0.0:
        return
    body.ApplyLinearImpulse(
        (m * vx * (k - 1.0), m * vy * (k - 1.0)),
        body.worldCenter,
        True,
    )

def agent_action_stage_2(sandbox, agent_body, step_count):
    tb = getattr(sandbox, "_terrain_bodies", None)
    if not tb:
        return
    k_hi = 0.9912 if step_count < 9000 else 0.9968
    for key in ("ball", "ball2", "ball3", "ball4", "ball5", "ball6", "ball7"):
        b = tb.get(key)
        if b is None:
            continue
        if b.position.x > 10.85:
            b.ApplyForceToCenter((-620.0, 0.0), True)
        vx, vy = b.linearVelocity.x, b.linearVelocity.y
        sp = (vx * vx + vy * vy) ** 0.5
        if sp < 0.05:
            continue
        k = k_hi if sp > 0.28 else 0.9984
        _d06_impulse_scale_linear_vel(b, k)

def agent_action_stage_3(sandbox, agent_body, step_count):
    pass

def agent_action_stage_4(sandbox, agent_body, step_count):
    if step_count > 200:
        return
    tb = getattr(sandbox, "_terrain_bodies", None)
    ball = tb.get("ball") if tb else None
    if ball is None:
        return
    vx, vy = ball.linearVelocity.x, ball.linearVelocity.y
    sp = (vx * vx + vy * vy) ** 0.5
    if sp < 0.22:
        return
    drag = 0.987 if step_count < 100 else 0.993
    _d06_impulse_scale_linear_vel(ball, drag)
