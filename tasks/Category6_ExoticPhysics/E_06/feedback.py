"""
Audited task-specific feedback for E-06: Cantilever Endurance.
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Expose physical and damage metrics strictly from evaluator.py.
    """
    parts = []

    if "step_count" in metrics:
        parts.append(f"**Structural Lifetime**: {metrics['step_count']} steps")
    if "structure_mass" in metrics:
        mass = metrics["structure_mass"]
        limit = metrics.get("max_structure_mass", 1.0)
        parts.append(f"**Structural Mass**: {mass:.2f} / {limit:.1f} kg")

    if "joint_count" in metrics:
        parts.append(f"**Topology**: {metrics.get('body_count', 0)} beams, {metrics['joint_count']} joints")

    if "max_joint_damage" in metrics:
        damage = metrics["max_joint_damage"]
        limit = metrics.get("damage_limit", 100.0)
        used_pct = (damage / limit * 100) if limit > 0 else 0
        parts.append(f"**Critical Damage**: {damage:.1f} / {limit:.0f} pts ({used_pct:.1f}% Capacity)")

    if "max_joint_force" in metrics:
        force = metrics["max_joint_force"]
        limit = metrics.get("joint_break_force", 1.0)
        f_load = (force / limit * 100) if limit != 0 else 0
        parts.append(f"**Peak Reaction Force**: {force:.2f} N ({f_load:.1f}% Yield)")

    if "max_joint_torque" in metrics:
        torque = metrics["max_joint_torque"]
        limit = metrics.get("joint_break_torque", 1.0)
        t_load = (torque / limit * 100) if limit != 0 else 0
        parts.append(f"**Peak Reaction Torque**: {torque:.2f} N·m ({t_load:.1f}% Yield)")

    if "tip_stability_ratio" in metrics:
        ratio = metrics["tip_stability_ratio"]
        req = metrics.get("tip_stability_required", 0.0)
        parts.append(f"**Tip Tracking**: {ratio*100:.1f}% uptime (Target: >{req*100:.1f}%)")

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

    if error:
        return [f"Design rejected: {error}"]

    if failed:
        damage = metrics.get("max_joint_damage", 0)
        damage_limit = metrics.get("damage_limit", 1)
        torque_load = (metrics.get("max_joint_torque", 0) / max(metrics.get("joint_break_torque", 1), 0.001)) * 100

        if damage_limit > 0 and damage > damage_limit * 0.9:
            suggestions.append("- **Progressive Fatigue Accumulation**: Extreme damage levels detected. Cumulative environmental pulses are causing structural wear.")
        
        if torque_load > 100:
            suggestions.append("- **Primary Anchor Torque Breach**: Overturning moment at the support anchor exceeded capacity. The cantilever span is generating excessive torque at the root.")

        req = metrics.get("tip_stability_required", 0.0)
        if req > 0 and metrics.get("tip_stability_ratio", 1.0) < req:
            suggestions.append("- **Stability-Mass Interaction**: The tip is oscillating outside the target band. Increased mass for strength may be increasing the dynamic response to noise.")

        suggestions.append("- **Dynamic Load Scaling**: External shocks generate significantly higher stress at the cantilever tip than at the support anchor.")

        if failure_reason and "span" in failure_reason.lower():
            suggestions.append("- **Spatial Reach Violation**: The structure failed to meet the required horizontal or vertical extent.")

    return suggestions
