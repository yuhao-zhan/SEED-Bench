GLASS_Y = 2.0

CENTER_X = 6.0

GROUND_Y = 2.06

BAR_Y = 2.08

BAR_H = 0.24

SEG_W = 2.0

DENSITY = 0.12

BAR_FRICTION = 0.6

def build_agent(sandbox):
    if hasattr(sandbox, 'remove_initial_template'):
        sandbox.remove_initial_template()
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

def build_agent_stage_1(sandbox):
    if hasattr(sandbox, 'remove_initial_template'):
        sandbox.remove_initial_template()
    GLASS_Y = 2.0
    CENTER_X = 6.0
    GROUND_Y = 2.06
    BAR_Y = 2.08
    BAR_H = 0.2
    SEG_W = 2.0
    DENSITY = 0.065
    seg_centers = [2.0, 4.0, 6.0, 8.0, 10.0]
    base = sandbox.add_beam(x=CENTER_X, y=GROUND_Y, width=0.2, height=0.08, angle=0, density=0.15)
    if hasattr(sandbox, 'weld_to_glass'):
        sandbox.weld_to_glass(base, (CENTER_X, GLASS_Y))
    bars = []
    for cx in seg_centers:
        b = sandbox.add_beam(x=cx, y=BAR_Y, width=SEG_W, height=BAR_H, angle=0, density=DENSITY)
        sandbox.set_material_properties(b, restitution=0.0, friction=0.75)
        bars.append(b)
    for i in range(len(bars) - 1):
        jx = (seg_centers[i] + seg_centers[i+1]) / 2.0
        sandbox.add_joint(bars[i], bars[i+1], (jx, BAR_Y), type='rigid')
    pivot = sandbox.add_joint(base, bars[2], (CENTER_X, BAR_Y), type='pivot', lower_limit=-1.3, upper_limit=1.3)
    base.motor1 = pivot
    return base

