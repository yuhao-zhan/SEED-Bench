"""
Task-specific feedback for D-03: Phase-Locked Gate.
Metrics: gate crossing, gate-open timing, target reach, final speed, structure mass.
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """Format task-specific metrics for D-03: Phase-Locked Gate."""
    parts = []

    if "gate_crossed" in metrics:
        parts.append(f"**Gate (x=10) crossed**: {'Yes' if metrics['gate_crossed'] else 'No'}")
    if "gate_was_open_when_crossed" in metrics:
        parts.append(
            f"**Gate was open when crossed**: {'Yes' if metrics['gate_was_open_when_crossed'] else 'No'} "
            "(must be Yes to pass)"
        )
    if "target_reached" in metrics:
        x_min = metrics.get("target_x_min", 11.75)
        parts.append(f"**Target x≥{x_min} reached**: {'Yes' if metrics['target_reached'] else 'No'}")
    if "final_speed" in metrics and metrics["final_speed"] is not None:
        lo = metrics.get("target_speed_min", 0.45)
        hi = metrics.get("target_speed_max", 2.6)
        parts.append(
            f"**Final speed at target**: {metrics['final_speed']:.2f} m/s "
            f"(required: [{lo:.1f}, {hi:.1f}] m/s)"
        )
    if "structure_mass" in metrics:
        parts.append(f"**Structure mass (beams)**: {metrics['structure_mass']:.2f} kg")
    if "beam_count" in metrics:
        parts.append(f"**Beam count**: {metrics['beam_count']} (max 5)")
    if "step_count" in metrics:
        parts.append(f"**Simulation steps**: {metrics['step_count']}")

    excluded = {
        "gate_crossed", "gate_was_open_when_crossed", "target_reached", "final_speed",
        "target_speed_min", "target_speed_max", "structure_mass", "beam_count",
        "success", "failed", "failure_reason", "step_count",
    }
    other = {k: v for k, v in metrics.items() if k not in excluded}
    if other:
        parts.append("\n**Additional metrics**:")
        for k, v in other.items():
            parts.append(f"- {k}: {v:.3f}" if isinstance(v, float) else f"- {k}: {v}")
    return parts


def get_improvement_suggestions(
    metrics: Dict[str, Any],
    score: float,
    success: bool,
    failed: bool,
    failure_reason: str = None,
    error: str = None,
) -> List[str]:
    """Generate task-specific improvement suggestions for D-03: Phase-Locked Gate."""
    suggestions = []
    if error:
        err_lower = error.lower()
        if "mass" in err_lower and "exceeds" in err_lower:
            suggestions.append("- Keep total structure mass (beams) below 14 kg")
        if "beam" in err_lower and "count" in err_lower:
            suggestions.append("- Use at most 5 beams")
        if "build zone" in err_lower or "outside" in err_lower:
            suggestions.append("- Place all beam centers inside build zone x=[4.8, 9.0], y=[2, 3.2]")

    elif failed:
        if failure_reason and "design constraint" in failure_reason.lower():
            if "mass" in failure_reason.lower():
                suggestions.append("- Reduce total beam mass below 14 kg")
            if "beam" in failure_reason.lower():
                suggestions.append("- Use at most 5 beams; keep beams in build zone")
        elif failure_reason and "collided" in failure_reason.lower() and "gate" in failure_reason.lower():
            suggestions.append("- Time the cart so it crosses x=10 only when the gate is open (rod nearly vertical)")
            suggestions.append("- Use beam mass and position to shift arrival time; sinusoidal wind changes trajectory")
            suggestions.append("- Avoid beams that stick out forward and hit the gate rod")
        elif failure_reason and "target" in failure_reason.lower():
            suggestions.append("- Ensure the cart reaches x≥11.75 and final speed is in [0.45, 2.6] m/s")
        elif failure_reason and "speed" in failure_reason.lower():
            suggestions.append("- Tune mass so that after passing the gate the cart reaches x=11.75 with speed in [0.45, 2.6] m/s")

    elif not success:
        if not metrics.get("gate_was_open_when_crossed", False):
            suggestions.append("- Design so the cart crosses the gate when the rod is vertical (phase-lock arrival time)")
        if not metrics.get("target_reached", False):
            suggestions.append("- Ensure the cart reaches x≥11.75")
        if metrics.get("final_speed") is not None:
            lo, hi = metrics.get("target_speed_min", 0.45), metrics.get("target_speed_max", 2.6)
            if metrics["final_speed"] < lo:
                suggestions.append(f"- Increase momentum so final speed is at least {lo} m/s")
            elif metrics["final_speed"] > hi:
                suggestions.append(f"- Add mass or drag so final speed is at most {hi} m/s")

    return suggestions
