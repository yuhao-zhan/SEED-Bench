import math

def build_agent_stage_4(sandbox):
    beam1 = sandbox.add_beam(6.5, 2.0, 1.5, 1.0, 0, 8.0)
    beam2 = sandbox.add_beam(9.5, 5.5, 1.5, 1.0, 0, 8.0)
    beam3 = sandbox.add_beam(14.0, 2.0, 2.0, 1.0, 0, 8.0)
    sandbox.add_joint(beam1, None, (5.75, 1.0), type="rigid")
    sandbox.add_joint(beam1, beam2, (8.0, 3.5), type="rigid")
    sandbox.add_joint(beam2, beam3, (12.0, 3.5), type="rigid")
    return beam1

def agent_action_stage_4(sandbox, agent_body, step_count):
    pass

def build_agent_stage_3(sandbox):
    bw, bh = 0.7, 0.55
    density = 2.8
    bottom_y = 1.6
    top_y = 5.2
    xs = [5.75, 8.0, 10.5, 13.0, 15.0]
    def get_seg_w(i):
        return (xs[i + 1] - xs[i]) if i < len(xs) - 1 else 1.0
    bottom_beams = []
    for i in range(len(xs)):
        w = get_seg_w(i)
        bottom_beams.append(sandbox.add_beam(xs[i], bottom_y, w, bh, 0, density))
    for i in range(len(bottom_beams) - 1):
        ax = (xs[i] + xs[i + 1]) / 2
        sandbox.add_joint(bottom_beams[i], bottom_beams[i + 1], (ax, bottom_y), type="rigid")
    top_beams = []
    for i in range(len(xs)):
        w = get_seg_w(i)
        ty = top_y - (xs[i] - 5.75) * 0.05
        top_beams.append(sandbox.add_beam(xs[i], ty, w, bh, 0, density))
    for i in range(len(top_beams) - 1):
        ax = (xs[i] + xs[i + 1]) / 2
        ay = (top_beams[i].position.y + top_beams[i+1].position.y) / 2
        sandbox.add_joint(top_beams[i], top_beams[i + 1], (ax, ay), type="rigid")
    for i in range(len(xs)):
        ty = top_beams[i].position.y
        vy = (bottom_y + ty) / 2
        vh = ty - bottom_y - bh - 0.05
        vert = sandbox.add_beam(xs[i], vy, 0.6, vh, 0, density)
        sandbox.add_joint(bottom_beams[i], vert, (xs[i], bottom_y + bh / 2), type="rigid")
        sandbox.add_joint(top_beams[i], vert, (xs[i], ty - bh / 2), type="rigid")
    for i in range(len(xs) - 1):
        dx = xs[i + 1] - xs[i]
        ty_avg = (top_beams[i].position.y + top_beams[i+1].position.y) / 2
        dy = ty_avg - bottom_y
        d = math.sqrt(dx**2 + dy**2) * 0.98
        ang = math.atan2(dy, dx)
        diag1 = sandbox.add_beam((xs[i] + xs[i + 1]) / 2, (bottom_y + ty_avg) / 2, 0.45, d, ang, density)
        sandbox.add_joint(bottom_beams[i], diag1, (xs[i] + 0.1, bottom_y + 0.1), type="rigid")
        sandbox.add_joint(top_beams[i + 1], diag1, (xs[i + 1] - 0.1, top_beams[i+1].position.y - 0.1), type="rigid")
        diag2 = sandbox.add_beam((xs[i] + xs[i + 1]) / 2, (bottom_y + ty_avg) / 2, 0.45, d, -ang, density)
        sandbox.add_joint(bottom_beams[i + 1], diag2, (xs[i + 1] - 0.1, bottom_y + 0.1), type="rigid")
        sandbox.add_joint(top_beams[i], diag2, (xs[i] + 0.1, top_beams[i].position.y - 0.1), type="rigid")
    ground_y = 1.0
    sandbox.add_joint(bottom_beams[0], None, (5.75, ground_y), type="rigid")
    total_mass = sandbox.get_structure_mass()
    if total_mass > 120.0:
        raise ValueError(f"Mass {total_mass} exceeds 120.0")
    return bottom_beams[0]

def agent_action_stage_3(sandbox, agent_body, step_count):
    pass

