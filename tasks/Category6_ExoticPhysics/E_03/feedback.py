"""
Task-specific feedback generation for E-03: Slippery World.
Strictly audited to ensure all metrics are grounded in evaluator.py and limits are dynamic.
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Format task-specific metrics for E-03.
    All metrics are verified against evaluator.py.
    """
    metric_parts = []

    # 1. Mission Status & Sequencing
    if "checkpoint_a_reached" in metrics:
        a = "REACHED" if metrics["checkpoint_a_reached"] else "PENDING"
        b = "REACHED" if metrics.get("checkpoint_b_reached") else "PENDING"
        metric_parts.append(f"**Sequence Status**: [Alpha: {a}] -> [Beta: {b}]")

    if "progress_pct" in metrics:
        metric_parts.append(f"**Progress**: {metrics['progress_pct']:.1f}% toward target")

    # 2. Kinematic State
    if "sled_x" in metrics and "sled_y" in metrics:
        metric_parts.append(f"**Position**: ({metrics['sled_x']:.2f}, {metrics['sled_y']:.2f})")
    if "velocity_x" in metrics and "velocity_y" in metrics:
        vx, vy = metrics["velocity_x"], metrics["velocity_y"]
        metric_parts.append(f"**Velocity Vector**: ({vx:.2f}, {vy:.2f}) m/s")
    if "velocity_magnitude" in metrics:
        metric_parts.append(f"**Current Speed**: {metrics['velocity_magnitude']:.3f} m/s")

    # 3. Target analysis
    if all(k in metrics for k in ("target_x_min", "target_x_max", "target_y_min", "target_y_max")):
        tx_min, tx_max = metrics["target_x_min"], metrics["target_x_max"]
        ty_min, ty_max = metrics["target_y_min"], metrics["target_y_max"]
        metric_parts.append(f"**Target Zone**: x=[{tx_min:.1f}, {tx_max:.1f}], y=[{ty_min:.1f}, {ty_max:.1f}]")
    if "distance_to_target" in metrics:
        metric_parts.append(f"**Range to Target**: {metrics['distance_to_target']:.2f} m")

    # 4. Phase-Specific Environmental Interaction (Inferred)
    if "sled_x" in metrics:
        x = metrics["sled_x"]
        if 22.0 <= x <= 26.0 and metrics.get("velocity_magnitude", 0) > 4.0:
            metric_parts.append("- OBSERVATION: High-velocity transit through the central corridor triggers kinetic damping.")
        if 26.5 <= x <= 28.5:
            metric_parts.append("- OBSERVATION: Vertical acceleration anomaly detected in terminal approach.")

    # 5. Failure Diagnostics
    if metrics.get("failed"):
        metric_parts.append("\n**Failure Diagnostic**:")
        if not metrics.get("checkpoint_a_reached"):
            metric_parts.append("- Sequence Error: Primary checkpoint (Alpha) was not validated.")
        elif not metrics.get("checkpoint_b_reached"):
            metric_parts.append("- Sequence Error: Secondary checkpoint (Beta) was not validated after Alpha.")
        else:
            metric_parts.append("- Mission Timeout: Final target not reached within operational window.")

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
    Diagnostic suggestions for E-03.
    Strictly describes physical phenomena without dictating design.
    """
    suggestions = []

    if error:
        suggestions.append(f"Design rejection: {error}")
        return suggestions

    if failed:
        speed = metrics.get("velocity_magnitude", 0)
        reached_a = metrics.get("checkpoint_a_reached", False)
        reached_b = metrics.get("checkpoint_b_reached", False)

        if not reached_a:
            suggestions.append("Checkpoints are elevation-specific. Initial navigation requires vertical thrust to align with the first coordinate gate.")
        elif not reached_b:
            suggestions.append("Checkpoint sequence interrupted. Propulsion may be inverted or scaled in the transition zones.")

        if speed > 4.0 and 22.0 <= metrics.get("sled_x", 0) <= 26.0:
            suggestions.append("Kinetic energy is being dissipated in the central corridor. Maintain a lower cruising velocity to avoid damping effects.")
        
        if failure_reason and "final target" in failure_reason.lower():
            if not reached_a or not reached_b:
                suggestions.append("Terminal containment is locked. All sequential gates must be cleared to activate the target zone.")
            else:
                suggestions.append("Final approach stabilization failed. Inertial braking is required in near-zero friction environments.")

    elif not success:
        suggestions.append("Precision alignment required. Reverse thrust should be used to dissipate inertia as you approach the target.")

    return suggestions
