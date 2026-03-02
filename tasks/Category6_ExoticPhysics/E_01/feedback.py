"""
Task-specific feedback generation for E-01: Inverted Gravity.
Returns rich physical metrics for process and outcome (aligned with S_01 style).
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """Format task-specific metrics for E-01 with process and outcome indicators."""
    metric_parts = []

    # Simulation progress
    if "step_count" in metrics:
        metric_parts.append(f"**Simulation steps**: {metrics['step_count']}")
    if "progress_pct" in metrics:
        metric_parts.append(f"**Progress**: {metrics['progress_pct']:.1f}%")

    # Structure
    if "structure_mass" in metrics:
        metric_parts.append(f"**Structure mass**: {metrics['structure_mass']:.2f} kg")
        if "max_structure_mass" in metrics:
            metric_parts.append(f"**Mass limit**: {metrics['max_structure_mass']:.0f} kg")
    if "joint_count" in metrics:
        metric_parts.append(f"**Joint count**: {metrics['joint_count']}")
    if "beam_count" in metrics:
        metric_parts.append(f"**Beam count**: {metrics['beam_count']}" + (
            f" (limit: {metrics['max_beam_count']})" if "max_beam_count" in metrics else ""
        ))
    if "body_count" in metrics:
        metric_parts.append(f"**Dynamic body count**: {metrics['body_count']}")

    # Outcome
    if "out_of_bounds" in metrics:
        metric_parts.append(f"**Out of bounds**: {'YES' if metrics['out_of_bounds'] else 'NO'}")
    if "obstacle_overlap" in metrics:
        metric_parts.append(f"**Obstacle overlap**: {'YES' if metrics['obstacle_overlap'] else 'NO'}")
    if "forbidden_zone_violation" in metrics:
        metric_parts.append(f"**Forbidden zone**: {'VIOLATED' if metrics['forbidden_zone_violation'] else 'OK'}")
    if "structure_broken" in metrics:
        metric_parts.append(f"**Structure integrity**: {'BROKEN' if metrics['structure_broken'] else 'INTACT'}")

    # Arena bounds
    if "arena_x_min" in metrics:
        metric_parts.append(
            f"**Arena bounds**: x=[{metrics.get('arena_x_min', 0):.0f}, {metrics.get('arena_x_max', 40):.0f}], "
            f"y=[{metrics.get('arena_y_min', 0):.0f}, {metrics.get('arena_y_max', 20):.0f}]"
        )

    # Physical state: body extent (process indicator)
    if any(k in metrics for k in ("body_x_min", "body_x_max", "body_y_min", "body_y_max")):
        metric_parts.append("\n**Physical State (body extent)**:")
        if metrics.get("body_x_min") is not None:
            metric_parts.append(
                f"- Body extent: x=[{metrics['body_x_min']:.3f}, {metrics['body_x_max']:.3f}], "
                f"y=[{metrics['body_y_min']:.3f}, {metrics['body_y_max']:.3f}]"
            )
        if metrics.get("gravity_current") is not None:
            gx, gy = metrics["gravity_current"]
            metric_parts.append(f"- Gravity at evaluation: ({gx:.2f}, {gy:.2f}) m/s²")

    # Offending positions when out of bounds
    if "offending_positions" in metrics and metrics["offending_positions"]:
        metric_parts.append("**Offending positions (sample)**: " + ", ".join(
            f"({x:.2f}, {y:.2f})" for x, y in metrics["offending_positions"][:5]
        ))
    if metrics.get("obstacle_overlap") and metrics.get("obstacle_offending"):
        metric_parts.append("**Bodies overlapping obstacle**: " + ", ".join(
            f"({x:.2f}, {y:.2f})" for x, y in metrics["obstacle_offending"][:5]
        ))
    if metrics.get("forbidden_zone_violation") and metrics.get("forbidden_offending"):
        metric_parts.append("**Bodies in forbidden zone**: " + ", ".join(
            f"({x:.2f}, {y:.2f})" for x, y in metrics["forbidden_offending"][:5]
        ))

    # Additional metrics
    excluded = {
        "step_count", "progress_pct", "structure_mass", "max_structure_mass", "joint_count", "body_count",
        "out_of_bounds", "obstacle_overlap", "obstacle_offending", "forbidden_zone_violation", "forbidden_offending",
        "structure_broken", "success", "failed", "failure_reason",
        "arena_x_min", "arena_x_max", "arena_y_min", "arena_y_max", "offending_positions",
        "body_x_min", "body_x_max", "body_y_min", "body_y_max", "gravity_current",
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
    """Generate task-specific improvement suggestions for E-01."""
    suggestions = []

    if error:
        err_lower = error.lower()
        if "beams" in err_lower and ("exceeds" in err_lower or "maximum" in err_lower):
            suggestions.append(f"Reduce the number of beams to within the limit (infer from feedback beam_count / max_beam_count)")
            suggestions.append("Use fewer beams per pillar or a simpler bridge topology.")
        elif "structure mass" in err_lower and "exceeds" in err_lower:
            suggestions.append(f"Reduce structure mass to within {metrics.get('max_structure_mass', 500):.0f} kg")
            suggestions.append("Use lower density or smaller beams")
        elif "build zone" in err_lower or "outside build zone" in err_lower:
            suggestions.append("Place all beams inside the build zone (x in [10, 30], y in [5, 15])")
        elif "error building" in err_lower:
            suggestions.append("Check the error message and ensure parameters are within allowed ranges")

    elif failed:
        if failure_reason and "design constraint" in failure_reason.lower():
            if "beams" in failure_reason.lower():
                suggestions.append(f"Use at most {metrics.get('max_beam_count', 12)} beams; infer limit from feedback beam_count / max_beam_count")
                suggestions.append("Use fewer beams per pillar or a simpler bridge topology.")
            if "mass" in failure_reason.lower():
                suggestions.append(f"Keep total structure mass ≤ {metrics.get('max_structure_mass', 500):.0f} kg")
            if "build zone" in failure_reason.lower():
                suggestions.append("Ensure every beam center is inside the build zone (infer limits from feedback)")
        elif failure_reason and "forbidden zone" in failure_reason.lower():
            suggestions.append("At least one beam center lies in a forbidden zone. Redesign so no beam center is placed there; infer the zone from feedback.")
            suggestions.append("Use forbidden_offending positions to infer the forbidden region; move connecting beams above or below it.")
        elif failure_reason and "obstacle" in failure_reason.lower():
            suggestions.append("At least one body overlaps an obstacle. Redesign so no beam center lies in any blocked region.")
            suggestions.append("Use feedback body positions and obstacle-overlap metrics to infer obstacle locations (there may be more than one); route the structure around all of them.")
        elif failure_reason and "out of bounds" in failure_reason.lower():
            suggestions.append("Gravity is time-varying (sometimes upward). Ensure your structure cannot be lifted out of the arena.")
            suggestions.append("Consider anchoring to both floor and ceiling, or using symmetric mass so that net force stays controlled.")
            suggestions.append("Avoid tall or top-heavy structures that can be flipped or lifted when gravity reverses.")
        elif failure_reason and "structure integrity" in failure_reason.lower():
            suggestions.append("Joints are breaking under the changing loads. Use more or stronger connections.")
            suggestions.append("Reduce stress concentrations; distribute anchors.")

    elif not success:
        suggestions.append("Structure may be drifting over time. Add more anchors or balance the design for both gravity directions.")

    return suggestions
