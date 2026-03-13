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
    if mass > sandbox.MAX_STRUCTURE_MASS:
        raise ValueError(f"Mass {mass:.2f} > {sandbox.MAX_STRUCTURE_MASS} kg")
    return slab_right_a

def agent_action(sandbox, agent_body, step_count):
    pass

def build_agent_stage_1(sandbox):
    density = 30.0
    anchor = sandbox.add_beam(7.1, 5.4, 0.1, 0.1, 0, 1.0)
    sandbox.add_joint(anchor, None, (7.1, 5.5), type="rigid")
    y_safe = [0.75, 1.75, 2.75, 3.85]
    for y in y_safe:
        b1 = sandbox.add_beam(10.75, y, 0.4, 0.1, 0, density)
        sandbox.set_damping(b1, 100, 100)
        b2 = sandbox.add_beam(9.75, y, 0.4, 0.1, 0, density)
        sandbox.set_damping(b2, 100, 100)
    return anchor

def build_agent_stage_2(sandbox):
    return build_agent_stage_1(sandbox)

def build_agent_stage_3(sandbox):
    density = 10.0
    anchor = sandbox.add_beam(7.1, 5.4, 0.1, 0.1, 0, 0.1)
    sandbox.add_joint(anchor, None, (7.1, 5.5), type="rigid")
    y_safe = [0.75, 1.75, 2.75, 3.85]
    for y in y_safe:
        b1 = sandbox.add_beam(10.6, y, 0.1, 0.9, 0, density)
        sandbox.set_damping(b1, 100, 100)
        b2 = sandbox.add_beam(7.1, y, 0.1, 0.9, 0, density)
        sandbox.set_damping(b2, 100, 100)
    return anchor

def build_agent_stage_4(sandbox):
    density = 5.0
    anchor = sandbox.add_beam(7.1, 5.4, 0.1, 0.1, 0, 0.1)
    sandbox.add_joint(anchor, None, (7.1, 5.5), type="rigid")
    for y in [0.75, 1.75, 2.75, 3.85]:
        b = sandbox.add_beam(7.1, y, 0.1, 0.9, 0, density)
        sandbox.set_damping(b, 100, 100)
    for x in [7.76, 9.75, 10.75]:
        b = sandbox.add_beam(x, 0.6, 1.0, 0.2, 0, density)
        sandbox.set_damping(b, 100, 100)
    return anchor

def agent_action_stage_1(sandbox, agent_body, step_count):
    pass

def agent_action_stage_2(sandbox, agent_body, step_count):
    pass

def agent_action_stage_3(sandbox, agent_body, step_count):
    pass

def agent_action_stage_4(sandbox, agent_body, step_count):
    pass
