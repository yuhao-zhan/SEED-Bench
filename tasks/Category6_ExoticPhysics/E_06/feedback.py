"""
Task-specific feedback generation for E-06: Cantilever Endurance.
Returns detailed physical metrics for fatigue / joint stress analysis.
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Format task-specific metrics for E-06: Cantilever Endurance.
    Provides process and result physical metrics for feedback.
    """
    metric_parts = []

    # Simulation progress
    if "step_count" in metrics:
        metric_parts.append(f"**Simulation steps**: {metrics['step_count']}")

    # Structure mass
    if "structure_mass" in metrics:
        metric_parts.append(f"**Structure mass**: {metrics['structure_mass']:.2f} kg")
        if "max_structure_mass" in metrics:
            metric_parts.append(f"**Mass limit**: {metrics['max_structure_mass']:.0f} kg")

    # Structure topology
    if "body_count" in metrics:
        metric_parts.append(f"**Beam count**: {metrics['body_count']}")
        if "initial_body_count" in metrics and metrics["body_count"] < metrics["initial_body_count"]:
            metric_parts.append(f"**Beams lost**: {metrics['initial_body_count'] - metrics['body_count']} beam(s) destroyed (e.g. excessive rotation)")
    if "joint_count" in metrics:
        metric_parts.append(f"**Joint count**: {metrics['joint_count']}")
        if "initial_joint_count" in metrics:
            metric_parts.append(f"**Initial joint count**: {metrics['initial_joint_count']}")

    # Structure integrity
    if "structure_broken" in metrics:
        metric_parts.append(
            f"**Structure integrity**: {'BROKEN (fatigue)' if metrics['structure_broken'] else 'INTACT'}"
        )

    # Span check
    if "span_check_passed" in metrics and not metrics.get("span_check_passed", True):
        metric_parts.append(f"**Span/height check**: FAILED - {metrics.get('span_check_message', 'Structure does not meet span or height requirements')}")
    elif "span_check_passed" in metrics:
        metric_parts.append("**Span/height check**: OK")

    # Tip stability (dynamics constraint: rightmost tip must stay in vertical band)
    if "tip_stability_ratio" in metrics:
        ratio = metrics["tip_stability_ratio"]
        req = metrics.get("tip_stability_required", 0.88)
        metric_parts.append(
            f"**Tip stability**: {ratio:.1%} of steps in band (required >= {req:.0%})"
        )
        if "tip_y_last" in metrics and metrics["tip_y_last"] is not None:
            metric_parts.append(f"**Tip y (last)**: {metrics['tip_y_last']:.2f} m")
        if "tip_y_band" in metrics:
            lo, hi = metrics["tip_y_band"]
            metric_parts.append(f"**Tip band**: y in [{lo}, {hi}] m")

    # Joint stress and damage (key for fatigue feedback)
    if "max_joint_damage" in metrics:
        damage = metrics["max_joint_damage"]
        limit = metrics.get("damage_limit", 100.0)
        metric_parts.append(f"**Max joint damage**: {damage:.1f} (limit: {limit:.0f})")
    if "max_joint_force" in metrics:
        max_f = metrics["max_joint_force"]
        limit_f = metrics.get("joint_break_force", 30.0)
        margin_f = limit_f - max_f if limit_f > 0 else 0
        metric_parts.append(
            f"**Max joint reaction force**: {max_f:.2f} N (limit: {limit_f:.0f} N, margin: {margin_f:.2f} N)"
        )
    if "max_joint_torque" in metrics:
        max_t = metrics["max_joint_torque"]
        limit_t = metrics.get("joint_break_torque", 45.0)
        margin_t = limit_t - max_t if limit_t > 0 else 0
        metric_parts.append(
            f"**Max joint reaction torque**: {max_t:.2f} N·m (limit: {limit_t:.0f} N·m, margin: {margin_t:.2f} N·m)"
        )

    # Physical state summary (for debugging fatigue)
    if "max_joint_force" in metrics or "max_joint_torque" in metrics:
        metric_parts.append("\n**Physical State Information**:")
        if "max_joint_force" in metrics:
            metric_parts.append(f"- Peak force seen at any joint: {metrics['max_joint_force']:.3f} N")
        if "max_joint_torque" in metrics:
            metric_parts.append(f"- Peak torque seen at any joint: {metrics['max_joint_torque']:.3f} N·m")
        if "max_joint_damage" in metrics:
            metric_parts.append(f"- Joint damage accumulation: {metrics['max_joint_damage']:.1f} (limit {metrics.get('damage_limit', 100):.0f})")
        if "joint_break_force" in metrics and "joint_break_torque" in metrics:
            metric_parts.append(
                f"- Instant break thresholds: force > {metrics['joint_break_force']:.0f} N or torque > {metrics['joint_break_torque']:.0f} N·m"
            )

    excluded = {
        "step_count", "structure_mass", "max_structure_mass", "joint_count",
        "initial_joint_count", "structure_broken", "success", "failed", "failure_reason",
        "max_joint_force", "max_joint_torque", "joint_break_force", "joint_break_torque",
        "max_joint_damage", "damage_limit", "body_count", "initial_body_count",
        "span_check_passed", "span_check_message",
        "tip_stability_ratio", "tip_stability_required", "tip_y_last", "tip_y_band",
    }
    other = {k: v for k, v in metrics.items() if k not in excluded}
    if other:
        metric_parts.append("\n**Additional metrics**:")
        for k, v in other.items():
            metric_parts.append(f"- {k}: {v:.3f}" if isinstance(v, float) else f"- {k}: {v}")
    return metric_parts


