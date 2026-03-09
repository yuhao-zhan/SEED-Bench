"""
Task-specific feedback for D-04: The Swing
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Format task-specific metrics for D-04: The Swing.
    Exposes metrics directly from the evaluator.
    """
    parts = []

    if "touched_target" in metrics:
        parts.append(f"**Target Touched**: {'Yes' if metrics['touched_target'] else 'No'}")
    
    if "max_seat_y_reached" in metrics:
        parts.append(f"**Max Seat Height Reached**: {metrics['max_seat_y_reached']:.2f} m")
    
    if "progress_pct" in metrics:
        parts.append(f"**Vertical Progress to Target**: {metrics['progress_pct']:.1f}%")

    if "seat_x" in metrics and "seat_y" in metrics:
        parts.append(f"**Seat Position**: ({metrics['seat_x']:.2f}, {metrics['seat_y']:.2f}) m")
    
    if "seat_speed" in metrics:
        parts.append(f"**Seat Speed**: {metrics['seat_speed']:.2f} m/s")
    
    if "swing_angle_deg" in metrics:
        parts.append(f"**Swing Angle**: {metrics['swing_angle_deg']:.1f}° from vertical")

    if "structure_mass" in metrics:
        mass = metrics["structure_mass"]
        limit = metrics.get("max_structure_mass", 0.0)
        parts.append(f"**Mechanism Mass**: {mass:.2f} kg (Limit: {limit:.1f} kg)")

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
    Generate diagnostic warnings for D-04: The Swing.
    """
    suggestions = []
    
    msg = (error or failure_reason or "").lower()

    # 1. Structural Failures
    if "mass" in msg:
        suggestions.append("- **Mass Constraint**: The pumping mechanism exceeds the structural limit. Analyze weight distribution.")
    if "build zone" in msg:
        suggestions.append("- **Spatial Violation**: Components are placed outside the designated fabrication area.")

    # 2. Performance Diagnostics
    if failed or not success:
        y_peak = metrics.get("max_seat_y_reached", 0.0)
        y_target = metrics.get("target_y_min", 0.0)
        
        if y_peak < y_target:
            suggestions.append("- **Amplitude Deficiency**: The system failed to reach the required altitude. Evaluate the pumping cycle efficiency.")
        
        elif y_peak >= y_target:
            suggestions.append("- **Apex State Mismatch**: The target altitude was achieved, but the system did not meet the stability criteria (v < 1.0 m/s or vertical fall). Analyze timing.")

        if "wind" in msg:
            suggestions.append("- **Phase-Lock Failure**: The system is susceptible to external wind disturbances. Analyze timing rhythm.")

    return suggestions
