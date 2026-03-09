"""
Task-specific feedback generation for E-04: Variable Mass.
Strictly audited to ensure all metrics are grounded in evaluator.py and limits are dynamic.
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Format task-specific metrics for E-04.
    All metrics are verified against evaluator.py.
    """
    metric_parts = []

    # 1. Structural Performance
    if "step_count" in metrics:
        metric_parts.append(f"**Endurance**: {metrics['step_count']} steps")
    if "structure_mass" in metrics:
        mass = metrics["structure_mass"]
        limit = metrics.get("max_structure_mass", 1.0)
        metric_parts.append(f"**Instantaneous Mass**: {mass:.2f} / {limit:.0f} kg")

    # 2. Joint Stress & Fatigue Analysis
    if "max_joint_reaction_force" in metrics:
        force = metrics["max_joint_reaction_force"]
        limit = metrics.get("effective_joint_force_limit", metrics.get("joint_break_force_limit", 1.0))
        f_load = (force / limit * 100) if limit != 0 else 0
        metric_parts.append(f"**Peak Joint Force**: {force:.3f} N ({f_load:.1f}% of decaying capacity)")

    if "max_joint_reaction_torque" in metrics:
        torque = metrics["max_joint_reaction_torque"]
        limit = metrics.get("effective_joint_torque_limit", metrics.get("joint_break_torque_limit", 1.0))
        t_load = (torque / limit * 100) if limit != 0 else 0
        metric_parts.append(f"**Peak Joint Torque**: {torque:.3f} N·m ({t_load:.1f}% of decaying capacity)")

    # 3. Dynamic Mass State
    if metrics.get("step_count", 0) > 0:
        metric_parts.append("- OBSERVATION: Mass oscillation detected. Member density fluctuates sinusoidally.")

    # 4. Complexity Resources
    if "joint_count" in metrics:
        metric_parts.append(f"**Topology**: {metrics.get('beam_count', 0)} beams, {metrics['joint_count']} joints")

    # 5. Failure Diagnostics
    if metrics.get("failed"):
        metric_parts.append("\n**Failure Diagnostic**:")
        if metrics.get("structure_broken"):
            metric_parts.append("- FAILURE: Structural Disintegration. Joint reaction force/torque exceeded current fatigue limits.")
            if metrics.get("step_count", 0) > 200:
                metric_parts.append("  - FATIGUE ANALYSIS: Effective capacity has decayed significantly since mission start.")
        elif "Design constraint" in metrics.get("failure_reason", ""):
            metric_parts.append(f"- FAILURE: {metrics['failure_reason']}")

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
    Diagnostic suggestions for E-04.
    Strictly describes physical phenomena without dictating design.
    """
    suggestions = []

    if error:
        suggestions.append(f"Design rejection: {error}")
        return suggestions

    if failed:
        f_load = (metrics.get("max_joint_reaction_force", 0) / max(metrics.get("effective_joint_force_limit", 1), 0.001)) * 100
        
        if metrics.get("structure_broken"):
            if f_load > 100:
                suggestions.append("Peak dynamic stress is higher than the joint yield point. Analyze the mass-distribution phases to find high-stress coordinates.")
            
            suggestions.append("Joint strength is non-stationary. Structural configurations that appear stable early in the simulation may fail as cumulative fatigue reduces load capacity.")
            suggestions.append("Concentrated loads accelerate joint failure. Distributing reaction forces across more nodes may improve endurance.")

        # Environmental factors
        if metrics.get("step_count", 0) > 50:
            suggestions.append("The base support is undergoing ellipsoidal excitation. The structure must resist both horizontal and vertical harmonic forces.")

        if failure_reason and "span" in failure_reason.lower():
            suggestions.append("Cantilever requirements not met. The structure must extend members into both the designated left and right coordinate ranges.")

    elif not success:
        suggestions.append("Long-term endurance target not reached. Focus on reducing peak reaction torques at the anchor points.")

    return suggestions
