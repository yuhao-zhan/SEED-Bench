import math

def build_agent(sandbox):
    sandbox.add_anchored_base(-2.0, 0.2, 0.4, 0.4, angle=0, density=10.0)
    tower = sandbox.add_anchored_base(-2.0, 0.75, 0.4, 1.5, angle=0, density=400.0)
    arm1 = sandbox.add_beam(-1.25, 1.5, 1.5, 0.2, angle=0, density=20.0)
    arm2 = sandbox.add_beam(0.25, 1.5, 1.5, 0.2, angle=0, density=20.0)
    arm3 = sandbox.add_beam(1.5, 1.5, 1.0, 0.2, angle=0, density=20.0)
    sandbox.add_joint(arm1, arm2, (-0.5, 1.5))
    sandbox.add_joint(arm2, arm3, (1.0, 1.5))
    _aj = sandbox.add_revolute_joint(tower, arm1, (-2.0, 1.5), enable_motor=True, max_motor_torque=3000.0)
    scoop_w, scoop_h = 2.0, 1.0
    scoop = sandbox.add_scoop(2.0, 1.5, scoop_w, scoop_h, angle=0, density=20.0)
    _bj = sandbox.add_revolute_joint(arm3, scoop, (2.0, 1.5), enable_motor=True, max_motor_torque=3000.0)
    sandbox._aj = _aj
    sandbox._bj = _bj
    return scoop

def agent_action(sandbox, agent_body, step_count):
    _aj = getattr(sandbox, '_aj', None)
    _bj = getattr(sandbox, '_bj', None)
    if not _aj or not _bj: return
    dt = 1.0 / 60.0
    t = step_count * dt
    phase_duration = 10.0
    phase = (t % phase_duration) / phase_duration
    arm_angle = _aj.angle
    bucket_world_angle = agent_body.angle
    if phase < 0.3:
        ta, tb = -0.2, 0.5
    elif phase < 0.5:
        ta, tb = 0.0, 0.0
    elif phase < 0.8:
        ta, tb = 2.4, 0.0
    elif phase < 0.9:
        ta, tb = 2.4, 1.2
    else:
        ta, tb = 0.5, 1.2
    _aj.motorSpeed = 1.0 * (ta - arm_angle)
    _bj.motorSpeed = 3.0 * (tb - bucket_world_angle)
    _aj.motorEnabled = True
    _bj.motorEnabled = True
