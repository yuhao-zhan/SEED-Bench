"""
D-01: The Launcher task Agent module
Reference solution: pivot right of ball; arm tip left of ball; single strong spring
so trajectory reaches y in [2,5] when x in [40,45]. Success = projectile center inside red zone.
"""
import math


def build_agent(sandbox):
    """
    Pivot at (12, 1), tip at (9.5, 2.8). One strong spring (max stiffness, short rest)
    so arc reaches red zone [40,45] x [2,5] without overshooting.
    Returns projectile for camera.
    """
    ground = sandbox.get_ground()
    projectile = sandbox.get_projectile()
    if not ground or not projectile:
        raise ValueError("Ground or projectile not found in environment")

    pivot_x, pivot_y = 12.0, 1.0
    tip_x, tip_y = 9.5, 2.8

    arm_dx = tip_x - pivot_x
    arm_dy = tip_y - pivot_y
    arm_length = math.sqrt(arm_dx * arm_dx + arm_dy * arm_dy)
    arm_angle = math.atan2(arm_dy, arm_dx)
    arm_center_x = (pivot_x + tip_x) / 2
    arm_center_y = (pivot_y + tip_y) / 2

    arm = sandbox.add_beam(
        x=arm_center_x,
        y=arm_center_y,
        width=arm_length,
        height=0.2,
        angle=arm_angle,
        density=2.0,
    )
    sandbox.set_material_properties(arm, restitution=0.35)
    sandbox.add_joint(arm, None, (pivot_x, pivot_y), type="pivot")

    # Single spring: high stiffness so arc reaches y in [2,5] in band (stiffness limit 3000)
    sandbox.add_spring(
        ground,
        arm,
        (12.0, 3.0),
        (11.0, 2.0),
        rest_length=0.28,
        stiffness=2800.0,
        damping_ratio=0.24,
    )

    total_mass = sandbox.get_structure_mass()
    if total_mass > sandbox.MAX_STRUCTURE_MASS:
        raise ValueError(
            f"Structure mass {total_mass:.2f} kg exceeds limit {sandbox.MAX_STRUCTURE_MASS} kg"
        )

    print(
        f"Launcher constructed: {len(sandbox.bodies)} beams, {len(sandbox.joints)} joints, "
        f"{len(sandbox.springs)} springs, {total_mass:.2f} kg"
    )

    return projectile


def agent_action(sandbox, agent_body, step_count):
    pass
