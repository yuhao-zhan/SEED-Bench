"""
Audited task-specific feedback for D-01: The Launcher
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Expose high-resolution physical metrics strictly from evaluator.py.
    """
    parts = []

    if "hit_occurred" in metrics:
        parts.append(f"**Target Hit**: {'Yes' if metrics['hit_occurred'] else 'No'}")
    
    if "progress" in metrics:
        parts.append(f"**Horizontal Progress**: {metrics['progress']:.1f}%")

    if "projectile_x" in metrics and "projectile_y" in metrics:
        parts.append(f"**Final Position**: (x: {metrics['projectile_x']:.2f} m, y: {metrics['projectile_y']:.2f} m)")

    if "projectile_speed" in metrics:
        parts.append(f"**Final Speed**: {metrics['projectile_speed']:.2f} m/s")

    if "max_y_in_target_x" in metrics and metrics["max_y_in_target_x"] is not None:
        parts.append(f"**Peak Altitude in Target Band**: {metrics['max_y_in_target_x']:.2f} m")

    if "structure_mass" in metrics:
        mass = metrics["structure_mass"]
        limit = metrics.get("max_structure_mass", float('inf'))
        parts.append(f"**Launcher Mass**: {mass:.2f} kg / {limit:.1f} kg")

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
    msg = (error or failure_reason or "").lower()

    # 1. Structural Diagnostics
    max_mass = metrics.get("max_structure_mass", float('inf'))
    if metrics.get("structure_mass", 0.0) > max_mass:
        suggestions.append("- **Mass Constraint Violation**: The launcher exceeds the maximum mass budget. Consider optimizing for a higher strength-to-weight ratio.")
    
    if "build zone" in msg:
        suggestions.append("- **Spatial Violation**: Components were detected outside the valid construction area.")

    # 2. Trajectory & Energy Diagnostics
    if failed or not success:
        px = metrics.get("projectile_x", 0.0)
        tx_min = metrics.get("target_x_min", 0.0)
        tx_max = metrics.get("target_x_max", 0.0)
        y_peak = metrics.get("max_y_in_target_x")
        ty_min = metrics.get("target_y_min", 0.0)
        ty_max = metrics.get("target_y_max", 0.0)

        if px < tx_min:
            suggestions.append("- **Energy Transfer Deficit**: The projectile failed to reach the required distance. Analyze the efficiency of energy storage or release.")
        elif px > tx_max:
            suggestions.append("- **Momentum Overshoot**: The projectile traveled beyond the target zone.")

        if y_peak is not None:
            if y_peak > ty_max:
                suggestions.append("- **Apex Elevation Violation**: The trajectory reached its peak above the target zone's vertical capture range.")
            elif y_peak < ty_min:
                suggestions.append("- **Insufficient Flight Loft**: The trajectory was too shallow to enter the target zone at the required height.")

    return suggestions
