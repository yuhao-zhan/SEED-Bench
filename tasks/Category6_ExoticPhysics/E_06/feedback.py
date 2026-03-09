"""
Task-specific feedback generation for E-06: Cantilever Endurance.
Strictly audited to ensure all metrics are grounded in evaluator.py and limits are dynamic.
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Format task-specific metrics for E-06.
    All metrics are verified against evaluator.py.
    """
    metric_parts = []

    # 1. Operational Endurance
    if "step_count" in metrics:
        metric_parts.append(f"**Structural Lifetime**: {metrics['step_count']} steps")
    if "structure_mass" in metrics:
        mass = metrics["structure_mass"]
        limit = metrics.get("max_structure_mass", 1.0)
        metric_parts.append(f"**Structural Mass**: {mass:.2f} / {limit:.0f} kg")

    # 2. Support & Constraint Analysis
    if "joint_count" in metrics:
        metric_parts.append(f"**Topology**: {metrics.get('body_count', 0)} beams, {metrics['joint_count']} joints")
    if "span_check_passed" in metrics:
        metric_parts.append(f"**Span Requirements**: {'MET' if metrics['span_check_passed'] else 'FAILED'}")

    # 3. Dynamic Stress & Damage Analysis
    if "max_joint_damage" in metrics:
        damage = metrics["max_joint_damage"]
        limit = metrics.get("damage_limit", 100.0)
        metric_parts.append(f"**Critical Damage Level**: {damage:.1f}% toward failure")

    if "max_joint_force" in metrics:
        force = metrics["max_joint_force"]
        limit = metrics.get("joint_break_force", 1.0)
        f_load = (force / limit * 100) if limit != 0 else 0
        metric_parts.append(f"**Peak Reaction Force**: {force:.2f} N ({f_load:.1f}% Yield)")

    if "max_joint_torque" in metrics:
        torque = metrics["max_joint_torque"]
        limit = metrics.get("joint_break_torque", 1.0)
        t_load = (torque / limit * 100) if limit != 0 else 0
        metric_parts.append(f"**Peak Reaction Torque**: {torque:.2f} N·m ({t_load:.1f}% Yield)")

    # 4. Stability Analysis (Tip Tracking)
    if "tip_stability_ratio" in metrics:
        ratio = metrics["tip_stability_ratio"]
        req = metrics.get("tip_stability_required", 0.0)
        metric_parts.append(f"**Tip Stability Tracking**: {ratio*100:.1f}% uptime (Target: >{req*100:.1f}%)")

    # 5. Failure Diagnostics
    if metrics.get("failed"):
        metric_parts.append("\n**Failure Diagnostic**:")
        if metrics.get("structure_broken"):
            metric_parts.append("- FAILURE: Structural Collapse. Joints or members exceeded operational thresholds.")
        if metrics.get("span_check_passed") is False:
            metric_parts.append(f"- FAILURE: {metrics.get('span_check_message', 'Incomplete span or height.')}")

    return metric_parts


def get_improvement_suggestions(
    metrics: Dict[str, Any],
    score: float,
    success: bool,
    failed: bool,
    failure_reason: str = None,
    error: str = None,
) -> List[str]:
    """
    Diagnostic suggestions for E-06.
    Strictly describes physical phenomena without dictating design.
    """
    suggestions = []

    if error:
        suggestions.append(f"Design rejection: {error}")
        return suggestions

    if failed:
        damage = metrics.get("max_joint_damage", 0)
        torque_load = (metrics.get("max_joint_torque", 0) / max(metrics.get("joint_break_torque", 1), 0.001)) * 100

        # Structural stress analysis
        if damage > 90:
            suggestions.append("Progressive joint fatigue detected. High-excitation cycles are causing cumulative damage. Distributing reaction forces may improve endurance.")
        
        if torque_load > 100:
            suggestions.append("Overturning moment exceeded primary anchor capacity. The cantilever span is generating excessive torque at the root.")

        # Cantilever specific logic
        suggestions.append("Excitation magnitude is distance-scaled from the support. Dynamic loads are significantly higher at the cantilever tip than at the anchor.")
        suggestions.append("Monitor high-damage coordinates. Localized stresses near the primary joints suggest a need for improved counter-balance or moment distribution.")

    elif not success:
        suggestions.append("Stability optimization suggested. The cantilever tip is oscillating outside the target vertical band. Refine the mass distribution to dampen dynamic response.")

    return suggestions
