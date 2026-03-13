"""
Task-specific feedback generation for S-04: The Balancer.
Process-aware, diagnostic feedback for Statics/Equilibrium domain.
Uses only metrics returned by evaluator.evaluate(); no hardcoded thresholds.
"""

from typing import Dict, Any, List
import math


def _is_finite_number(x: Any) -> bool:
    """True if x is a real number (no NaN, no inf)."""
    if x is None:
        return False
    try:
        f = float(x)
        return math.isfinite(f)
    except (TypeError, ValueError):
        return False


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Expose high-resolution physical metrics from the evaluator output only.
    Phase-segregated (capture vs balance), boundary proximity, torque state.
    All thresholds read from metrics (stage-mutation safe).
    """
    parts: List[str] = []

    # --- Numerical sanity (physics engine limits) ---
    numeric_keys = [
        'balance_duration', 'target_balance_time', 'beam_angle_deg', 'max_angle_seen_deg',
        'max_angle_deviation_deg', 'structure_mass', 'structure_com_x', 'structure_com_y',
        'min_body_y', 'net_torque_about_pivot', 'load_mass', 'ground_y_limit',
    ]
    for key in numeric_keys:
        val = metrics.get(key)
        if val is not None and not _is_finite_number(val):
            parts.append(f">> **Numerical instability**: metric `{key}` is non-finite. Simulation state may be invalid.")
            break

    # --- Phase 1: Capture / payload engagement ---
    if 'load_caught' in metrics:
        caught = metrics['load_caught']
        status = "✅ ATTACHED" if caught else "❌ NOT CAUGHT"
        parts.append(f"**Payload status**: {status}")
    if 'load_pos' in metrics and metrics['load_pos'] is not None:
        lp = metrics['load_pos']
        if _is_finite_number(lp[0]) and _is_finite_number(lp[1]):
            parts.append(f"**Load position**: ({lp[0]:.2f}, {lp[1]:.2f}) m")
    if 'load_mass' in metrics and _is_finite_number(metrics.get('load_mass')):
        parts.append(f"**Load mass**: {metrics['load_mass']:.2f} kg")

    # --- Phase 2: Balance / equilibrium ---
    target_time = metrics.get('target_balance_time')
    if target_time is not None and _is_finite_number(target_time):
        bd = metrics.get('balance_duration')
        if bd is not None and _is_finite_number(bd):
            ok = bd >= target_time
            parts.append(f"{'✅' if ok else '❌'} **Balance duration**: {bd:.2f}s / {target_time:.2f}s")

    tol_deg = metrics.get('max_angle_deviation_deg')
    if tol_deg is not None and _is_finite_number(tol_deg):
        if 'beam_angle_deg' in metrics and _is_finite_number(metrics['beam_angle_deg']):
            parts.append(f"**Current beam angle**: {metrics['beam_angle_deg']:+.2f}° (tolerance ±{tol_deg:.1f}°)")
        if 'max_angle_seen_deg' in metrics and _is_finite_number(metrics['max_angle_seen_deg']):
            parts.append(f"**Peak angle recorded**: {metrics['max_angle_seen_deg']:.2f}°")

    # --- Torque about pivot (static equilibrium indicator) ---
    if 'net_torque_about_pivot' in metrics and _is_finite_number(metrics['net_torque_about_pivot']):
        parts.append(f"**Net torque about pivot**: {metrics['net_torque_about_pivot']:+.2f} N·m")

    # --- Structure mass and center of mass (lever-arm / moment insight) ---
    if 'structure_mass' in metrics and _is_finite_number(metrics['structure_mass']):
        parts.append(f"**Structure mass**: {metrics['structure_mass']:.2f} kg")
    if 'structure_com_x' in metrics and 'structure_com_y' in metrics:
        cx, cy = metrics.get('structure_com_x'), metrics.get('structure_com_y')
        if _is_finite_number(cx) and _is_finite_number(cy):
            parts.append(f"**Structure CoM**: ({cx:.2f}, {cy:.2f}) m")

    # --- Boundary proximity (distance to ground failure) ---
    ground_limit = metrics.get('ground_y_limit')
    min_y = metrics.get('min_body_y')
    if ground_limit is not None and _is_finite_number(ground_limit) and min_y is not None and _is_finite_number(min_y):
        margin = min_y - ground_limit
        parts.append(f"**Lowest body y**: {min_y:.2f} m (ground limit y = {ground_limit:.1f}; margin = {margin:.2f} m)")

    # --- Outcome flags (no interpretation here) ---
    if 'success' in metrics:
        parts.append(f"**Success**: {metrics['success']}")
    if 'failed' in metrics and metrics['failed']:
        parts.append(f"**Failed**: True")
    if metrics.get('failure_reason'):
        parts.append(f"**Failure reason**: {metrics['failure_reason']}")

    return parts


def get_improvement_suggestions(
    metrics: Dict[str, Any],
    score: float,
    success: bool,
    failed: bool,
    failure_reason: str = None,
    error: str = None,
) -> List[str]:
    """
    Diagnostic, process-aware suggestions. No spoilers: describe physical mechanism
    and root-cause chain, never prescribe exact design or parameters.
    All thresholds from metrics (stage-mutation safe).
    """
    suggestions: List[str] = []

    # --- Design constraint / API violation (from runner, not physics) ---
    if error:
        suggestions.append(">> DIAGNOSTIC: A design constraint or build limit was violated. Infer allowed build zone and primitive limits from the error; do not assume default values.")
        return suggestions

    # --- Physics engine numerical instability ---
    for key in ['net_torque_about_pivot', 'beam_angle_deg', 'balance_duration', 'structure_mass', 'min_body_y']:
        v = metrics.get(key)
        if v is not None and not _is_finite_number(v):
            suggestions.append(">> DIAGNOSTIC: Simulation produced non-finite values. This may indicate extreme forces, penetrations, or numerical instability. Consider constraining geometry or loads to stable ranges.")
            break

    if not failed:
        # --- Multi-objective trade-off: success=False but not yet "failed" ---
        target_time = metrics.get('target_balance_time')
        tol_deg = metrics.get('max_angle_deviation_deg')
        caught = metrics.get('load_caught', False)
        bd = metrics.get('balance_duration')
        max_angle = metrics.get('max_angle_seen_deg')

        if caught and target_time is not None and _is_finite_number(target_time) and bd is not None:
            if bd < target_time and (tol_deg is None or max_angle is None or max_angle <= tol_deg):
                suggestions.append("-> DIAGNOSTIC: Payload is attached and angle within tolerance, but balance duration is below the required time. The system is momentarily in equilibrium but not sustained; consider what could cause late divergence (e.g. drift, damping, or residual moment).")
            elif tol_deg is not None and max_angle is not None and max_angle > tol_deg:
                suggestions.append("-> DIAGNOSTIC: Payload attached but angular tolerance was exceeded at some point. Identify whether the dominant cause is initial imbalance (net moment at rest) or a transient (e.g. impact, wind). Sustained balance requires net torque about the pivot to stay within the allowed angle band.")
        elif not caught:
            suggestions.append("-> DIAGNOSTIC: Load was never attached. The capture condition depends on structure geometry reaching the load location; revise how and where the structure extends relative to the target position.")
        return suggestions

    # --- Failed: root-cause chain (what broke first) ---
    suggestions.append(f">> FAILURE MODE: {failure_reason or 'Unknown'}")

    reason_lower = (failure_reason or "").lower()

    # Root cause: capture vs balance vs grounding
    if "catch" in reason_lower or "load" in reason_lower and "ground" not in reason_lower and "fell" not in reason_lower:
        suggestions.append("-> ROOT CAUSE (capture): Engagement with the payload did not occur. The physical mechanism is geometric: some part of the structure must reach the load location within the allowed proximity. Consider how the design reaches that region without violating other constraints.")
    elif "angle" in reason_lower or "tilt" in reason_lower or "exceeds" in reason_lower:
        net_t = metrics.get('net_torque_about_pivot')
        tol_deg = metrics.get('max_angle_deviation_deg')
        suggestions.append("-> ROOT CAUSE (balance): The main beam exceeded the allowed angular deviation. In statics, this indicates a net moment about the pivot—mass distribution and external forces (e.g. wind) set that moment. Improve equilibrium by reducing net torque (e.g. moving center of mass or counterweight) or by respecting a stricter angle margin; do not assume the tolerance is the same in all stages.")
        if net_t is not None and _is_finite_number(net_t):
            suggestions.append(f"   (Net torque about pivot at evaluation: {net_t:+.2f} N·m. Sustained level balance requires this to remain near zero within the angle band.)")
    elif "ground" in reason_lower or "fell" in reason_lower or "touched" in reason_lower:
        min_y = metrics.get('min_body_y')
        ground_limit = metrics.get('ground_y_limit')
        suggestions.append("-> ROOT CAUSE (grounding): A body crossed the vertical boundary and contacted the ground. This usually follows large rotation or collapse—either from static imbalance (overturning moment) or from a broken joint. Consider what sets the margin between the lowest part of the structure and the ground limit.")
        if min_y is not None and ground_limit is not None and _is_finite_number(min_y) and _is_finite_number(ground_limit):
            suggestions.append(f"   (Lowest body y = {min_y:.2f} m; ground limit y = {ground_limit:.1f} m.)")

    # --- Multi-objective paradox: one objective met, another severely missed ---
    caught = metrics.get('load_caught', False)
    bd = metrics.get('balance_duration')
    target_time = metrics.get('target_balance_time')
    if caught and target_time is not None and bd is not None and bd < target_time and "angle" not in reason_lower and "ground" not in reason_lower:
        suggestions.append("-> TRADE-OFF: Capture was achieved but balance duration was insufficient. This suggests the design can reach the load but the resulting equilibrium is unstable or the allowed angle was exceeded later; focus on the moment balance and how it evolves over time.")

    return suggestions
