"""
S-05: The Shelter task Agent module

Goal (current environment):
- Protect fragile Core at (0,0) from 28 boulders (260kg each); 2 of every 3 from CENTER.
- Core breaks if Force > 14N
- Cannot build within 1.3m of core
- No structure above y=4.5m
- Max structure mass: 120kg

Strategy:
- Solid layered barrier: multiple WIDE horizontal beams stacked from y=1.4 to 4.2,
  covering full meteor zone x in [-2.5, 2.5]. No gaps. Center beams at (0,y) with y>=1.3.
- Heavy (use ~100kg), restitution=0 to absorb 260kg impacts.
- Base on ground, supports outside keep-out.
"""

import math

def _keep_out(sandbox):
    return getattr(sandbox, 'KEEP_OUT_RADIUS', 1.3)

def _max_height(sandbox):
    return getattr(sandbox, 'MAX_STRUCTURE_HEIGHT', 4.5)


def build_agent(sandbox):
    """
    Build a shelter: solid layered barrier, no gaps. Keep-out 1.3m, max height 4.5m, max mass 120kg.
    """
    K = _keep_out(sandbox)
    H_MAX = _max_height(sandbox)

    ground_top = 0.5
    base_h = 0.35
    base_y = ground_top + base_h / 2

    # Split base on ground, outside keep-out
    base_left = sandbox.add_beam(-2.2, base_y, 1.6, base_h, angle=0, density=2.5)
    base_right = sandbox.add_beam(2.2, base_y, 1.6, base_h, angle=0, density=2.5)
    sandbox.set_material_properties(base_left, restitution=0.0)
    sandbox.set_material_properties(base_right, restitution=0.0)

    # Columns
    col_h = 3.5
    col_xs = [-2.4, -1.8, 1.8, 2.4]
    col_y_c = base_y + base_h/2 + col_h/2
    cols = []
    for x in col_xs:
        col = sandbox.add_beam(x, col_y_c, 0.4, col_h, angle=0, density=2.5)
        base_use = base_left if x < 0 else base_right
        sandbox.add_joint(base_use, col, (x, base_y + base_h/2), type='rigid')
        sandbox.set_material_properties(col, restitution=0.0)
        cols.append(col)

    # SOLID barrier: y + max(w,h)/2 <= 4.5. Extend to ±3 to catch side meteors.
    barrier_layers = [
        (1.5, 6.0, 0.4, 3.5),    # 1.5+3=4.5, covers x in [-3,3]
        (2.0, 5.0, 0.4, 3.5),
        (2.5, 4.0, 0.4, 3.2),
        (3.0, 3.0, 0.4, 3.0),
        (3.5, 2.0, 0.35, 2.8),
    ]
    prev_barrier = None
    wide_barrier = None  # barrier that extends to x=±2.5 for top beam connections
    for i, (by, bw, bh, dens) in enumerate(barrier_layers):
        barrier = sandbox.add_beam(0.0, by, bw, bh, angle=0, density=dens)
        sandbox.set_material_properties(barrier, restitution=0.0)
        if prev_barrier is None:
            for j, col in enumerate(cols):
                sandbox.add_joint(col, barrier, (col_xs[j], by), type='rigid')
        else:
            for sx in (-1.5, 0, 1.5):
                mid_y = (by + prev_barrier.position.y) / 2
                sandbox.add_joint(prev_barrier, barrier, (sx, mid_y), type='rigid')
        if bw >= 5.0:
            wide_barrier = barrier
        prev_barrier = barrier

    # Top layer: struts from prev_barrier (y~3.5) to top beams - anchor must be on both
    # prev_barrier at y=3.5 has width 2, so x in [-1,1]. Connect top beams at x in [-1,1] directly.
    # For |tx|>1, add struts: vertical beam from (tx, 3.65) to (tx, 4.0)
    for tx in (-2.5, -1.5, -0.75, 0, 0.75, 1.5, 2.5):
        top_b = sandbox.add_beam(tx, 4.0, 1.0, 0.3, angle=0, density=2.2)
        sandbox.set_material_properties(top_b, restitution=0.0)
        if abs(tx) <= 1.0:
            sandbox.add_joint(prev_barrier, top_b, (tx, 3.65), type='rigid')
        else:
            # Strut from wide_barrier top to top_b bottom
            bar_top = wide_barrier.position.y + 0.2
            strut_y = (bar_top + 3.85) / 2
            strut_h = 3.85 - bar_top
            strut = sandbox.add_beam(tx, strut_y, 0.25, max(0.3, strut_h), angle=0, density=2.0)
            sandbox.set_material_properties(strut, restitution=0.0)
            sandbox.add_joint(wide_barrier, strut, (tx, bar_top), type='rigid')
            sandbox.add_joint(strut, top_b, (tx, 3.85), type='rigid')

    # Cross braces
    by = base_y + base_h/2 + col_h * 0.4
    brace_left = sandbox.add_beam(-2.1, by, 1.5, 0.2, angle=math.pi/4, density=1.5)
    sandbox.add_joint(cols[0], brace_left, (col_xs[0], by), type='rigid')
    sandbox.add_joint(cols[1], brace_left, (col_xs[1], by), type='rigid')
    brace_right = sandbox.add_beam(2.1, by, 1.5, 0.2, angle=-math.pi/4, density=1.5)
    sandbox.add_joint(cols[2], brace_right, (col_xs[2], by), type='rigid')
    sandbox.add_joint(cols[3], brace_right, (col_xs[3], by), type='rigid')

    total_mass = sandbox.get_structure_mass()
    max_mass = getattr(sandbox, 'MAX_MASS', 120.0)
    if total_mass > max_mass:
        raise ValueError(f"Structure mass {total_mass:.2f}kg exceeds limit {max_mass}kg")

    print(f"Shelter: {len(sandbox._bodies)} beams, {len(sandbox._joints)} joints, {total_mass:.2f}kg (limit {max_mass}kg)")
    return base_left


def agent_action(sandbox, agent_body, step_count):
    """No active control; passive structure."""
    pass
