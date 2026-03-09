"""
Audited task-specific feedback for E-01: Inverted Gravity.
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Expose high-resolution physical metrics strictly from evaluator.py.
    """
    parts = []

    if "progress_pct" in metrics:
        parts.append(f"**Temporal Progress**: {metrics['progress_pct']:.1f}%")
    
    if "structure_mass" in metrics:
        mass = metrics["structure_mass"]
        limit = metrics.get("max_structure_mass", float('inf'))
        parts.append(f"**Structural Mass**: {mass:.2f} kg / {limit:.1f} kg")

    if "beam_count" in metrics:
        parts.append(f"**Complexity**: {metrics['beam_count']} beams / {metrics.get('max_beam_count', 'N/A')} max")

    if "gravity_current" in metrics and metrics["gravity_current"] is not None:
        gx, gy = metrics["gravity_current"]
        parts.append(f"**Instantaneous Gravity**: ({gx:.2f}, {gy:.2f}) m/s²")

    if all(k in metrics for k in ("body_y_min", "body_y_max", "arena_y_min", "arena_y_max")):
        y_min, y_max = metrics["body_y_min"], metrics["body_y_max"]
        ay_min, ay_max = metrics["arena_y_min"], metrics["arena_y_max"]
        parts.append(f"**Vertical Envelope**: y=[{y_min:.2f}, {y_max:.2f}] (Arena: [{ay_min:.1f}, {ay_max:.1f}])")

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
    msg = (error or failure_reason or "").lower()

    if failed:
        mass = metrics.get("structure_mass", 0)
        max_m = metrics.get("max_structure_mass", 1)
        if max_m > 0 and mass > max_m * 0.95:
            suggestions.append("- **Mass-Containment Balance**: The structure is operating near the maximum mass budget. High mass increases inertial loads during gravity reversals.")

        if metrics.get("out_of_bounds"):
            gx, gy = metrics.get("gravity_current", (0, 0))
            if gy > 0:
                suggestions.append("- **Containment Failure (Upward Phase)**: The structure left the arena during a positive vertical gravity event. The current anchoring is insufficient for inverted loads.")
            else:
                suggestions.append("- **Containment Failure (Downward Phase)**: The structure left the arena during standard or lateral gravity.")

        if metrics.get("structure_broken"):
            suggestions.append("- **Structural Disintegration**: Joint forces exceeded limits during dynamic gravity shifts.")

        if metrics.get("obstacle_overlap") or metrics.get("forbidden_zone_violation"):
            suggestions.append("- **Spatial Violation**: Components detected in restricted or obstacle zones.")

    return suggestions
