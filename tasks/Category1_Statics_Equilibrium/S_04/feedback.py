"""
Task-specific feedback generation for S-04: The Balancer.
Process-aware, diagnostic feedback for Statics/Equilibrium domain.
Uses only metrics returned by evaluator.evaluate(); no hardcoded thresholds.
All thresholds (balance time, angle tolerance, ground limit) are read from metrics
so feedback adapts to stage mutations (stages.py).
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
    Phase-segregated (Capture vs Balance), boundary proximity, torque state.
    No suggestions; no hardcoded thresholds—all limits come from metrics.
    """
    parts: List[str] = []

    # --- Physics engine limits: non-finite values indicate numerical instability ---
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
        parts.append(f"**Phase 1 — Payload status**: {status}")
    if 'load_pos' in metrics and metrics['load_pos'] is not None:
        lp = metrics['load_pos']
        if isinstance(lp, (list, tuple)) and len(lp) >= 2 and _is_finite_number(lp[0]) and _is_finite_number(lp[1]):
            parts.append(f"**Load position**: ({float(lp[0]):.2f}, {float(lp[1]):.2f}) m")
    if 'load_mass' in metrics and _is_finite_number(metrics.get('load_mass')):
        parts.append(f"**Load mass**: {metrics['load_mass']:.2f} kg")

    # --- Phase 2: Balance / equilibrium ---
    target_time = metrics.get('target_balance_time')
    if target_time is not None and _is_finite_number(target_time):
        bd = metrics.get('balance_duration')
        if bd is not None and _is_finite_number(bd):
            ok = bd >= target_time
            parts.append(f"{'✅' if ok else '❌'} **Phase 2 — Balance duration**: {bd:.2f}s / {target_time:.2f}s (required)")

    tol_deg = metrics.get('max_angle_deviation_deg')
    if tol_deg is not None and _is_finite_number(tol_deg):
        if 'beam_angle_deg' in metrics and _is_finite_number(metrics['beam_angle_deg']):
            parts.append(f"**Current beam angle**: {metrics['beam_angle_deg']:+.2f}° (tolerance ±{tol_deg:.1f}°)")
        max_angle = metrics.get('max_angle_seen_deg')
        if max_angle is not None and _is_finite_number(max_angle):
            parts.append(f"**Peak angle recorded**: {max_angle:.2f}°")
            # Boundary proximity: how close peak angle was to the limit
            angle_margin_deg = tol_deg - abs(max_angle) if tol_deg >= 0 else None
            if angle_margin_deg is not None and math.isfinite(angle_margin_deg):
                parts.append(f"**Angle margin** (tolerance − |peak|): {angle_margin_deg:+.2f}°")

    # --- Net torque about pivot (static equilibrium indicator) ---
    if 'net_torque_about_pivot' in metrics and _is_finite_number(metrics['net_torque_about_pivot']):
        parts.append(f"**Net torque about pivot**: {metrics['net_torque_about_pivot']:+.2f} N·m")

    # --- Structure mass and center of mass (lever-arm / moment insight) ---
    if 'structure_mass' in metrics and _is_finite_number(metrics['structure_mass']):
        parts.append(f"**Structure mass**: {metrics['structure_mass']:.2f} kg")
    if 'structure_com_x' in metrics and 'structure_com_y' in metrics:
        cx, cy = metrics.get('structure_com_x'), metrics.get('structure_com_y')
        if _is_finite_number(cx) and _is_finite_number(cy):
            parts.append(f"**Structure CoM**: ({float(cx):.2f}, {float(cy):.2f}) m")

    # --- Boundary proximity: distance to ground failure ---
    ground_limit = metrics.get('ground_y_limit')
    min_y = metrics.get('min_body_y')
    if ground_limit is not None and _is_finite_number(ground_limit) and min_y is not None and _is_finite_number(min_y):
        margin = min_y - ground_limit
        parts.append(f"**Lowest body y**: {min_y:.2f} m (ground limit y = {ground_limit:.1f}); **vertical margin** = {margin:.2f} m")

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
    and root-cause chain; never prescribe exact design or parameters.
    All thresholds read from metrics (stage-mutation safe).
    """
    suggestions: List[str] = []

    # --- Design constraint / API violation (from runner, not physics) ---
    if error:
        suggestions.append(">> DIAGNOSTIC: A design constraint or build limit was violated. Infer allowed build zone and primitive limits from the error; do not assume default values.")
        return suggestions

    # --- Physics engine numerical instability (metrics returned by evaluator only) ---
    check_keys = ['net_torque_about_pivot', 'beam_angle_deg', 'balance_duration', 'structure_mass', 'min_body_y']
    for key in check_keys:
        v = metrics.get(key)
        if v is not None and not _is_finite_number(v):
            suggestions.append(">> DIAGNOSTIC: Simulation produced non-finite values. This may indicate extreme forces, penetrations, or numerical instability. Infer the physical cause from which metric became non-finite.")
            break

    # Resolve thresholds from metrics only (dynamic; adapts to stages)
    target_balance_time = metrics.get('target_balance_time')
    max_angle_deviation_deg = metrics.get('max_angle_deviation_deg')
    ground_y_limit = metrics.get('ground_y_limit')
    load_caught = metrics.get('load_caught', False)
    balance_duration = metrics.get('balance_duration')
    max_angle_seen_deg = metrics.get('max_angle_seen_deg')
    net_torque = metrics.get('net_torque_about_pivot')
    min_body_y = metrics.get('min_body_y')

    if not failed:
        # --- Multi-objective: success=False but not yet "failed" ---
        if load_caught and target_balance_time is not None and _is_finite_number(target_balance_time) and balance_duration is not None:
            if balance_duration < target_balance_time:
                angle_exceeded = (
                    max_angle_deviation_deg is not None and max_angle_seen_deg is not None
                    and abs(max_angle_seen_deg) > max_angle_deviation_deg
                )
                if not angle_exceeded:
                    suggestions.append("-> DIAGNOSTIC: Payload is attached and angle stayed within tolerance, but balance duration is below the required time. The system was momentarily in equilibrium but not sustained; consider what could cause late divergence (e.g. drift, damping, or residual moment).")
                else:
                    suggestions.append("-> DIAGNOSTIC: Payload attached but angular tolerance was exceeded at some point. Identify whether the dominant cause is initial imbalance (net moment at rest) or a transient (e.g. impact, wind). Sustained balance requires net torque about the pivot to stay within the allowed angle band.")
        elif not load_caught:
            suggestions.append("-> DIAGNOSTIC: Load was never attached. The capture condition requires some part of the structure to reach the load location; the failure indicates this geometric condition was not met.")
        return suggestions

    # --- Failed: root-cause chain (what broke first) ---
    suggestions.append(f">> FAILURE MODE: {failure_reason or 'Unknown'}")

    reason_lower = (failure_reason or "").lower()

    # Root cause: capture vs balance vs grounding
    if "catch" in reason_lower or ("load" in reason_lower and "ground" not in reason_lower and "fell" not in reason_lower):
        suggestions.append("-> ROOT CAUSE (capture): Engagement with the payload did not occur. The physical mechanism is geometric: some part of the structure must reach the load location within the allowed proximity. Diagnose why that condition was not met (e.g. build zone, obstacle, or timing) without assuming a specific design.")
    elif "angle" in reason_lower or "tilt" in reason_lower or "exceeds" in reason_lower:
        suggestions.append("-> ROOT CAUSE (balance): The main beam exceeded the allowed angular deviation. In statics, this indicates a net moment about the pivot—mass distribution and external forces set that moment. Focus on reducing the net torque about the pivot; the allowed angle margin may differ across stages.")
        if net_torque is not None and _is_finite_number(net_torque):
            suggestions.append(f"   (Net torque about pivot at evaluation: {net_torque:+.2f} N·m. Sustained level balance requires this to remain near zero within the angle band.)")
    elif "ground" in reason_lower or "fell" in reason_lower or "touched" in reason_lower:
        suggestions.append("-> ROOT CAUSE (grounding): A body crossed the vertical boundary and contacted the ground. This usually follows large rotation or collapse—either from static imbalance (overturning moment) or from a broken joint. Consider what sets the margin between the lowest part of the structure and the ground limit.")
        if min_body_y is not None and ground_y_limit is not None and _is_finite_number(min_body_y) and _is_finite_number(ground_y_limit):
            suggestions.append(f"   (Lowest body y = {min_body_y:.2f} m; ground limit y = {ground_y_limit:.1f} m.)")

    return suggestions
