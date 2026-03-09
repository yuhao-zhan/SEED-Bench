"""
Task-specific feedback for D-05: The Hammer
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Format task-specific metrics for D-05: The Hammer.
    Exposes metrics directly from the evaluator.
    """
    parts = []

    if "shell_broken" in metrics:
        parts.append(f"**Target Breach**: {'Yes' if metrics['shell_broken'] else 'No'}")
    
    if "shell_break_force" in metrics:
        parts.append(f"**Target Threshold**: {metrics['shell_break_force']:.0f} N")

    if "kinetic_energy" in metrics:
        parts.append(f"**Impact Kinetic Energy**: {metrics['kinetic_energy']:.2f} J")
    
    if "speed" in metrics:
        parts.append(f"**Hammer Speed**: {metrics['speed']:.3f} m/s")

    if "hammer_x" in metrics and "hammer_y" in metrics:
        parts.append(f"**Hammer Position**: ({metrics['hammer_x']:.2f}, {metrics['hammer_y']:.2f}) m")

    if "structure_mass" in metrics:
        mass = metrics["structure_mass"]
        limit = metrics.get("max_structure_mass", 0.0)
        parts.append(f"**System Mass**: {mass:.2f} kg (Limit: {limit:.1f} kg)")

    # Report collisions detected by evaluator
    if metrics.get("hammer_hit_wall"): parts.append("**Obstacle collision**: Static wall")
    if metrics.get("hammer_hit_pendulum"): parts.append("**Obstacle collision**: Pendulum")
    if metrics.get("hammer_hit_slot_wall"): parts.append("**Obstacle collision**: Slot boundary")
    if metrics.get("hammer_hit_slot_bar"): parts.append("**Obstacle collision**: Slot bar")

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
    Generate diagnostic warnings for D-05: The Hammer.
    """
    suggestions = []
    
    msg = (error or failure_reason or "").lower()

    # 1. Structural Failures
    if "mass" in msg:
        suggestions.append("- **Mass Constraint**: The hammer exceeds the structural limit. Analyze the mass distribution between arm and head.")
    if "build zone" in msg:
        suggestions.append("- **Spatial Violation**: Components are placed outside the designated fabrication area.")

    # 2. Performance Diagnostics
    if failed or not success:
        if any(metrics.get(k) for k in ("hammer_hit_wall", "hammer_hit_slot_wall")):
            suggestions.append("- **Geometric Obstruction**: The trajectory was blocked by a static barrier. Analyze the swing arc.")
        
        if any(metrics.get(k) for k in ("hammer_hit_pendulum", "hammer_hit_slot_bar")):
            suggestions.append("- **Synchronization Failure**: The hammer collided with a moving obstacle. Analyze timing.")

        elif "shell not broken" in msg:
            suggestions.append("- **Impact Force Deficiency**: The impact delivered insufficient energy to breach the target. Analyze kinetic energy at contact.")
            threshold = metrics.get("shell_break_force", 0.0)
            if threshold > 0:
                suggestions.append(f"- **Requirement**: The instantaneous force must exceed {threshold:.0f} N.")

    return suggestions
