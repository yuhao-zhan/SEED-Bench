import math

def build_agent(sandbox):
    ground_top = sandbox.get_ground_y_top()
    x_min, x_max, _, _ = sandbox.get_build_zone()
    span_left, span_right = sandbox.get_span_bounds()
    deck_cy = 2.0
    deck_h = 0.2
    density = 0.28
    strut_w = 0.18
    strut_density = 0.25
    strut_h = deck_cy - ground_top
    strut_cy = ground_top + strut_h / 2
    left_span = sandbox.add_beam(
        x=span_left, y=deck_cy,
        width=0.5, height=deck_h,
        angle=0, density=density,
    )
    right_span = sandbox.add_beam(
        x=span_right, y=deck_cy,
        width=0.5, height=deck_h,
        angle=0, density=density,
    )
    deck_left = sandbox.add_beam(
        x=8.0, y=deck_cy,
        width=2.0, height=deck_h,
        angle=0, density=density,
    )
    deck_right = sandbox.add_beam(
        x=12.0, y=deck_cy,
        width=2.0, height=deck_h,
        angle=0, density=density,
    )
    strut_xs = [6.0, 7.0, 8.0, 9.0, 11.0, 12.0, 13.0, 14.0]
    strut_bodies = []
    for sx in strut_xs:
        s = sandbox.add_beam(
            x=sx, y=strut_cy,
            width=strut_w, height=strut_h,
            angle=0, density=strut_density,
        )
        strut_bodies.append((sx, s))
        sandbox.add_joint(s, None, (sx, ground_top), type="rigid")
        if sx <= 9:
            sandbox.add_joint(deck_left, s, (sx, deck_cy), type="rigid")
        else:
            sandbox.add_joint(deck_right, s, (sx, deck_cy), type="rigid")
    sx_center = 10.0
    strut_center = sandbox.add_beam(
        x=sx_center, y=strut_cy,
        width=strut_w, height=strut_h,
        angle=0, density=strut_density,
    )
    sandbox.add_joint(strut_center, None, (sx_center, ground_top), type="rigid")
    sandbox.add_joint(deck_left, strut_center, (sx_center, deck_cy), type="rigid")
    sandbox.add_joint(deck_right, strut_center, (sx_center, deck_cy), type="pivot")
    sandbox.add_joint(left_span, deck_left, (7.0, deck_cy), type="rigid")
    sandbox.add_joint(deck_left, deck_right, (10.0, deck_cy), type="rigid")
    sandbox.add_joint(deck_right, right_span, (13.0, deck_cy), type="rigid")
    sandbox.add_joint(left_span, strut_bodies[0][1], (span_left, deck_cy), type="rigid")
    sandbox.add_joint(right_span, strut_bodies[-1][1], (span_right, deck_cy), type="rigid")
    return deck_left

def agent_action(sandbox, agent_body, step_count):
    pass

def build_agent_stage_1(sandbox):
    L_X, R_X = 6.0, 14.0
    deck_y = 2.5
    density = 0.005
    xs = [6.0, 7.5, 9.2, 11.0, 12.5, 14.0]
    beams = []
    for i in range(len(xs)-1):
        w = xs[i+1] - xs[i]
        b = sandbox.add_beam(x=(xs[i]+xs[i+1])/2, y=deck_y, width=w+0.05, height=0.1, density=density)
        beams.append(b)
    vs = []
    for x in xs:
        v = sandbox.add_beam(x=x, y=2.0, width=0.1, height=1.0, density=density)
        vs.append(v)
        sandbox.add_joint(v, None, (x, 1.5), type="rigid")
    for i in range(len(xs)):
        if i < len(beams):
            sandbox.add_joint(vs[i], beams[i], (xs[i], deck_y), type="pivot" if i==0 else "rigid")
        if i > 0:
            sandbox.add_joint(vs[i], beams[i-1], (xs[i], deck_y), type="rigid")
            dw = math.sqrt((xs[i]-xs[i-1])**2 + 0.5**2)
            d = sandbox.add_beam(x=(xs[i]+xs[i-1])/2, y=2.25, width=dw, height=0.05,
                                 angle=math.atan2(0.5, xs[i]-xs[i-1]), density=density)
            sandbox.add_joint(d, vs[i-1], (xs[i-1], 2.0), type="rigid")
            sandbox.add_joint(d, vs[i], (xs[i], deck_y), type="rigid")
    return beams[0]

def agent_action_stage_1(sandbox, agent_body, step_count): pass

