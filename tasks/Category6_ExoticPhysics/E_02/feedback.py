"""
Task-specific feedback generation for E-02: Thick Air.
Strictly audited to ensure all metrics are grounded in evaluator.py and limits are dynamic.
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Format task-specific metrics for E-02.
    All metrics are verified against evaluator.py.
    """
    metric_parts = []

    # 1. Mission Progress
    if "progress_x" in metrics:
        metric_parts.append(f"**Horizontal Progress**: {metrics['progress_x']:.1f}% toward target")
    if "distance_to_target" in metrics:
        metric_parts.append(f"**Range to Target**: {metrics['distance_to_target']:.2f} m")

    # 2. Thermodynamic State (Heat-Thrust)
    if "heat" in metrics:
        heat = metrics["heat"]
        limit = metrics.get("overheat_limit", 1.0)
        metric_parts.append(f"**Heat Accumulation**: {heat:.1f} / {limit:.0f} N·s")
    if "heat_remaining" in metrics:
        metric_parts.append(f"**Heat Margin**: {metrics['heat_remaining']:.1f} N·s")

    # 3. Kinematic State
    if "craft_x" in metrics and "craft_y" in metrics:
        metric_parts.append(f"**Position**: ({metrics['craft_x']:.2f}, {metrics['craft_y']:.2f})")
    if "velocity_x" in metrics and "velocity_y" in metrics:
        vx, vy = metrics["velocity_x"], metrics["velocity_y"]
        metric_parts.append(f"**Velocity Vector**: ({vx:.2f}, {vy:.2f}) m/s")
    if "speed" in metrics:
        metric_parts.append(f"**Current Speed**: {metrics['speed']:.3f} m/s")

    # 4. Target analysis
    if all(k in metrics for k in ("target_x_min", "target_x_max", "target_y_min", "target_y_max")):
        tx_min, tx_max = metrics["target_x_min"], metrics["target_x_max"]
        ty_min, ty_max = metrics["target_y_min"], metrics["target_y_max"]
        metric_parts.append(f"**Target Zone**: x=[{tx_min:.1f}, {tx_max:.1f}], y=[{ty_min:.1f}, {ty_max:.1f}]")

    # 5. Failure Diagnostics
    if metrics.get("failed"):
        metric_parts.append("\n**Failure Diagnostic**:")
        if metrics.get("overheated"):
            metric_parts.append("- Thermal Limit: Propulsion system shutdown due to excessive heat.")
        elif not metrics.get("reached_target") and metrics.get("step_count", 0) > 0:
            metric_parts.append("- Temporal Exhaustion: Craft failed to reach target zone within operational time.")

    return metric_parts


def get_improvement_suggestions(
    metrics: Dict[str, Any],
    score: float,
    success: bool,
    failed: bool,
    failure_reason: str = None,
    error: str = None,
) -> List[str]:
    """
    Diagnostic suggestions for E-02.
    Strictly describes physical phenomena without dictating design.
    """
    suggestions = []

    if error:
        suggestions.append(f"Design rejection: {error}")
        return suggestions

    if failed:
        # Dynamic threshold based on heat capacity
        heat = metrics.get("heat", 0)
        limit = metrics.get("overheat_limit", 1)
        progress = metrics.get("progress_x", 0)

        if metrics.get("overheated"):
            if progress < 50:
                suggestions.append("The system is overheating before the midpoint. High fluid resistance at lower velocities consumes impulse inefficiently.")
            else:
                suggestions.append("Thermal exhaustion occurred during the final approach. Consider momentum-based transit to conserve thermal margin.")
            
            suggestions.append("Continuous thrust leads to rapid heat accumulation. Optimizing the thrust profile may improve distance-per-unit-heat.")

        elif not metrics.get("reached_target"):
            if heat < limit * 0.5:
                suggestions.append("Sufficient thermal margin remains. Higher thrust levels may be required to overcome environmental drag.")
            else:
                suggestions.append("Progress is hampered by localized drag or momentum drain zones. Map the coordinates where speed drops significantly.")

    elif not success:
        suggestions.append("The craft is moving but did not arrive. Refine the trajectory to minimize horizontal resistance.")

    return suggestions
