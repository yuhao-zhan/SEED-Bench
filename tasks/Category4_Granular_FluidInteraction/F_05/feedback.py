"""
Task-specific feedback for F-05: The Boat
Returns process and result physical metrics for feedback (reference: S_01).
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    metric_parts = []

    # Result metrics
    if "initial_cargo_count" in metrics:
        metric_parts.append(f"**Initial cargo**: {metrics['initial_cargo_count']}")
    if "cargo_in_water" in metrics:
        thresh = metrics.get("cargo_water_y", 1.98)
        metric_parts.append(f"**Cargo in water** (y<{thresh}m): {metrics['cargo_in_water']}")
    if "cargo_retained" in metrics and metrics.get("cargo_retained") is not None and "initial_cargo_count" in metrics:
        metric_parts.append(f"**Cargo retained**: {metrics.get('cargo_retained', '—')}/{metrics['initial_cargo_count']}")
    if "cargo_retained_ratio" in metrics and metrics["cargo_retained_ratio"] is not None:
        metric_parts.append(f"**Cargo retained ratio**: {metrics['cargo_retained_ratio']*100:.1f}%")
    if "boat_angle_deg" in metrics and metrics["boat_angle_deg"] is not None:
        metric_parts.append(f"**Boat angle** (final): {metrics['boat_angle_deg']:.1f}°")
        if "boat_max_angle_deg" in metrics:
            metric_parts.append(f"**Capsize limit**: {metrics['boat_max_angle_deg']:.0f}°")
    if "structure_mass" in metrics:
        metric_parts.append(f"**Structure mass**: {metrics['structure_mass']:.2f} kg")
        if "max_structure_mass" in metrics:
            metric_parts.append(f"**Mass limit**: {metrics['max_structure_mass']:.0f} kg")
    if "structure_broken" in metrics:
        metric_parts.append(f"**Structure integrity**: {'BROKEN' if metrics['structure_broken'] else 'INTACT'}")
    if "joint_count" in metrics:
        metric_parts.append(f"**Joint count**: {metrics['joint_count']}")
    if "step_count" in metrics:
        metric_parts.append(f"**Simulation steps**: {metrics['step_count']}")

    # Physical state information (process/result, like S_01)
    if "boat_x" in metrics or "boat_y" in metrics or "boat_angle_deg" in metrics:
        metric_parts.append("\n**Physical State Information**:")
        if "boat_x" in metrics and metrics["boat_x"] is not None and "boat_y" in metrics and metrics["boat_y"] is not None:
            metric_parts.append(f"- Boat position: x={metrics['boat_x']:.3f} m, y={metrics['boat_y']:.3f} m")
        if "boat_angle_deg" in metrics and metrics["boat_angle_deg"] is not None:
            metric_parts.append(f"- Boat angle: {metrics['boat_angle_deg']:.3f}° (limit {metrics.get('boat_max_angle_deg', 18):.0f}°)")
        if "cargo_in_water" in metrics and "initial_cargo_count" in metrics:
            thresh = metrics.get("cargo_water_y", 1.98)
            metric_parts.append(f"- Cargo in water: {metrics['cargo_in_water']}/{metrics['initial_cargo_count']} (y<{thresh}m = lost)")
        if "structure_mass" in metrics and "max_structure_mass" in metrics:
            metric_parts.append(f"- Structure mass: {metrics['structure_mass']:.2f} kg / {metrics['max_structure_mass']:.0f} kg limit")

    excluded = {
        "initial_cargo_count", "cargo_in_water", "cargo_retained", "cargo_retained_ratio",
        "cargo_water_y", "boat_angle_rad", "boat_angle_deg", "boat_max_angle_deg", "boat_x", "boat_y",
        "structure_mass", "max_structure_mass", "structure_broken", "joint_count", "step_count",
        "success", "failed", "failure_reason",
    }
    other = {k: v for k, v in metrics.items() if k not in excluded}
    if other:
        metric_parts.append("\n**Additional metrics**:")
        for k, v in other.items():
            metric_parts.append(f"- {k}: {v:.3f}" if isinstance(v, float) else f"- {k}: {v}")
    return metric_parts


def get_improvement_suggestions(
    metrics: Dict[str, Any], score: float, success: bool, failed: bool,
    failure_reason: str = None, error: str = None,
) -> List[str]:
    suggestions = []
    if error:
        error_lower = error.lower()
        if "structure mass" in error_lower and "exceeds" in error_lower:
            suggestions.append(f"- Reduce structure mass to be within {metrics.get('max_structure_mass', 60):.0f} kg")
        elif "build zone" in error_lower:
            suggestions.append(f"- Place all beams within build zone x=[{metrics.get('build_zone_x_min', 12.0):.1f}, {metrics.get('build_zone_x_max', 18.0):.1f}], y=[{metrics.get('build_zone_y_min', 2.0):.1f}, {metrics.get('build_zone_y_max', 4.5):.1f}]")
    elif failed:
        if failure_reason and "design constraint" in failure_reason.lower():
            if "structure mass" in failure_reason.lower():
                suggestions.append(f"- Keep total mass below {metrics.get('max_structure_mass', 60):.0f} kg")
            if "build zone" in failure_reason.lower():
                suggestions.append(f"- Ensure all beams are inside the build zone x=[{metrics.get('build_zone_x_min', 12.0):.1f}, {metrics.get('build_zone_x_max', 18.0):.1f}], y=[{metrics.get('build_zone_y_min', 2.0):.1f}, {metrics.get('build_zone_y_max', 4.5):.1f}]")
        elif failure_reason and "cargo" in failure_reason.lower() and "water" in failure_reason.lower():
            suggestions.append("- Add rails or ties to secure cargo so it cannot roll or slide off the boat")
            suggestions.append("- Lower the center of gravity and widen the base to improve stability (metacentric height)")
        elif failure_reason and "capsized" in failure_reason.lower():
            suggestions.append("- Improve boat stability: add ballast or structure to lower center of gravity")
            suggestions.append("- Secure cargo so it does not shift and cause listing")
        elif failure_reason and "structure integrity" in failure_reason.lower():
            suggestions.append("- Strengthen joints; wave forces can break weak connections")
    elif not success:
        if metrics.get("cargo_in_water", 0) > 0:
            thresh = metrics.get("cargo_water_y", 1.98)
            suggestions.append(f"- Secure all cargo above y={thresh}m (rails, ties, or barriers)")
        max_deg = metrics.get("boat_max_angle_deg", 18)
        if metrics.get("boat_angle_deg") is not None and metrics.get("boat_angle_deg", 0) > max_deg:
            suggestions.append(f"- Reduce boat roll (angle) by improving stability and cargo fixation (limit {max_deg:.0f}°)")
    return suggestions
