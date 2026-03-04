"""
Task-specific feedback generation for E-04: Variable Mass.
Returns physical metrics (joint forces/torques, mass, integrity) for process and result feedback.
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """Format task-specific metrics for E-04 (process and result physical metrics)."""
    metric_parts = []

    if "step_count" in metrics:
        metric_parts.append(f"**Simulation steps**: {metrics['step_count']}")
    if "structure_mass" in metrics:
        metric_parts.append(f"**Structure mass**: {metrics['structure_mass']:.2f} kg")
        if "max_structure_mass" in metrics:
            metric_parts.append(f"**Mass limit**: {metrics['max_structure_mass']:.0f} kg")
    if "joint_count" in metrics:
        metric_parts.append(f"**Joint count**: {metrics['joint_count']}")
        if "initial_joint_count" in metrics:
            metric_parts.append(f"**Initial joint count**: {metrics['initial_joint_count']}")
    if "structure_broken" in metrics:
        metric_parts.append(f"**Structure integrity**: {'BROKEN (disintegrated)' if metrics['structure_broken'] else 'INTACT'}")

    # Joint stress metrics (process/result); show effective limit if fatigue is used
    if "max_joint_reaction_force" in metrics:
        f_max = metrics["max_joint_reaction_force"]
        f_lim = metrics.get("effective_joint_force_limit") or metrics.get("joint_break_force_limit", 6.0)
        metric_parts.append(f"**Max joint reaction force**: {f_max:.2f} N (effective limit: {f_lim:.2f} N)")
    if "max_joint_reaction_torque" in metrics:
        t_max = metrics["max_joint_reaction_torque"]
        t_lim = metrics.get("effective_joint_torque_limit") or metrics.get("joint_break_torque_limit", 10.0)
        metric_parts.append(f"**Max joint reaction torque**: {t_max:.2f} N·m (effective limit: {t_lim:.2f} N·m)")

    # Physical state / vibration context (like S_01 physical state block)
    if any(k in metrics for k in ("max_joint_reaction_force", "max_joint_reaction_torque", "structure_mass")):
        metric_parts.append("\n**Physical state (vibration / joint stress)**")
        if "max_joint_reaction_force" in metrics:
            metric_parts.append(f"- Max joint force observed: {metrics['max_joint_reaction_force']:.3f} N")
        if "max_joint_reaction_torque" in metrics:
            metric_parts.append(f"- Max joint torque observed: {metrics['max_joint_reaction_torque']:.3f} N·m")
        if "effective_joint_force_limit" in metrics:
            metric_parts.append(f"- Effective joint force limit (current): {metrics['effective_joint_force_limit']:.2f} N")
        elif "joint_break_force_limit" in metrics:
            metric_parts.append(f"- Joint force break limit: {metrics['joint_break_force_limit']:.0f} N")
        if "effective_joint_torque_limit" in metrics:
            metric_parts.append(f"- Effective joint torque limit (current): {metrics['effective_joint_torque_limit']:.2f} N·m")
        elif "joint_break_torque_limit" in metrics:
            metric_parts.append(f"- Joint torque break limit: {metrics['joint_break_torque_limit']:.0f} N·m")
        if "simulation_time_s" in metrics:
            metric_parts.append(f"- Simulation time elapsed: {metrics['simulation_time_s']:.1f} s")
        if "structure_mass" in metrics:
            metric_parts.append(f"- Current structure mass (time-varying): {metrics['structure_mass']:.3f} kg")

    excluded = {
        "step_count", "structure_mass", "max_structure_mass", "joint_count",
        "initial_joint_count", "structure_broken", "success", "failed", "failure_reason",
        "max_joint_reaction_force", "max_joint_reaction_torque",
        "joint_break_force_limit", "joint_break_torque_limit",
        "effective_joint_force_limit", "effective_joint_torque_limit", "simulation_time_s",
    }
    other = {k: v for k, v in metrics.items() if k not in excluded}
    if other:
        metric_parts.append("\n**Additional metrics**:")
        for k, v in other.items():
            if isinstance(v, float):
                metric_parts.append(f"- {k}: {v:.3f}")
            else:
                metric_parts.append(f"- {k}: {v}")

    return metric_parts


def get_improvement_suggestions(
    metrics: Dict[str, Any],
    score: float,
    success: bool,
    failed: bool,
    failure_reason: str = None,
    error: str = None,
) -> List[str]:
    """Generate task-specific improvement suggestions for E-04."""
    suggestions = []

    if error:
        err_lower = error.lower()
        if "structure mass" in err_lower and "exceeds" in err_lower:
            max_mass = metrics.get('max_structure_mass', 400.0)
            suggestions.append(f"Reduce structure mass to within {max_mass:.0f} kg")
        elif "build zone" in err_lower or "outside build zone" in err_lower:
            suggestions.append("Place all beams inside the build zone (infer limits from feedback)")

    elif failed:
        if failure_reason and "design constraint" in failure_reason.lower():
            if "mass" in failure_reason.lower():
                max_mass = metrics.get('max_structure_mass', 400.0)
                suggestions.append(f"Keep total structure mass ≤ {max_mass:.0f} kg")
            if "build zone" in failure_reason.lower():
                suggestions.append("Ensure every beam center is inside the build zone (infer limits from feedback)")
        elif failure_reason and ("disintegrat" in failure_reason.lower() or "joint" in failure_reason.lower()):
            suggestions.append("Mass varies sinusoidally; resonance can cause high forces and break joints.")
            suggestions.append("Consider stiffer or more redundant connections, or geometries that avoid resonance.")
            suggestions.append("Reduce stress concentrations; distribute loads across more joints.")
            f_lim = metrics.get("joint_break_force_limit") or metrics.get("effective_joint_force_limit", 6.0)
            t_lim = metrics.get("joint_break_torque_limit") or metrics.get("effective_joint_torque_limit", 10.0)
            suggestions.append(f"Keep max joint reaction force < {f_lim:.1f} N and max torque < {t_lim:.1f} N·m.")

    elif not success:
        suggestions.append("Design for variable mass: ensure joints can withstand the varying reaction forces over time.")
        f_max = metrics.get("max_joint_reaction_force")
        t_max = metrics.get("max_joint_reaction_torque")
        f_lim = metrics.get("effective_joint_force_limit") or metrics.get("joint_break_force_limit", 6.0)
        t_lim = metrics.get("effective_joint_torque_limit") or metrics.get("joint_break_torque_limit", 10.0)
        if f_max is not None and f_lim and f_max > 0.8 * f_lim:
            suggestions.append(f"Max joint force ({f_max:.1f} N) is close to limit ({f_lim:.0f} N); add joints or lighten structure.")
        if t_max is not None and t_lim and t_max > 0.8 * t_lim:
            suggestions.append(f"Max joint torque ({t_max:.1f} N·m) is close to limit ({t_lim:.0f} N·m); shorten beams or add supports.")

    return suggestions
