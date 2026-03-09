"""
Task-specific feedback for D-03: Phase-Locked Gate.
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Format task-specific metrics for D-03: Phase-Locked Gate.
    Only uses keys guaranteed by the evaluator.
    """
    parts = []

    if "x" in metrics:
        parts.append(f"**Position (x)**: {metrics['x']:.2f} m")
    
    if "speed" in metrics:
        parts.append(f"**Velocity (Magnitude)**: {metrics['speed']:.3f} m/s")
    
    if "failure_reason" in metrics and metrics["failure_reason"]:
        parts.append(f"**Status Indicator**: {metrics['failure_reason']}")

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
    Generate diagnostic warnings for D-03: Phase-Locked Gate.
    """
    suggestions = []
    
    msg = (error or failure_reason or "").lower()

    # 1. Structural Failures (from parsing reason)
    if "mass" in msg:
        suggestions.append("- **Inertial Constraint**: The system mass exceeds the permissible threshold. Analyze the structural density.")
    if "beam count" in msg:
        suggestions.append("- **Component Configuration**: The number of beams is outside the valid range.")
    if "build zone" in msg:
        suggestions.append("- **Spatial Violation**: Components are placed outside the designated fabrication volume.")

    # 2. Performance Diagnostics
    if failed or not success:
        if "gate collision" in msg:
            suggestions.append("- **Synchronization Failure**: The vehicle arrived at the gate while it was closed. Analyze the timing of arrival (phase-locking).")
        
        elif "speed trap" in msg:
            suggestions.append("- **Impulse Management**: The vehicle velocity at the speed trap was outside the required range.")

        elif "final speed" in msg:
            suggestions.append("- **Terminal Momentum**: The vehicle reached the target but its final speed did not meet the specification.")

        elif "broken" in msg:
            suggestions.append("- **Structural Integrity**: A joint failed under load. Evaluate the distribution of stresses across the mechanism.")

    return suggestions
