"""
Task-specific feedback for F-06: The Pipeline
Returns process and result physical metrics for feedback (ref S_01).
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    metric_parts = []
    if "initial_particle_count" in metrics:
        metric_parts.append(f"**Initial fluid particles**: {metrics['initial_particle_count']}")
    if "particles_in_target" in metrics:
        metric_parts.append(f"**Particles in target** (zone x=[18,22], y=[0,1.5]): {metrics['particles_in_target']}")
    if "delivery_ratio_percent" in metrics:
        target_pct = metrics.get("min_delivery_ratio_percent", 90.0)
        metric_parts.append(f"**Delivery efficiency**: {metrics['delivery_ratio_percent']:.1f}% (target: {target_pct:.0f}%)")
    if "particles_lost" in metrics:
        metric_parts.append(f"**Particles lost** (pit or out of world): {metrics['particles_lost']}")
    if "particles_in_source" in metrics:
        metric_parts.append(f"**Particles still in source** (x=[2,6], y=[0,1.5]): {metrics['particles_in_source']}")
    if "particles_in_build_zone" in metrics:
        metric_parts.append(f"**Particles in build zone** (x=[6,18], y=[0,6]): {metrics['particles_in_build_zone']}")
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

    # Physical state information for debugging (ref S_01)
    if "particle_mean_x" in metrics or "particle_mean_y" in metrics or "particle_active_count" in metrics:
        metric_parts.append("\n**Physical State Information**:")
        if "particle_mean_x" in metrics and "particle_mean_y" in metrics:
            metric_parts.append(f"- Particle centroid: ({metrics['particle_mean_x']:.3f}, {metrics['particle_mean_y']:.3f}) m")
        if "particle_active_count" in metrics:
            metric_parts.append(f"- Active particle count: {metrics['particle_active_count']}")
        if "particles_in_source" in metrics and "particles_in_target" in metrics:
            metric_parts.append(f"- In source vs in target: {metrics['particles_in_source']} vs {metrics['particles_in_target']}")

    excluded = {
        "initial_particle_count", "particles_in_target", "particles_lost", "particles_in_source", "particles_in_build_zone",
        "delivery_ratio", "delivery_ratio_percent", "min_delivery_ratio", "min_delivery_ratio_percent",
        "structure_mass", "max_structure_mass", "structure_broken", "joint_count", "step_count",
        "success", "failed", "failure_reason", "particle_mean_x", "particle_mean_y", "particle_active_count",
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
            suggestions.append(f"- Reduce structure mass to be within {metrics.get('max_structure_mass', 380):.0f} kg")
        elif "build zone" in error_lower:
            suggestions.append("- Place all beams within build zone x=[6, 18], y=[0, 6]")
    elif failed:
        if failure_reason and "design constraint" in failure_reason.lower():
            if "structure mass" in failure_reason.lower():
                suggestions.append(f"- Keep total mass below {metrics.get('max_structure_mass', 380):.0f} kg")
            if "build zone" in failure_reason.lower():
                suggestions.append("- Ensure all beams are inside the build zone between source and target")
        elif failure_reason and "delivery" in failure_reason.lower() and "efficiency" in failure_reason.lower():
            suggestions.append("- **Avoid all three pits**: PIT3 x=[11,12.5] y<1.6; PIT1 x=[13.5,15.5] y<2.0; PIT2 x=[16,17.5] y<1.6. Route above each.")
            suggestions.append("- **Headwind**: For y>3 add +X force to overcome headwind.")
            suggestions.append("- **Gravity well**: In x=[10,14], y=[1.5,3.5] add extra upward force to overcome downward pull.")
            budget = metrics.get('force_budget', 12000.0)
            suggestions.append(f"- Aim for 90% delivery; force budget {budget:.0f} N/step; prioritize which particles to push.")
        elif failure_reason and "structure integrity" in failure_reason.lower():
            suggestions.append("- Strengthen joints; moving particles exert forces on the structure")
    elif not success:
        target_pct = metrics.get("min_delivery_ratio_percent", 90.0)
        if metrics.get("delivery_ratio_percent", 0) < target_pct:
            suggestions.append(f"- Aim to deliver at least {target_pct:.0f}% of particles to the target x=[18,22], y=[0,1.5]; avoid all three pits.")
    return suggestions
