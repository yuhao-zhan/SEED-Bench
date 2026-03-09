"""
Audited task-specific feedback for E-02: Thick Air.
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Expose high-resolution physical metrics strictly from evaluator.py.
    """
    parts = []

    if "progress_x" in metrics:
        parts.append(f"**Horizontal Progress**: {metrics['progress_x']:.1f}% toward target")
    
    if "distance_to_target" in metrics:
        parts.append(f"**Range-to-Objective**: {metrics['distance_to_target']:.2f} m")

    if "heat" in metrics:
        heat = metrics["heat"]
        limit = metrics.get("overheat_limit", 1.0)
        used_pct = (heat / limit * 100) if limit > 0 else 0
        parts.append(f"**Thermal Budget**: {heat:.1f} / {limit:.0f} N·s ({used_pct:.1f}% utilized)")

    if "speed" in metrics:
        parts.append(f"**Current Speed**: {metrics['speed']:.3f} m/s")

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
        heat = metrics.get("heat", 0)
        limit = metrics.get("overheat_limit", 1)
        
        if metrics.get("overheated"):
            suggestions.append("- **Propulsion Efficiency Deficit**: High atmospheric resistance is causing thermal exhaustion. Excessive static thrusting dissipates the heat budget without forward progress.")
            suggestions.append("- **Thermal Accumulation Rate**: Thermal loads are cumulative. Intermittent propulsion or higher-impulse design may improve distance-per-unit-heat.")

        elif not metrics.get("reached_target") and metrics.get("step_count", 0) > 0:
            if limit > 0 and heat < limit * 0.5:
                suggestions.append("- **Insufficient Thrust-to-Drag**: Significant thermal margin remains, but velocity is stalling. The environmental drag force is equal to or greater than current thrust.")
            else:
                suggestions.append("- **Progress Stalled**: Resistance increases significantly at certain coordinates. Map areas where speed drops to conserve energy.")

    return suggestions
