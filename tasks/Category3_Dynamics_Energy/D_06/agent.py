"""
D-06: The Catch — deflector cooperation, ball-ball coupling, order constraint.
Center is blocked by deflector; left + right coverage only.
6 beams, ~10 kg. Must anchor to ground.
"""
import math

GROUND_TOP = 0.5


def build_agent(sandbox):
    """
    Center [8.22, 8.55] is forbidden (deflector blocks). Use left [7, 7.18] and right [9.5, 10], [10.5, 11].
    Low restitution for fast absorption — each ball caught before next arrives.
    """
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
