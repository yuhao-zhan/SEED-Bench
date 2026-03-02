"""
E-04: Variable Mass task agent module (hard variant).
Reference solution: survives spatial-phase mass variation + 2D base excitation + fatigue,
with span requirement and at least one revolute joint.
Strategy: span [6, 14] with outriggers; one pivot at symmetric center; many light beams/joints.
"""
import math


def build_agent(sandbox):
    """
    Build a structure that survives:
    - Mass variation with position-dependent phase (internal forces between beams)
    - 2D base excitation (support moves in horizontal and vertical)
    - Joint fatigue (effective limits decay over time)
    - Span: at least one beam center x <= 6, one >= 14
    - At least one pivot (revolute) joint; rest rigid.
    Keep forces/torques very low: many joints, very light, low profile.
    """
    ground_top = sandbox.get_ground_y_top()
    x_min, x_max, _, _ = sandbox.get_build_zone()
    span_left, span_right = sandbox.get_span_bounds()
    deck_cy = 2.0
    deck_h = 0.2
    density = 0.28
    strut_w = 0.18
    strut_density = 0.25
    strut_h = deck_cy - ground_top
    strut_cy = ground_top + strut_h / 2

    # Span beams: left at x=6, right at x=14
    left_span = sandbox.add_beam(
        x=span_left, y=deck_cy,
        width=0.5, height=deck_h,
        angle=0, density=density,
    )
    right_span = sandbox.add_beam(
        x=span_right, y=deck_cy,
        width=0.5, height=deck_h,
        angle=0, density=density,
    )
    # Middle deck segments (max width 4 each)
    deck_left = sandbox.add_beam(
        x=8.0, y=deck_cy,
        width=2.0, height=deck_h,
        angle=0, density=density,
    )
    deck_right = sandbox.add_beam(
        x=12.0, y=deck_cy,
        width=2.0, height=deck_h,
        angle=0, density=density,
    )

    # Struts at x = 6, 7, 8, 9, 11, 12, 13, 14 (center 10 added separately with pivot)
    strut_xs = [6.0, 7.0, 8.0, 9.0, 11.0, 12.0, 13.0, 14.0]
    strut_bodies = []
    for sx in strut_xs:
        s = sandbox.add_beam(
            x=sx, y=strut_cy,
            width=strut_w, height=strut_h,
            angle=0, density=strut_density,
        )
        strut_bodies.append((sx, s))
        sandbox.add_joint(s, None, (sx, ground_top), type="rigid")
        if sx <= 9:
            sandbox.add_joint(deck_left, s, (sx, deck_cy), type="rigid")
        else:
            sandbox.add_joint(deck_right, s, (sx, deck_cy), type="rigid")
    # Center strut (x=10): connect to both decks; ONE pivot here to satisfy constraint
    sx_center = 10.0
    strut_center = sandbox.add_beam(
        x=sx_center, y=strut_cy,
        width=strut_w, height=strut_h,
        angle=0, density=strut_density,
    )
    sandbox.add_joint(strut_center, None, (sx_center, ground_top), type="rigid")
    sandbox.add_joint(deck_left, strut_center, (sx_center, deck_cy), type="rigid")
    sandbox.add_joint(deck_right, strut_center, (sx_center, deck_cy), type="pivot")

    # Connect deck segments and outriggers
    sandbox.add_joint(left_span, deck_left, (7.0, deck_cy), type="rigid")
    sandbox.add_joint(deck_left, deck_right, (10.0, deck_cy), type="rigid")
    sandbox.add_joint(deck_right, right_span, (13.0, deck_cy), type="rigid")
    # Anchor left/right span to their struts
    sandbox.add_joint(left_span, strut_bodies[0][1], (span_left, deck_cy), type="rigid")
    sandbox.add_joint(right_span, strut_bodies[-1][1], (span_right, deck_cy), type="rigid")

    total_mass = sandbox.get_structure_mass()
    mass_limit = sandbox.get_structure_mass_limit()
    if total_mass > mass_limit:
        raise ValueError(
            "Structure mass {:.2f} kg exceeds limit {} kg".format(total_mass, mass_limit)
        )
    n_bodies = len(sandbox.bodies)
    n_joints = len(sandbox.joints)
    min_beams = sandbox.get_min_beams()
    min_joints = sandbox.get_min_joints()
    if n_bodies < min_beams:
        raise ValueError("At least {} beams required, got {}".format(min_beams, n_bodies))
    if n_joints < min_joints:
        raise ValueError("At least {} joints required, got {}".format(min_joints, n_joints))
    return deck_left


def agent_action(sandbox, agent_body, step_count):
    """No per-step action required for E-04 (purely structural)."""
    pass
