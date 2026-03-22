BOAT_LEFT_X = 13.5

BOAT_RIGHT_X = 16.5

RAIL_HEIGHT = 0.9

RAIL_WIDTH = 0.2

def _nominal_hull_center_y(sandbox):
    cfg = getattr(sandbox, "_terrain_config", None) or {}
    off = float(cfg.get("boat_y_offset", 0.0))
    return 2.5 + off

def _hull_deck_top(sandbox):
    boat = sandbox.get_boat_body()
    if boat is None or not boat.active:
        by = _nominal_hull_center_y(sandbox)
        return by + 0.2, by
    by = float(boat.position.y)
    return by + 0.2, by

def build_agent(sandbox):
    deck_top, by = _hull_deck_top(sandbox)
    yz = float(getattr(sandbox, "BUILD_ZONE_Y_MIN", 2.0))
    y_min_anchor = yz + 0.01
    ballast_half_h = 0.17 / 2.0
    ballast_y = max(by - 0.26, yz + ballast_half_h + 0.001)
    joint_ballast_y = max(deck_top - 0.26, y_min_anchor)
    joint_rail_y = max(deck_top - 0.05, y_min_anchor)
    bodies = []
    for bx in (14.25, 15.75):
        b = sandbox.add_beam(bx, ballast_y, 0.5, 0.17, angle=0, density=254.0)
        sandbox.set_material_properties(b, restitution=0.05)
        bodies.append(b)
        sandbox.add_joint(b, None, (bx, joint_ballast_y), type='rigid')
    rail_density = 30.0
    left_rail_y = deck_top + RAIL_HEIGHT / 2
    for x_rail in (BOAT_LEFT_X, BOAT_RIGHT_X):
        r = sandbox.add_beam(x_rail, left_rail_y, RAIL_WIDTH, RAIL_HEIGHT, angle=0, density=rail_density)
        sandbox.set_material_properties(r, restitution=0.07)
        bodies.append(r)
        sandbox.add_joint(r, None, (x_rail, joint_rail_y), type='rigid')
    lip_front = sandbox.add_beam(14.5, deck_top + 0.06, 0.18, 0.06, angle=0, density=35.0)
    sandbox.set_material_properties(lip_front, restitution=0.07)
    bodies.append(lip_front)
    sandbox.add_joint(lip_front, None, (14.5, deck_top), type='rigid')
    lip_back = sandbox.add_beam(15.5, deck_top + 0.06, 0.18, 0.06, angle=0, density=35.0)
    sandbox.set_material_properties(lip_back, restitution=0.07)
    bodies.append(lip_back)
    sandbox.add_joint(lip_back, None, (15.5, deck_top), type='rigid')
    barrier_y = deck_top + 0.18
    for bx in (14.5, 15.5):
        bar = sandbox.add_beam(bx, barrier_y, 0.26, 0.2, angle=0, density=42.0)
        sandbox.set_material_properties(bar, restitution=0.07)
        bodies.append(bar)
        sandbox.add_joint(bar, None, (bx, deck_top), type='rigid')
    total_mass = sandbox.get_structure_mass()
    if total_mass > sandbox.MAX_STRUCTURE_MASS:
        raise ValueError(f"Structure mass {total_mass:.2f} kg exceeds limit {sandbox.MAX_STRUCTURE_MASS} kg")
    return bodies[0]

def _f05_roll_trim(sandbox, k_p: float, k_d: float):
    boat = sandbox.get_boat_body()
    if boat is None or not boat.active:
        return
    boat.ApplyTorque(-k_p * boat.angle - k_d * boat.angularVelocity, True)

def _f05_cargo_upwash(sandbox, margin: float, fy: float, inward: float = 0.0):
    ylim = float(getattr(sandbox, "CARGO_WATER_Y", 1.98))
    cx = 15.0
    for c in getattr(sandbox, "_cargo", []) or []:
        if not c.active:
            continue
        px, py = c.position.x, c.position.y
        if py < ylim + margin:
            c.ApplyForceToCenter((inward * (cx - px), fy), True)

def agent_action(sandbox, agent_body, step_count):
    _f05_roll_trim(sandbox, 5600.0, 118.0)

def _hull_anchor_y(sandbox):
    deck_top, by = _hull_deck_top(sandbox)
    yz = float(getattr(sandbox, "BUILD_ZONE_Y_MIN", 2.0))
    ay = max(yz + 0.008, deck_top - 0.035)
    return min(ay, deck_top - 0.012), deck_top, by

