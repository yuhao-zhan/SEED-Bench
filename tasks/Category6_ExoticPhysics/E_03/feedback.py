"""
Task-specific feedback generation for E-03: Slippery World.
Returns physical metrics (position, velocity, distance to target, progress) for process and result feedback.
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """Format task-specific metrics for E-03 (S_01-style: process and result physical metrics)."""
    metric_parts = []

    if "step_count" in metrics:
        metric_parts.append(f"**Simulation steps**: {metrics['step_count']}")
    if "sled_x" in metrics:
        metric_parts.append(f"**Sled position**: x={metrics['sled_x']:.2f}m, y={metrics.get('sled_y', 0):.2f}m")
    if "target_x_min" in metrics:
        metric_parts.append(
            f"**Target zone**: x=[{metrics.get('target_x_min', 28):.0f}, {metrics.get('target_x_max', 32):.0f}], "
            f"y=[{metrics.get('target_y_min', 2):.0f}, {metrics.get('target_y_max', 5):.0f}] m"
        )
    if "progress_pct" in metrics:
        metric_parts.append(f"**Progress (x toward target)**: {metrics['progress_pct']:.1f}%")
    if "distance_to_target" in metrics:
        metric_parts.append(f"**Distance to target zone**: {metrics['distance_to_target']:.2f} m")
    if "checkpoint_a_reached" in metrics:
        metric_parts.append(f"**Checkpoint A (first intermediate zone) reached**: {'YES' if metrics['checkpoint_a_reached'] else 'NO'}")
    if "checkpoint_b_reached" in metrics:
        metric_parts.append(f"**Checkpoint B (second intermediate zone) reached**: {'YES' if metrics['checkpoint_b_reached'] else 'NO'}")
    if "checkpoint_reached" in metrics:
        metric_parts.append(f"**All checkpoints reached (sequence satisfied)**: {'YES' if metrics['checkpoint_reached'] else 'NO'}")
    if "reached_target" in metrics:
        metric_parts.append(f"**Final target zone reached**: {'YES' if metrics['reached_target'] else 'NO'}")
    if "velocity_x" in metrics:
        vx, vy = metrics.get("velocity_x", 0), metrics.get("velocity_y", 0)
        metric_parts.append(f"**Sled velocity**: vx={vx:.2f} m/s, vy={vy:.2f} m/s")
    if "velocity_magnitude" in metrics:
        metric_parts.append(f"**Sled speed**: {metrics['velocity_magnitude']:.2f} m/s")

    # Physical state block for fine-grained debugging (like S_01)
    if "sled_x" in metrics or "velocity_x" in metrics or "distance_to_target" in metrics:
        metric_parts.append("\n**Physical State Information**:")
        if "sled_x" in metrics and "sled_y" in metrics:
            metric_parts.append(f"- Sled position: ({metrics['sled_x']:.3f}, {metrics['sled_y']:.3f}) m")
        if "velocity_x" in metrics and "velocity_y" in metrics:
            metric_parts.append(f"- Sled velocity: vx={metrics['velocity_x']:.3f} m/s, vy={metrics['velocity_y']:.3f} m/s")
        if "velocity_magnitude" in metrics:
            metric_parts.append(f"- Speed: {metrics['velocity_magnitude']:.3f} m/s")
        if "distance_to_target" in metrics:
            metric_parts.append(f"- Distance to target zone: {metrics['distance_to_target']:.3f} m")
        if "progress_pct" in metrics:
            metric_parts.append(f"- Progress: {metrics['progress_pct']:.1f}%")

    excluded = {
        "step_count", "sled_x", "sled_y", "target_x_min", "target_x_max",
        "target_y_min", "target_y_max", "checkpoint_a_reached", "checkpoint_b_reached",
        "checkpoint_reached", "reached_target",
        "velocity_x", "velocity_y", "velocity_magnitude", "distance_to_target", "progress_pct",
        "success", "failed", "failure_reason",
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
    """Generate task-specific improvement suggestions for E-03."""
    suggestions = []

    if error:
        err_lower = error.lower()
        if "sled" in err_lower or "target" in err_lower:
            suggestions.append("Ensure you call apply_thrust(fx, fy) each step to move the sled (friction cannot provide traction).")

    elif failed:
        if failure_reason and "cannot get traction" in failure_reason.lower():
            suggestions.append("Friction is near zero; the sled cannot move by sliding or rolling alone.")
            suggestions.append("Use reaction-force thrust: call apply_thrust(fx, fy) every step toward the target (x in [28, 32], y in [2, 5]).")
            suggestions.append("Use get_sled_position() and get_sled_velocity() to steer efficiently.")

    elif not success:
        suggestions.append("Apply thrust consistently toward the target zone until the sled center enters it.")

    return suggestions
