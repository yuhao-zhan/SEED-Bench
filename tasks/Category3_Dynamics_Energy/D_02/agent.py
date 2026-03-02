"""
D-02: The Jumper task Agent module (slots: trajectory must pass through narrow gaps between lower and upper red bars)
Reference: impulse (vx, vy) so trajectory passes through all three slots and lands on right platform.
Tuned: (10, 15.9) passes slot 1 (x~17), slot 3 (x~19), slot 2 (x~21) and lands x>=26.
"""
import math


def build_agent(sandbox):
    """
    Build a minimal launcher pad and return the jumper. Launch via impulse in agent_action.
    Trajectory must pass through all three narrow slots (between lower and upper red bars) and land at x>=26.
    """
    jumper = sandbox.get_jumper()
    if jumper is None:
        raise ValueError("Jumper not found in environment")

    pad = sandbox.add_beam(
        x=5.0,
        y=2.75,
        width=1.0,
        height=0.2,
        angle=0,
        density=40.0,
    )
    sandbox.set_material_properties(pad, restitution=0.2)
    sandbox.add_joint(pad, None, (5.0, 2.75), type="rigid")

    total_mass = sandbox.get_structure_mass()
    if total_mass > sandbox.MAX_STRUCTURE_MASS:
        raise ValueError(
            f"Structure mass {total_mass:.2f} kg exceeds limit {sandbox.MAX_STRUCTURE_MASS} kg"
        )

    return jumper


def agent_action(sandbox, agent_body, step_count):
    """
    Apply impulse on first step. Trajectory must pass through all three slots (center inside floor+margin to ceil-margin).
    (10, 15.65): at x=17 y~13.7, x=19 y~13.2, x=21 y~12.1; lands x>=26.
    """
    if step_count != 0:
        return
    vx, vy = 10.0, 15.9  # tuned: pass all three slots and land on right platform
    sandbox.set_jumper_velocity(vx, vy)
