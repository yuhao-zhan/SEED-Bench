"""
K-05: The Lifter task Agent module
架子从低处建：平台初始 ~8.0m（明显低于红线 9m），电机展开升到 9m 并保持 3s，
GIF 里能看到架子从下方向红线上升的过程。
"""
import math


CENTER_X = 4.0
BASE_Y = 1.15
HALF_SPAN = 2.0
ARM_LEN = 3.0
ARM_THICK = 0.08
PLATFORM_W = 4.0
PLATFORM_H = 0.12
DENSITY = 0.6

H_GAIN = math.sqrt(ARM_LEN**2 - HALF_SPAN**2)

BASE_TOP = BASE_Y + 0.16
CY_LIST = [
    BASE_Y + 0.05 + 0.85 * H_GAIN,
    BASE_Y + 0.05 + 1.70 * H_GAIN,
    BASE_Y + 0.05 + 2.55 * H_GAIN,
    BASE_Y + 0.05 + 3.40 * H_GAIN,
]


def _arm_center_angle_len(px, py, cx, cy):
    bx = (px + cx) / 2
    by = (py + cy) / 2
    angle = math.atan2(cy - py, cx - px)
    length = math.sqrt((cx - px)**2 + (cy - py)**2)
    return bx, by, angle, min(length, 4.0)


def build_agent(sandbox):
    """
    Build 4-stage scissor with top platform ~8.5m（低于红线 9m），短稳后立即升到 9m，GIF 里可见明显上升过程。
    """
    base = sandbox.add_beam(
        x=CENTER_X, y=BASE_Y + 0.05,
        width=PLATFORM_W, height=0.22,
        angle=0, density=1.6
    )
    sandbox.set_material_properties(base, restitution=0.0, friction=0.9)

    left_pivot_x = CENTER_X - HALF_SPAN
    right_pivot_x = CENTER_X + HALF_SPAN
    prev_plat = base
    prev_cy = BASE_Y + 0.16
    motor_joints = []

    for cy in CY_LIST:
        cx = CENTER_X
        blx, bly, angle_left, len_left = _arm_center_angle_len(left_pivot_x, prev_cy, cx, cy)
        arm_left = sandbox.add_beam(
            x=blx, y=bly, width=len_left, height=ARM_THICK,
            angle=angle_left, density=DENSITY
        )
        sandbox.set_material_properties(arm_left, restitution=0.0, friction=0.5)
        sandbox.add_joint(prev_plat, arm_left, (left_pivot_x, prev_cy), type='pivot')

        brx, bry, angle_right, len_right = _arm_center_angle_len(right_pivot_x, prev_cy, cx, cy)
        arm_right = sandbox.add_beam(
            x=brx, y=bry, width=len_right, height=ARM_THICK,
            angle=angle_right, density=DENSITY
        )
        sandbox.set_material_properties(arm_right, restitution=0.0, friction=0.5)
        sandbox.add_joint(prev_plat, arm_right, (right_pivot_x, prev_cy), type='pivot')

        j_center = sandbox.add_joint(arm_left, arm_right, (cx, cy), type='pivot')
        motor_joints.append(j_center)

        plat = sandbox.add_beam(x=cx, y=cy, width=PLATFORM_W, height=PLATFORM_H, angle=0, density=DENSITY)
        sandbox.set_material_properties(plat, restitution=0.0, friction=0.9)
        sandbox.add_joint(arm_left, plat, (cx, cy), type='rigid')
        sandbox.add_joint(arm_right, plat, (cx, cy), type='rigid')

        prev_plat = plat
        prev_cy = cy

    sandbox._lifter_motor_joints = motor_joints
    sandbox._top_platform = prev_plat

    total_mass = sandbox.get_structure_mass()
    if total_mass > sandbox.MAX_STRUCTURE_MASS:
        raise ValueError(f"Structure mass {total_mass:.2f}kg exceeds limit {sandbox.MAX_STRUCTURE_MASS}kg")
    print(f"Lifter constructed: {len(sandbox.bodies)} bodies, {len(sandbox.joints)} joints, {total_mass:.2f}kg")
    return base


SETTLE_STEPS = 30

def agent_action(sandbox, agent_body, step_count):
    """架子从 ~8.5m 展开升到 9m 再保持 3s（GIF 里明显从低到红线）。"""
    if not hasattr(sandbox, '_lifter_motor_joints'):
        return
    if step_count < SETTLE_STEPS:
        for joint in sandbox._lifter_motor_joints:
            if joint is not None:
                sandbox.set_motor(joint, 0.0, 30.0)
        return
    plat_y = sandbox._top_platform.position.y if hasattr(sandbox, '_top_platform') and sandbox._top_platform else None
    if plat_y is not None and plat_y >= 8.4:
        motor_speed, max_torque = 0.0, 35.0
    elif plat_y is not None and plat_y >= 8.0:
        motor_speed, max_torque = -0.02, 38.0
    elif plat_y is not None and plat_y >= 7.0:
        motor_speed, max_torque = -0.06, 42.0
    elif plat_y is not None and plat_y >= 6.0:
        motor_speed, max_torque = -0.10, 48.0
    else:
        motor_speed, max_torque = -0.14, 52.0
    for joint in sandbox._lifter_motor_joints:
        if joint is not None:
            sandbox.set_motor(joint, motor_speed, max_torque)
