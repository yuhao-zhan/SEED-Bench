"""
Audited task-specific feedback for E-04: Variable Mass.
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Expose physical and fatigue metrics strictly from evaluator.py.
    """
    parts = []

    if "simulation_time_s" in metrics:
        parts.append(f"**Structural Lifetime**: {metrics['simulation_time_s']:.2f} s")
    
    if "structure_mass" in metrics:
        mass = metrics["structure_mass"]
        limit = metrics.get("max_structure_mass", 1.0)
        parts.append(f"**Instantaneous Mass**: {mass:.2f} kg / {limit:.0f} kg")

    if "max_joint_reaction_force" in metrics:
        force = metrics["max_joint_reaction_force"]
        limit = metrics.get("effective_joint_force_limit", metrics.get("joint_break_force_limit", 1.0))
        f_load = (force / limit * 100) if limit != 0 else 0
        parts.append(f"**Peak Reaction Force**: {force:.4f} N ({f_load:.1f}% of current capacity)")

    if "max_joint_reaction_torque" in metrics:
        torque = metrics["max_joint_reaction_torque"]
        limit = metrics.get("effective_joint_torque_limit", metrics.get("joint_break_torque_limit", 1.0))
        t_load = (torque / limit * 100) if limit != 0 else 0
        parts.append(f"**Peak Reaction Torque**: {torque:.4f} N·m ({t_load:.1f}% of current capacity)")

    if "joint_count" in metrics:
        parts.append(f"**Topology**: {metrics.get('joint_count', 0)} joints, {metrics.get('beam_count', 0)} beams")

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

    if failed:
        f_load = (metrics.get("max_joint_reaction_force", 0) / max(metrics.get("effective_joint_force_limit", 0.0001), 0.0001)) * 100
        
        if metrics.get("structure_broken"):
            if f_load > 100:
                suggestions.append("- **Peak Dynamic Stress Breach**: Reaction force exceeded the instantaneous joint yield point.")
            
            suggestions.append("- **Structural Fatigue Decay**: Joint capacity is non-stationary. Strength decreases as cumulative fatigue accumulates over the simulation.")
            suggestions.append("- **Load Distribution Inefficiency**: Concentrated reaction forces accelerate localized failure. Distributing dynamic loads across more connections may improve endurance.")

        if failure_reason and "span" in failure_reason.lower():
            suggestions.append("- **Spatial Reach Requirement**: The structure failed to span the required coordinate ranges.")

    elif not success:
        suggestions.append("- **Endurance Target**: Focus on minimizing peak reaction torques during the high-mass phases of the oscillation.")

    return suggestions
