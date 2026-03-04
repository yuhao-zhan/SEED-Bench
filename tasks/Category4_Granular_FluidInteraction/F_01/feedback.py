"""
Task-specific feedback generation for F-01: The Dam
Provides process and result physical metrics for solver feedback (reference: S-01 style).
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Format task-specific metrics for F-01: The Dam.
    Returns a list of formatted strings covering containment, structure, and process metrics.
    """
    metric_parts = []

    # Primary containment metrics
    if "initial_particle_count" in metrics:
        metric_parts.append(f"**Initial water particles**: {metrics['initial_particle_count']}")
    if "leaked_particle_count" in metrics:
        metric_parts.append(f"**Leaked particles** (downstream, x>14m): {metrics['leaked_particle_count']}")
    if "retained_particle_count" in metrics:
        metric_parts.append(f"**Retained particles** (not leaked): {metrics['retained_particle_count']}")
    if "leakage_rate_percent" in metrics:
        limit_pct = metrics.get("leakage_limit_percent", 3.0)
        metric_parts.append(f"**Leakage rate**: {metrics['leakage_rate_percent']:.1f}% (limit: {limit_pct:.0f}%)")
    if "containment_percent" in metrics:
        metric_parts.append(f"**Containment**: {metrics['containment_percent']:.1f}%")

    # Structure metrics
    if "structure_mass" in metrics:
        metric_parts.append(f"**Structure mass**: {metrics['structure_mass']:.2f} kg")
        if "max_structure_mass" in metrics:
            metric_parts.append(f"**Mass limit**: {metrics['max_structure_mass']:.0f} kg")
    if "beam_count" in metrics:
        metric_parts.append(f"**Beam count**: {metrics['beam_count']}")
    if "structure_broken" in metrics:
        metric_parts.append(f"**Structure integrity**: {'BROKEN' if metrics['structure_broken'] else 'INTACT'}")
    if "joint_count" in metrics:
        metric_parts.append(f"**Joint count**: {metrics['joint_count']}")

    # Simulation progress
    if "step_count" in metrics:
        metric_parts.append(f"**Simulation steps**: {metrics['step_count']}")
    if "current_particle_count" in metrics:
        metric_parts.append(f"**Current particles in world**: {metrics['current_particle_count']}")

    # Physical state / process information (for fine-grained debugging, like S-01)
    metric_parts.append("\n**Physical State / Process Metrics**:")
    if "initial_particle_count" in metrics and "leaked_particle_count" in metrics:
        init_ = metrics["initial_particle_count"]
        leak_ = metrics["leaked_particle_count"]
        metric_parts.append(f"- Particles contained: {init_ - leak_} / {init_} ({100.0 * (init_ - leak_) / max(init_, 1):.1f}%)")
    if "leakage_rate" in metrics:
        metric_parts.append(f"- Leakage rate (ratio): {metrics['leakage_rate']:.4f}")
    if "structure_mass" in metrics and "max_structure_mass" in metrics:
        used = metrics["structure_mass"] / max(metrics["max_structure_mass"], 1) * 100
        metric_parts.append(f"- Mass budget used: {used:.1f}%")

    # Excluded from "other" so we don't duplicate
    excluded = {
        "initial_particle_count", "leaked_particle_count", "leakage_rate", "leakage_rate_percent",
        "retained_particle_count", "containment_percent", "current_particle_count",
        "structure_mass", "max_structure_mass", "structure_broken", "joint_count", "beam_count",
        "step_count", "success", "failed", "failure_reason",
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
    """
    Generate task-specific improvement suggestions for F-01: The Dam.
    """
    suggestions = []

    if error:
        error_lower = error.lower()
        if "structure mass" in error_lower and "exceeds" in error_lower:
            max_mass = metrics.get("max_structure_mass", 3000.0)
            suggestions.append(f"- Reduce dam mass to be within {max_mass:.0f} kg limit")
            suggestions.append("- Use fewer or smaller beams, or lower density where strength allows")
        elif "build zone" in error_lower:
            suggestions.append("- Place all beams within the dam build zone x=[12, 14], y=[0, 10]")
        elif "error" in error_lower:
            suggestions.append("- Review the error message above to fix the constraint violation")

    elif failed:
        if failure_reason and "design constraint" in failure_reason.lower():
            if "structure mass" in failure_reason.lower():
                max_mass = metrics.get("max_structure_mass", 380.0)
                suggestions.append(f"- Keep total structure mass below {max_mass:.0f} kg")
            if "build zone" in failure_reason.lower():
                suggestions.append("- Ensure all beams are inside the narrow build strips (left x=[12.4,12.6], middle x=[12.9,13.1], or right x=[13.4,13.6])")
            if "right strip" in failure_reason.lower():
                suggestions.append("- At most 2 beams may have centers in the right strip; put the rest in the left and middle strips")
            if "middle strip" in failure_reason.lower():
                suggestions.append("- Exactly one beam center must be in the middle strip x=[12.9, 13.1] (forces bridge connectivity)")
            if "terrain" in failure_reason.lower() or "anchor" in failure_reason.lower():
                suggestions.append("- ZERO floor anchors allowed; the dam must be free-standing, held by water pressure and its own weight")
            if "joint" in failure_reason.lower():
                suggestions.append("- At most 15 beam-to-beam joints allowed; use them to form a single connected structure")
        elif failure_reason and "leakage" in failure_reason.lower():
            suggestions.append("- Mandatory underflow gap: beams cannot extend below y=0.5; minimize gaps; max beam width 0.6 m")
            suggestions.append("- Minimize gaps between beams; ensure the structure spans from left to right strip to block the particles")
        elif failure_reason and "structure integrity" in failure_reason.lower():
            suggestions.append("- Strengthen joints and connections; lateral pressure from water and surges can break joints")
            suggestions.append("- Dam must be free-standing (no floor anchors); use the middle strip beam to bridge and stabilize the columns")

    elif not success:
        limit_pct = metrics.get("leakage_limit_percent", 0.1)
        if metrics.get("leakage_rate_percent", 0) > limit_pct:
            suggestions.append("- Mandatory underflow (no beam below y=0.5); beam width <= 0.6 m; at most 15 joints; leakage must not exceed {:.1f}%".format(limit_pct))
            suggestions.append("- Ensure the dam spans the entire gate; resist nine surges, backward slosh, and three upward surge events")

    return suggestions
