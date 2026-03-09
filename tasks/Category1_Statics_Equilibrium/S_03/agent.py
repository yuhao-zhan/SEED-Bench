import math

def build_agent(sandbox):
    target_reach = 13.5
    structure_y = 10.0
    WALL_X = 0.0
    num_segments = 5
    seg_len = target_reach / num_segments
    top_chord = []
    bot_chord = []
    angle = 0.08
    for i in range(num_segments):
        x = WALL_X + (i + 0.5) * seg_len
        ty = structure_y + 0.5 + i * seg_len * math.sin(angle)
        by = structure_y - 0.5 + i * seg_len * math.sin(angle)
        tb = sandbox.add_beam(x=x, y=ty, width=seg_len + 0.1, height=0.6, angle=angle, density=15.0)
        bb = sandbox.add_beam(x=x, y=by, width=seg_len + 0.1, height=0.6, angle=angle, density=15.0)
        top_chord.append(tb)
        bot_chord.append(bb)
        if i > 0:
            sandbox.add_joint(top_chord[i-1], tb, (WALL_X + i * seg_len, ty), type='rigid')
            sandbox.add_joint(bot_chord[i-1], bb, (WALL_X + i * seg_len, by), type='rigid')
    wall = sandbox._terrain_bodies["wall"]
    sandbox.add_joint(wall, top_chord[0], (WALL_X, structure_y + 1.0), type='rigid')
    sandbox.add_joint(wall, bot_chord[0], (WALL_X, structure_y - 1.0), type='rigid')
    for i in range(num_segments):
        x = WALL_X + i * seg_len
        ty = structure_y + 0.5 + i * seg_len * math.sin(angle)
        by = structure_y - 0.5 + i * seg_len * math.sin(angle)
        next_ty = structure_y + 0.5 + (i+1) * seg_len * math.sin(angle)
        next_by = structure_y - 0.5 + (i+1) * seg_len * math.sin(angle)
        v = sandbox.add_beam(x=x + seg_len, y=(next_ty + next_by)/2, width=0.3, height=next_ty - next_by, density=12.0)
        sandbox.add_joint(top_chord[i], v, (x + seg_len, next_ty), type='rigid')
        sandbox.add_joint(bot_chord[i], v, (x + seg_len, next_by), type='rigid')
        d = sandbox.add_beam(x=x + seg_len/2, y=(ty + next_by)/2, width=math.sqrt(seg_len**2 + (ty-next_by)**2), height=0.3, angle=-math.atan2(ty-next_by, seg_len), density=10.0)
        sandbox.add_joint(top_chord[i], d, (x, ty), type='rigid')
        sandbox.add_joint(bot_chord[i], d, (x + seg_len, next_by), type='rigid')
    return top_chord[0]

def agent_action(sandbox, agent_body, step_count):
    pass

def build_agent_stage_1(sandbox):
    target_reach = 27.0
    structure_y = 5.0
    WALL_X = 0.0
    num_segments = 12
    seg_len = target_reach / num_segments
    top_chord = []
    bot_chord = []
    angle = 0.05
    depth = 14.0
    for i in range(num_segments):
        x = WALL_X + (i + 0.5) * seg_len
        ty = structure_y + depth/2 + i * seg_len * math.sin(angle)
        by = structure_y - depth/2 + i * seg_len * math.sin(angle)
        tb = sandbox.add_beam(x=x, y=ty, width=seg_len + 0.3, height=1.0, angle=angle, density=10.0)
        bb = sandbox.add_beam(x=x, y=by, width=seg_len + 0.3, height=1.0, angle=angle, density=10.0)
        top_chord.append(tb)
        bot_chord.append(bb)
        if i > 0:
            sandbox.add_joint(top_chord[i-1], tb, (WALL_X + i * seg_len, ty), type='rigid')
            sandbox.add_joint(bot_chord[i-1], bb, (WALL_X + i * seg_len, by), type='rigid')
    wall = sandbox._terrain_bodies["wall"]
    sandbox.add_joint(wall, top_chord[0], (WALL_X, structure_y + depth/2 + 0.5), type='rigid')
    sandbox.add_joint(wall, bot_chord[0], (WALL_X, structure_y - depth/2 - 0.5), type='rigid')
    for i in range(num_segments):
        x = WALL_X + i * seg_len
        ty = structure_y + depth/2 + i * seg_len * math.sin(angle)
        by = structure_y - depth/2 + i * seg_len * math.sin(angle)
        next_ty = structure_y + depth/2 + (i+1) * seg_len * math.sin(angle)
        next_by = structure_y - depth/2 + (i+1) * seg_len * math.sin(angle)
        v = sandbox.add_beam(x=x + seg_len, y=(next_ty + next_by)/2, width=0.6, height=next_ty - next_by, density=8.0)
        sandbox.add_joint(top_chord[i], v, (x + seg_len, next_ty), type='rigid')
        sandbox.add_joint(bot_chord[i], v, (x + seg_len, next_by), type='rigid')
        d = sandbox.add_beam(x=x + seg_len/2, y=(ty + next_by)/2, width=math.sqrt(seg_len**2 + (ty-next_by)**2), height=0.6, angle=-math.atan2(ty-next_by, seg_len), density=8.0)
        sandbox.add_joint(top_chord[i], d, (x, ty), type='rigid')
        sandbox.add_joint(bot_chord[i], d, (x + seg_len, next_by), type='rigid')
        d2 = sandbox.add_beam(x=x + seg_len/2, y=(by + next_ty)/2, width=math.sqrt(seg_len**2 + (next_ty-by)**2), height=0.6, angle=math.atan2(next_ty-by, seg_len), density=8.0)
        sandbox.add_joint(bot_chord[i], d2, (x, by), type='rigid')
        sandbox.add_joint(top_chord[i], d2, (x + seg_len, next_ty), type='rigid')
    return top_chord[0]

