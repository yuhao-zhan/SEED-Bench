"""
Audited task-specific feedback for D-06: The Catch
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Expose high-resolution physical and damage metrics strictly from evaluator.py.
    """
    parts = []

    if "balls_caught_count" in metrics and "balls_required_count" in metrics:
        parts.append(f"**Balls Caught**: {metrics['balls_caught_count']} / {metrics['balls_required_count']}")

    if "ball_speed" in metrics:
        parts.append(f"**Lead Ball Speed**: {metrics['ball_speed']:.2f} m/s")
    
    if "ball_speed_vs_threshold" in metrics:
        diff = metrics["ball_speed_vs_threshold"]
        parts.append(f"**Capture Speed Margin**: {diff:+.2f} m/s")

    if "structure_mass" in metrics:
        mass = metrics["structure_mass"]
        limit = metrics.get("max_structure_mass", float('inf'))
        parts.append(f"**System Mass**: {mass:.2f} kg / {limit:.1f} kg")

    if "structure_smashed" in metrics:
        parts.append(f"**Structural Failure**: {'Yes' if metrics['structure_smashed'] else 'No'}")

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

    # 1. Structural Integrity & Impact
    if "structure smashed" in msg or "joint broke" in msg:
        suggestions.append("- **Impulse Overload**: The mechanism failed to absorb momentum safely. Peak joint forces exceeded the structural limit. Analyze the mechanism's damping and energy dissipation.")
    
    # 2. Sequential & Arrival Diagnostics
    if "sequential" in msg:
        suggestions.append("- **Phased Arrival Congestion**: A ball arrived before the previous one was stabilized. The mechanism must reset or clear the zone faster.")

    if "pit failure" in msg:
        suggestions.append("- **Capture Velocity Violation**: A ball reached the lower boundary with excessive speed. Decelerate the balls within the target zone's range.")

    # 3. Energy Dissipation Diagnostics
    if not success and not failed and metrics.get("balls_caught_count", 0) < metrics.get("balls_required_count", 1):
        speed_margin = metrics.get("ball_speed_vs_threshold", 0.0)
        if speed_margin > 0:
            suggestions.append("- **Energy Dissipation Deficit**: Balls are entering the target zone but are moving too fast to be caught. Increase the number of energy-reducing interactions.")

    # 4. Spatial Constraints
    if "forbidden zone" in msg:
        suggestions.append("- **Static Obstruction Violation**: Beams were detected in a prohibited x-coordinate range.")
    
    if "sweeper band" in msg:
        suggestions.append("- **Dynamic Interference Violation**: Beams are located in a swept path, causing collision with moving environmental elements.")

    # 5. Design Constraints
    if "mass" in msg:
        suggestions.append("- **Mass Budget Violation**: The total system mass exceeds design limits.")
    
    if "beam count" in msg:
        suggestions.append("- **Complexity Limit Exceeded**: The design uses more beams than allowed.")

    return suggestions
