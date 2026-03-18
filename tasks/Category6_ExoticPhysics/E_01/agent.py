def build_agent(sandbox):
    _, _, arena_y_min, arena_y_max = sandbox.get_arena_bounds()
    x_left = 12.0
    x_right = 26.0
    y_centers_pillar = [8.0, 12.0, 16.0]
    beam_w = 2.0
    beam_h = 4.0
    density = 1.0
    left_beams = []
    for yc in y_centers_pillar:
        b = sandbox.add_beam(x_left, yc, beam_w, beam_h, angle=0, density=density)
        left_beams.append(b)
    for i in range(len(left_beams) - 1):
        mid_y = (y_centers_pillar[i] + y_centers_pillar[i + 1]) / 2
        sandbox.add_joint(left_beams[i], left_beams[i + 1], (x_left, mid_y), type="rigid")
    sandbox.add_joint(left_beams[0], None, (x_left, arena_y_min), type="rigid")
    sandbox.add_joint(left_beams[-1], None, (x_left, arena_y_max), type="rigid")
    right_beams = []
    for yc in y_centers_pillar:
        b = sandbox.add_beam(x_right, yc, beam_w, beam_h, angle=0, density=density)
        right_beams.append(b)
    for i in range(len(right_beams) - 1):
        mid_y = (y_centers_pillar[i] + y_centers_pillar[i + 1]) / 2
        sandbox.add_joint(right_beams[i], right_beams[i + 1], (x_right, mid_y), type="rigid")
    sandbox.add_joint(right_beams[0], None, (x_right, arena_y_min), type="rigid")
    sandbox.add_joint(right_beams[-1], None, (x_right, arena_y_max), type="rigid")
    bridge_left = sandbox.add_beam(15.0, 14.0, 6.0, 2.0, angle=0, density=density)
    bridge_right = sandbox.add_beam(23.5, 14.0, 5.0, 2.0, angle=0, density=density)
    sandbox.add_joint(left_beams[-1], bridge_left, (x_left, 14.0), type="rigid")
    sandbox.add_joint(right_beams[-1], bridge_right, (x_right, 14.0), type="rigid")
    vert_left = sandbox.add_beam(18.0, 15.5, 1.0, 3.0, angle=0, density=density)
    vert_right = sandbox.add_beam(21.0, 15.5, 1.0, 3.0, angle=0, density=density)
    sandbox.add_joint(bridge_left, vert_left, (18.0, 14.0), type="rigid")
    sandbox.add_joint(bridge_right, vert_right, (21.0, 14.0), type="rigid")
    top_conn = sandbox.add_beam(19.5, 17.0, 3.0, 2.0, angle=0, density=density)
    sandbox.add_joint(vert_left, top_conn, (18.0, 17.0), type="rigid")
    sandbox.add_joint(vert_right, top_conn, (21.0, 17.0), type="rigid")
    return left_beams[0]

def agent_action(sandbox, agent_body, step_count):
    pass

def build_agent_stage_1(sandbox):
    _, _, arena_y_min, _ = sandbox.get_arena_bounds()
    x_pos = [14.0, 18.0, 22.0, 26.0]
    beams = []
    for x in x_pos:
        b = sandbox.add_beam(x, 6.5, 3.8, 1.0, density=0.1)
        for dx in [-1.5, -0.5, 0.5, 1.5]:
            sandbox.add_joint(b, None, (x + dx, arena_y_min), type="rigid")
        beams.append(b)
    return beams[0]

def build_agent_stage_2(sandbox):
    _, _, arena_y_min, arena_y_max = sandbox.get_arena_bounds()
    y_centers = [7.5, 10.5, 13.5]
    beams = []
    for yc in y_centers:
        b = sandbox.add_beam(20.0, yc, 3.0, 2.5, density=1.5)
        beams.append(b)
    for i in range(len(beams)-1):
        mid_y = (y_centers[i] + y_centers[i+1]) / 2
        sandbox.add_joint(beams[i], beams[i+1], (20.0, mid_y), type="rigid")
    sandbox.add_joint(beams[0], None, (19.0, arena_y_min), type="rigid")
    sandbox.add_joint(beams[0], None, (21.0, arena_y_min), type="rigid")
    sandbox.add_joint(beams[-1], None, (19.0, arena_y_max), type="rigid")
    sandbox.add_joint(beams[-1], None, (21.0, arena_y_max), type="rigid")
    return beams[0]

def build_agent_stage_3(sandbox):
    _, arena_x_max, arena_y_min, _ = sandbox.get_arena_bounds()
    b1 = sandbox.add_beam(25.0, 8.0, 5.0, 1.0, density=1.0)
    sandbox.add_joint(b1, None, (arena_x_max, 8.0), type="rigid")
    b2 = sandbox.add_beam(20.0, 8.0, 5.0, 1.0, density=1.0)
    sandbox.add_joint(b1, b2, (22.5, 8.0), type="rigid")
    v1 = sandbox.add_beam(20.0, 7.0, 1.0, 2.0, density=2.0)
    sandbox.add_joint(b2, v1, (20.0, 8.0), type="rigid")
    sandbox.add_joint(v1, None, (20.0, arena_y_min), type="rigid")
    return b1

def build_agent_stage_4(sandbox):
    _, _, arena_y_min, _ = sandbox.get_arena_bounds()
    b1 = sandbox.add_beam(20.0, 6.5, 0.8, 0.8, density=1.0)
    for dx in [-1.5, -0.9, -0.3, 0.3, 0.9, 1.5]:
        sandbox.add_joint(b1, None, (20.0 + dx, arena_y_min), type="rigid")
    return b1

def agent_action_stage_1(sandbox, agent_body, step_count): pass

def agent_action_stage_2(sandbox, agent_body, step_count): pass

def agent_action_stage_3(sandbox, agent_body, step_count): pass

def agent_action_stage_4(sandbox, agent_body, step_count): pass