def agent_action_stage_1(sandbox, agent_body, step_count):
    pass

def build_agent_stage_2(sandbox):
    target_reach = 30.0
    structure_y = 18.0
    WALL_X = 0.0
    num_segments = 10
    seg_len = target_reach / num_segments
    top_chord = []
    bot_chord = []
    angle = 0.03
    depth = 12.0
    for i in range(num_segments):
        x = WALL_X + (i + 0.5) * seg_len
        ty = structure_y + depth/2 + i * seg_len * math.sin(angle)
        by = structure_y - depth/2 + i * seg_len * math.sin(angle)
        tb = sandbox.add_beam(x=x, y=ty, width=seg_len + 0.4, height=1.8, angle=angle, density=20.0)
        bb = sandbox.add_beam(x=x, y=by, width=seg_len + 0.4, height=1.8, angle=angle, density=20.0)
        top_chord.append(tb)
        bot_chord.append(bb)
        if i > 0:
            sandbox.add_joint(top_chord[i-1], tb, (WALL_X + i * seg_len, ty), type='rigid')
            sandbox.add_joint(bot_chord[i-1], bb, (WALL_X + i * seg_len, by), type='rigid')
    wall = sandbox._terrain_bodies["wall"]
    sandbox.add_joint(wall, top_chord[0], (WALL_X, structure_y + depth/2 + 0.5), type='rigid')
    sandbox.add_joint(wall, bot_chord[0], (WALL_X, structure_y - depth/2 - 0.5), type='rigid')
    for i in range(num_segments):
        x = WALL_X + i * seg_len
        ty = structure_y + depth/2 + i * seg_len * math.sin(angle)
        by = structure_y - depth/2 + i * seg_len * math.sin(angle)
        next_ty = structure_y + depth/2 + (i+1) * seg_len * math.sin(angle)
        next_by = structure_y - depth/2 + (i+1) * seg_len * math.sin(angle)
        v = sandbox.add_beam(x=x + seg_len, y=(next_ty + next_by)/2, width=1.0, height=next_ty - next_by, density=15.0)
        sandbox.add_joint(top_chord[i], v, (x + seg_len, next_ty), type='rigid')
        sandbox.add_joint(bot_chord[i], v, (x + seg_len, next_by), type='rigid')
        d1 = sandbox.add_beam(x=x + seg_len/2, y=(ty + next_by)/2, width=math.sqrt(seg_len**2 + (ty-next_by)**2), height=0.8, angle=-math.atan2(ty-next_by, seg_len), density=15.0)
        sandbox.add_joint(top_chord[i], d1, (x, ty), type='rigid')
        sandbox.add_joint(bot_chord[i], d1, (x + seg_len, next_by), type='rigid')
        d2 = sandbox.add_beam(x=x + seg_len/2, y=(by + next_ty)/2, width=math.sqrt(seg_len**2 + (next_ty-by)**2), height=0.8, angle=math.atan2(next_ty-by, seg_len), density=15.0)
        sandbox.add_joint(bot_chord[i], d2, (x, by), type='rigid')
        sandbox.add_joint(top_chord[i], d2, (x + seg_len, next_ty), type='rigid')
    return top_chord[0]

def agent_action_stage_2(sandbox, agent_body, step_count):
    pass

