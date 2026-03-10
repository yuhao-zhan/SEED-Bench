import math

_booster = None

_enabled = False

def build_agent(sandbox):
    global _booster
    chassis_y = 2.1
    chassis_x = 6.0
    chassis = sandbox.add_beam(x=chassis_x, y=chassis_y, width=1.0, height=0.2, density=1.0)
    sandbox.set_fixed_rotation(chassis, True)
    _booster = sandbox.add_beam(x=chassis_x, y=chassis_y, width=0.4, height=0.4, density=120.0)
    sandbox.add_joint(chassis, _booster, (chassis_x, chassis_y), type='rigid')
    for x_off in [-0.4, 0.4]:
        w = sandbox.add_wheel(x=chassis_x + x_off, y=1.7, radius=0.2, density=1.0)
        sandbox.add_joint(chassis, w, (chassis_x + x_off, 1.7), type='pivot')
    plate = sandbox.add_beam(x=chassis_x + 0.6, y=1.9, width=0.1, height=0.8, density=1.0)
    sandbox.add_joint(chassis, plate, (chassis_x + 0.5, 2.1), type='rigid')
    return chassis

def agent_action(sandbox, agent_body, step_count):
    global _booster, _enabled
    if _booster is None:
        return
    if step_count == 1:
        if abs(_booster.linearVelocity.x - 3.0) < 0.5:
            _enabled = True
        else:
            _enabled = False
    if not _enabled:
        _booster.linearVelocity = (0, 0)
        return
    if 1 < step_count < 400:
        _booster.linearVelocity = (2.0, 0.0)
    else:
        _booster.linearVelocity = (0, 0)

_stage_1_booster = None

def build_agent_stage_1(sandbox):
    global _stage_1_booster
    chassis_y = 1.6
    chassis_x = 5.0
    chassis = sandbox.add_beam(x=chassis_x, y=chassis_y, width=2.0, height=0.2, density=2.0)
    sandbox.set_fixed_rotation(chassis, True)
    _stage_1_booster = sandbox.add_beam(x=chassis_x, y=chassis_y, width=0.4, height=0.4, density=100.0)
    sandbox.add_joint(chassis, _stage_1_booster, (chassis_x, chassis_y), type='rigid')
    mast = sandbox.add_beam(x=chassis_x + 1.0, y=2.4, width=0.2, height=1.6, density=1.0)
    sandbox.add_joint(chassis, mast, (chassis_x + 1.0, 1.6), type='rigid')
    hook = sandbox.add_beam(x=chassis_x + 1.5, y=3.1, width=1.0, height=0.2, density=1.0)
    sandbox.add_joint(mast, hook, (chassis_x + 1.0, 3.1), type='rigid')
    return chassis

def agent_action_stage_1(sandbox, agent_body, step_count):
    global _stage_1_booster
    if _stage_1_booster: _stage_1_booster.linearVelocity = (4.0, 0.0)

_stage_2_booster = None

def build_agent_stage_2(sandbox):
    global _stage_2_booster
    chassis_x = 5.0
    chassis_y = 2.0
    plate = sandbox.add_beam(x=chassis_x + 1.0, y=2.0, width=0.4, height=2.0, density=10.0)
    sandbox.set_fixed_rotation(plate, True)
    _stage_2_booster = sandbox.add_beam(x=chassis_x, y=2.0, width=0.5, height=0.5, density=100.0)
    sandbox.add_joint(plate, _stage_2_booster, (chassis_x, 2.0), type='rigid')
    w1 = sandbox.add_wheel(x=chassis_x, y=1.5, radius=0.6, density=5.0)
    sandbox.add_joint(plate, w1, (chassis_x, 1.5), type='pivot')
    return plate

def agent_action_stage_2(sandbox, agent_body, step_count):
    global _stage_2_booster
    if _stage_2_booster: _stage_2_booster.linearVelocity = (4.0, 0.0)

_stage_3_booster = None

def build_agent_stage_3(sandbox):
    global _stage_3_booster
    chassis_x = 5.0
    chassis_y = 2.0
    chassis = sandbox.add_beam(x=chassis_x, y=chassis_y, width=1.5, height=0.2, density=1.0)
    sandbox.set_fixed_rotation(chassis, True)
    _stage_3_booster = sandbox.add_beam(x=chassis_x, y=chassis_y, width=0.4, height=0.4, density=50.0)
    sandbox.add_joint(chassis, _stage_3_booster, (chassis_x, chassis_y), type='rigid')
    top_wedge = sandbox.add_beam(x=chassis_x + 1.2, y=chassis_y + 0.5, width=1.0, height=0.1, angle=0.8, density=1.0)
    sandbox.add_joint(chassis, top_wedge, (chassis_x + 0.75, chassis_y), type='rigid')
    bot_wedge = sandbox.add_beam(x=chassis_x + 1.2, y=chassis_y - 0.5, width=1.0, height=0.1, angle=-0.8, density=1.0)
    sandbox.add_joint(chassis, bot_wedge, (chassis_x + 0.75, chassis_y), type='rigid')
    return chassis

def agent_action_stage_3(sandbox, agent_body, step_count):
    global _stage_3_booster
    if _stage_3_booster:
        if step_count < 600:
            _stage_3_booster.linearVelocity = (4.0, 0.0)
        else:
            _stage_3_booster.linearVelocity = (0.0, 0.0)

_stage_4_booster = None

def build_agent_stage_4(sandbox):
    global _stage_4_booster
    chassis_x = 5.0
    chassis_y = 1.6
    bottom = sandbox.add_beam(x=chassis_x, y=chassis_y, width=3.0, height=0.2, density=1.0)
    sandbox.set_fixed_rotation(bottom, True)
    _stage_4_booster = sandbox.add_beam(x=chassis_x, y=chassis_y, width=0.4, height=0.4, density=100.0)
    sandbox.add_joint(bottom, _stage_4_booster, (chassis_x, chassis_y), type='rigid')
    back = sandbox.add_beam(x=chassis_x + 1.4, y=2.2, width=0.2, height=1.4, density=1.0)
    sandbox.add_joint(bottom, back, (chassis_x + 1.4, 1.6), type='rigid')
    roof = sandbox.add_beam(x=chassis_x + 2.5, y=3.0, width=2.4, height=0.2, density=1.0)
    sandbox.add_joint(back, roof, (chassis_x + 1.4, 3.0), type='rigid')
    return bottom

def agent_action_stage_4(sandbox, agent_body, step_count):
    global _stage_4_booster
    if _stage_4_booster: _stage_4_booster.linearVelocity = (3.0, 0.0)
