"""
Task-specific feedback generation for E-05: The Magnet.
Strictly audited to ensure all metrics are grounded in evaluator.py and limits are dynamic.
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Format task-specific metrics for E-05.
    All metrics are verified against evaluator.py.
    """
    metric_parts = []

    # 1. Operational Progress
    if "step_count" in metrics:
        metric_parts.append(f"**Step**: {metrics['step_count']}")
    if "progress_x" in metrics:
        metric_parts.append(f"**Progress**: {metrics['progress_x']*100:.1f}% Toward Final Corridor")
    if "dist_to_target" in metrics:
        metric_parts.append(f"**Range**: {metrics['dist_to_target']:.2f} m from target")

    # 2. Kinematic State
    if "body_x" in metrics and "body_y" in metrics:
        metric_parts.append(f"**Position**: ({metrics['body_x']:.2f}, {metrics['body_y']:.2f})")
    if "velocity_x" in metrics and "velocity_y" in metrics:
        vx, vy = metrics["velocity_x"], metrics["velocity_y"]
        metric_parts.append(f"**Velocity Vector**: ({vx:.2f}, {vy:.2f}) m/s")
    if "speed" in metrics:
        metric_parts.append(f"**Current Speed**: {metrics['speed']:.3f} m/s")

    # 3. Environment Interaction (Force Field Detection)
    if metrics.get("step_count", 0) > 0:
        metric_parts.append("\n**Environment Observation (Real-time Analysis)**:")
        speed = metrics.get("speed", 0)
        if speed < 0.1 and metrics.get("step_count", 0) > 50:
            metric_parts.append("- OBSERVED: Potential 'Local Minimum' detected. External force fields are likely canceling thrust or pinning the body.")
        elif speed > 5.0:
            metric_parts.append("- OBSERVED: High-gradient field detected. Rapid kinetic energy gain from invisible sources.")

    # 4. Failure Diagnostic
    if metrics.get("failed"):
        metric_parts.append("\n**Failure Diagnostic**:")
        if "pit zone" in metrics.get("failure_reason", "").lower():
            metric_parts.append("- FAILURE: Containment Failure. Body entered a forbidden pit region.")
        else:
            metric_parts.append("- FAILURE: Mission Timeout. Target not reached within operational window.")

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
    Diagnostic suggestions for E-05.
    Strictly describes physical phenomena without dictating design.
    """
    suggestions = []

    if error:
        suggestions.append(f"Design rejection: {error}")
        return suggestions

    if failed:
        x = metrics.get("body_x", 0)
        speed = metrics.get("speed", 0)

        # Spatial diagnosis
        if x < 15.0:
            suggestions.append("Navigation obstructed in the initial corridor. Invisible repulsive barriers may be present. Monitor x-coordinates where speed drops to zero.")
        elif x < 25.0:
            suggestions.append("Checkpoint cleared. However, the body is stalling in the central region. Use inertia and maximum thrust to overcome attractive traps.")

        if speed < 0.1:
            suggestions.append("System is stalled. Gravity and environmental repulsion are likely in equilibrium. Higher thrust magnitudes may be needed to escape local minima.")
        
        suggestions.append("Force field intensities are non-stationary. If a passage is blocked, maintain position and analyze the timing of velocity fluctuations to find 'open windows' in the barriers.")

    elif not success:
        suggestions.append("Terminal approach incomplete. The target zone is guarded by high-gradient repulsive fields. Focus on maintaining kinetic energy through the final corridor.")

    return suggestions
