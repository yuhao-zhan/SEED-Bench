"""
Task-specific feedback generation for D-02: The Jumper
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Format task-specific metrics for D-02: The Jumper.
    Exposes metrics directly from the evaluator.
    """
    parts = []

    if "landed" in metrics:
        parts.append(f"**Landed on Platform**: {'Yes' if metrics['landed'] else 'No'}")
    
    if "progress" in metrics:
        parts.append(f"**Progress to Target**: {metrics['progress']:.1f}%")
    
    if "jumper_x" in metrics and "jumper_y" in metrics:
        parts.append(f"**Jumper Position**: x={metrics['jumper_x']:.2f} m, y={metrics['jumper_y']:.2f} m")

    if "jumper_speed" in metrics:
        parts.append(f"**Jumper Speed**: {metrics['jumper_speed']:.2f} m/s")

    if "structure_mass" in metrics:
        mass = metrics["structure_mass"]
        limit = metrics.get("max_structure_mass", 0.0)
        parts.append(f"**Mechanism Mass**: {mass:.2f} kg (Limit: {limit:.1f} kg)")

    if "distance_from_platform" in metrics:
        parts.append(f"**Gap to Platform**: {metrics['distance_from_platform']:.2f} m")

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
    Generate diagnostic warnings for D-02: The Jumper.
    """
    suggestions = []
    
    msg = (error or failure_reason or "").lower()

    # 1. Structural Failures
    if "mass" in msg:
        suggestions.append("- **Mass Constraint**: The launcher exceeds the permissible mass. Analyze the weight of components.")
    if "build zone" in msg:
        suggestions.append("- **Spatial Violation**: Components are placed outside the designated fabrication area.")

    # 2. Performance Diagnostics
    if failed or not success:
        px = metrics.get("jumper_x", 0.0)
        target_x = metrics.get("right_platform_start_x", 0.0)
        
        if "bar" in msg or "slot" in msg:
            suggestions.append("- **Obstacle Collision**: The jumper's trajectory intersected a barrier. Analyze vertical clearance.")
        
        elif "pit" in msg:
            suggestions.append("- **Momentum Deficit**: The jumper failed to clear the gap. Analyze the horizontal launch impulse.")

        elif px >= target_x and not metrics.get("landed"):
            suggestions.append("- **Landing Instability**: The jumper reached the target distance but failed to secure a stable position.")

    return suggestions
