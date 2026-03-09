"""
Audited task-specific feedback for D-05: The Hammer
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Expose high-resolution physical metrics strictly from evaluator.py.
    """
    parts = []

    if "shell_broken" in metrics:
        parts.append(f"**Target Shell Status**: {'Broken' if metrics['shell_broken'] else 'Intact'}")
    
    if "hammer_x" in metrics and "hammer_y" in metrics:
        parts.append(f"**Hammer Position**: (x: {metrics['hammer_x']:.2f} m, y: {metrics['hammer_y']:.2f} m)")

    if "speed" in metrics:
        parts.append(f"**Impact Speed**: {metrics['speed']:.2f} m/s")

    if "kinetic_energy" in metrics:
        parts.append(f"**Hammer Kinetic Energy**: {metrics['kinetic_energy']:.2f} J")

    # Obstacle Collision Status
    obs = []
    if metrics.get("hammer_hit_pendulum"): obs.append("Pendulum")
    if metrics.get("hammer_hit_gate") or metrics.get("hammer_hit_gate2"): obs.append("Gate")
    if metrics.get("hammer_hit_wall"): obs.append("Central Wall")
    if metrics.get("hammer_hit_slot_wall"): obs.append("Slot Barrier")
    if metrics.get("hammer_hit_slot_bar"): obs.append("Slot Bar")
    
    if obs:
        parts.append(f"**Collision Detected**: {', '.join(obs)}")

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

    # 1. Impact Force Diagnostics
    if not success and metrics.get("shell_broken") == False and "hit" not in msg:
        suggestions.append("- **Impact Energy Deficit**: The hammer failed to break the shell. Analyze the kinetic energy or instantaneous force at impact.")
        ke = metrics.get("kinetic_energy", 0.0)
        break_force = metrics.get("shell_break_force")
        if break_force is not None and ke > 0 and ke < break_force:
            suggestions.append("- **Momentum Inefficiency**: The impact magnitude appears insufficient relative to the shell's durability.")

    # 2. Timing & Obstacle Diagnostics
    if "pendulum" in msg:
        suggestions.append("- **Aperture-Timing Conflict**: The hammer collided with a pendulum. Analyze the period of oscillation.")
    
    if "gate" in msg:
        suggestions.append("- **Synchronization Error**: The gates were not open during transit. Precisely time the launch relative to the gate cycles.")

    if "wall" in msg:
        suggestions.append("- **Spatial Obstruction**: The direct path to the shell is blocked. Analyze the vertical trajectory requirements.")

    if "slot" in msg:
        suggestions.append("- **Trajectory Precision Error**: The hammer head failed to thread the narrow vertical gap.")

    # 3. Structural/Design Constraints
    if "mass" in msg:
        suggestions.append("- **Mass Limit Violation**: The total mass exceeds the design budget.")
    
    if "build zone" in msg:
        suggestions.append("- **Spatial Violation**: Components were detected outside the valid construction area.")

    return suggestions
