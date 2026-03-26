"""
Task-specific feedback for C-01: Cart-pole balance (upright start).
"""
from typing import Dict, Any, List
import math

from .evaluator import BALANCE_ANGLE_DEG, FAILURE_ANGLE_DEG

def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """Format high-resolution physical metrics for C-01."""
    bal_deg = float(metrics.get("grading_balance_angle_deg", BALANCE_ANGLE_DEG))
    fail_deg = float(metrics.get("grading_failure_angle_deg", FAILURE_ANGLE_DEG))
    metric_parts = []
    
    # Timeline
    step = metrics.get("step_count", 0)
    metric_parts.append(f"- Mission Duration: {step} steps")
    
    # Pole State
    if "pole_angle_true_deg" in metrics:
        p_true = metrics['pole_angle_true_deg']
        p_peak = metrics.get('peak_pole_angle_deg', 0.0)
        line = (
            f"- Pole State: True Angle {p_true:.2f}° (Peak |Angle|: {p_peak:.2f}°). "
            f"Stability threshold: ≤{bal_deg:g}°."
        )
        metric_parts.append(line)
    
    # Boundary Proximity
    dist = metrics.get("dist_from_center", 0.0)
    safe = metrics.get("safe_half_range", 8.5)
    margin = safe - dist
    metric_parts.append(f"- Track Health: {dist:.3f}m from center (Margin to fail-zone: {margin:.3f}m)")

    # Failure Mode
    if metrics.get("failed") and metrics.get("failure_reason"):
        reason = metrics.get("failure_reason")
        metric_parts.append(f"**Failure Event (Step {step})**: {reason}")
    elif metrics.get("success"):
        metric_parts.append("**Status**: Task Success")
    else:
        metric_parts.append("**Status**: Active (Balancing Lock-in: " + ("Achieved" if metrics.get("balance_achieved") else "Pending") + ")")
        
    return metric_parts

def get_improvement_suggestions(
    metrics: Dict[str, Any],
    score: float,
    success: bool,
    failed: bool,
    failure_reason: str = None,
    error: str = None,
) -> List[str]:
    """Generate diagnostic suggestions based on grounded physical failure modes."""
    suggestions = []
    bal_deg = float(metrics.get("grading_balance_angle_deg", BALANCE_ANGLE_DEG))

    if error:
        return [f"System Error: {error}. Check API usage."]

    safe_range = metrics.get("safe_half_range")
    dist_from_center = metrics.get("dist_from_center", 0.0)
    balance_achieved = metrics.get("balance_achieved", False)

    if not failed and not success:
        if not balance_achieved:
            suggestions.append(
                "The consecutive in-band upright requirement has not been met. Check that the true pole angle "
                f"stays within ±{bal_deg:g}° for long enough stretches while limiting cart excursion."
            )
        else:
            suggestions.append("Long-term stability was not maintained. This indicates a potential mismatch between the controller's response frequency and the system's natural oscillations.")

    if failed:
        # 1. Boundary vs Stability Root-Cause
        if safe_range is not None and dist_from_center > safe_range:
            if not balance_achieved:
                suggestions.append(
                    "Cart motion exceeded the safe track half-range before balance lock-in. "
                    "Reduce lateral excursions while keeping the pole within the upright grading band."
                )
            else:
                suggestions.append("The stabilization phase is inducing horizontal drift. Ensure the balancing loop accounts for the cart's displacement from the track center.")
            
        # 2a. Pole fell past horizontal after lock-in
        fr = (failure_reason or "").lower()
        if balance_achieved and (
            "fell after balancing" in fr or "pole fell" in fr
        ):
            suggestions.append(
                "The pole reached the balance zone but was lost due to excessive entry momentum or uncompensated disturbances. "
                "Compare reported versus true (grading) state in the metrics and revisit how your controller uses the available observations."
            )
        # 2b. Horizon ended while not in upright band (do not blame latency on substring "upright")
        elif balance_achieved and "pole not in upright region at end" in fr:
            suggestions.append(
                f"Balance lock-in occurred earlier, but the true pole angle was outside the upright band when the episode ended; "
                f"focus on terminal-phase regulation to satisfy |angle| ≤ {bal_deg:g}° at the last step."
            )
            
        # 3. Lock-in not achieved while on track
        if not balance_achieved and (safe_range is None or dist_from_center <= safe_range):
            suggestions.append(
                "The pole is not staying in the upright grading band long enough for lock-in. "
                "Consider whether the plant dynamics or the relationship between observations and grading state differ from your model, "
                "and adjust gains or structure so the loop spends longer stretches inside the true-angle band."
            )

    return suggestions