def build_agent_stage_1(sandbox):
    bodies = []
    anchor_y, deck_top, by = _hull_anchor_y(sandbox)
    for ox in (12.5, 17.5):
        pontoon = sandbox.add_beam(ox, by - 0.02, 0.7, 0.11, angle=0, density=72.0)
        bodies.append(pontoon)
        for dx in (-0.28, -0.14, 0.0, 0.14, 0.28):
            sandbox.add_joint(pontoon, None, (ox + dx, anchor_y), type="rigid")
    for bx in [13.55 + i * 0.28 for i in range(10)]:
        slab = sandbox.add_beam(bx, by + 0.06, 0.22, 0.09, angle=0, density=118.0)
        bodies.append(slab)
        for dx in (-0.07, 0.0, 0.07):
            sandbox.add_joint(slab, None, (bx + dx, anchor_y), type="rigid")
    for x_rail in (13.42, 16.58):
        r = sandbox.add_beam(x_rail, deck_top + 0.48, 0.13, 0.94, angle=0, density=16.5)
        bodies.append(r)
        for dy in (0.0, 0.2, 0.4):
            sandbox.add_joint(r, None, (x_rail, anchor_y + dy), type="rigid")
    ceiling_y = deck_top + 0.92
    for cx in (13.5, 14.5, 15.5, 16.5):
        seg = sandbox.add_beam(cx, ceiling_y, 1.0, 0.1, angle=0, density=9.0)
        bodies.append(seg)
        for wx in (cx - 0.35, cx, cx + 0.35):
            wxc = min(max(wx, 12.05), 17.95)
            sandbox.add_joint(seg, None, (wxc, ceiling_y), type="rigid")
    for bx in (13.9, 14.6, 15.4, 16.1):
        bar = sandbox.add_beam(bx, deck_top + 0.2, 0.11, 0.44, angle=0, density=22.0)
        bodies.append(bar)
        sandbox.add_joint(bar, None, (bx, anchor_y + 0.06), type="rigid")
    total_mass = sandbox.get_structure_mass()
    if total_mass > sandbox.MAX_STRUCTURE_MASS:
        raise ValueError(f"Structure mass {total_mass:.2f} kg exceeds limit {sandbox.MAX_STRUCTURE_MASS} kg")
    return bodies[0]

def agent_action_stage_1(sandbox, agent_body, step_count):
    _f05_roll_trim(sandbox, 7200.0, 135.0)
    _f05_cargo_upwash(sandbox, 0.42, 285.0, inward=22.0)

def build_agent_stage_2(sandbox):
    bodies = []
    anchor_y, deck_top, by = _hull_anchor_y(sandbox)
    for ox in (12.5, 17.5):
        arm = sandbox.add_beam(ox, by + 0.02, 0.68, 0.11, angle=0, density=118.0)
        bodies.append(arm)
        for dx in (-0.26, -0.13, 0.0, 0.13, 0.26):
            sandbox.add_joint(arm, None, (ox + dx, anchor_y), type="rigid")
    for bx in (14.0, 15.0, 16.0):
        k = sandbox.add_beam(bx, deck_top + 0.08, 0.62, 0.11, angle=0, density=168.0)
        bodies.append(k)
        for dx in (-0.22, 0.0, 0.22):
            sandbox.add_joint(k, None, (bx + dx, anchor_y), type="rigid")
    rail_h = 0.58
    for x_rail in (13.48, 16.52):
        r = sandbox.add_beam(x_rail, deck_top + rail_h / 2, 0.13, rail_h, angle=0, density=14.0)
        bodies.append(r)
        sandbox.add_joint(r, None, (x_rail, anchor_y), type="rigid")
        sandbox.add_joint(r, None, (x_rail, anchor_y + 0.18), type="rigid")
    ceiling_y = deck_top + rail_h + 0.09
    for cx in (14.0, 15.0, 16.0):
        seg = sandbox.add_beam(cx, ceiling_y, 1.0, 0.1, angle=0, density=8.6)
        bodies.append(seg)
        for wx in (cx - 0.35, cx, cx + 0.35):
            wxc = min(max(wx, 12.05), 17.95)
            sandbox.add_joint(seg, None, (wxc, ceiling_y), type="rigid")
    for bx in (13.65, 14.25, 14.85, 15.45, 16.05, 16.65):
        bar = sandbox.add_beam(bx, deck_top + 0.26, 0.1, 0.36, angle=0, density=14.0)
        bodies.append(bar)
        sandbox.add_joint(bar, None, (bx, anchor_y + 0.05), type="rigid")
    total_mass = sandbox.get_structure_mass()
    if total_mass > sandbox.MAX_STRUCTURE_MASS:
        raise ValueError(f"Structure mass {total_mass:.2f} kg exceeds limit {sandbox.MAX_STRUCTURE_MASS} kg")
    return bodies[0]

def agent_action_stage_2(sandbox, agent_body, step_count):
    _f05_roll_trim(sandbox, 8400.0, 152.0)
    _f05_cargo_upwash(sandbox, 0.55, 410.0, inward=34.0)