def build_agent_stage_3(sandbox):
    target_reach = 30.0
    structure_y = 26.0
    WALL_X = 0.0
    num_segments = 14
    seg_len = target_reach / num_segments
    top_chord = []
    bot_chord = []
    angle = -0.05
    for i in range(num_segments):
        x = WALL_X + (i + 0.5) * seg_len
        ty = structure_y + 2.0 + i * seg_len * math.sin(angle)
        by = structure_y - 2.0 + i * seg_len * math.sin(angle)
        tb = sandbox.add_beam(x=x, y=ty, width=seg_len + 0.3, height=1.2, angle=angle, density=15.0)
        bb = sandbox.add_beam(x=x, y=by, width=seg_len + 0.3, height=1.2, angle=angle, density=15.0)
        top_chord.append(tb)
        bot_chord.append(bb)
        if i > 0:
            sandbox.add_joint(top_chord[i-1], tb, (WALL_X + i * seg_len, ty), type='rigid')
            sandbox.add_joint(bot_chord[i-1], bb, (WALL_X + i * seg_len, by), type='rigid')
    wall = sandbox._terrain_bodies["wall"]
    sandbox.add_joint(wall, top_chord[0], (WALL_X, structure_y + 2.5), type='rigid')
    sandbox.add_joint(wall, bot_chord[0], (WALL_X, structure_y - 2.5), type='rigid')
    for i in range(num_segments):
        x = WALL_X + i * seg_len
        ty = structure_y + 2.0 + i * seg_len * math.sin(angle)
        by = structure_y - 2.0 + i * seg_len * math.sin(angle)
        next_ty = structure_y + 2.0 + (i+1) * seg_len * math.sin(angle)
        next_by = structure_y - 2.0 + (i+1) * seg_len * math.sin(angle)
        v = sandbox.add_beam(x=x + seg_len, y=(next_ty + next_by)/2, width=0.6, height=next_ty - next_by, density=12.0)
        sandbox.add_joint(top_chord[i], v, (x + seg_len, next_ty), type='rigid')
        sandbox.add_joint(bot_chord[i], v, (x + seg_len, next_by), type='rigid')
        d = sandbox.add_beam(x=x + seg_len/2, y=(ty + next_by)/2, width=math.sqrt(seg_len**2 + (ty-next_by)**2), height=0.6, angle=-math.atan2(ty-next_by, seg_len), density=12.0)
        sandbox.add_joint(top_chord[i], d, (x, ty), type='rigid')
        sandbox.add_joint(bot_chord[i], d, (x + seg_len, next_by), type='rigid')
    return top_chord[0]

def agent_action_stage_3(sandbox, agent_body, step_count):
    pass

def build_agent_stage_4(sandbox):
    target_reach = 37.0
    structure_y = 23.0
    WALL_X = 0.0
    num_segments = 16
    seg_len = target_reach / num_segments
    top_chord = []
    bot_chord = []
    angle = 0.0
    depth = 12.0
    for i in range(num_segments):
        x = WALL_X + (i + 0.5) * seg_len
        ty = structure_y + depth/2 + i * seg_len * math.sin(angle)
        by = structure_y - depth/2 + i * seg_len * math.sin(angle)
        tb = sandbox.add_beam(x=x, y=ty, width=seg_len + 0.3, height=1.2, angle=angle, density=15.0)
        bb = sandbox.add_beam(x=x, y=by, width=seg_len + 0.3, height=1.2, angle=angle, density=15.0)
        top_chord.append(tb)
        bot_chord.append(bb)
        if i > 0:
            sandbox.add_joint(top_chord[i-1], tb, (WALL_X + i * seg_len, ty), type='rigid')
            sandbox.add_joint(bot_chord[i-1], bb, (WALL_X + i * seg_len, by), type='rigid')
    wall = sandbox._terrain_bodies["wall"]
    sandbox.add_joint(wall, top_chord[0], (WALL_X, structure_y + depth/2 + 0.5), type='rigid')
    sandbox.add_joint(wall, bot_chord[0], (WALL_X, structure_y - depth/2 - 0.5), type='rigid')
    for i in range(num_segments):
        x = WALL_X + i * seg_len
        ty = structure_y + depth/2 + i * seg_len * math.sin(angle)
        by = structure_y - depth/2 + i * seg_len * math.sin(angle)
        next_ty = structure_y + depth/2 + (i+1) * seg_len * math.sin(angle)
        next_by = structure_y - depth/2 + (i+1) * seg_len * math.sin(angle)
        v = sandbox.add_beam(x=x + seg_len, y=(next_ty + next_by)/2, width=0.6, height=next_ty - next_by, density=12.0)
        sandbox.add_joint(top_chord[i], v, (x + seg_len, next_ty), type='rigid')
        sandbox.add_joint(bot_chord[i], v, (x + seg_len, next_by), type='rigid')
        d = sandbox.add_beam(x=x + seg_len/2, y=(ty + next_by)/2, width=math.sqrt(seg_len**2 + (ty-next_by)**2), height=0.6, angle=-math.atan2(ty-next_by, seg_len), density=12.0)
        sandbox.add_joint(top_chord[i], d, (x, ty), type='rigid')
        sandbox.add_joint(bot_chord[i], d, (x + seg_len, next_by), type='rigid')
        d2 = sandbox.add_beam(x=x + seg_len/2, y=(by + next_ty)/2, width=math.sqrt(seg_len**2 + (next_ty-by)**2), height=0.6, angle=math.atan2(next_ty-by, seg_len), density=12.0)
        sandbox.add_joint(bot_chord[i], d2, (x, by), type='rigid')
        sandbox.add_joint(top_chord[i], d2, (x + seg_len, next_ty), type='rigid')
    return top_chord[0]

def agent_action_stage_4(sandbox, agent_body, step_count):
    pass
