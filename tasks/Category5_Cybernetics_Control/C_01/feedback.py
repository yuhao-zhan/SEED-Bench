"""
Task-specific feedback for C-01: Cart-Pole Swing-up then Balance.
Purified version: strictly grounded in evaluator metrics.
"""
from typing import Dict, Any, List

def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """Format high-resolution physical metrics for C-01."""
    metric_parts = []
    
    if "pole_angle_deg" in metrics:
        metric_parts.append(f"**Pole Angle**: {metrics['pole_angle_deg']:.2f}° (Vertical = 0°)")
    if "pole_angular_velocity" in metrics:
        metric_parts.append(f"**Angular Velocity**: {metrics['pole_angular_velocity']:.3f} rad/s")
    if "cart_x" in metrics:
        metric_parts.append(f"**Cart Position (x)**: {metrics['cart_x']:.3f} m")
    if "cart_velocity_x" in metrics:
        metric_parts.append(f"**Cart Velocity (vx)**: {metrics['cart_velocity_x']:.3f} m/s")
    
    metric_parts.append("\n**Task Progress**")
    if "balance_achieved" in metrics:
        metric_parts.append(f"- Upright Region Reached: {metrics['balance_achieved']}")
    if "dist_from_center" in metrics:
        metric_parts.append(f"- Displacement from Track Center: {metrics['dist_from_center']:.3f} m")
    if "safe_half_range" in metrics:
        metric_parts.append(f"- Track Limit Boundary: ±{metrics.get('safe_half_range', 'N/A')} m")
    if "step_count" in metrics:
        metric_parts.append(f"- Total Steps: {metrics['step_count']}")
    
    if metrics.get("failed") and metrics.get("failure_reason"):
        metric_parts.append(f"\n**Primary Failure Event**: {metrics['failure_reason']}")
        
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
    
    if error:
        return [f"System Error: {error}. Check API usage."]

    if not failed and not success:
        if not metrics.get("balance_achieved", False):
            suggestions.append("The system timed out before the pole reached the upright region. Analyze the impulse phase to ensure sufficient energy is injected for swing-up.")
        else:
            suggestions.append("The system reached the upright region but failed to hold stability until the end. Verify the transition between impulse-based and balancing control.")

    if failed:
        balance_achieved = metrics.get("balance_achieved", False)
        cart_x = metrics.get("cart_x", 0)
        safe_range = metrics.get("safe_half_range", 8.5)
        track_center = metrics.get("track_center_x", 10.0)
        
        # 1. Boundary Violation
        if abs(cart_x - track_center) > safe_range:
            suggestions.append("The cart exceeded the track limits. This indicates the swing-up impulse or correction forces exceeded the spatial displacement budget.")
            
        # 2. Stability Failure
        if balance_achieved and "upright" in (failure_reason or "").lower():
            suggestions.append("The pole reached the balance zone but was not maintained. This suggests insufficient damping or high entry velocity upon reaching the upright region.")
            
        # 3. Energy Transfer Failure
        if not balance_achieved and abs(cart_x - track_center) <= safe_range:
            suggestions.append("The pole failed to reach vertical within the track limits. Optimize the timing and phase of cart acceleration to improve energy transfer to the pole.")

    return suggestions