def build_agent_stage_2(sandbox):
    L_X, R_X = 6.0, 14.0
    density = 0.0001
    n = 10
    nodes = []
    for i in range(n + 1):
        x = L_X + i * (R_X - L_X) / n
        y = 4.5 - 0.15 * (x - 10.0)**2
        nodes.append((x, y))
    arch = []
    for i in range(n):
        x1, y1 = nodes[i]; x2, y2 = nodes[i+1]
        d = math.sqrt((x2-x1)**2 + (y2-y1)**2)
        b = sandbox.add_beam(x=(x1+x2)/2, y=(y1+y2)/2, width=d+0.05, height=0.1,
                             angle=math.atan2(y2-y1, x2-x1), density=density)
        arch.append(b)
        if i == 0: sandbox.add_joint(b, None, nodes[i], type="pivot")
        elif i == n-1:
            sandbox.add_joint(arch[i-1], b, nodes[i], type="pivot")
            sandbox.add_joint(b, None, nodes[i+1], type="pivot")
        else: sandbox.add_joint(arch[i-1], b, nodes[i], type="pivot")
    deck = []
    for i in range(n):
        x = (nodes[i][0] + nodes[i+1][0]) / 2
        db = sandbox.add_beam(x=x, y=4.7, width=(R_X-L_X)/n + 0.05, height=0.1, density=density)
        deck.append(db)
        v = sandbox.add_beam(x=x, y=(nodes[i][1]+4.7)/2, width=0.05, height=4.7-nodes[i][1], density=density)
        sandbox.add_joint(v, arch[i], (x, nodes[i][1]), type="pivot")
        sandbox.add_joint(v, db, (x, 4.7), type="pivot")
        if i > 0: sandbox.add_joint(deck[i-1], db, (nodes[i][0], 4.7), type="pivot")
    sandbox.add_beam(x=6.0, y=4.7, width=0.1, height=0.1, density=density)
    sandbox.add_beam(x=14.0, y=4.7, width=0.1, height=0.1, density=density)
    return deck[0]

def agent_action_stage_2(sandbox, agent_body, step_count): pass

def build_agent_stage_3(sandbox):
    L_X, R_X = 6.0, 14.0
    density = 0.0001
    top_y, bot_y = 3.5, 2.0
    n = 10
    w = (R_X - L_X) / n
    vs = []
    for i in range(n + 1):
        x = L_X + i*w
        v = sandbox.add_beam(x=x, y=(top_y+bot_y)/2, width=0.05, height=top_y-bot_y, density=density)
        vs.append(v)
        sandbox.add_joint(v, None, (x, 1.5), type="pivot")
        lx = x - 0.5
        lb = sandbox.add_beam(x=x-0.25, y=1.75, width=math.sqrt(0.5**2+0.5**2), height=0.05,
                              angle=math.atan2(0.5, -0.5), density=density)
        sandbox.add_joint(lb, None, (lx, 1.5), type="pivot")
        sandbox.add_joint(lb, v, (x, 2.0), type="pivot")
    for i in range(n):
        x1 = L_X+i*w; x2 = L_X+(i+1)*w
        t = sandbox.add_beam(x=(x1+x2)/2, y=top_y, width=w+0.05, height=0.05, density=density)
        sandbox.add_joint(t, vs[i], (x1, top_y), type="pivot")
        sandbox.add_joint(t, vs[i+1], (x2, top_y), type="pivot")
        b = sandbox.add_beam(x=(x1+x2)/2, y=bot_y, width=w+0.05, height=0.05, density=density)
        sandbox.add_joint(b, vs[i], (x1, bot_y), type="pivot")
        sandbox.add_joint(b, vs[i+1], (x2, bot_y), type="pivot")
        d = sandbox.add_beam(x=(x1+x2)/2, y=(top_y+bot_y)/2, width=math.sqrt(w**2+(top_y-bot_y)**2),
                             height=0.05, angle=math.atan2(top_y-bot_y, w), density=density)
        sandbox.add_joint(d, vs[i], (x1, bot_y), type="pivot")
        sandbox.add_joint(d, vs[i+1], (x2, top_y), type="pivot")
    sandbox.add_beam(x=6.0, y=top_y, width=0.1, height=0.1, density=density)
    sandbox.add_beam(x=14.0, y=top_y, width=0.1, height=0.1, density=density)
    return vs[0]

def agent_action_stage_3(sandbox, agent_body, step_count): pass

def build_agent_stage_4(sandbox):
    L_X, R_X = 6.0, 14.0
    density = 0.0001
    deck_y = 3.0
    n = 12
    w = (R_X - L_X) / n
    deck = []
    for i in range(n):
        b = sandbox.add_beam(x=L_X+(i+0.5)*w, y=deck_y, width=w+0.05, height=0.05, density=density)
        deck.append(b)
        if i > 0: sandbox.add_joint(deck[i-1], b, (L_X+i*w, deck_y), type="pivot")
    for px in [6.5, 8.5, 11.5, 13.5]:
        pylon = sandbox.add_beam(x=px, y=5.0, width=0.1, height=4.0, density=density*2)
        sandbox.add_joint(pylon, None, (px, 1.5), type="pivot")
        for sy in [4.0, 6.0]:
            stay = sandbox.add_beam(x=px-1.0, y=(1.5+sy)/2, width=math.sqrt(2.0**2+(sy-1.5)**2),
                                    height=0.02, angle=math.atan2(sy-1.5, -2.0), density=density)
            sandbox.add_joint(stay, None, (px-2.0, 1.5), type="pivot")
            sandbox.add_joint(stay, pylon, (px, sy), type="pivot")
        for i in range(n):
            dx = (L_X+(i+0.5)*w) - px
            dist = math.sqrt(dx**2 + (7.0-deck_y)**2)
            s = sandbox.add_beam(x=px+dx/2, y=(7.0+deck_y)/2, width=dist, height=0.02,
                                 angle=math.atan2(deck_y-7.0, dx), density=density)
            sandbox.add_joint(s, pylon, (px, 7.0), type="pivot")
            sandbox.add_joint(s, deck[i], (L_X+(i+0.5)*w, deck_y), type="pivot")
    sandbox.add_beam(x=6.0, y=deck_y, width=0.1, height=0.1, density=density)
    sandbox.add_beam(x=14.0, y=deck_y, width=0.1, height=0.1, density=density)
    return deck[0]

def agent_action_stage_4(sandbox, agent_body, step_count): pass
