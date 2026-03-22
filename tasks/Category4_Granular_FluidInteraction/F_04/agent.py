BAR_WIDTH = 0.08

GAP_UPPER = 0.22

GAP_LOWER = 0.14

BAR_HEIGHT_UPPER = 0.34

BAR_HEIGHT_LOWER = 0.28

Y_UPPER = 2.22

Y_LOWER = 2.00

DENSITY = 170.0

N_UPPER = 4

N_LOWER = 2

X_START = 5.25

LOWER_X_OFFSET = (BAR_WIDTH + GAP_UPPER) / 2

NUDGE_PERIOD = 32

NUDGE_FORCE_SMALL = 30.0

NUDGE_FORCE_MEDIUM = 25.5

def build_agent(sandbox):
    bodies = []
    x = X_START
    for _ in range(N_UPPER):
        bar = sandbox.add_static_beam(x, Y_UPPER, BAR_WIDTH, BAR_HEIGHT_UPPER, angle=0, density=DENSITY)
        sandbox.set_material_properties(bar, restitution=0.0)
        bodies.append(bar)
        x += BAR_WIDTH + GAP_UPPER
    x = X_START + LOWER_X_OFFSET
    for _ in range(N_LOWER):
        bar = sandbox.add_static_beam(x, Y_LOWER, BAR_WIDTH, BAR_HEIGHT_LOWER, angle=0, density=DENSITY)
        sandbox.set_material_properties(bar, restitution=0.0)
        bodies.append(bar)
        x += BAR_WIDTH + GAP_LOWER
    return bodies[0]

def agent_action(sandbox, agent_body, step_count):
    if step_count % NUDGE_PERIOD != 0:
        return
    for p in sandbox.get_particles_small():
        if p.active and p.position.y > 1.92:
            sandbox.apply_force(p, (0, -NUDGE_FORCE_SMALL))
    for p in sandbox.get_particles_medium():
        if p.active and p.position.y > 2.52:
            sandbox.apply_force(p, (0, -NUDGE_FORCE_MEDIUM))

def build_agent_stage_1(sandbox):
    bodies = []
    w_u = 0.62
    h_u = 0.08
    y_u = 2.34
    x_u = 5.24 + w_u / 2
    for _ in range(2):
        bar = sandbox.add_static_beam(x_u, y_u, w_u, h_u, density=55.0)
        sandbox.set_material_properties(bar, restitution=0.0)
        bodies.append(bar)
        x_u += w_u + 0.20
    w_l = 0.66
    h_l = 0.09
    y_l = 1.78
    x_l = 5.24 + w_l / 2
    for _ in range(2):
        bar = sandbox.add_static_beam(x_l, y_l, w_l, h_l, density=55.0)
        sandbox.set_material_properties(bar, restitution=0.0)
        bodies.append(bar)
        x_l += w_l + 0.13
    return bodies[0] if bodies else None

def agent_action_stage_1(sandbox, agent_body, step_count):
    for p in sandbox.get_particles_small():
        if not p.active:
            continue
        y = p.position.y
        if y > 1.86:
            sandbox.apply_force(p, (0, -720.0))
        elif y > 1.72:
            sandbox.apply_force(p, (0, -280.0))
    for p in sandbox.get_particles_medium():
        if not p.active:
            continue
        y = p.position.y
        if y > 2.50:
            sandbox.apply_force(p, (0, -620.0))
        elif y < 1.94:
            sandbox.apply_force(p, (0, 420.0))

def build_agent_stage_2(sandbox):
    bodies = []
    x = 5.56
    for _ in range(4):
        bar = sandbox.add_static_beam(x, 2.22, 0.08, 0.34, angle=0, density=120.0)
        sandbox.set_material_properties(bar, restitution=0.1)
        bodies.append(bar)
        x += 0.08 + 0.22
    x = 5.56 + (0.08 + 0.22) / 2
    for _ in range(2):
        bar = sandbox.add_static_beam(x, 2.00, 0.08, 0.28, angle=0, density=120.0)
        sandbox.set_material_properties(bar, restitution=0.1)
        bodies.append(bar)
        x += 0.08 + 0.14
    return bodies[0]

def agent_action_stage_2(sandbox, agent_body, step_count):
    if step_count % 3 != 0:
        return
    for p in sandbox.get_particles_small():
        if p.active and p.position.y > 1.90:
            sandbox.apply_force(p, (0, -22000.0))
    for p in sandbox.get_particles_medium():
        if p.active and p.position.y > 2.22:
            sandbox.apply_force(p, (0, -16000.0))

def build_agent_stage_3(sandbox):
    bodies = []
    wall = sandbox.add_static_beam(6.85, 2.05, 0.06, 0.66, density=95.0)
    sandbox.set_material_properties(wall, restitution=0.0)
    bodies.append(wall)
    w_u = 0.69
    y_u = 2.37
    x_u = 5.22 + w_u / 2
    for _ in range(2):
        bar = sandbox.add_static_beam(x_u, y_u, w_u, 0.08, density=95.0)
        sandbox.set_material_properties(bar, restitution=0.0)
        bodies.append(bar)
        x_u += w_u + 0.22
    w_l = 0.73
    y_l = 1.80
    x_l = 5.22 + w_l / 2
    for _ in range(2):
        bar = sandbox.add_static_beam(x_l, y_l, w_l, 0.08, density=95.0)
        sandbox.set_material_properties(bar, restitution=0.0)
        bodies.append(bar)
        x_l += w_l + 0.14
    return bodies[0]

def agent_action_stage_3(sandbox, agent_body, step_count):
    flip = -1.0 if (step_count // 24) % 2 == 0 else 1.0
    wx = flip * 320.0
    for p in sandbox.get_particles_small():
        if p.active and p.position.y > 1.92:
            sandbox.apply_force(p, (wx - 180.0, -265.0))
    for p in sandbox.get_particles_medium():
        if p.active and p.position.y > 2.23:
            sandbox.apply_force(p, (wx * 0.9 - 160.0, -230.0))

def build_agent_stage_4(sandbox):
    bodies = []
    wall = sandbox.add_static_beam(6.85, 2.05, 0.06, 0.66, density=50.0)
    sandbox.set_material_properties(wall, restitution=0.0)
    bodies.append(wall)
    w_u = 0.69
    y_u = 2.37
    x_u = 5.22 + w_u/2
    for _ in range(2):
        bar = sandbox.add_static_beam(x_u, y_u, w_u, 0.08, density=50.0)
        sandbox.set_material_properties(bar, restitution=0.0)
        bodies.append(bar)
        x_u += w_u + 0.22
    w_l = 0.73
    y_l = 1.80
    x_l = 5.22 + w_l/2
    for _ in range(2):
        bar = sandbox.add_static_beam(x_l, y_l, w_l, 0.08, density=50.0)
        sandbox.set_material_properties(bar, restitution=0.0)
        bodies.append(bar)
        x_l += w_l + 0.14
    return bodies[0]

def agent_action_stage_4(sandbox, agent_body, step_count):
    for p in sandbox.get_particles_small():
        if p.active and p.position.y > 1.92:
            sandbox.apply_force(p, (-800.0, -300.0))
    for p in sandbox.get_particles_medium():
        if p.active and p.position.y > 2.25:
            sandbox.apply_force(p, (-600.0, -200.0))
