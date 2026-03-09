"""
Task-specific feedback for D-06: The Catch
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Format task-specific metrics for D-06: The Catch.
    Exposes metrics directly from the evaluator.
    """
    parts = []

    if "balls_caught_count" in metrics and "balls_required_count" in metrics:
        caught = metrics["balls_caught_count"]
        required = metrics["balls_required_count"]
        parts.append(f"**Balls Caught**: {caught} / {required}")
    
    if "ball_speed_vs_threshold" in metrics:
        diff = metrics["ball_speed_vs_threshold"]
        status = "Stabilized" if diff <= 0 else "Active"
        parts.append(f"**Projectile Stability**: {status} (Speed Margin: {diff:+.3f} m/s)")

    if "structure_smashed" in metrics:
        parts.append(f"**Structural Failure**: {'Yes' if metrics['structure_smashed'] else 'No'}")
    
    if "max_joint_force_limit" in metrics:
        parts.append(f"**Stress Limit**: {metrics['max_joint_force_limit']:.0f} N")

    if "joint_count" in metrics:
        parts.append(f"**Joint Count**: {metrics['joint_count']}")

    if "structure_mass" in metrics:
        mass = metrics["structure_mass"]
        limit = metrics.get("max_structure_mass", 0.0)
        parts.append(f"**System Mass**: {mass:.2f} kg (Limit: {limit:.1f} kg)")

    if metrics.get("uncaptured_positions"):
        parts.append("**Spatial Coverage Gaps**: Projectiles escaped in specific sectors. Analyze terminal locations.")

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
    Generate diagnostic warnings for D-06: The Catch.
    """
    suggestions = []
    
    msg = (error or failure_reason or "").lower()

    # 1. Structural Failures
    if "mass" in msg:
        suggestions.append("- **Mass Constraint**: The catcher exceeds the weight limit. Analyze density of components.")
    if "anchored" in msg:
        suggestions.append("- **Stability Failure**: The structure is not secured to the environment. Implement rigid ground anchors.")
    if "forbidden" in msg or "sweeper" in msg:
        suggestions.append("- **Spatial Violation**: Components are positioned in restricted sectors.")

    # 2. Performance Diagnostics
    if failed or not success:
        if metrics.get("structure_smashed") or "smashed" in msg:
            suggestions.append("- **Mechanical Overload**: A joint failed under force. Evaluate energy absorption (dampening) and stress distribution.")

        elif "sequential" in msg:
            suggestions.append("- **Absorption Delay**: Projectiles collided or piled up before stabilization. Analyze restitution and dampening.")

        elif "pit" in msg:
            suggestions.append("- **Containment Failure**: A projectile reached a critical failure zone with excessive momentum.")

        elif not metrics.get("ball_caught", False):
            suggestions.append("- **Stabilization Deficiency**: Projectiles entered the capture zone but were not decelerated below the threshold.")

    return suggestions
