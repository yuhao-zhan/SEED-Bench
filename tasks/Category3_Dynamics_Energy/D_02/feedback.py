"""
Task-specific feedback generation for D-02: The Jumper
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """Format task-specific metrics for D-02: The Jumper (rich physical metrics like S_01)."""
    parts = []

    # Position and target
    if "jumper_x" in metrics:
        parts.append(
            f"**Jumper position**: x={metrics['jumper_x']:.2f} m, y={metrics['jumper_y']:.2f} m"
        )
    if "right_platform_start_x" in metrics:
        parts.append(f"**Right platform start**: x={metrics['right_platform_start_x']:.1f} m")
    if "progress" in metrics:
        parts.append(f"**Progress toward platform**: {metrics['progress']:.1f}%")
    if "distance_from_platform" in metrics:
        parts.append(f"**Distance to platform**: {metrics['distance_from_platform']:.2f} m")

    # Velocity (process and result)
    if "jumper_speed" in metrics:
        parts.append(f"**Jumper speed**: {metrics['jumper_speed']:.2f} m/s")
    if "jumper_vx" in metrics and "jumper_vy" in metrics:
        parts.append(
            f"**Velocity components**: vx={metrics['jumper_vx']:.2f} m/s, vy={metrics['jumper_vy']:.2f} m/s"
        )

    # Structure
    if "structure_mass" in metrics:
        parts.append(f"**Launcher mass**: {metrics['structure_mass']:.2f} kg")
        if "max_structure_mass" in metrics:
            parts.append(f"**Mass limit**: {metrics['max_structure_mass']:.0f} kg")

    # Simulation
    if "step_count" in metrics:
        parts.append(f"**Simulation steps**: {metrics['step_count']}")
    if "landed" in metrics:
        parts.append(f"**Landed on platform**: {'Yes' if metrics['landed'] else 'No'}")

    # Physical state (like S_01)
    if "angular_velocity" in metrics or "angle" in metrics:
        parts.append("\n**Physical state (jumper)**")
        if "angular_velocity" in metrics:
            rad_s = metrics["angular_velocity"]
            parts.append(f"- Angular velocity: {rad_s:.3f} rad/s")
        if "angle" in metrics:
            rad = metrics["angle"]
            deg = rad * 180 / 3.14159
            parts.append(f"- Angle: {rad:.3f} rad ({deg:.1f}°)")

    # Failure thresholds for debugging
    if "pit_fail_y" in metrics:
        parts.append(f"- Pit fail threshold: y < {metrics['pit_fail_y']} m")
    if "landing_min_y" in metrics:
        parts.append(f"- Landing min y: {metrics['landing_min_y']} m")

    excluded = {
        "jumper_x", "jumper_y", "jumper_vx", "jumper_vy", "jumper_speed",
        "right_platform_start_x", "progress", "success", "failed", "failure_reason",
        "step_count", "structure_mass", "max_structure_mass", "landed",
        "angular_velocity", "angle", "distance_from_platform", "pit_fail_y", "landing_min_y",
    }
    other = {k: v for k, v in metrics.items() if k not in excluded}
    if other:
        parts.append("\n**Other metrics**:")
        for k, v in other.items():
            parts.append(f"- {k}: {v:.3f}" if isinstance(v, float) else f"- {k}: {v}")
    return parts


def get_improvement_suggestions(
    metrics: Dict[str, Any],
    score: float,
    success: bool,
    failed: bool,
    failure_reason: str = None,
    error: str = None,
) -> List[str]:
    """Generate task-specific improvement suggestions for D-02: The Jumper."""
    suggestions = []
    if error:
        err_lower = error.lower()
        if "structure mass" in err_lower and "exceeds" in err_lower:
            suggestions.append("- Reduce launcher mass to stay within 180 kg")
        if "build_zone" in err_lower or "outside" in err_lower:
            suggestions.append("- Place all beam centers inside build zone x=[1.5, 6.5], y=[2.5, 5.5]")

    elif failed:
        if failure_reason and "design constraint" in failure_reason.lower():
            if "mass" in failure_reason.lower():
                suggestions.append("- Reduce total launcher mass below 180 kg")
            if "build zone" in failure_reason.lower():
                suggestions.append("- Keep all beam centers inside build zone x=[1.5, 6.5], y=[2.5, 5.5]")
        elif failure_reason and "hit lower red bar" in failure_reason.lower():
            suggestions.append("- Trajectory too low: Increase launch angle (vy/vx ratio) to pass through the gap between red bars")
        elif failure_reason and "hit upper red bar" in failure_reason.lower():
            suggestions.append("- Trajectory too high: Decrease launch angle or power to pass through the slot without hitting the upper red bar")
        elif failure_reason and "hit obstacle" in failure_reason.lower() or "slot" in failure_reason.lower():
            suggestions.append("- The pit has three barrier slots that must be cleared sequentially:")
            suggestions.append("- Slot 1 (x~17.0 m): Gap y=[13.2, 14.7] m")
            suggestions.append("- Slot 2 (x~19.0 m): Gap y=[12.4, 14.2] m")
            suggestions.append("- Slot 3 (x~21.0 m): Gap y=[11.3, 13.3] m")
            suggestions.append("- Use simulation feedback to tune your launch velocity to pass through the center of these gaps")
        elif failure_reason and "fall into pit" in failure_reason.lower():
            suggestions.append("- Increase launch impulse (velocity magnitude) or angle so the jumper clears the pit (reaches x >= 26.0 m)")
            suggestions.append("- Ensure the initial velocity vx is high enough to reach the target platform distance")
        elif failure_reason and "did not reach" in failure_reason.lower():
            suggestions.append("- Jumper did not reach x=26.0 m; increase launch energy or optimize launch angle")
            suggestions.append("- If the jumper is hitting obstacles, try adjusting the launch direction")

    elif not success:
        px = metrics.get("jumper_x", 0)
        if px < metrics.get("right_platform_start_x", 26.0):
            suggestions.append("- Increase launch impulse so the jumper reaches the right platform (x >= 26.0 m)")
        else:
            suggestions.append("- Jumper reached the target x range but did not land safely (y >= 1.0 m); tune landing behavior")

    return suggestions
