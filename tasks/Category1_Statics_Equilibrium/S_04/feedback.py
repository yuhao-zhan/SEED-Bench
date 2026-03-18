"""
Task-specific feedback generation for S-04: The Balancer.
Uses only metrics returned by evaluator.evaluate(). No hardcoded thresholds.
All limits read from metrics (stage-mutation safe). Strictly diagnostic; no design spoilers.
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
    Expose physical metrics from the evaluator output only.
    Every key and derived value traces to the metrics dict. No suggestions.
    """
    parts: List[str] = []

    # Only report on metrics the evaluator actually returns
    numeric_keys = [
        'balance_duration', 'target_balance_time', 'beam_angle_deg', 'max_angle_seen_deg',
        'max_angle_deviation_deg', 'structure_mass', 'structure_com_x', 'structure_com_y',
        'min_body_y', 'net_torque_about_pivot', 'load_mass', 'ground_y_limit',
    ]
    for key in numeric_keys:
        val = metrics.get(key)
        if val is not None and not _is_finite_number(val):
            parts.append(f">> Metric `{key}` is non-finite. Simulation state may be invalid.")
            break

    step_count = metrics.get('step_count')
    if step_count is not None and _is_finite_number(step_count):
        parts.append(f"Simulation steps: {int(step_count)}")

    # Phase 1: Capture (metrics: load_caught, load_pos, load_mass)
    parts.append("--- Phase 1: Capture ---")
    if 'load_caught' in metrics:
        status = "ATTACHED" if metrics['load_caught'] else "NOT CAUGHT"
        parts.append(f"Payload status: {status}")
    if 'load_pos' in metrics and metrics['load_pos'] is not None:
        lp = metrics['load_pos']
        if isinstance(lp, (list, tuple)) and len(lp) >= 2 and _is_finite_number(lp[0]) and _is_finite_number(lp[1]):
            parts.append(f"Load position: ({float(lp[0]):.2f}, {float(lp[1]):.2f}) m")
    if 'load_mass' in metrics and _is_finite_number(metrics.get('load_mass')):
        parts.append(f"Load mass: {metrics['load_mass']:.2f} kg")

    # Phase 2: Balance (metrics: balance_duration, target_balance_time, beam_angle_deg, max_angle_seen_deg, max_angle_deviation_deg)
    parts.append("--- Phase 2: Balance ---")
    target_time = metrics.get('target_balance_time')
    if target_time is not None and _is_finite_number(target_time):
        bd = metrics.get('balance_duration')
        if bd is not None and _is_finite_number(bd):
            ok = bd >= target_time
            parts.append(f"Balance duration: {bd:.2f}s / {target_time:.2f}s required {'(met)' if ok else '(not met)'}")

    tol_deg = metrics.get('max_angle_deviation_deg')
    if tol_deg is not None and _is_finite_number(tol_deg):
        if 'beam_angle_deg' in metrics and _is_finite_number(metrics['beam_angle_deg']):
            parts.append(f"Current beam angle: {metrics['beam_angle_deg']:+.2f}° (tolerance ±{tol_deg:.1f}°)")
        max_angle = metrics.get('max_angle_seen_deg')
        if max_angle is not None and _is_finite_number(max_angle):
            parts.append(f"Peak angle recorded: {max_angle:.2f}°")
            angle_margin_deg = tol_deg - abs(max_angle) if tol_deg >= 0 else None
            if angle_margin_deg is not None and math.isfinite(angle_margin_deg):
                parts.append(f"Angle margin (tolerance − |peak|): {angle_margin_deg:+.2f}°")

    if 'net_torque_about_pivot' in metrics and _is_finite_number(metrics['net_torque_about_pivot']):
        parts.append(f"Net torque about pivot: {metrics['net_torque_about_pivot']:+.2f} N·m")

    if 'structure_mass' in metrics and _is_finite_number(metrics['structure_mass']):
        parts.append(f"Structure mass: {metrics['structure_mass']:.2f} kg")
    if 'structure_com_x' in metrics and 'structure_com_y' in metrics:
        cx, cy = metrics.get('structure_com_x'), metrics.get('structure_com_y')
        if _is_finite_number(cx) and _is_finite_number(cy):
            parts.append(f"Structure CoM: ({float(cx):.2f}, {float(cy):.2f}) m")

    ground_limit = metrics.get('ground_y_limit')
    min_y = metrics.get('min_body_y')
    if ground_limit is not None and _is_finite_number(ground_limit) and min_y is not None and _is_finite_number(min_y):
        margin = min_y - ground_limit
        parts.append(f"Lowest body y: {min_y:.2f} m (ground limit y = {ground_limit:.1f}); vertical margin = {margin:.2f} m")

    if 'success' in metrics:
        parts.append(f"Success: {metrics['success']}")
    if metrics.get('failed'):
        parts.append("Failed: True")
    if metrics.get('failure_reason'):
        parts.append(f"Failure reason: {metrics['failure_reason']}")

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
    Strictly diagnostic suggestions. Thresholds from metrics only. No design or parameter spoilers.
    """
    suggestions: List[str] = []

    if error:
        suggestions.append(">> DIAGNOSTIC: A design constraint or build limit was violated. Infer allowed build zone and primitive limits from the error.")
        return suggestions

    # Non-finite metric values (evaluator returns numbers; we only react to what it returned)
    check_keys = ['net_torque_about_pivot', 'beam_angle_deg', 'balance_duration', 'structure_mass', 'min_body_y']
    for key in check_keys:
        v = metrics.get(key)
        if v is not None and not _is_finite_number(v):
            suggestions.append(">> DIAGNOSTIC: A returned metric is non-finite. Simulation may have become invalid.")
            break

    target_balance_time = metrics.get('target_balance_time')
    ground_y_limit = metrics.get('ground_y_limit')
    load_caught = metrics.get('load_caught', False)
    balance_duration = metrics.get('balance_duration')
    net_torque = metrics.get('net_torque_about_pivot')
    min_body_y = metrics.get('min_body_y')

    if not failed:
        # Reachable: load_caught and balance_duration < target_balance_time (angle still in tolerance)
        if load_caught and target_balance_time is not None and _is_finite_number(target_balance_time) and balance_duration is not None and balance_duration < target_balance_time:
            suggestions.append("-> DIAGNOSTIC: Payload is attached and angle stayed within tolerance, but balance duration is below the required time. Consider what causes late divergence (e.g. drift or residual moment).")
        elif not load_caught:
            suggestions.append("-> DIAGNOSTIC: Load was never attached. The capture condition is geometric: some part of the structure must reach the load location within the allowed proximity.")
        return suggestions

    suggestions.append(f">> FAILURE MODE: {failure_reason or 'Unknown'}")
    reason_lower = (failure_reason or "").lower()

    # Root causes match evaluator failure_reason strings exactly
    if "pivot" in reason_lower and ("snap" in reason_lower or "torque" in reason_lower):
        suggestions.append("-> ROOT CAUSE (pivot capacity): The pivot joint failed under static load; net torque about the pivot exceeded the joint's capacity for this stage.")
        if net_torque is not None and _is_finite_number(net_torque):
            suggestions.append(f"   Net torque about pivot at evaluation: {net_torque:+.2f} N·m.")
    elif "catch" in reason_lower or ("load" in reason_lower and "ground" not in reason_lower and "fell" not in reason_lower):
        suggestions.append("-> ROOT CAUSE (capture): Engagement with the payload did not occur. The condition is geometric: some part of the structure must reach the load location within the allowed proximity.")
    elif "angle" in reason_lower or "exceeds" in reason_lower:
        suggestions.append("-> ROOT CAUSE (balance): The main beam exceeded the allowed angular deviation. A net moment about the pivot (from mass distribution and external forces) sets the angle.")
        if net_torque is not None and _is_finite_number(net_torque):
            suggestions.append(f"   Net torque about pivot at evaluation: {net_torque:+.2f} N·m.")
    elif "ground" in reason_lower or "fell" in reason_lower or "touched" in reason_lower:
        suggestions.append("-> ROOT CAUSE (grounding): A body crossed the vertical boundary. This typically follows large rotation or collapse from imbalance or joint failure.")
        if min_body_y is not None and ground_y_limit is not None and _is_finite_number(min_body_y) and _is_finite_number(ground_y_limit):
            suggestions.append(f"   Lowest body y = {min_body_y:.2f} m; ground limit y = {ground_y_limit:.1f} m.")

    return suggestions
