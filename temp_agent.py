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


# Stage-1: Minimalist Constraints (Max beams: 4, Max mass: 30.0)

# Stage-2: Dense & Viscous (Density: 4000.0, Damping: 0.9)

# Stage-3: Hurricane Elasticity (Wind: 100, Gust: 150, Restitution: 0.8)

# Stage-4: The Ultimate Vortex Sieve (Combined limits)

def build_agent(sandbox):
    bodies = []
    # Build zone X: [5.22, 6.88]. Width = 1.66
    # Upper Sieve (Blocks Large): 2 bars, 1 gap. Gap must be 0.22.
    # 2*W + 0.22 = 1.44. We will use W = 0.60 to keep mass very low. Total width 1.42 (centered at 6.05)
    w_u = 0.60
    h_u = 0.08
    y_u = 2.37
    x_u = 6.05 - 1.42/2 + w_u/2
    for _ in range(2):
        bar = sandbox.add_static_beam(x_u, y_u, w_u, h_u, density=60.0)
        sandbox.set_material_properties(bar, restitution=0.1)
        bodies.append(bar)
        x_u += w_u + 0.22
        
    # Lower Sieve (Blocks Medium): 2 bars, 1 gap. Gap must be 0.14.
    # 2*W + 0.14 = 1.44. W = 0.65. Total width 1.44.
    w_l = 0.65
    h_l = 0.08
    y_l = 1.80
    x_l = 6.05 - 1.44/2 + w_l/2
    for _ in range(2):
        bar = sandbox.add_static_beam(x_l, y_l, w_l, h_l, density=60.0)
        sandbox.set_material_properties(bar, restitution=0.1)
        bodies.append(bar)
        x_l += w_l + 0.14
        
    return bodies[0] if bodies else None


def agent_action(sandbox, agent_body, step_count):
    if step_count % 10 != 0: return
    for p in sandbox.get_particles_small():
        if p.active and p.position.y > 1.92:
            p.ApplyForceToCenter((0, -35.0), wake=True)
    for p in sandbox.get_particles_medium():
        if p.active and p.position.y > 2.25:
            p.ApplyForceToCenter((0, -30.0), wake=True)