def build_agent_stage_3(sandbox):
    bodies = []
    def _cage_beam(body):
        sandbox.set_material_properties(body, restitution=0.04)
        return body
    anchor_y, deck_top, _by = _hull_anchor_y(sandbox)
    yz = float(getattr(sandbox, "BUILD_ZONE_Y_MIN", 2.0))
    pile_top = deck_top + 0.55 + 0.15 + 0.08
    grill_y = max(pile_top, yz + 0.22)
    for cx, xj in (
        (12.55, (12.08, 12.28, 12.48, 12.68, 12.88, 13.02)),
        (17.45, (16.98, 17.18, 17.38, 17.58, 17.78, 17.92)),
    ):
        wing = sandbox.add_beam(cx, deck_top + 0.05, 1.0, 0.1, angle=0, density=34.0)
        bodies.append(wing)
        for xa in xj:
            sandbox.add_joint(wing, None, (xa, anchor_y), type="rigid")
    low_beam_y = max(deck_top + 0.11, yz + 0.06)
    for bx in (13.85, 14.45, 15.0, 15.55, 16.15):
        b = sandbox.add_beam(bx, low_beam_y, 0.4, 0.1, angle=0, density=72.0)
        bodies.append(b)
        for dx in (-0.11, 0.0, 0.11):
            sandbox.add_joint(b, None, (bx + dx, anchor_y), type="rigid")
    for ox in (12.38, 17.62):
        arm = sandbox.add_beam(ox, deck_top + 0.1, 0.42, 0.1, angle=0, density=44.0)
        bodies.append(arm)
        for dx in (-0.11, 0.0, 0.11):
            sandbox.add_joint(arm, None, (ox + dx, anchor_y), type="rigid")
    rail_h = 0.46
    for x_rail in (13.46, 16.54):
        r = _cage_beam(sandbox.add_beam(x_rail, deck_top + rail_h / 2, 0.11, rail_h, angle=0, density=8.5))
        bodies.append(r)
        for dy in (0.0, 0.14, 0.28, 0.42):
            sandbox.add_joint(r, None, (x_rail, anchor_y + dy), type="rigid")
    ceiling_y = max(deck_top + rail_h + 0.12, yz + 0.52, grill_y + 0.65)
    for cx in (13.55, 14.48, 15.52, 16.45):
        seg = _cage_beam(sandbox.add_beam(cx, ceiling_y, 1.0, 0.09, angle=0, density=5.4))
        bodies.append(seg)
        for wx in (cx - 0.32, cx, cx + 0.32):
            wxc = min(max(wx, 12.05), 17.95)
            sandbox.add_joint(seg, None, (wxc, ceiling_y), type="rigid")
    gate_cy = (deck_top + 0.12 + ceiling_y) / 2
    for gx in (13.505, 13.58, 16.42, 16.495):
        gate = _cage_beam(sandbox.add_beam(gx, gate_cy, 0.1, 0.98, angle=0, density=10.0))
        bodies.append(gate)
        for dy in (0.12, 0.42, 0.72):
            sandbox.add_joint(gate, None, (gx, anchor_y + dy), type="rigid")
    for bx in [13.52 + i * 0.28 for i in range(12)]:
        if bx > 16.6:
            continue
        slat = _cage_beam(sandbox.add_beam(bx, grill_y, 0.1, 0.26, angle=0, density=30.0))
        bodies.append(slat)
        sandbox.add_joint(slat, None, (bx, anchor_y + 0.04), type="rigid")
    for bx in (13.7, 14.35, 15.0, 15.65, 16.3):
        bar = _cage_beam(sandbox.add_beam(bx, grill_y + 0.12, 0.1, 0.28, angle=0, density=26.0))
        bodies.append(bar)
        sandbox.add_joint(bar, None, (bx, anchor_y + 0.08), type="rigid")
        sandbox.add_joint(bar, None, (bx, anchor_y + 0.2), type="rigid")
    total_mass = sandbox.get_structure_mass()
    if total_mass > sandbox.MAX_STRUCTURE_MASS:
        raise ValueError(f"Structure mass {total_mass:.2f} kg exceeds limit {sandbox.MAX_STRUCTURE_MASS} kg")
    return bodies[0]

def agent_action_stage_3(sandbox, agent_body, step_count):
    pass

