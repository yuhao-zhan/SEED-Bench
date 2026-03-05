"""
E-01: Inverted Gravity task agent module (hard variant: obstacles + two forbidden zones + beam limit).
Reference solution: two pillars 3 beams each (x=12, x=26), split bridge, vertical connectors
height 3 (center 15.5, clear of second forbidden band at y=15.9–16.1), top connector at y=17; 11 beams.
"""



def build_agent(sandbox):
    """
    Build a structure that avoids all obstacles, no beam center in any forbidden zone,
    and uses at most 12 beams. Second forbidden band blocks y≈16; use verticals with
    center 15.5 (clear) and top connector at y=17.
    """
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
    """No per-step control needed; structure is purely passive."""
    pass
