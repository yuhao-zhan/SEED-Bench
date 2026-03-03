"""
S-03: The Cantilever task Agent module
Build a horizontal cantilever anchored to wall that supports two loads:
tip load 600kg at t=5s and mid-span load 400kg at t=10s (node near x=7.5m).
Max 2 wall anchors, torque limit 2600 Nm, reach >= 14m. Tip must not sag below y=-2.5m.
"""
import math

def build_agent(sandbox):
    """
    Build a stiffer cantilever (tip must stay above y=-2.5m): fewer, thicker segments + strong diagonals.
    """
    target_reach = 14.0
    density_mult = 1.0
    structure_y = 1.0
    anchor1_y = 1.0
    anchor2_y = 0.45

    WALL_X = 0.0
    BEAM_HEIGHT = 0.4
    DIAG_HEIGHT = 0.2

    num_segments = math.ceil(target_reach / 6.0) + 1
    segment_ends = [float(i * 6.0) for i in range(num_segments + 1)]
    
    chord_beams = []
    for i in range(len(segment_ends) - 1):
        x0, x1 = segment_ends[i], segment_ends[i + 1]
        cx = (x0 + x1) / 2
        length = x1 - x0
        beam = sandbox.add_beam(
            x=WALL_X + cx,
            y=structure_y,
            width=length,
            height=BEAM_HEIGHT,
            angle=0,
            density=5.0 * density_mult
        )
        chord_beams.append(beam)
        if i > 0:
            sandbox.add_joint(
                chord_beams[i - 1],
                beam,
                (WALL_X + x0, structure_y),
                type='rigid'
            )

    wall = sandbox._terrain_bodies.get("wall")
    if not wall:
        raise ValueError("Wall not found")

    sandbox.add_joint(wall, chord_beams[0], (WALL_X, anchor1_y), type='rigid')

    support_beam = sandbox.add_beam(
        x=WALL_X + 0.6,
        y=(structure_y + anchor2_y) / 2,
        width=math.sqrt(1.2**2 + (structure_y - anchor2_y)**2),
        height=0.22,
        angle=-math.atan2(structure_y - anchor2_y, 1.2),
        density=5.0 * density_mult
    )
    sandbox.add_joint(wall, support_beam, (WALL_X, anchor2_y), type='rigid')
    sandbox.add_joint(
        support_beam,
        chord_beams[0],
        (WALL_X + 1.2, structure_y),
        type='rigid'
    )

    for i in range(1, len(chord_beams)):
        from_x = WALL_X + 0.8
        from_y = structure_y
        to_x = WALL_X + segment_ends[i]
        to_y = structure_y
        dx = to_x - from_x
        dy = to_y - from_y
        length = math.sqrt(dx*dx + dy*dy)
        angle = math.atan2(dy, dx)
        mid_x = (from_x + to_x) / 2
        mid_y = (from_y + to_y) / 2
        diag = sandbox.add_beam(
            x=mid_x,
            y=mid_y,
            width=length,
            height=DIAG_HEIGHT,
            angle=angle,
            density=4.0 * density_mult
        )
        sandbox.add_joint(chord_beams[0], diag, (from_x, from_y), type='rigid')
        sandbox.add_joint(chord_beams[i], diag, (to_x, to_y), type='rigid')

    return chord_beams[0]

def agent_action(sandbox, agent_body, step_count):
    pass

# --- Mutated Task Solutions ---

def build_agent_stage_1(sandbox):
    """Stage 1: Structural Obstruction. Build the structure higher (y=4.5) to bypass the obstacle at y=[0, 3.5]."""
    target_reach = 14.0
    density_mult = 1.2
    structure_y = 4.5
    anchor1_y = 4.5
    anchor2_y = 3.8

    WALL_X = 0.0
    BEAM_HEIGHT = 0.4
    DIAG_HEIGHT = 0.2

    num_segments = math.ceil(target_reach / 6.0) + 1
    segment_ends = [float(i * 6.0) for i in range(num_segments + 1)]
    
    chord_beams = []
    for i in range(len(segment_ends) - 1):
        x0, x1 = segment_ends[i], segment_ends[i + 1]
        cx = (x0 + x1) / 2
        length = x1 - x0
        beam = sandbox.add_beam(
            x=WALL_X + cx,
            y=structure_y,
            width=length,
            height=BEAM_HEIGHT,
            angle=0,
            density=5.0 * density_mult
        )
        chord_beams.append(beam)
        if i > 0:
            sandbox.add_joint(
                chord_beams[i - 1],
                beam,
                (WALL_X + x0, structure_y),
                type='rigid'
            )

    wall = sandbox._terrain_bodies.get("wall")
    if not wall:
        raise ValueError("Wall not found")

    sandbox.add_joint(wall, chord_beams[0], (WALL_X, anchor1_y), type='rigid')

    support_beam = sandbox.add_beam(
        x=WALL_X + 0.6,
        y=(structure_y + anchor2_y) / 2,
        width=math.sqrt(1.2**2 + (structure_y - anchor2_y)**2),
        height=0.22,
        angle=-math.atan2(structure_y - anchor2_y, 1.2),
        density=5.0 * density_mult
    )
    sandbox.add_joint(wall, support_beam, (WALL_X, anchor2_y), type='rigid')
    sandbox.add_joint(
        support_beam,
        chord_beams[0],
        (WALL_X + 1.2, structure_y),
        type='rigid'
    )

    for i in range(1, len(chord_beams)):
        from_x = WALL_X + 0.8
        from_y = structure_y
        to_x = WALL_X + segment_ends[i]
        to_y = structure_y
        dx = to_x - from_x
        dy = to_y - from_y
        length = math.sqrt(dx*dx + dy*dy)
        angle = math.atan2(dy, dx)
        mid_x = (from_x + to_x) / 2
        mid_y = (from_y + to_y) / 2
        diag = sandbox.add_beam(
            x=mid_x,
            y=mid_y,
            width=length,
            height=DIAG_HEIGHT,
            angle=angle,
            density=4.0 * density_mult
        )
        sandbox.add_joint(chord_beams[0], diag, (from_x, from_y), type='rigid')
        sandbox.add_joint(chord_beams[i], diag, (to_x, to_y), type='rigid')

    return chord_beams[0]

