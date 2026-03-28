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
    
    # Core State Variables (reported = sensor; true = grading state when evaluator provides it)
    if "pole_angle_deg" in metrics:
        line = (
            f"**Pole State**: Reported angle {metrics['pole_angle_deg']:.2f}° (Vertical = 0°), "
            f"reported ω {metrics.get('pole_angular_velocity', 0.0):.3f} rad/s"
        )
        if "pole_angle_true_deg" in metrics:
            line += (
                f"; **true (grading) angle** {metrics['pole_angle_true_deg']:.2f}°, "
                f"true ω {metrics.get('pole_angular_velocity_true', 0.0):.3f} rad/s"
            )
        metric_parts.append(line)
    
    if "cart_x" in metrics:
        metric_parts.append(f"**Cart State**: Position {metrics['cart_x']:.3f} m, Velocity {metrics.get('cart_velocity_x', 0.0):.3f} m/s")
    
    # Phase diagnostics: grading uses true angle; after lock-in, |angle| may exceed balance band until failure band.
    if "balance_achieved" in metrics:
        if not metrics["balance_achieved"]:
            phase = (
                f"Pre-lock-in: accumulate consecutive steps with |true angle| ≤ {bal_deg:.0f}° "
                "while staying on the track"
            )
        elif "pole_angle_true_deg" in metrics and abs(metrics["pole_angle_true_deg"]) > bal_deg:
            phase = (
                f"Post lock-in (true angle outside {bal_deg:.0f}° band; "
                f"still within mid-episode rules until |true angle| > {fail_deg:.0f}°)"
            )
        else:
            phase = "Balancing/Stability (hold terminal band through horizon)"
        metric_parts.append(f"- Active Control Objective: {phase}")
    
    # Boundary Proximity
    if "dist_from_center" in metrics and "safe_half_range" in metrics:
        metric_parts.append(f"- Track Displacement: {metrics['dist_from_center']:.3f} m (Safety limit: ±{metrics['safe_half_range']:.1f}m)")
    
    if "step_count" in metrics:
        metric_parts.append(f"- Mission Duration: {metrics['step_count']} steps")
    
    if metrics.get("failed") and metrics.get("failure_reason"):
        metric_parts.append(f"\n**Primary System Failure**: {metrics['failure_reason']}")
        
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
                f"stays within ±{bal_deg:.0f}° for long enough stretches while limiting cart excursion."
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
                f"focus on terminal-phase regulation to satisfy |angle| ≤ {bal_deg:.0f}° at the last step."
            )
            
        # 3. Lock-in not achieved while on track
        if not balance_achieved and (safe_range is None or dist_from_center <= safe_range):
            suggestions.append(
                "The pole is not staying in the upright grading band long enough for lock-in. "
                "Consider whether the plant dynamics or the relationship between observations and grading state differ from your model, "
                "and adjust gains or structure so the loop spends longer stretches inside the true-angle band."
            )

    return suggestions