def build_agent_stage_2(sandbox):
    bw, bh = 0.65, 0.5
    density = 3.1
    bottom_y = 1.6
    top_y = 5.5
    xs = [5.75, 7.0, 8.5, 10.5, 12.0, 13.5, 15.0]
    def get_seg_w(i):
        return (xs[i + 1] - xs[i]) if i < len(xs) - 1 else 0.8
    bottom_beams = []
    for i in range(len(xs)):
        w = get_seg_w(i)
        bottom_beams.append(sandbox.add_beam(xs[i], bottom_y, w, bh, 0, density))
    for i in range(len(bottom_beams) - 1):
        ax = (xs[i] + xs[i + 1]) / 2
        sandbox.add_joint(bottom_beams[i], bottom_beams[i + 1], (ax, bottom_y), type="rigid")
    top_beams = []
    for i in range(len(xs)):
        w = get_seg_w(i)
        ty = top_y - (xs[i] - 5.75) * 0.12
        top_beams.append(sandbox.add_beam(xs[i], ty, w, bh, 0, density))
    for i in range(len(top_beams) - 1):
        ax = (xs[i] + xs[i + 1]) / 2
        ay = (top_beams[i].position.y + top_beams[i+1].position.y) / 2
        sandbox.add_joint(top_beams[i], top_beams[i + 1], (ax, ay), type="rigid")
    for i in range(len(xs)):
        ty = top_beams[i].position.y
        vy = (bottom_y + ty) / 2
        vh = ty - bottom_y - bh - 0.05
        vert = sandbox.add_beam(xs[i], vy, 0.55, vh, 0, density)
        sandbox.add_joint(bottom_beams[i], vert, (xs[i], bottom_y + bh / 2), type="rigid")
        sandbox.add_joint(top_beams[i], vert, (xs[i], ty - bh / 2), type="rigid")
    for i in range(len(xs) - 1):
        dx = xs[i + 1] - xs[i]
        ty_avg = (top_beams[i].position.y + top_beams[i+1].position.y) / 2
        dy = ty_avg - bottom_y
        d = math.sqrt(dx**2 + dy**2) * 0.96
        ang = math.atan2(dy, dx)
        diag1 = sandbox.add_beam((xs[i] + xs[i + 1]) / 2, (bottom_y + ty_avg) / 2, 0.4, d, ang, density)
        sandbox.add_joint(bottom_beams[i], diag1, (xs[i] + 0.1, bottom_y + 0.1), type="rigid")
        sandbox.add_joint(top_beams[i + 1], diag1, (xs[i + 1] - 0.1, top_beams[i+1].position.y - 0.1), type="rigid")
        diag2 = sandbox.add_beam((xs[i] + xs[i + 1]) / 2, (bottom_y + ty_avg) / 2, 0.4, d, -ang, density)
        sandbox.add_joint(bottom_beams[i + 1], diag2, (xs[i + 1] - 0.1, bottom_y + 0.1), type="rigid")
        sandbox.add_joint(top_beams[i], diag2, (xs[i] + 0.1, top_beams[i].position.y - 0.1), type="rigid")
    ground_y = 1.0
    sandbox.add_joint(bottom_beams[0], None, (5.75, ground_y), type="rigid")
    return bottom_beams[0]

def agent_action_stage_2(sandbox, agent_body, step_count):
    pass

