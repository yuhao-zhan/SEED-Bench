"""
F-05: The Boat task Agent (EXTREME mode)
Reference: 60 kg budget, 10 cargo, y≥2.0, angle≤18°, 4 rocks + current + rogue double-hit + lateral gusts.
"""
BOAT_LEFT_X = 13.5
BOAT_RIGHT_X = 16.5
BOAT_TOP_Y = 2.7
RAIL_HEIGHT = 0.9
RAIL_WIDTH = 0.2


def build_agent(sandbox):
    """
    Extreme: 60 kg, 10 cargo, y≥2.0, 18°, 4 rocks, current, rogue double-hit, lateral gusts.
    Strategy: heavy ballast for 18° stability, compact rails + front/back barriers, all under 60 kg.
    """
    bodies = []


    ballast_y = 2.24
    for bx in (14.25, 15.75):
        b = sandbox.add_beam(bx, ballast_y, 0.5, 0.17, angle=0, density=247.0)
        sandbox.set_material_properties(b, restitution=0.05)
        bodies.append(b)
        sandbox.add_joint(b, None, (bx, BOAT_TOP_Y - 0.26), type='rigid')


    rail_density = 30.0
    left_rail_y = BOAT_TOP_Y + RAIL_HEIGHT / 2
    for x_rail in (BOAT_LEFT_X, BOAT_RIGHT_X):
        r = sandbox.add_beam(x_rail, left_rail_y, RAIL_WIDTH, RAIL_HEIGHT, angle=0, density=rail_density)
        sandbox.set_material_properties(r, restitution=0.07)
        bodies.append(r)
        sandbox.add_joint(r, None, (x_rail, BOAT_TOP_Y - 0.05), type='rigid')


    lip_front = sandbox.add_beam(14.5, BOAT_TOP_Y + 0.06, 0.18, 0.06, angle=0, density=35.0)
    sandbox.set_material_properties(lip_front, restitution=0.07)
    bodies.append(lip_front)
    sandbox.add_joint(lip_front, None, (14.5, BOAT_TOP_Y), type='rigid')


    lip_back = sandbox.add_beam(15.5, BOAT_TOP_Y + 0.06, 0.18, 0.06, angle=0, density=35.0)
    sandbox.set_material_properties(lip_back, restitution=0.07)
    bodies.append(lip_back)
    sandbox.add_joint(lip_back, None, (15.5, BOAT_TOP_Y), type='rigid')


    barrier_y = BOAT_TOP_Y + 0.18
    for bx in (14.5, 15.5):
        bar = sandbox.add_beam(bx, barrier_y, 0.26, 0.2, angle=0, density=42.0)
        sandbox.set_material_properties(bar, restitution=0.07)
        bodies.append(bar)
        sandbox.add_joint(bar, None, (bx, BOAT_TOP_Y), type='rigid')

    total_mass = sandbox.get_structure_mass()
    if total_mass > sandbox.MAX_STRUCTURE_MASS:
        raise ValueError(f"Structure mass {total_mass:.2f} kg exceeds limit {sandbox.MAX_STRUCTURE_MASS} kg")

    return bodies[0]


def agent_action(sandbox, agent_body, step_count):
    """No active control; structure is passive."""
    pass
