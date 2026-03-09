"""
Audited task-specific feedback for E-03: Slippery World.
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Expose physical and sequential metrics strictly from evaluator.py.
    """
    parts = []

    if "checkpoint_a_reached" in metrics:
        a = "REACHED" if metrics["checkpoint_a_reached"] else "PENDING"
        b = "REACHED" if metrics.get("checkpoint_b_reached") else "PENDING"
        parts.append(f"**Gate Status**: [Alpha: {a}] -> [Beta: {b}]")
    
    if "reached_target" in metrics:
        target = "ENTERED" if metrics["reached_target"] else "NOT REACHED"
        parts.append(f"**Final Objective**: {target}")

    if "progress_pct" in metrics:
        parts.append(f"**Horizontal Range**: {metrics['progress_pct']:.1f}% toward target")

    if "velocity_magnitude" in metrics:
        parts.append(f"**Current Speed**: {metrics['velocity_magnitude']:.3f} m/s")

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
        reached_a = metrics.get("checkpoint_a_reached", False)
        reached_b = metrics.get("checkpoint_b_reached", False)

        if not reached_a:
            suggestions.append("- **Initial Sequence Breach**: Alpha checkpoint was not validated. Initial navigation requires achieving specific elevation (vertical thrust) to intersect with the first gate.")
        elif not reached_b:
            suggestions.append("- **Sequential Discontinuity**: Beta checkpoint was missed after Alpha. Analyze transition timing between horizontal corridors.")

        if failure_reason and "final target" in failure_reason.lower():
            if not reached_a or not reached_b:
                suggestions.append("- **Terminal Lockout**: The target zone exists but cannot be activated until the gate sequence is validated.")
            else:
                suggestions.append("- **Inertial Control Failure**: Final approach failed due to unmanaged momentum. In near-zero friction, proactive inertial braking is required for containment.")

    elif not success:
        suggestions.append("- **Containment Refinement**: Sequence is validated but arrival is unstable. Dissipate velocity before target entry.")

    return suggestions
