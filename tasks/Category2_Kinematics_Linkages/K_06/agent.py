"""
K-06: The Wiper task Agent module
Center-pinned bar on glass; motor oscillates to sweep.
6 segments (12m) for full coverage [1,12]; high bar friction for 100% particle removal.
"""
GLASS_Y = 2.0
CENTER_X = 6.0
GROUND_Y = 2.06
BAR_Y = 2.08   # Same height as particles for good contact
BAR_H = 0.24   # Slightly taller for particle contact
SEG = 2.0
DENSITY = 0.08
BAR_FRICTION = 0.55  # High friction to push sticky particles off

def build_agent(sandbox):
    """
    Center-pinned bar; 6 segments to cover [1,12]; strong motor for 100% cleaning.
    """
    base = sandbox.add_beam(x=CENTER_X, y=GROUND_Y, width=0.5, height=0.12, angle=0, density=1.0)
    sandbox.set_material_properties(base, restitution=0.0, friction=0.5)
    if hasattr(sandbox, 'weld_to_glass'):
        sandbox.weld_to_glass(base, (CENTER_X, GLASS_Y))

    # 6 segments: centers 2,4,6,8,10,11 -> span [1,12]
    seg_centers = [2.0, 4.0, 6.0, 8.0, 10.0, 11.0]

    bars = []
    for cx in seg_centers:
        b = sandbox.add_beam(x=cx, y=BAR_Y, width=SEG, height=BAR_H, angle=0, density=DENSITY)
        sandbox.set_material_properties(b, restitution=0.0, friction=BAR_FRICTION)
        bars.append(b)

    mid = len(bars) // 2  # index 2, center at 6
    # Wider swing (±1.05 rad ≈ ±60°) for better edge coverage
    pivot = sandbox.add_joint(
        base, bars[mid], (CENTER_X, BAR_Y), type='pivot',
        lower_limit=-1.05, upper_limit=1.05
    )
    for i in range(len(bars) - 1):
        jx = (seg_centers[i] + seg_centers[i + 1]) / 2.0
        sandbox.add_joint(bars[i], bars[i + 1], (jx, BAR_Y), type='rigid')

    sandbox._wiper_motor_joint = pivot

    total_mass = sandbox.get_structure_mass()
    if total_mass > sandbox.MAX_STRUCTURE_MASS:
        raise ValueError(f"Structure mass {total_mass:.2f}kg exceeds limit {sandbox.MAX_STRUCTURE_MASS}kg")
    print(f"Wiper: {len(bars)}×2m bar, mass={total_mass:.2f}kg")
    return base


def agent_action(sandbox, agent_body, step_count):
    if not hasattr(sandbox, '_wiper_motor_joint') or sandbox._wiper_motor_joint is None:
        return
    # Ensure structure stays awake
    if hasattr(sandbox, 'set_awake'):
        for body in sandbox.bodies:
            sandbox.set_awake(body, True)
    # Longer period = more dwell at extremes = better clearance (target 100%)
    period = 500
    half = (step_count // period) % 2
    motor_speed = 10.0 if half == 0 else -10.0
    sandbox.set_motor(sandbox._wiper_motor_joint, motor_speed, max_torque=8000.0)
