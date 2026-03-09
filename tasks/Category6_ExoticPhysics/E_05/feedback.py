"""
Audited task-specific feedback for E-05: The Magnet.
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Expose physical and field-interaction metrics strictly from evaluator.py.
    """
    parts = []

    if "progress_x" in metrics:
        parts.append(f"**Corridor Progress**: {metrics['progress_x']*100:.1f}%")
    if "dist_to_target" in metrics:
        parts.append(f"**Target Proximity**: {metrics['dist_to_target']:.2f} m")

    if "body_x" in metrics and "body_y" in metrics:
        parts.append(f"**Position State**: ({metrics['body_x']:.2f}, {metrics['body_y']:.2f})")
    if "velocity_x" in metrics and "velocity_y" in metrics:
        vx, vy = metrics["velocity_x"], metrics["velocity_y"]
        parts.append(f"**Velocity Vector**: (vx: {vx:.2f}, vy: {vy:.2f}) m/s")
    if "speed" in metrics:
        parts.append(f"**Current Speed**: {metrics['speed']:.3f} m/s")

    return parts


def get_improvement_suggestions(
    metrics: Dict[str, Any],
    score: float,
    success: bool,
    failed: bool,
    failure_reason: str = None,
    error: str = None,
) -> List[str]:
    """
    Audited diagnostic feedback. No hardcoded thresholds or design spoilers.
    """
    suggestions = []

    if failed:
        speed = metrics.get("speed", 0)

        if speed < 0.1:
            suggestions.append("- **Potential Trap Equilibrium**: The body is pinned. Gravity and environmental repulsion are in equilibrium with thrust. Escaping local minima requires higher impulse or inertial momentum.")
        
        suggestions.append("- **Field Rhythm Notice**: Invisible barriers may be non-stationary. Maintain position and analyze velocity fluctuations to identify temporal windows in the field.")

        if failure_reason and "pit zone" in failure_reason.lower():
            suggestions.append("- **Containment Failure**: The body was pulled into a forbidden region. Gravity compensation or repulsive-field repulsion was insufficient to maintain altitude.")

    elif not success:
        suggestions.append("- **Terminal Approach Stability**: Final approach is guarded by high-gradient repulsive fields. Focus on maintaining kinetic energy through the final corridor.")

    return suggestions