def agent_action_stage_1(sandbox, agent_body, step_count):
    pass

def build_agent_stage_2(sandbox):
    """Stage 2: Dynamic Impact Loading. Heavy reinforcement to absorb impact at x=7.5."""
    target_reach = 14.0
    density_mult = 2.5
    structure_y = 5.0
    anchor1_y = 5.0
    anchor2_y = 3.5

    WALL_X = 0.0
    BEAM_HEIGHT = 0.4
    DIAG_HEIGHT = 0.2

    num_segments = math.ceil(target_reach / 6.0) + 1
    segment_ends = [float(i * 6.0) for i in range(num_segments + 1)]
    
    chord_beams = []
    for i in range(len(segment_ends) - 1):
        x0, x1 = segment_ends[i], segment_ends[i + 1]
        cx = (x0 + x1) / 2
        length = x1 - x0
        beam = sandbox.add_beam(
            x=WALL_X + cx,
            y=structure_y,
            width=length,
            height=BEAM_HEIGHT,
            angle=0,
            density=5.0 * density_mult
        )
        chord_beams.append(beam)
        if i > 0:
            sandbox.add_joint(
                chord_beams[i - 1],
                beam,
                (WALL_X + x0, structure_y),
                type='rigid'
            )

    wall = sandbox._terrain_bodies.get("wall")
    if not wall:
        raise ValueError("Wall not found")

    sandbox.add_joint(wall, chord_beams[0], (WALL_X, anchor1_y), type='rigid')

    support_beam = sandbox.add_beam(
        x=WALL_X + 0.6,
        y=(structure_y + anchor2_y) / 2,
        width=math.sqrt(1.2**2 + (structure_y - anchor2_y)**2),
        height=0.22,
        angle=-math.atan2(structure_y - anchor2_y, 1.2),
        density=5.0 * density_mult
    )
    sandbox.add_joint(wall, support_beam, (WALL_X, anchor2_y), type='rigid')
    sandbox.add_joint(
        support_beam,
        chord_beams[0],
        (WALL_X + 1.2, structure_y),
        type='rigid'
    )

    for i in range(1, len(chord_beams)):
        from_x = WALL_X + 0.8
        from_y = structure_y
        to_x = WALL_X + segment_ends[i]
        to_y = structure_y
        dx = to_x - from_x
        dy = to_y - from_y
        length = math.sqrt(dx*dx + dy*dy)
        angle = math.atan2(dy, dx)
        mid_x = (from_x + to_x) / 2
        mid_y = (from_y + to_y) / 2
        diag = sandbox.add_beam(
            x=mid_x,
            y=mid_y,
            width=length,
            height=DIAG_HEIGHT,
            angle=angle,
            density=4.0 * density_mult
        )
        sandbox.add_joint(chord_beams[0], diag, (from_x, from_y), type='rigid')
        sandbox.add_joint(chord_beams[i], diag, (to_x, to_y), type='rigid')

    return chord_beams[0]

def agent_action_stage_2(sandbox, agent_body, step_count):
    pass

