import math

def build_agent(sandbox):
    x_min, x_max, _, _ = sandbox.get_build_zone()
    support_lo, support_hi = 5.0, 6.5
    bw, bh = 0.32, 0.2
    density = 1.0
    bottom_y = 2.0
    top_y = 5.8
    xs = [5.75, 6.5, 8.0, 9.0, 10.35, 12.0, 14.0, 15.0]
    xs = [min(x_max - bw / 2, max(x_min + bw / 2, x)) for x in xs]
    def seg(i):
        return (xs[i + 1] - xs[i]) if i < len(xs) - 1 else 0.8
    bottom_beams = [sandbox.add_beam(xs[i], bottom_y, seg(i), bh, 0, density) for i in range(len(xs))]
    for i in range(len(bottom_beams) - 1):
        ax = (xs[i] + xs[i + 1]) / 2
        sandbox.add_joint(bottom_beams[i], bottom_beams[i + 1], (ax, bottom_y), type="rigid")
    top_beams = [sandbox.add_beam(xs[i], top_y, seg(i), bh, 0, density) for i in range(len(xs))]
    for i in range(len(top_beams) - 1):
        ax = (xs[i] + xs[i + 1]) / 2
        sandbox.add_joint(top_beams[i], top_beams[i + 1], (ax, top_y), type="rigid")
    vy = (bottom_y + top_y) / 2
    vh = top_y - bottom_y - bh - 0.03
    for i in range(len(xs)):
        vert = sandbox.add_beam(xs[i], vy, bw * 0.65, vh, 0, density)
        sandbox.add_joint(bottom_beams[i], vert, (xs[i], bottom_y + bh / 2), type="rigid")
        sandbox.add_joint(top_beams[i], vert, (xs[i], top_y - bh / 2), type="rigid")
    for i in range(len(xs) - 1):
        dx = xs[i + 1] - xs[i]
        d = math.sqrt(dx**2 + (top_y - bottom_y)**2) * 0.92
        ang = math.atan2(top_y - bottom_y, dx)
        diag1 = sandbox.add_beam((xs[i] + xs[i + 1]) / 2, vy, 0.16, d, ang, density)
        sandbox.add_joint(bottom_beams[i], diag1, (xs[i] + 0.06, bottom_y + 0.02), type="rigid")
        sandbox.add_joint(top_beams[i + 1], diag1, (xs[i + 1] - 0.06, top_y - 0.02), type="rigid")
        diag2 = sandbox.add_beam((xs[i] + xs[i + 1]) / 2, vy, 0.16, d, -ang, density)
        sandbox.add_joint(bottom_beams[i + 1], diag2, (xs[i + 1] - 0.06, bottom_y + 0.02), type="rigid")
        sandbox.add_joint(top_beams[i], diag2, (xs[i] + 0.06, top_y - 0.02), type="rigid")
    ground_y = 1.0
    sandbox.add_joint(bottom_beams[0], None, (5.75, ground_y), type="rigid")
    total_mass = sandbox.get_structure_mass()
    mass_limit = sandbox.get_structure_mass_limit()
    if total_mass > mass_limit:
        raise ValueError(f"Structure mass {total_mass:.2f} kg exceeds limit {mass_limit} kg")
    return bottom_beams[0]

def agent_action(sandbox, agent_body, step_count):
    pass
