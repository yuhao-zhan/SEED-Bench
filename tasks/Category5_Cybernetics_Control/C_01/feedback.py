"""
Task-specific feedback for C-01: Cart-Pole Swing-up then Balance.
Hints at swing-up vs balance phase and upright threshold without giving exact formulas.
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """Format task-specific metrics for C-01 Swing-up then Balance."""
    metric_parts = []

    if "pole_angle_deg" in metrics:
        metric_parts.append(f"**Pole angle**: {metrics['pole_angle_deg']:.2f}° (upright region ±45°)")
    if "pole_angle_rad" in metrics:
        metric_parts.append(f"**Pole angle (rad)**: {metrics['pole_angle_rad']:.3f}")
    if "step_count" in metrics:
        metric_parts.append(f"**Simulation steps**: {metrics['step_count']}")
    if "success" in metrics:
        metric_parts.append(f"**Success**: {metrics['success']}")
    if "balance_achieved" in metrics:
        metric_parts.append(f"**Upright region reached**: {metrics['balance_achieved']}")
    if "failed" in metrics and metrics["failed"] and metrics.get("failure_reason"):
        metric_parts.append(f"**Failure reason**: {metrics['failure_reason']}")

    metric_parts.append("\n**Physical State (final)**")
    if "cart_x" in metrics:
        metric_parts.append(f"- Cart position (x): {metrics['cart_x']:.3f} m")
    if "track_center_x" in metrics and "cart_x" in metrics:
        d = abs(metrics["cart_x"] - metrics["track_center_x"])
        metric_parts.append(f"- Distance from track center: {d:.3f} m")
    if "safe_half_range" in metrics:
        metric_parts.append(f"- Safe zone half-width: ±{metrics['safe_half_range']:.1f} m from center")
    if "cart_velocity_x" in metrics:
        metric_parts.append(f"- Cart velocity (x): {metrics['cart_velocity_x']:.3f} m/s")
    if "pole_angular_velocity" in metrics:
        metric_parts.append(f"- Pole angular velocity: {metrics['pole_angular_velocity']:.3f} rad/s")
    if "pole_angle_deg" in metrics:
        metric_parts.append(f"- Deviation from vertical: |angle| = {abs(metrics['pole_angle_deg']):.2f}°")

    if "score" in metrics:
        metric_parts.append(f"\n**Score**: {metrics.get('score', 0):.1f}/100")
    metric_parts.append("- Task: reach upright region and hold; cart within safe zone.")

    return metric_parts


def get_improvement_suggestions(
    metrics: Dict[str, Any],
    score: float,
    success: bool,
    failed: bool,
    failure_reason: str = None,
    error: str = None,
) -> List[str]:
    """Suggestions for C-01 Swing-up then Balance."""
    suggestions = []

    if error:
        error_lower = error.lower()
        if "apply_cart_force" in error_lower or "sandbox" in error_lower:
            suggestions.append("- Use only the provided API: get_pole_angle(), get_cart_position(), get_cart_velocity(), get_pole_angular_velocity(), apply_cart_force(force_x)")
        elif "attribute" in error_lower:
            suggestions.append("- Check that you are calling methods on the sandbox (environment) object correctly")

    elif failed:
        balance_achieved = metrics.get("balance_achieved", False)
        if failure_reason and "upright" in failure_reason.lower() and "left" in failure_reason.lower():
            suggestions.append("- The pole left the upright region after having reached it. You must switch from swing-up to a balancing controller once the pole is near vertical, and keep the pole in the upright region.")
            suggestions.append("- Use angle and angular velocity to detect when the pole is near upright; then apply a stabilizing (e.g. PD) control instead of swing-up actuation.")
        elif failure_reason and "safe zone" in failure_reason.lower():
            cart_x = metrics.get("cart_x", 0)
            center = metrics.get("track_center_x", 10.0)
            suggestions.append("- Cart left the allowed zone. During swing-up, keep the cart within the safe zone; use get_cart_position() and a position-restoring term.")
            suggestions.append(f"- Last cart position was x={cart_x:.2f} m (track center at {center:.1f} m).")
        elif not balance_achieved:
            suggestions.append("- The pole never reached the upright region. If the pole starts hanging down, you must inject energy by moving the cart in phase with the swing. If it starts upright, ensure your balance controller catches it immediately.")
            suggestions.append("- For swing-up: consider a two-phase strategy. First, an energy-based or bang-bang phase to bring the pole near vertical, then switch to a stabilizing (e.g., PD) controller when the angle is small.")
        else:
            suggestions.append("- Reach the upright region and hold; keep the cart within the safe zone. Use feedback (balance_achieved, pole angle) to refine swing-up and balance logic.")

    elif not success:
        suggestions.append("- Ensure you first swing the pole to upright, then hold it there. Use angle and angular velocity to decide when to switch from swing-up to balance.")
        suggestions.append("- Keep the cart within the safe zone during both swing-up and balance.")

    return suggestions
