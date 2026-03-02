"""
D-05: The Hammer — LATE safe window: bar at bottom only at step ~409. Must WAIT, then three-phase swing.
Not "one hit": hammer idle ~380 steps, then timed swing to pass slot at 409 and break shell.
Reference: pivot (12, 7.5); phase1 step 380 omega 26; phase2 step 398 omega 2.2; phase3 step 408 omega 12.
"""
import math


def build_agent(sandbox):
    # Pivot (12, 7.5): head at x=15 has y≈2.89; pass slot at step ~409 when bar at bottom (late window)
    pivot_x, pivot_y = 12.0, 7.5
    arm_len = 5.5
    arm_center_y = pivot_y - arm_len / 2
    arm = sandbox.add_beam(
        x=pivot_x,
        y=arm_center_y,
        width=0.26,
        height=arm_len,
        angle=0.0,
        density=28.0,
    )
    sandbox.add_joint(arm, None, (pivot_x, pivot_y), type="pivot")
    head_dist = 5.5
    head = sandbox.add_beam(
        x=pivot_x,
        y=pivot_y - head_dist,
        width=0.55,
        height=0.55,
        angle=0.0,
        density=85.0,
    )
    sandbox.add_joint(arm, head, (pivot_x, pivot_y - head_dist), type="rigid")
    sandbox.set_material_properties(arm, restitution=0.2)
    sandbox.set_material_properties(head, restitution=0.2)
    mass = sandbox.get_structure_mass()
    if mass > sandbox.MAX_STRUCTURE_MASS:
        raise ValueError(f"Structure mass {mass:.2f} kg exceeds limit {sandbox.MAX_STRUCTURE_MASS} kg")
    return head


def agent_action(sandbox, agent_body, step_count):
    # LATE window: bar at bottom at step ~409. Hammer WAITs ~380 steps, then three-phase (pass at 409, then re-accelerate).
    # Not "one hit": long idle then timed swing.
    arm = sandbox.bodies[0] if sandbox.bodies else None
    if not arm:
        return
    if step_count == 380:
        arm.angularVelocity = 26.0
    elif step_count == 398:
        arm.angularVelocity = 2.2
    elif step_count == 408:
        arm.angularVelocity = 12.0
