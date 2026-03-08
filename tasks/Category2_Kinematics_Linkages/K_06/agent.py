GLASS_Y = 2.0

CENTER_X = 6.0

GROUND_Y = 2.06

BAR_Y = 2.08

BAR_H = 0.24

SEG_W = 2.0

DENSITY = 0.12

BAR_FRICTION = 0.6

def build_agent(sandbox):
    base = sandbox.add_beam(x=CENTER_X, y=GROUND_Y, width=0.5, height=0.12, angle=0, density=1.0)
    if hasattr(sandbox, 'weld_to_glass'):
        sandbox.weld_to_glass(base, (CENTER_X, GLASS_Y))
    seg_centers = [2.0, 4.0, 6.0, 8.0, 10.0]
    bars = []
    for cx in seg_centers:
        b = sandbox.add_beam(x=cx, y=BAR_Y, width=SEG_W, height=BAR_H, angle=0, density=DENSITY)
        sandbox.set_material_properties(b, restitution=0.0, friction=BAR_FRICTION)
        bars.append(b)
    for i in range(len(bars) - 1):
        jx = (seg_centers[i] + seg_centers[i+1]) / 2.0
        sandbox.add_joint(bars[i], bars[i+1], (jx, BAR_Y), type='rigid')
    pivot = sandbox.add_joint(
        base, bars[2], (CENTER_X, BAR_Y), type='pivot',
        lower_limit=-1.3, upper_limit=1.3
    )
    sandbox._wiper_motor_joint = pivot
    total_mass = sandbox.get_structure_mass()
    print(f"Wiper: 5 segments, total width {SEG_W*5}m, mass={total_mass:.2f}kg")
    return base

def agent_action(sandbox, agent_body, step_count):
    if not hasattr(sandbox, '_wiper_motor_joint'):
        return
    if hasattr(sandbox, 'set_awake'):
        for body in sandbox.bodies:
            sandbox.set_awake(body, True)
    period = 300
    half = (step_count // period) % 2
    motor_speed = 18.0 if half == 0 else -18.0
    sandbox.set_motor(sandbox._wiper_motor_joint, motor_speed, max_torque=4500.0)
