"""
Task-specific feedback for C-06: The Governor.
Suggestions stay generic so hidden physics (delay, deadzone, cogging, etc.) are not leaked.
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """Format high-resolution physical metrics for C-06."""
    metric_parts = []

    if "wheel_angular_velocity" in metrics:
        metric_parts.append(
            f"**Rotational State**: Speed {metrics['wheel_angular_velocity']:.3f} rad/s, "
            f"Reference Target {metrics.get('target_speed', 0.0):.3f} rad/s"
        )

    if "mean_speed_error" in metrics:
        metric_parts.append(
            f"**Regulation (mean |ω_true − target| over regulation phase only; same metric as grading)**: "
            f"{metrics['mean_speed_error']:.4f} rad/s"
        )

    metric_parts.append("\n**Operational Stability Profile**")
    if "stall_count" in metrics:
        metric_parts.append(f"- Stall Counter: {metrics['stall_count']} consecutive steps")
    if "stall_speed_threshold" in metrics:
        metric_parts.append(
            f"- Critical Velocity Threshold: {metrics['stall_speed_threshold']:.2f} rad/s"
        )

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
    """Generic diagnostics only; no hidden-mechanism spoilers."""
    suggestions = []

    if error:
        return [
            f"System Error: {error}. Check documented wheel and motor APIs (target speed, angular velocity, torque)."
        ]

    if failed:
        reason = (failure_reason or "").lower()
        if "stall" in reason:
            suggestions.append(
                "Stall failure: increase drive authority or adjust control so the wheel recovers from low speed."
            )
        elif "regulation" in reason:
            suggestions.append(
                "Regulation failure: reduce tracking error vs. the queried target over the full regulation phase "
                "(tune gains, account for unmodeled dynamics, and re-check the target each step)."
            )
        else:
            suggestions.append(
                "Task failed; compare measured wheel speed to the current target and revise the control loop."
            )
    elif success:
        suggestions.append("Success: controller met stall and mean-error criteria for this run.")

    return suggestions
