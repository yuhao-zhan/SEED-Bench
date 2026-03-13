BOAT_LEFT_X = 13.5

BOAT_RIGHT_X = 16.5

BOAT_TOP_Y = 2.7

RAIL_HEIGHT = 0.9

RAIL_WIDTH = 0.2

def build_agent(sandbox):
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
    pass

def build_agent_stage_1(sandbox):
    bodies = []
    anchor_y = 2.6
    for ox in (12.2, 17.8):
        pontoon = sandbox.add_beam(ox, 2.55, 0.6, 0.12, angle=0, density=80.0)
        bodies.append(pontoon)
        for dx in [-0.2, -0.1, 0, 0.1, 0.2]:
            sandbox.add_joint(pontoon, None, (ox + dx, anchor_y), type='rigid')
    xs = [13.8 + i*0.3 for i in range(10)]
    for bx in xs:
        b = sandbox.add_beam(bx, 2.55, 0.2, 0.1, angle=0, density=80.0)
        bodies.append(b)
        for dx in [-0.08, 0, 0.08]:
            sandbox.add_joint(b, None, (bx + dx, anchor_y), type='rigid')
    for x_rail in (BOAT_LEFT_X, BOAT_RIGHT_X):
        r = sandbox.add_beam(x_rail, BOAT_TOP_Y + 0.5, 0.15, 1.0, angle=0, density=10.0)
        bodies.append(r)
        for dy in [0, 0.2, 0.4]:
            sandbox.add_joint(r, None, (x_rail, anchor_y + dy), type='rigid')
    ceiling = sandbox.add_beam(15.0, BOAT_TOP_Y + 1.0, 3.2, 0.1, angle=0, density=10.0)
    bodies.append(ceiling)
    for cx in [13.5, 14.5, 15.5, 16.5]:
        sandbox.add_joint(ceiling, None, (cx, BOAT_TOP_Y + 1.0), type='rigid')
    for bx in [14.0, 14.5, 15.0, 15.5, 16.0]:
        bar = sandbox.add_beam(bx, BOAT_TOP_Y + 0.25, 0.1, 0.5, angle=0, density=8.0)
        bodies.append(bar)
        sandbox.add_joint(bar, None, (bx, anchor_y), type='rigid')
    return bodies[0]

def agent_action_stage_1(sandbox, agent_body, step_count):
    pass

def build_agent_stage_2(sandbox):
    bodies = []
    anchor_y = 2.6
    for bx in (14.2, 15.8):
        b = sandbox.add_beam(bx, 2.6, 0.8, 0.1, angle=0, density=180.0)
        bodies.append(b)
        for dx in [-0.2, 0, 0.2]:
            sandbox.add_joint(b, None, (bx + dx, anchor_y), type='rigid')
    for x_rail in (BOAT_LEFT_X - 0.1, BOAT_RIGHT_X + 0.1):
        r = sandbox.add_beam(x_rail, BOAT_TOP_Y + 0.5, 0.2, 1.0, angle=0, density=20.0)
        bodies.append(r)
        sandbox.add_joint(r, None, (x_rail, anchor_y), type='rigid')
        sandbox.add_joint(r, None, (x_rail, anchor_y + 0.2), type='rigid')
    ceiling = sandbox.add_beam(15.0, BOAT_TOP_Y + 1.0, 3.2, 0.1, angle=0, density=15.0)
    bodies.append(ceiling)
    for cx in [13.5, 14.5, 15.5, 16.5]:
        sandbox.add_joint(ceiling, None, (cx, BOAT_TOP_Y + 1.0), type='rigid')
    for bx in (14.2, 15.0, 15.8):
        bar = sandbox.add_beam(bx, BOAT_TOP_Y + 0.3, 0.1, 0.6, angle=0, density=15.0)
        bodies.append(bar)
        sandbox.add_joint(bar, None, (bx, anchor_y), type='rigid')
    return bodies[0]

def agent_action_stage_2(sandbox, agent_body, step_count):
    pass

def build_agent_stage_3(sandbox):
    bodies = []
    anchor_y = 2.6
    for bx in (14.0, 15.0, 16.0):
        b = sandbox.add_beam(bx, 2.5, 0.8, 0.1, angle=0, density=150.0)
        bodies.append(b)
        sandbox.add_joint(b, None, (bx, anchor_y), type='rigid')
    for ox in (12.5, 17.5):
        pontoon = sandbox.add_beam(ox, 2.5, 0.8, 0.2, angle=0, density=40.0)
        bodies.append(pontoon)
        sandbox.add_joint(pontoon, None, (ox, anchor_y), type='rigid')
    for x_rail in (BOAT_LEFT_X, BOAT_RIGHT_X):
        r = sandbox.add_beam(x_rail, BOAT_TOP_Y + 0.4, 0.15, 0.8, angle=0, density=20.0)
        bodies.append(r)
        sandbox.add_joint(r, None, (x_rail, anchor_y), type='rigid')
    for bx in (14.3, 15.7):
        bar = sandbox.add_beam(bx, BOAT_TOP_Y + 0.2, 0.1, 0.4, angle=0, density=20.0)
        bodies.append(bar)
        sandbox.add_joint(bar, None, (bx, anchor_y), type='rigid')
    return bodies[0]

def agent_action_stage_3(sandbox, agent_body, step_count):
    pass

def build_agent_stage_4(sandbox):
    bodies = []
    anchor_y = 2.6
    xs = [13.6 + i*0.2 for i in range(15)]
    for bx in xs:
        b = sandbox.add_beam(bx, 2.55, 0.15, 0.08, angle=0, density=60.0)
        bodies.append(b)
        for dx in [-0.05, 0, 0.05]:
            sandbox.add_joint(b, None, (bx + dx, anchor_y), type='rigid')
    for ox in (12.0, 18.0):
        pontoon = sandbox.add_beam(ox, 2.55, 0.7, 0.12, angle=0, density=50.0)
        bodies.append(pontoon)
        for dx in [-0.2, -0.1, 0, 0.1, 0.2]:
            sandbox.add_joint(pontoon, None, (ox + dx, anchor_y), type='rigid')
    for x_rail in (BOAT_LEFT_X - 0.2, BOAT_RIGHT_X + 0.2):
        r = sandbox.add_beam(x_rail, BOAT_TOP_Y + 0.5, 0.2, 1.0, angle=0, density=8.0)
        bodies.append(r)
        for dy in [0, 0.2, 0.4, 0.6, 0.8]:
            sandbox.add_joint(r, None, (x_rail, anchor_y + dy), type='rigid')
    ceiling = sandbox.add_beam(15.0, BOAT_TOP_Y + 1.0, 3.6, 0.1, angle=0, density=6.0)
    bodies.append(ceiling)
    for cx in [13.0, 13.5, 14.0, 14.5, 15.0, 15.5, 16.0, 16.5, 17.0, 17.5]:
        sandbox.add_joint(ceiling, None, (cx, BOAT_TOP_Y + 1.0), type='rigid')
    for bx in [13.8, 14.2, 14.6, 15.0, 15.4, 15.8, 16.2]:
        bar = sandbox.add_beam(bx, BOAT_TOP_Y + 0.4, 0.06, 0.8, angle=0, density=6.0)
        bodies.append(bar)
        sandbox.add_joint(bar, None, (bx, anchor_y), type='rigid')
        sandbox.add_joint(bar, None, (bx, anchor_y + 0.4), type='rigid')
    return bodies[0]

def agent_action_stage_4(sandbox, agent_body, step_count):
    pass
