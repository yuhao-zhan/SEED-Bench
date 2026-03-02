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
            suggestions.append("- Reduce launcher mass to stay within 300 kg")
        if "build zone" in err_lower or "outside" in err_lower:
            suggestions.append("- Place all beam centers inside build zone x=[1, 7], y=[2.5, 6]")

    elif failed:
        if failure_reason and "design constraint" in failure_reason.lower():
            if "mass" in failure_reason.lower():
                suggestions.append("- Reduce total launcher mass below 300 kg")
            if "build zone" in failure_reason.lower():
                suggestions.append("- Keep all parts inside build zone x=[1, 7], y=[2.5, 6]")
        elif failure_reason and "touched red barrier" in failure_reason.lower():
            suggestions.append("- Touching any red bar = fail; the jumper must not overlap any of the three red bars")
            suggestions.append("- There are three red bars (x~17 top 11.5 m, x~19 top 11.5 m, x~21 top 11 m); arc must clear all without contact")
            suggestions.append("- Increase vy and/or tune vx so the trajectory passes above all three bars with clearance")
        elif failure_reason and "first obstacle" in failure_reason.lower():
            suggestions.append("- First barrier: x 16.5–17.5 m, top y=11.5 m; trajectory must go OVER it without touching")
            suggestions.append("- Increase vy so the arc clears y=11.5 m when passing x~17 m")
        elif failure_reason and "second obstacle" in failure_reason.lower():
            suggestions.append("- Second barrier: x 20.5–21.5 m, top y=11 m; trajectory must go OVER all barriers without touching")
            suggestions.append("- Arc must be high enough to clear all three red bars and still land x>=26")
        elif failure_reason and "hit obstacle" in failure_reason.lower():
            suggestions.append("- The pit has three red bars; touching any = fail. Arc must clear all without contact")
            suggestions.append("- Increase vy and tune vx so the arc clears all three and lands on the right platform")
        elif failure_reason and "fall into pit" in failure_reason.lower():
            suggestions.append("- Increase launch impulse or angle so the jumper clears the pit and barrier")
            suggestions.append("- Optimize take-off: enough vx to reach x>=26, enough vy to clear the barrier (y>10.5 at x~17)")
        elif failure_reason and "did not reach" in failure_reason.lower():
            suggestions.append("- Jumper did not reach x=20 m; increase launch energy or improve angle")
            suggestions.append("- Ensure the mechanism imparts sufficient impulse to the jumper")

    elif not success:
        px = metrics.get("jumper_x", 0)
        if px < metrics.get("right_platform_start_x", 20):
            suggestions.append("- Increase launch impulse so the jumper reaches the right platform")
        else:
            suggestions.append("- Jumper may have overshot or bounced; tune restitution or landing")

    return suggestions
