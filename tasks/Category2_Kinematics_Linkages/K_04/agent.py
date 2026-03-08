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
