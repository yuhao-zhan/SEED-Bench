"""
Task-specific feedback generation for D-01: The Launcher
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Format task-specific metrics for D-01: The Launcher.
    """
    parts = []

    if "projectile_x" in metrics:
        parts.append(
            f"**Projectile position**: x={metrics['projectile_x']:.2f} m, y={metrics['projectile_y']:.2f} m"
        )
    if "target_x_min" in metrics and "target_x_max" in metrics:
        parts.append(
            f"**Target zone (x)**: [{metrics['target_x_min']:.1f}, {metrics['target_x_max']:.1f}] m"
        )
    if "target_y_min" in metrics and "target_y_max" in metrics:
        parts.append(
            f"**Target zone (y)**: [{metrics['target_y_min']:.1f}, {metrics['target_y_max']:.1f}] m"
        )
    if "progress" in metrics:
        parts.append(f"**Progress toward target**: {metrics['progress']:.1f}%")
    if "projectile_speed" in metrics:
        parts.append(f"**Projectile speed**: {metrics['projectile_speed']:.2f} m/s")
    if "structure_mass" in metrics:
        parts.append(f"**Launcher mass**: {metrics['structure_mass']:.2f} kg")
        if "max_structure_mass" in metrics:
            parts.append(f"**Mass limit**: {metrics['max_structure_mass']:.0f} kg")
    if "step_count" in metrics:
        parts.append(f"**Simulation steps**: {metrics['step_count']}")
    if "hit_occurred" in metrics:
        parts.append(f"**Target hit**: {'Yes' if metrics['hit_occurred'] else 'No'}")
    if "max_y_in_target_x" in metrics and metrics["max_y_in_target_x"] is not None:
        parts.append(
            f"**Max height in target x-band**: {metrics['max_y_in_target_x']:.2f} m "
            f"(target y band: [{metrics.get('target_y_min', 2):.1f}, {metrics.get('target_y_max', 5):.1f}] m)"
        )

    # Physical state (velocity, trajectory diagnostics)
    parts.append("\n**Physical state**")
    if "projectile_vx" in metrics and "projectile_vy" in metrics:
        parts.append(
            f"- Velocity: vx={metrics['projectile_vx']:.3f} m/s, vy={metrics['projectile_vy']:.3f} m/s"
        )
    if "projectile_speed" in metrics:
        parts.append(f"- Speed: {metrics['projectile_speed']:.3f} m/s")
    if "progress" in metrics:
        parts.append(f"- Progress toward target x: {metrics['progress']:.1f}%")

    excluded = {
        "projectile_x", "projectile_y", "projectile_vx", "projectile_vy",
        "projectile_speed", "target_x_min", "target_x_max", "target_y_min", "target_y_max",
        "progress", "success", "failed", "failure_reason", "step_count",
        "structure_mass", "max_structure_mass", "hit_occurred", "max_y_in_target_x",
    }
    other = {k: v for k, v in metrics.items() if k not in excluded}
    if other:
        parts.append("\n**Other metrics**:")
        for k, v in other.items():
            if isinstance(v, float):
                parts.append(f"- {k}: {v:.3f}")
            else:
                parts.append(f"- {k}: {v}")

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
    Generate task-specific improvement suggestions for D-01: The Launcher.
    """
    suggestions = []

    if error:
        err_lower = error.lower()
        if "structure mass" in err_lower and "exceeds" in err_lower:
            suggestions.append("- Reduce launcher mass to stay within 500 kg")
            suggestions.append("- Use lighter beams (lower density) or fewer/smaller parts")
        if "build zone" in err_lower or "outside" in err_lower:
            suggestions.append("- Place all beam centers inside build zone x=[5, 15], y=[1.5, 8]")
        if "add_joint" in err_lower or "add_spring" in err_lower:
            suggestions.append("- Check joint/spring arguments: valid bodies and anchor points inside build zone")

    elif failed:
        if failure_reason and "design constraint" in failure_reason.lower():
            if "mass" in failure_reason.lower():
                suggestions.append("- Reduce total launcher mass below 500 kg")
            if "build zone" in failure_reason.lower():
                suggestions.append("- Keep all launcher parts inside build zone x=[5, 15], y=[1.5, 8]")
        elif failure_reason and "insufficient distance" in failure_reason.lower():
            suggestions.append("- Increase launch energy: use a stronger spring or longer lever arm")
            suggestions.append("- Consider spring stiffness and rest length to store more energy")
            suggestions.append("- Orient the launcher so the projectile is propelled toward positive x")
        elif failure_reason and "miss" in failure_reason.lower():
            suggestions.append("- Adjust launch angle or direction so the projectile lands in the vertical band y=[2, 5]")
            suggestions.append("- Reduce launch power or add damping if the projectile overshoots in x")
            suggestions.append("- Ensure the projectile is released in the right direction (toward the target zone)")
        elif failure_reason and "bounds" in failure_reason.lower():
            suggestions.append("- Keep the projectile within the simulation area; avoid launching straight down or out of world")

    elif not success:
        px = metrics.get("projectile_x", 0)
        if px < metrics.get("target_x_min", 40):
            suggestions.append("- Projectile did not reach the target x range; increase launch energy or efficiency")
        else:
            suggestions.append("- Projectile reached x but missed the y band or overshot; tune angle and power")

    return suggestions