def build_agent_stage_1(sandbox):
    bw, bh = 0.6, 0.45
    density = 3.0
    bottom_y = 1.65
    top_y = 6.0
    xs = [5.75, 7.2, 8.8, 10.4, 12.0, 13.5, 15.0]
    xs = [5.75, 7.0, 8.5, 10.5, 12.0, 13.5, 15.0]
    def get_seg_w(i):
        return (xs[i + 1] - xs[i]) if i < len(xs) - 1 else 0.8
    bottom_beams = []
    for i in range(len(xs)):
        w = get_seg_w(i)
        bottom_beams.append(sandbox.add_beam(xs[i], bottom_y, w, bh, 0, density))
    for i in range(len(bottom_beams) - 1):
        ax = (xs[i] + xs[i + 1]) / 2
        sandbox.add_joint(bottom_beams[i], bottom_beams[i + 1], (ax, bottom_y), type="rigid")
    top_beams = []
    for i in range(len(xs)):
        w = get_seg_w(i)
        ty = top_y - (xs[i] - 5.75) * 0.15
        top_beams.append(sandbox.add_beam(xs[i], ty, w, bh, 0, density))
    for i in range(len(top_beams) - 1):
        ax = (xs[i] + xs[i + 1]) / 2
        ay = (top_beams[i].position.y + top_beams[i+1].position.y) / 2
        sandbox.add_joint(top_beams[i], top_beams[i + 1], (ax, ay), type="rigid")
    for i in range(len(xs)):
        ty = top_beams[i].position.y
        vy = (bottom_y + ty) / 2
        vh = ty - bottom_y - bh - 0.05
        vert = sandbox.add_beam(xs[i], vy, 0.5, vh, 0, density)
        sandbox.add_joint(bottom_beams[i], vert, (xs[i], bottom_y + bh / 2), type="rigid")
        sandbox.add_joint(top_beams[i], vert, (xs[i], ty - bh / 2), type="rigid")
    for i in range(len(xs) - 1):
        dx = xs[i + 1] - xs[i]
        ty_avg = (top_beams[i].position.y + top_beams[i+1].position.y) / 2
        dy = ty_avg - bottom_y
        d = math.sqrt(dx**2 + dy**2) * 0.96
        ang = math.atan2(dy, dx)
        diag1 = sandbox.add_beam((xs[i] + xs[i + 1]) / 2, (bottom_y + ty_avg) / 2, 0.35, d, ang, density)
        sandbox.add_joint(bottom_beams[i], diag1, (xs[i] + 0.1, bottom_y + 0.1), type="rigid")
        sandbox.add_joint(top_beams[i + 1], diag1, (xs[i + 1] - 0.1, top_beams[i+1].position.y - 0.1), type="rigid")
        diag2 = sandbox.add_beam((xs[i] + xs[i + 1]) / 2, (bottom_y + ty_avg) / 2, 0.35, d, -ang, density)
        sandbox.add_joint(bottom_beams[i + 1], diag2, (xs[i + 1] - 0.1, bottom_y + 0.1), type="rigid")
        sandbox.add_joint(top_beams[i], diag2, (xs[i] + 0.1, top_beams[i].position.y - 0.1), type="rigid")
    ground_y = 1.0
    sandbox.add_joint(bottom_beams[0], None, (5.75, ground_y), type="rigid")
    return bottom_beams[0]

def agent_action_stage_1(sandbox, agent_body, step_count):
    pass

def build_agent(sandbox):
    x_min, x_max, _, _ = sandbox.get_build_zone()
    support_lo, support_hi = 5.0, 6.5
    bw, bh = 0.35, 0.25
    density = 1.2
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
        vert = sandbox.add_beam(xs[i], vy, 0.25, vh, 0, density)
        sandbox.add_joint(bottom_beams[i], vert, (xs[i], bottom_y + bh / 2), type="rigid")
        sandbox.add_joint(top_beams[i], vert, (xs[i], top_y - bh / 2), type="rigid")
    for i in range(len(xs) - 1):
        dx = xs[i + 1] - xs[i]
        d = math.sqrt(dx**2 + (top_y - bottom_y)**2) * 0.92
        ang = math.atan2(top_y - bottom_y, dx)
        diag1 = sandbox.add_beam((xs[i] + xs[i + 1]) / 2, vy, 0.2, d, ang, density)
        sandbox.add_joint(bottom_beams[i], diag1, (xs[i] + 0.06, bottom_y + 0.02), type="rigid")
        sandbox.add_joint(top_beams[i + 1], diag1, (xs[i + 1] - 0.06, top_y - 0.02), type="rigid")
        diag2 = sandbox.add_beam((xs[i] + xs[i + 1]) / 2, vy, 0.2, d, -ang, density)
        sandbox.add_joint(bottom_beams[i + 1], diag2, (xs[i + 1] - 0.06, bottom_y + 0.02), type="rigid")
        sandbox.add_joint(top_beams[i], diag2, (xs[i] + 0.06, top_y - 0.02), type="rigid")
    ground_y = 1.0
    sandbox.add_joint(bottom_beams[0], None, (5.75, ground_y), type="rigid")
    return bottom_beams[0]

def agent_action(sandbox, agent_body, step_count):
    pass
