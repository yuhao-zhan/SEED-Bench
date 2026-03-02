"""
D-03: Phase-Locked Gate — reference solution: two impulse zones + velocity profile + four gates.
Must survive impulse [8,9] AND second impulse [10.5,11]; v(9)≥2.8, v(11) in band, final in [2.0,2.5].
"""
import math


def build_agent(sandbox):
    cabin = sandbox.get_vehicle_cabin()
    if cabin is None:
        raise ValueError("Cart not found")

    # 4 beams, higher density: enough mass to survive BOTH impulse [8,9] and second impulse [10.5,11], still reach target
    beams = []
    for (xx, yy) in [(5.5, 2.5), (6.0, 2.5), (6.5, 2.5), (6.2, 2.6)]:
        b = sandbox.add_beam(xx, yy, 0.18, 0.16, angle=0, density=1.48)
        sandbox.add_joint(cabin, b, (xx, yy), type="rigid")
        beams.append(b)

    n = len(sandbox.bodies)
    mass = sandbox.get_structure_mass()
    min_beams = getattr(sandbox, "MIN_BEAM_COUNT", 3)
    if n < min_beams:
        raise ValueError(f"Beam count {n} is below minimum {min_beams}")
    if n > sandbox.MAX_BEAM_COUNT:
        raise ValueError(f"Beam count {n} exceeds maximum {sandbox.MAX_BEAM_COUNT}")
    if mass > sandbox.MAX_STRUCTURE_MASS:
        raise ValueError(f"Structure mass {mass:.2f} kg exceeds limit {sandbox.MAX_STRUCTURE_MASS} kg")
    return cabin


def agent_action(sandbox, agent_body, step_count):
    pass
