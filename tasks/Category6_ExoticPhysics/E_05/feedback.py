"""
Task-specific feedback generation for E-05: The Magnet.
Returns rich physical metrics for process and result analysis (reference: S_01).
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """Format task-specific metrics for E-05 with comprehensive physical feedback."""
    metric_parts = []

    # Position and target (always show if available)
    if "body_x" in metrics:
        body_y = metrics.get("body_y", 0)
        metric_parts.append(f"**Body position**: x={metrics['body_x']:.2f}m, y={body_y:.2f}m")
        if "target_x_min" in metrics:
            tx_min = metrics.get('target_x_min', 28.0)
            tx_max = metrics.get('target_x_max', 32.0)
            ty_min = metrics.get('target_y_min', 6.0)
            ty_max = metrics.get('target_y_max', 9.0)
            metric_parts.append(
                f"**Target zone**: x=[{tx_min:.1f}, {tx_max:.1f}], "
                f"y=[{ty_min:.1f}, {ty_max:.1f}] m"
            )
        if "progress_x" in metrics:
            metric_parts.append(f"**Horizontal progress**: {metrics['progress_x']*100:.1f}%")
    elif "target_x_min" in metrics:
        metric_parts.append(
            f"**Target zone**: x=[{metrics.get('target_x_min', 28):.0f}, {metrics.get('target_x_max', 32):.0f}], "
            f"y=[{metrics.get('target_y_min', 6):.0f}, {metrics.get('target_y_max', 9):.0f}] m"
        )

    # Result status
    if "reached_target" in metrics:
        metric_parts.append(f"**Reached target**: {'YES' if metrics['reached_target'] else 'NO'}")
    if "in_target_x" in metrics and "in_target_y" in metrics:
        metric_parts.append(
            f"**In target X range**: {'YES' if metrics['in_target_x'] else 'NO'}, "
            f"**In target Y range**: {'YES' if metrics['in_target_y'] else 'NO'}"
        )

    # Velocity and speed
    if "velocity_x" in metrics:
        vx, vy = metrics.get("velocity_x", 0), metrics.get("velocity_y", 0)
        metric_parts.append(f"**Body velocity**: vx={vx:.3f} m/s, vy={vy:.3f} m/s")
    if "speed" in metrics:
        metric_parts.append(f"**Speed magnitude**: {metrics['speed']:.3f} m/s")

    # Distance to target (diagnostic when not reached)
    if "dist_to_target" in metrics and not metrics.get("reached_target", True):
        metric_parts.append(f"**Distance to target zone**: {metrics['dist_to_target']:.3f} m")

    # Simulation steps
    if "step_count" in metrics:
        metric_parts.append(f"**Simulation steps**: {metrics['step_count']}")

    # Physical state for fine-grained debugging (similar to S_01)
    if "body_x" in metrics or "velocity_x" in metrics:
        metric_parts.append("\n**Physical State Information**:")
        if "body_x" in metrics and "body_y" in metrics:
            metric_parts.append(f"- Body position: ({metrics['body_x']:.3f}, {metrics['body_y']:.3f}) m")
        if "velocity_x" in metrics and "velocity_y" in metrics:
            metric_parts.append(
                f"- Velocity components: vx={metrics['velocity_x']:.3f} m/s, vy={metrics['velocity_y']:.3f} m/s"
            )
        if "speed" in metrics:
            metric_parts.append(f"- Speed: {metrics['speed']:.3f} m/s")
        if "start_x" in metrics and "start_y" in metrics:
            metric_parts.append(f"- Start position: ({metrics['start_x']:.1f}, {metrics['start_y']:.1f}) m")

    excluded = {
        "step_count", "body_x", "body_y", "target_x_min", "target_x_max",
        "target_y_min", "target_y_max", "reached_target", "velocity_x", "velocity_y",
        "success", "failed", "failure_reason", "speed", "progress_x", "dist_to_target",
        "in_target_x", "in_target_y", "start_x", "start_y",
    }
    other = {k: v for k, v in metrics.items() if k not in excluded}
    if other:
        metric_parts.append("\n**Additional metrics**:")
        for k, v in other.items():
            if isinstance(v, float):
                metric_parts.append(f"- {k}: {v:.3f}")
            else:
                metric_parts.append(f"- {k}: {v}")

    return metric_parts


def get_improvement_suggestions(
    metrics: Dict[str, Any],
    score: float,
    success: bool,
    failed: bool,
    failure_reason: str = None,
    error: str = None,
) -> List[str]:
    """Generate task-specific improvement suggestions for E-05."""
    suggestions = []

    if error:
        err_lower = error.lower()
        if "body" in err_lower or "target" in err_lower:
            suggestions.append("Ensure you call apply_thrust(fx, fy) each step to move the body toward the target zone.")

    elif failed:
        if failure_reason and "local minimum" in failure_reason.lower():
            tx_min = metrics.get('target_x_min', 28.0)
            tx_max = metrics.get('target_x_max', 32.0)
            ty_min = metrics.get('target_y_min', 6.0)
            ty_max = metrics.get('target_y_max', 9.0)
            suggestions.append("Invisible force fields can trap the body; try different thrust directions or paths.")
            suggestions.append("Use get_body_position() and get_body_velocity() to detect when progress stalls and adjust thrust.")
            suggestions.append(f"Target zone is x in [{tx_min:.1f}, {tx_max:.1f}], y in [{ty_min:.1f}, {ty_max:.1f}]; plan a path that may need to go around repulsive regions.")

    elif not success:
        tx_min = metrics.get('target_x_min', 28.0)
        tx_max = metrics.get('target_x_max', 32.0)
        ty_min = metrics.get('target_y_min', 6.0)
        ty_max = metrics.get('target_y_max', 9.0)
        suggestions.append(f"Adjust thrust to navigate the force field and reach the target zone (x in [{tx_min:.1f}, {tx_max:.1f}], y in [{ty_min:.1f}, {ty_max:.1f}]).")

    return suggestions
