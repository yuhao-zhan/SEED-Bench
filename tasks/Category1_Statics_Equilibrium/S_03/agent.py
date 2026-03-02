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
    WALL_X = 0.0
    TARGET_REACH = 14.0
    STRUCTURE_HEIGHT = 1.0
    BEAM_HEIGHT = 0.4   # Thicker chord for stiffness
    DIAG_HEIGHT = 0.2

    # Fewer segments (3) -> less joints, stiffer; centers at 3, 9, 15 so node at 9 for mid-span load
    segment_ends = [0.0, 6.0, 12.0, 18.0]
    chord_beams = []
    for i in range(len(segment_ends) - 1):
        x0, x1 = segment_ends[i], segment_ends[i + 1]
        cx = (x0 + x1) / 2
        length = x1 - x0
        beam = sandbox.add_beam(
            x=WALL_X + cx,
            y=STRUCTURE_HEIGHT,
            width=length,
            height=BEAM_HEIGHT,
            angle=0,
            density=5.0
        )
        chord_beams.append(beam)
        if i > 0:
            sandbox.add_joint(
                chord_beams[i - 1],
                beam,
                (WALL_X + x0, STRUCTURE_HEIGHT),
                type='rigid'
            )

    wall = sandbox._terrain_bodies.get("wall")
    if not wall:
        raise ValueError("Wall not found")

    sandbox.add_joint(wall, chord_beams[0], (WALL_X, STRUCTURE_HEIGHT), type='rigid')

    anchor2_y = STRUCTURE_HEIGHT - 0.55
    support_beam = sandbox.add_beam(
        x=WALL_X + 1.2,
        y=(STRUCTURE_HEIGHT + anchor2_y) / 2,
        width=1.4,
        height=0.22,
        angle=-math.atan2(STRUCTURE_HEIGHT - anchor2_y, 1.2),
        density=5.0
    )
    sandbox.add_joint(wall, support_beam, (WALL_X, anchor2_y), type='rigid')
    sandbox.add_joint(
        support_beam,
        chord_beams[0],
        (WALL_X + 1.2, STRUCTURE_HEIGHT - 0.2),
        type='rigid'
    )

    for i in range(1, len(chord_beams)):
        from_x = WALL_X + 0.8
        from_y = STRUCTURE_HEIGHT
        to_x = WALL_X + segment_ends[i]
        to_y = STRUCTURE_HEIGHT
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
            density=4.0
        )
        sandbox.add_joint(chord_beams[0], diag, (from_x, from_y), type='rigid')
        sandbox.add_joint(chord_beams[i], diag, (to_x, to_y), type='rigid')

    total_mass = sandbox.get_structure_mass()
    max_reach = sandbox.get_structure_reach()
    print(f"Cantilever constructed: {len(chord_beams)} chord segments, {len(sandbox._bodies)} bodies, "
          f"{len(sandbox._joints)} joints, {total_mass:.2f}kg, max_reach={max_reach:.2f}m")
    return chord_beams[0]


def agent_action(sandbox, agent_body, step_count):
    """No active control; structure is passive."""
    pass