def agent_action_stage_1(sandbox, agent_body, step_count):
    if not hasattr(agent_body, 'motor1'):
        return
    if hasattr(sandbox, 'set_awake'):
        for body in sandbox.bodies:
            sandbox.set_awake(body, True)
    period = 380
    half = (step_count // period) % 2
    motor_speed = 18.0 if half == 0 else -18.0
    sandbox.set_motor(agent_body.motor1, motor_speed, max_torque=1e8)

def build_agent_stage_2(sandbox):
    if hasattr(sandbox, 'remove_initial_template'):
        sandbox.remove_initial_template()
    GLASS_Y = 2.0
    CENTER_X = 6.0
    GROUND_Y = 2.06
    BAR_Y = 2.08
    BAR_H = 0.2
    SEG_W = 2.0
    DENSITY = 0.035
    seg_centers = [2.0, 4.0, 6.0, 8.0, 10.0]
    base = sandbox.add_beam(x=CENTER_X, y=GROUND_Y, width=0.12, height=0.06, angle=0, density=0.06)
    if hasattr(sandbox, 'weld_to_glass'):
        sandbox.weld_to_glass(base, (CENTER_X, GLASS_Y))
    bars = []
    for cx in seg_centers:
        b = sandbox.add_beam(x=cx, y=BAR_Y, width=SEG_W, height=BAR_H, angle=0, density=DENSITY)
        sandbox.set_material_properties(b, restitution=0.0, friction=0.85)
        bars.append(b)
    for i in range(len(bars) - 1):
        jx = (seg_centers[i] + seg_centers[i+1]) / 2.0
        sandbox.add_joint(bars[i], bars[i+1], (jx, BAR_Y), type='rigid')
    pivot = sandbox.add_joint(base, bars[2], (CENTER_X, BAR_Y), type='pivot', lower_limit=-1.3, upper_limit=1.3)
    base.motor1 = pivot
    return base

def agent_action_stage_2(sandbox, agent_body, step_count):
    if not hasattr(agent_body, 'motor1'):
        return
    if hasattr(sandbox, 'set_awake'):
        for body in sandbox.bodies:
            sandbox.set_awake(body, True)
    period = 300
    half = (step_count // period) % 2
    motor_speed = 12.0 if half == 0 else -12.0
    sandbox.set_motor(agent_body.motor1, motor_speed, max_torque=1e8)

def build_agent_stage_3(sandbox):
    if hasattr(sandbox, 'remove_initial_template'):
        sandbox.remove_initial_template()
    PIVOT_Y = 8.0
    DENSITY = 0.015
    base = sandbox.add_beam(x=6.0, y=PIVOT_Y, width=0.15, height=0.15, angle=0, density=0.04)
    if hasattr(sandbox, 'weld_to_glass'):
        sandbox.weld_to_glass(base, (6.0, 2.0))
    bars_L = []
    for y in [7.0, 5.0, 3.0]:
        b = sandbox.add_beam(x=6.2, y=y, width=0.4, height=2.0, angle=0, density=DENSITY)
        sandbox.set_material_properties(b, restitution=0.0, friction=0.6)
        bars_L.append(b)
    for i in range(len(bars_L) - 1):
        sandbox.add_joint(bars_L[i], bars_L[i+1], (6.2, bars_L[i].position.y - 1.0), type='rigid')
    pivot_L = sandbox.add_joint(base, bars_L[0], (6.2, PIVOT_Y), type='pivot', lower_limit=-1.5, upper_limit=0.0)
    bars_R = []
    for y in [7.0, 5.0, 3.0]:
        b = sandbox.add_beam(x=5.8, y=y, width=0.4, height=2.0, angle=0, density=DENSITY)
        sandbox.set_material_properties(b, restitution=0.0, friction=0.6)
        bars_R.append(b)
    for i in range(len(bars_R) - 1):
        sandbox.add_joint(bars_R[i], bars_R[i+1], (5.8, bars_R[i].position.y - 1.0), type='rigid')
    pivot_R = sandbox.add_joint(base, bars_R[0], (5.8, PIVOT_Y), type='pivot', lower_limit=0.0, upper_limit=1.5)
    agent_body = bars_L[-1]
    agent_body.motor1 = pivot_L
    agent_body.motor2 = pivot_R
    return agent_body

def agent_action_stage_3(sandbox, agent_body, step_count):
    if hasattr(sandbox, 'set_awake'):
        for body in sandbox.bodies: sandbox.set_awake(body, True)
    if not hasattr(agent_body, 'motor1'):
        return
    period = 120
    half = (step_count // period) % 2
    speed_L = -5.0 if half == 0 else 5.0
    speed_R = 5.0 if half == 0 else -5.0
    sandbox.set_motor(agent_body.motor1, motor_speed=speed_L, max_torque=800.0)
    sandbox.set_motor(agent_body.motor2, motor_speed=speed_R, max_torque=800.0)

def build_agent_stage_4(sandbox):
    if hasattr(sandbox, 'remove_initial_template'):
        sandbox.remove_initial_template()
    GLASS_Y = 2.0
    CENTER_X = 6.0
    GROUND_Y = 2.06
    BAR_Y = 2.08
    BAR_H = 0.12
    SEG_W = 2.0
    DENSITY = 0.095
    seg_centers = [2.0, 4.0, 6.0, 8.0, 10.0]
    base = sandbox.add_beam(x=CENTER_X, y=GROUND_Y, width=0.15, height=0.06, angle=0, density=0.12)
    if hasattr(sandbox, 'weld_to_glass'):
        sandbox.weld_to_glass(base, (CENTER_X, GLASS_Y))
    bars = []
    for cx in seg_centers:
        b = sandbox.add_beam(x=cx, y=BAR_Y, width=SEG_W, height=BAR_H, angle=0, density=DENSITY)
        sandbox.set_material_properties(b, restitution=0.0, friction=0.78)
        bars.append(b)
    for i in range(len(bars) - 1):
        jx = (seg_centers[i] + seg_centers[i+1]) / 2.0
        sandbox.add_joint(bars[i], bars[i+1], (jx, BAR_Y), type='rigid')
    pivot = sandbox.add_joint(base, bars[2], (CENTER_X, BAR_Y), type='pivot', lower_limit=-1.3, upper_limit=1.3)
    base.motor1 = pivot
    return base

def agent_action_stage_4(sandbox, agent_body, step_count):
    if not hasattr(agent_body, 'motor1'):
        return
    if hasattr(sandbox, 'set_awake'):
        for body in sandbox.bodies:
            sandbox.set_awake(body, True)
    period = 240
    half = (step_count // period) % 2
    motor_speed = 10.0 if half == 0 else -10.0
    sandbox.set_motor(agent_body.motor1, motor_speed, max_torque=1e8)
