"""
Audited task-specific feedback for D-03: Phase-Locked Gate
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Expose physical metrics strictly grounded in evaluator.py.
    """
    parts = []

    if "success" in metrics:
        parts.append(f"**Objective Success**: {'Yes' if metrics['success'] else 'No'}")
    
    if "x" in metrics:
        parts.append(f"**Final Vehicle Position (x)**: {metrics['x']:.2f} m")

    if "speed" in metrics:
        parts.append(f"**Final Vehicle Speed**: {metrics['speed']:.2f} m/s")

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

    # 1. Collision & Timing Diagnostics
    if "gate collision" in msg:
        suggestions.append("- **Phase-Mismatch**: The vehicle collided with the gate. Analyze the vehicle's arrival timing relative to the gate's oscillation.")
    
    # 2. Speed Band Diagnostics
    if "speed trap" in msg or "speed out of band" in msg:
        suggestions.append("- **Velocity Control Violation**: The vehicle's speed was outside the required range. Adjust energy management to maintain the target velocity profile.")
    
    # 3. Structural Integrity
    if "structure broken" in msg:
        suggestions.append("- **Structural Overload**: Joint forces exceeded limits. Consider distributing loads more evenly to prevent stress concentrations.")
    
    # 4. Range/Progress Diagnostics
    if failed or not success:
        if "gate" not in msg and "speed" not in msg:
            suggestions.append("- **Kinetic Energy Deficit**: The vehicle stopped before reaching the target zone. Analyze energy transfer and friction.")

    # 5. Design Constraint Diagnostics
    if "beam count" in msg:
        suggestions.append("- **Complexity Constraint**: The number of structural elements is outside the permitted range.")
    
    if "mass" in msg:
        suggestions.append("- **Mass Budget Violation**: The total mass exceeds design limits.")

    return suggestions
