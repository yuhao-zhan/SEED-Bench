"""
Task-specific feedback generation for D-01: The Launcher
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Format task-specific metrics for D-01: The Launcher.
    Exposes metrics directly from the evaluator.
    """
    parts = []

    if "hit_occurred" in metrics:
        parts.append(f"**Target Hit**: {'Yes' if metrics['hit_occurred'] else 'No'}")
    
    if "progress" in metrics:
        parts.append(f"**Horizontal Progress**: {metrics['progress']:.1f}%")
    
    if "projectile_x" in metrics and "projectile_y" in metrics:
        parts.append(f"**Final Position**: x={metrics['projectile_x']:.2f} m, y={metrics['projectile_y']:.2f} m")

    if "projectile_speed" in metrics:
        parts.append(f"**Projectile Speed**: {metrics['projectile_speed']:.2f} m/s")

    if "structure_mass" in metrics:
        mass = metrics["structure_mass"]
        limit = metrics.get("max_structure_mass", 0.0)
        parts.append(f"**Launcher Mass**: {mass:.2f} kg (Limit: {limit:.1f} kg)")

    if "max_y_in_target_x" in metrics and metrics["max_y_in_target_x"] is not None:
        parts.append(f"**Peak Altitude in Target Band**: {metrics['max_y_in_target_x']:.2f} m")

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
    Generate diagnostic warnings for D-01: The Launcher.
    """
    suggestions = []
    
    msg = (error or failure_reason or "").lower()

    # 1. Structural Failures
    if "mass" in msg:
        suggestions.append("- **Mass Constraint**: The launcher exceeds the maximum mass limit. Analyze the design for high-density components.")
    if "build zone" in msg:
        suggestions.append("- **Spatial Violation**: Components are placed outside the designated build area.")

    # 2. Performance Diagnostics
    if failed or not success:
        px = metrics.get("projectile_x", 0.0)
        tx_min = metrics.get("target_x_min", 0.0)
        y_peak = metrics.get("max_y_in_target_x")
        ty_min = metrics.get("target_y_min", 0.0)
        ty_max = metrics.get("target_y_max", 0.0)

        if px < tx_min:
            suggestions.append("- **Energy Deficit**: The projectile failed to reach the target distance. Consider the efficiency of energy transfer to the projectile.")
        
        if y_peak is not None:
            if y_peak > ty_max:
                suggestions.append("- **Trajectory Overshoot**: The projectile altitude exceeded the target zone's upper boundary during transit.")
            elif y_peak < ty_min:
                suggestions.append("- **Insufficient Loft**: The projectile altitude was below the target zone's entry threshold.")

    return suggestions