def build_agent_stage_3(sandbox):
    """Stage 3: Restricted Anchor Zones. Avoid y=[0.5, 1.5]. Maximize separation."""
    target_reach = 14.5
    density_mult = 1.5
    structure_y = 2.5
    anchor1_y = 2.5
    anchor2_y = 0.0

    WALL_X = 0.0
    BEAM_HEIGHT = 0.4
    DIAG_HEIGHT = 0.2

    num_segments = math.ceil(target_reach / 6.0) + 1
    segment_ends = [float(i * 6.0) for i in range(num_segments + 1)]
    
    chord_beams = []
    for i in range(len(segment_ends) - 1):
        x0, x1 = segment_ends[i], segment_ends[i + 1]
        cx = (x0 + x1) / 2
        length = x1 - x0
        beam = sandbox.add_beam(
            x=WALL_X + cx,
            y=structure_y,
            width=length,
            height=BEAM_HEIGHT,
            angle=0,
            density=5.0 * density_mult
        )
        chord_beams.append(beam)
        if i > 0:
            sandbox.add_joint(
                chord_beams[i - 1],
                beam,
                (WALL_X + x0, structure_y),
                type='rigid'
            )

    wall = sandbox._terrain_bodies.get("wall")
    if not wall:
        raise ValueError("Wall not found")

    sandbox.add_joint(wall, chord_beams[0], (WALL_X, anchor1_y), type='rigid')

    support_beam = sandbox.add_beam(
        x=WALL_X + 0.6,
        y=(structure_y + anchor2_y) / 2,
        width=math.sqrt(1.2**2 + (structure_y - anchor2_y)**2),
        height=0.22,
        angle=-math.atan2(structure_y - anchor2_y, 1.2),
        density=5.0 * density_mult
    )
    sandbox.add_joint(wall, support_beam, (WALL_X, anchor2_y), type='rigid')
    sandbox.add_joint(
        support_beam,
        chord_beams[0],
        (WALL_X + 1.2, structure_y),
        type='rigid'
    )

    for i in range(1, len(chord_beams)):
        from_x = WALL_X + 0.8
        from_y = structure_y
        to_x = WALL_X + segment_ends[i]
        to_y = structure_y
        dx = to_x - from_x
        dy = to_y - from_y
        length = math.sqrt(dx*dx + dy*dy)
        angle = math.atan2(dy, dx)
        mid_x = (from_x + to_x) / 2
        mid_y = (from_y + to_y) / 2
        diag = sandbox.add_beam(
            x=mid_x,
            y=mid_y,
            width=length,
            height=DIAG_HEIGHT,
            angle=angle,
            density=4.0 * density_mult
        )
        sandbox.add_joint(chord_beams[0], diag, (from_x, from_y), type='rigid')
        sandbox.add_joint(chord_beams[i], diag, (to_x, to_y), type='rigid')

    return chord_beams[0]

def agent_action_stage_3(sandbox, agent_body, step_count):
    pass

def build_agent_stage_4(sandbox):
    """Stage 4: The Perfect Storm. Combined Extreme Challenge."""
    target_reach = 16.0
    density_mult = 3.0
    structure_y = 4.5
    anchor1_y = 4.5
    anchor2_y = 0.0

    WALL_X = 0.0
    BEAM_HEIGHT = 0.4
    DIAG_HEIGHT = 0.2

    num_segments = math.ceil(target_reach / 6.0) + 1
    segment_ends = [float(i * 6.0) for i in range(num_segments + 1)]
    
    chord_beams = []
    for i in range(len(segment_ends) - 1):
        x0, x1 = segment_ends[i], segment_ends[i + 1]
        cx = (x0 + x1) / 2
        length = x1 - x0
        beam = sandbox.add_beam(
            x=WALL_X + cx,
            y=structure_y,
            width=length,
            height=BEAM_HEIGHT,
            angle=0,
            density=5.0 * density_mult
        )
        chord_beams.append(beam)
        if i > 0:
            sandbox.add_joint(
                chord_beams[i - 1],
                beam,
                (WALL_X + x0, structure_y),
                type='rigid'
            )

    wall = sandbox._terrain_bodies.get("wall")
    if not wall:
        raise ValueError("Wall not found")

    sandbox.add_joint(wall, chord_beams[0], (WALL_X, anchor1_y), type='rigid')

    support_beam = sandbox.add_beam(
        x=WALL_X + 0.6,
        y=(structure_y + anchor2_y) / 2,
        width=math.sqrt(1.2**2 + (structure_y - anchor2_y)**2),
        height=0.22,
        angle=-math.atan2(structure_y - anchor2_y, 1.2),
        density=5.0 * density_mult
    )
    sandbox.add_joint(wall, support_beam, (WALL_X, anchor2_y), type='rigid')
    sandbox.add_joint(
        support_beam,
        chord_beams[0],
        (WALL_X + 1.2, structure_y),
        type='rigid'
    )

    for i in range(1, len(chord_beams)):
        from_x = WALL_X + 0.8
        from_y = structure_y
        to_x = WALL_X + segment_ends[i]
        to_y = structure_y
        dx = to_x - from_x
        dy = to_y - from_y
        length = math.sqrt(dx*dx + dy*dy)
        angle = math.atan2(dy, dx)
        mid_x = (from_x + to_x) / 2
        mid_y = (from_y + to_y) / 2
        diag = sandbox.add_beam(
            x=mid_x,
            y=mid_y,
            width=length,
            height=DIAG_HEIGHT,
            angle=angle,
            density=4.0 * density_mult
        )
        sandbox.add_joint(chord_beams[0], diag, (from_x, from_y), type='rigid')
        sandbox.add_joint(chord_beams[i], diag, (to_x, to_y), type='rigid')

    return chord_beams[0]

def agent_action_stage_4(sandbox, agent_body, step_count):
    pass
