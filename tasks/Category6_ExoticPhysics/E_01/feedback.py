"""
Task-specific feedback generation for E-01: Inverted Gravity.
Strictly audited to ensure all metrics are grounded in evaluator.py and limits are dynamic.
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Format task-specific metrics for E-01.
    All metrics are verified against evaluator.py.
    """
    metric_parts = []

    # 1. Temporal & Resource Progress
    if "step_count" in metrics:
        metric_parts.append(f"**Step**: {metrics['step_count']}")
    if "progress_pct" in metrics:
        metric_parts.append(f"**Progress**: {metrics['progress_pct']:.1f}%")
    
    if "structure_mass" in metrics:
        mass = metrics["structure_mass"]
        max_mass = metrics.get("max_structure_mass", 1.0)
        metric_parts.append(f"**Mass**: {mass:.1f} / {max_mass:.1f} kg")

    if "beam_count" in metrics:
        metric_parts.append(f"**Beams**: {metrics['beam_count']} / {metrics.get('max_beam_count', 'N/A')}")
    if "joint_count" in metrics:
        metric_parts.append(f"**Joints**: {metrics['joint_count']}")

    # 2. Gravity State
    if "gravity_current" in metrics and metrics["gravity_current"] is not None:
        gx, gy = metrics["gravity_current"]
        metric_parts.append(f"**Gravity Vector**: ({gx:.2f}, {gy:.2f}) m/s²")

    # 3. Spatial Analysis (Bounding Box)
    if all(k in metrics for k in ("body_y_min", "body_y_max", "arena_y_min", "arena_y_max")):
        y_min, y_max = metrics["body_y_min"], metrics["body_y_max"]
        ay_min, ay_max = metrics["arena_y_min"], metrics["arena_y_max"]
        metric_parts.append(f"**Vertical Envelope**: y=[{y_min:.2f}, {y_max:.2f}] (Arena: [{ay_min:.1f}, {ay_max:.1f}])")

    # 4. Failure Event Data
    if metrics.get("failed"):
        metric_parts.append("\n**Failure Events**:")
        if metrics.get("out_of_bounds"):
            metric_parts.append("- Boundary violation detected: Body centroid exited the arena.")
        if metrics.get("structure_broken"):
            metric_parts.append("- Structural integrity lost: Connection failure between members.")
        if metrics.get("obstacle_overlap"):
            metric_parts.append("- Geometric collision: Interference with static environment obstacles.")
        if metrics.get("forbidden_zone_violation"):
            metric_parts.append("- Restricted zone violation: Member centroid detected in forbidden coordinates.")

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
    Diagnostic suggestions for E-01.
    Strictly describes physical phenomena without dictating design.
    """
    suggestions = []

    if error:
        suggestions.append(f"Design rejection: {error}")
        return suggestions

    if failed:
        # Dynamic check of mass budget
        mass = metrics.get("structure_mass", 0)
        max_mass = metrics.get("max_structure_mass", 1)
        if mass > max_mass * 0.9:
            suggestions.append("The structure is operating near the maximum mass limit, which may increase inertial loads during gravity transitions.")

        # Analysis of failure mode
        if metrics.get("out_of_bounds"):
            gx, gy = metrics.get("gravity_current", (0, 0))
            if gy > 0:
                suggestions.append("Failure occurred while the environment was exerting upward force. The current anchoring system failed to maintain containment.")
            else:
                suggestions.append("Failure occurred under downward gravitational load. The structure likely collapsed or detached.")

        if metrics.get("structure_broken"):
            suggestions.append("Internal stress exceeded joint capacity. Rapid shifts in the gravity vector create significant dynamic loads.")

        if metrics.get("obstacle_overlap") or metrics.get("forbidden_zone_violation"):
            suggestions.append("Collision or placement violation. Re-evaluate the spatial distribution of structural members relative to environment obstacles.")

    elif not success:
        suggestions.append("The structure remains contained but exhibits drift. Consider refining the balance and anchoring to ensure stability over full oscillation cycles.")

    return suggestions
