"""
Audited task-specific feedback for D-04: The Swing
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Expose high-resolution physical metrics strictly from evaluator.py.
    """
    parts = []

    if "success" in metrics:
        parts.append(f"**Objective Success**: {'Yes' if metrics['success'] else 'No'}")
    
    if "progress_pct" in metrics:
        parts.append(f"**Height Progress**: {metrics['progress_pct']:.1f}%")

    if "seat_x" in metrics and "seat_y" in metrics:
        parts.append(f"**Final Seat State**: (x: {metrics['seat_x']:.2f} m, y: {metrics['seat_y']:.2f} m)")

    if "swing_angle_deg" in metrics:
        parts.append(f"**Max Swing Amplitude**: {metrics['swing_angle_deg']:.1f}°")

    if "max_seat_y_reached" in metrics:
        parts.append(f"**Peak Altitude Achieved**: {metrics['max_seat_y_reached']:.2f} m")

    if "apex_reached" in metrics:
        parts.append(f"**Apex State Detected**: {'Yes' if metrics['apex_reached'] else 'No'}")

    if "structure_mass" in metrics:
        mass = metrics["structure_mass"]
        limit = metrics.get("max_structure_mass", float('inf'))
        parts.append(f"**Structure Mass**: {mass:.2f} kg / {limit:.1f} kg")

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

    # 1. Energy Pumping Diagnostics
    if failed or not success:
        max_y = metrics.get("max_seat_y_reached", 0.0)
        target_y = metrics.get("target_y_min")
        apex_reached = metrics.get("apex_reached", False)

        if target_y is not None and max_y < target_y:
            suggestions.append("- **Energy Accumulation Deficit**: The swing failed to reach the required altitude. Analyze the synchronization of energy input with the swing's oscillation.")
        
        if not apex_reached and target_y is not None and max_y >= target_y:
            suggestions.append("- **Kinetic Energy Excess at Target**: The seat reached target height but possessed significant velocity. Success requires achieving the target at the trajectory apex.")

    # 2. Timing & Trajectory Diagnostics
    if "apex-in-zone" in msg or "did not succeed" in msg:
        dist_x = metrics.get("distance_to_target_x", 0.0)
        if dist_x > 0:
            suggestions.append("- **Horizontal Alignment Error**: The apex occurred outside the target zone's lateral boundaries. Adjust timing or force distribution.")

    # 3. Structural Constraints
    if "mass" in msg:
        suggestions.append("- **Mass Constraint Violation**: The structure's mass budget is exceeded. Higher mass increases inertia.")
    
    if "build zone" in msg:
        suggestions.append("- **Spatial Violation**: Components were detected outside the valid construction area.")

    return suggestions
