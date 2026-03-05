
import math

BASE_X = -2.0
BASE_Y = 0.0
HOPPER_X = -5.0
HOPPER_Y = 3.0
PIT_CENTER_X = 2.5


_arm_joint = None
_bucket_joint = None


def build_agent(sandbox):

    global _arm_joint, _bucket_joint

    base = sandbox.add_anchored_base(BASE_X, BASE_Y, 0.4, 0.2, angle=0, density=400.0)

    arm_len = 4.0
    arm_cx = BASE_X + arm_len / 2
    arm_cy = 0.5
    arm = sandbox.add_beam(arm_cx, arm_cy, arm_len, 0.2, angle=0, density=200.0)
    sandbox.set_material_properties(arm, restitution=0.05)

    _arm_joint = sandbox.add_revolute_joint(base, arm, (BASE_X, 0.5), enable_motor=True, motor_speed=0.0, max_motor_torque=9000.0)

    arm_tip_x = BASE_X + arm_len
    arm_tip_y = 0.5
    scoop_w, scoop_h = 0.65, 0.45
    scoop = sandbox.add_scoop(arm_tip_x, arm_tip_y, scoop_w, scoop_h, angle=0, density=280.0)
    _bucket_joint = sandbox.add_revolute_joint(arm, scoop, (arm_tip_x, arm_tip_y), enable_motor=True, motor_speed=0.0, max_motor_torque=2000.0)
    sandbox.agent_arm_joint = _arm_joint
    sandbox.agent_bucket_joint = _bucket_joint
    return scoop


def agent_action(sandbox, agent_body, step_count):

    global _arm_joint, _bucket_joint
    if agent_body is None or not agent_body.active:
        return
    if _arm_joint is None or _bucket_joint is None:
        _arm_joint = sandbox.agent_arm_joint
        _bucket_joint = sandbox.agent_bucket_joint
        if _arm_joint is None or _bucket_joint is None:
            return

    dt = 1.0 / 60.0
    t = step_count * dt
    has_wall = sandbox.has_central_wall()
    phase_duration = 12.0
    phase = (t % phase_duration) / phase_duration
    arm_angle = _arm_joint.angle
    ANGLE_PIT = 0.0
    ANGLE_CLEAR = 1.32
    ANGLE_HOPPER = 2.35
    ARM_K = 3.0
    ARM_SPEED_CAP = 3.0
    BUCKET_SCOOP = -1.3
    BUCKET_DUMP = 1.2

    if phase < 0.25:
        target_arm = ANGLE_PIT
        _arm_joint.motorSpeed = max(-ARM_SPEED_CAP, min(ARM_SPEED_CAP, ARM_K * (target_arm - arm_angle)))
        _arm_joint.motorEnabled = True
    elif phase < 0.48:
        if has_wall:
            target_arm = ANGLE_CLEAR if arm_angle < 1.2 else ANGLE_HOPPER
        else:
            target_arm = 1.6 if arm_angle < 1.4 else ANGLE_HOPPER
        _arm_joint.motorSpeed = max(-ARM_SPEED_CAP, min(ARM_SPEED_CAP, ARM_K * (target_arm - arm_angle)))
        _arm_joint.motorEnabled = True
    elif phase < 0.56:
        _arm_joint.motorSpeed = 0.0
        _arm_joint.motorEnabled = True
    elif phase < 0.88:
        target_arm = ANGLE_CLEAR if has_wall else ANGLE_PIT
        _arm_joint.motorSpeed = max(-ARM_SPEED_CAP, min(ARM_SPEED_CAP, ARM_K * (target_arm - arm_angle)))
        _arm_joint.motorEnabled = True
    else:
        target_arm = ANGLE_PIT
        _arm_joint.motorSpeed = max(-ARM_SPEED_CAP, min(ARM_SPEED_CAP, ARM_K * (target_arm - arm_angle)))
        _arm_joint.motorEnabled = True

    if phase < 0.18:
        _bucket_joint.motorSpeed = BUCKET_SCOOP
        _bucket_joint.motorEnabled = True
    elif phase < 0.28:
        _bucket_joint.motorSpeed = 0.4
        _bucket_joint.motorEnabled = True
    elif phase < 0.46:
        _bucket_joint.motorSpeed = 0.15
        _bucket_joint.motorEnabled = True
    elif phase < 0.58:
        _bucket_joint.motorSpeed = BUCKET_DUMP
        _bucket_joint.motorEnabled = True
    elif phase < 0.86:
        _bucket_joint.motorSpeed = -0.6
        _bucket_joint.motorEnabled = True
    else:
        _bucket_joint.motorSpeed = BUCKET_SCOOP
        _bucket_joint.motorEnabled = True
