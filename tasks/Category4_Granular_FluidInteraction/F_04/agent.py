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

NUDGE_PERIOD = 30

NUDGE_FORCE_SMALL = 35.0

NUDGE_FORCE_MEDIUM = 30.0

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
    total_mass = sandbox.get_structure_mass()
    if total_mass > sandbox.MAX_STRUCTURE_MASS:
        raise ValueError(f"Structure mass {total_mass:.2f} kg exceeds limit {sandbox.MAX_STRUCTURE_MASS} kg")
    if len(bodies) > getattr(sandbox, "MAX_BEAMS", 999):
        raise ValueError(f"Number of beams {len(bodies)} exceeds maximum {getattr(sandbox, 'MAX_BEAMS', 999)}")
    return bodies[0] if bodies else None

def agent_action(sandbox, agent_body, step_count):
    if step_count % NUDGE_PERIOD != 0:
        return
    for p in sandbox.get_particles_small():
        if p.active and p.position.y > 1.92:
            p.ApplyForceToCenter((0, -NUDGE_FORCE_SMALL), wake=True)
    for p in sandbox.get_particles_medium():
        if p.active and p.position.y > 2.52:
            p.ApplyForceToCenter((0, -NUDGE_FORCE_MEDIUM), wake=True)
