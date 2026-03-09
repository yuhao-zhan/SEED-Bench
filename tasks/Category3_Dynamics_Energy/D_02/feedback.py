"""
Audited task-specific feedback for D-02: The Jumper
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Expose high-resolution physical metrics strictly from evaluator.py.
    """
    parts = []

    if "landed" in metrics:
        parts.append(f"**Landed Successfully**: {'Yes' if metrics['landed'] else 'No'}")
    
    if "progress" in metrics:
        parts.append(f"**Jump Progress**: {metrics['progress']:.1f}%")

    if "jumper_x" in metrics and "jumper_y" in metrics:
        parts.append(f"**Final Jumper State**: (x: {metrics['jumper_x']:.2f} m, y: {metrics['jumper_y']:.2f} m)")

    if "jumper_speed" in metrics:
        parts.append(f"**Final Speed**: {metrics['jumper_speed']:.2f} m/s")

    if "angle" in metrics:
        parts.append(f"**Orientation**: {metrics['angle']:.2f} rad")

    if "angular_velocity" in metrics:
        parts.append(f"**Angular Velocity**: {metrics['angular_velocity']:.2f} rad/s")

    if "structure_mass" in metrics:
        mass = metrics["structure_mass"]
        limit = metrics.get("max_structure_mass", float('inf'))
        parts.append(f"**Structure Mass**: {mass:.2f} kg / {limit:.1f} kg")

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
        suggestions.append("- **Mass Constraint Violation**: The structure's mass budget is exceeded. Consider structural minimalism.")

    if "build zone" in msg:
        suggestions.append("- **Spatial Violation**: Components were detected outside the valid construction area.")

    # 2. Performance Diagnostics
    if failed or not success:
        px = metrics.get("jumper_x", 0.0)
        py = metrics.get("jumper_y", 0.0)
        target_x = metrics.get("right_platform_start_x", 0.0)
        pit_y = metrics.get("pit_fail_y", 0.0)

        if px < target_x:
            suggestions.append("- **Horizontal Momentum Deficit**: The jumper failed to clear the gap. Analyze the horizontal component of the launch impulse.")
        
        if py < pit_y:
            suggestions.append("- **Trajectory Failure (Pit Fall)**: The jumper entered the pit zone. This indicates insufficient vertical altitude during transit.")

    if "barrier" in msg or "red bar" in msg:
        suggestions.append("- **Obstacle Interference**: The trajectory intersected with a physical constraint. Adjust the launch timing or angle.")

    return suggestions