def get_improvement_suggestions(
    metrics: Dict[str, Any], score: float, success: bool, failed: bool,
    failure_reason: str = None, error: str = None
) -> List[str]:
    suggestions = []
    if error:
        err_lower = error.lower()
        if "structure mass" in err_lower and "exceeds" in err_lower:
            max_mass = metrics.get('max_structure_mass', 120.0)
            suggestions.append(
                f"Reduce structure mass to within {max_mass:.0f} kg"
            )
        elif "build zone" in err_lower or "outside build zone" in err_lower:
            suggestions.append("Place all beams inside the build zone (infer limits from feedback)")
        elif "maximum" in err_lower and "beams allowed" in err_lower:
            suggestions.append("Reduce the number of beams; there is a limit on total beams.")
        elif "maximum" in err_lower and "joints allowed" in err_lower:
            suggestions.append("Reduce the number of joints; use a leaner structure.")
        elif "ground anchors" in err_lower and "apart" in err_lower:
            suggestions.append("Ground anchors must be well-spaced; spread them across the structure.")
        elif "maximum" in err_lower and "ground anchors" in err_lower:
            suggestions.append(
                "The number of ground anchors is very limited. Design a cantilever that "
                "relies on a single support (or the allowed count) and spans to the right."
            )
        elif "left support zone" in err_lower or ("anchor" in err_lower and "allowed only" in err_lower):
            suggestions.append(
                "Ground anchors are allowed only in the left support zone. Place anchors there "
                "and design a cantilever structure that spans to the right."
            )
        elif "beam placement" in err_lower and "not allowed" in err_lower or "this region" in err_lower:
            suggestions.append(
                "Beam placement is disallowed in some regions. Use the build error to infer "
                "the forbidden zone (e.g. x range) and route the structure around it or span "
                "across it without placing beam centers inside that zone."
            )
    elif failed:
        if failure_reason and "design constraint" in failure_reason.lower():
            if "mass" in failure_reason.lower():
                max_mass = metrics.get('max_structure_mass', 120.0)
                suggestions.append(
                    f"Keep total structure mass <= {max_mass:.0f} kg"
                )
            if "build zone" in failure_reason.lower():
                suggestions.append("Ensure every beam center is inside the build zone (infer limits from feedback)")
            if "span" in failure_reason.lower() or "extend" in failure_reason.lower() or "height" in failure_reason.lower():
                suggestions.append("Structure must span x from left to right and reach required height.")
                suggestions.append("Check feedback for specific span or height requirements.")
        elif failure_reason and (
            "disintegrat" in failure_reason.lower()
            or "fatigue" in failure_reason.lower()
            or "joint" in failure_reason.lower()
        ):
            suggestions.append(
                "Joints fail under sustained or peak stress. Damage accumulates over time when stress exceeds a threshold."
            )
            suggestions.append(
                "Keep joint forces and torques well below limits; design for load distribution."
            )
            suggestions.append("Ground anchors may be more fragile than beam-beam joints; use structural redundancy.")
            max_f = metrics.get("max_joint_force", 0)
            max_t = metrics.get("max_joint_torque", 0)
            f_lim = metrics.get("joint_break_force", 78.0)
            t_lim = metrics.get("joint_break_torque", 115.0)
            if max_f > f_lim:
                suggestions.append(
                    f"Force exceeded limit ({max_f:.1f} N > {f_lim:.0f} N). "
                    "Add more joints to share the load."
                )
            if max_t > t_lim:
                suggestions.append(
                    f"Torque exceeded limit. Reduce moment arms; use shorter beams or lower structure."
                )
            if metrics.get("max_joint_damage", 0) >= metrics.get("damage_limit", 100):
                suggestions.append(
                    "Damage accumulation caused failure. Reduce sustained stress at joints; avoid prolonged high forces."
                )
            if metrics.get("body_count", 0) < metrics.get("initial_body_count", float("inf")):
                suggestions.append(
                    "Beam(s) were destroyed (e.g. excessive rotation). Use stiffer bracing to limit beam motion."
                )
    elif not success:
        suggestions.append(
            "Design for fatigue: ensure joints can withstand the random impulse loads over the full evaluation."
        )
    return suggestions