def build_agent_stage_4(sandbox):
    bodies = []
    def _cage_beam(body):
        sandbox.set_material_properties(body, restitution=0.04)
        return body
    anchor_y, deck_top, _by = _hull_anchor_y(sandbox)
    yz = float(getattr(sandbox, "BUILD_ZONE_Y_MIN", 2.0))
    low_beam_y = max(deck_top + 0.11, yz + 0.06)
    for cx, xj in (
        (12.55, (12.08, 12.28, 12.48, 12.68, 12.88, 13.02)),
        (17.45, (16.98, 17.18, 17.38, 17.58, 17.78, 17.92)),
    ):
        wing = _cage_beam(sandbox.add_beam(cx, deck_top + 0.05, 1.0, 0.1, angle=0, density=30.0))
        bodies.append(wing)
        for xa in xj:
            sandbox.add_joint(wing, None, (xa, anchor_y), type="rigid")
    for bx in (13.85, 14.45, 15.0, 15.55, 16.15):
        b = _cage_beam(sandbox.add_beam(bx, low_beam_y, 0.4, 0.1, angle=0, density=68.0))
        bodies.append(b)
        for dx in (-0.11, 0.0, 0.11):
            sandbox.add_joint(b, None, (bx + dx, anchor_y), type="rigid")
    for ox in (12.38, 17.62):
        arm = _cage_beam(sandbox.add_beam(ox, deck_top + 0.1, 0.42, 0.1, angle=0, density=40.0))
        bodies.append(arm)
        for dx in (-0.11, 0.0, 0.11):
            sandbox.add_joint(arm, None, (ox + dx, anchor_y), type="rigid")
    rail_h = 0.48
    for x_rail in (13.46, 16.54):
        r = _cage_beam(sandbox.add_beam(x_rail, deck_top + rail_h / 2, 0.11, rail_h, angle=0, density=8.5))
        bodies.append(r)
        for dy in (0.0, 0.12, 0.24, 0.36):
            sandbox.add_joint(r, None, (x_rail, anchor_y + dy), type="rigid")
    ceiling_y = max(deck_top + rail_h + 0.62, yz + 0.88, deck_top + 1.02)
    for cx, w in ((14.09, 1.0), (15.09, 1.0), (16.09, 0.82)):
        seg = _cage_beam(sandbox.add_beam(cx, ceiling_y, w, 0.09, angle=0, density=5.4))
        bodies.append(seg)
        nudge = 0.32 if w >= 1.0 else 0.28
        for wx in (cx - nudge, cx, cx + nudge):
            wxc = min(max(wx, 12.05), 17.95)
            sandbox.add_joint(seg, None, (wxc, ceiling_y), type="rigid")
    gate_h = 0.82
    gh = gate_h * 0.5
    gate_cy = max(
        (deck_top + rail_h + ceiling_y) * 0.5,
        yz + gh + 0.04,
        anchor_y + 0.85,
    )
    gate_cy = min(gate_cy, ceiling_y - gh - 0.04)
    for gx in (13.52, 13.62, 16.38, 16.48):
        gate = _cage_beam(sandbox.add_beam(gx, gate_cy, 0.1, gate_h, angle=0, density=6.8))
        bodies.append(gate)
        for dy in (0.12, 0.42, 0.72):
            sandbox.add_joint(gate, None, (gx, anchor_y + dy), type="rigid")
    for bx in [13.52 + i * 0.28 for i in range(12)]:
        if bx > 16.6:
            continue
        slat = _cage_beam(sandbox.add_beam(bx, deck_top + 0.21, 0.1, 0.26, angle=0, density=30.0))
        bodies.append(slat)
        sandbox.add_joint(slat, None, (bx, anchor_y + 0.04), type="rigid")
    for bx in (13.7, 14.35, 15.0, 15.65, 16.3):
        bar = _cage_beam(sandbox.add_beam(bx, deck_top + 0.3, 0.1, 0.28, angle=0, density=26.0))
        bodies.append(bar)
        sandbox.add_joint(bar, None, (bx, anchor_y + 0.08), type="rigid")
        sandbox.add_joint(bar, None, (bx, anchor_y + 0.2), type="rigid")
    total_mass = sandbox.get_structure_mass()
    if total_mass > sandbox.MAX_STRUCTURE_MASS:
        raise ValueError(f"Structure mass {total_mass:.2f} kg exceeds limit {sandbox.MAX_STRUCTURE_MASS} kg")
    return bodies[0]

def _f05_cargo_radial_pin(sandbox, y_thresh: float, k: float):
    cx = 15.0
    for c in getattr(sandbox, "_cargo", []) or []:
        if not c.active:
            continue
        px, py = c.position.x, c.position.y
        if py >= y_thresh:
            continue
        c.ApplyForceToCenter((k * (cx - px), 0.0), True)

def agent_action_stage_4(sandbox, agent_body, step_count):
    ylim = float(getattr(sandbox, "CARGO_WATER_Y", 1.98))
    kp = 12020.0 if step_count < 1800 else 10800.0
    _f05_roll_trim(sandbox, kp, 178.0)
    _f05_cargo_upwash(sandbox, 0.66, 540.0, inward=42.0)
    _f05_cargo_radial_pin(sandbox, ylim + 0.85, 95.0)
