"""
Task-specific feedback for D-05: The Hammer
Provides detailed physical metrics for debugging and improvement suggestions.
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Format task-specific metrics for D-05: The Hammer.
    Returns process and result physical metrics similar to S_01.
    """
    parts = []

    # Shell status (always show)
    if "shell_broken" in metrics:
        parts.append(f"**Shell broken**: {'Yes' if metrics['shell_broken'] else 'No'}")
    if "shell_break_force" in metrics:
        parts.append(f"**Break threshold**: {metrics['shell_break_force']:.0f} N")

    # Structure mass
    if "structure_mass" in metrics:
        parts.append(f"**Hammer mass**: {metrics['structure_mass']:.2f} kg")
        if "max_structure_mass" in metrics:
            parts.append(f"**Mass limit**: {metrics['max_structure_mass']:.0f} kg")

    # Simulation steps
    if "step_count" in metrics:
        parts.append(f"**Simulation steps**: {metrics['step_count']}")

    # Shell and target position
    if "shell_x" in metrics:
        parts.append(f"**Shell position**: x={metrics['shell_x']:.2f}m")
        if "shell_y" in metrics:
            parts.append(f"**Shell center**: ({metrics['shell_x']:.2f}, {metrics['shell_y']:.2f}) m")
    if metrics.get("central_wall"):
        parts.append("**Central wall**: vertical barrier at x≈14 m; hammer must pass OVER the wall (high arc) to reach the shell")
    if metrics.get("hammer_hit_wall"):
        parts.append("**Hammer hit wall**: The hammer touched the central wall before reaching the shell; design a high pivot and swing so the head goes OVER the wall.")
    if "shell_y" in metrics and metrics.get("shell_y", 5.0) >= 7.0:
        parts.append(f"**Shell position**: center ({metrics.get('shell_x', 18):.2f}, {metrics['shell_y']:.2f}) m — high; must swing over the wall to reach it")
    if metrics.get("shield_has_window"):
        parts.append("**Shield**: disappears for a short window then reappears; strike must occur during that window")
    if "pendulum_pivot" in metrics:
        parts.append(f"**Pendulum obstacle**: pivot at {metrics['pendulum_pivot']}; rod length ~{metrics.get('pendulum_rod_length', 5.5):.1f}m — time your swing so the head passes when the pendulum clears the path")
    if metrics.get("hammer_hit_pendulum"):
        parts.append("**Hammer hit pendulum**: The hammer touched the swinging rod before reaching the shell; try a different trigger step so the head passes when the pendulum has cleared.")

    # Physical State Information (hammer head)
    if "hammer_x" in metrics or "velocity_x" in metrics or "speed" in metrics:
        parts.append("\n**Physical State (Hammer Head)**:")
        if "hammer_x" in metrics and "hammer_y" in metrics:
            parts.append(f"- Hammer head position: ({metrics['hammer_x']:.3f}, {metrics['hammer_y']:.3f}) m")
        if "velocity_x" in metrics and "velocity_y" in metrics:
            parts.append(f"- Hammer velocity: vx={metrics['velocity_x']:.3f} m/s, vy={metrics['velocity_y']:.3f} m/s")
        if "speed" in metrics:
            parts.append(f"- Hammer speed: {metrics['speed']:.3f} m/s")
        if "angular_velocity" in metrics:
            parts.append(f"- Hammer angular velocity: {metrics['angular_velocity']:.3f} rad/s")
        if "kinetic_energy" in metrics:
            parts.append(f"- Hammer kinetic energy: {metrics['kinetic_energy']:.2f} J")

    # Distance to shell (if both positions available)
    if "hammer_x" in metrics and "shell_x" in metrics:
        dx = metrics["shell_x"] - metrics["hammer_x"]
        parts.append(f"- Distance to shell (x): {dx:.2f} m")

    excluded = {"success", "failed", "failure_reason", "step_count", "structure_mass", "max_structure_mass",
                "shell_broken", "shell_break_force", "shell_x", "shell_y", "hammer_x", "hammer_y",
                "velocity_x", "velocity_y", "speed", "angular_velocity", "kinetic_energy", "hammer_hit_pendulum", "hammer_hit_gate", "hammer_hit_wall", "central_wall"}
    other = {k: v for k, v in metrics.items() if k not in excluded}
    if other:
        parts.append("\n**Additional Metrics**:")
        for k, v in other.items():
            if isinstance(v, (int, float)):
                parts.append(f"- {k}: {v:.3f}" if isinstance(v, float) else f"- {k}: {v}")
            else:
                parts.append(f"- {k}: {v}")

    return parts


def get_improvement_suggestions(metrics: Dict[str, Any], score: float, success: bool, failed: bool,
                                failure_reason: str = None, error: str = None) -> List[str]:
    """Generate task-specific improvement suggestions for D-05: The Hammer."""
    suggestions = []

    if error:
        error_lower = error.lower()
        if "structure mass" in error_lower and "exceeds" in error_lower:
            max_mass = metrics.get("max_structure_mass", 70.0)
            suggestions.append(f"- Reduce hammer mass to stay within {max_mass:.0f} kg limit")
            suggestions.append("- Use lower density for arm; concentrate mass in hammer head only")
        if "build zone" in error_lower or "outside" in error_lower:
            suggestions.append("- Place all beam centers inside build zone x=[2, 12], y=[2, 8]")

    elif failed:
        if failure_reason and "design constraint" in (failure_reason or "").lower():
            if "mass" in (failure_reason or "").lower():
                suggestions.append("- Reduce total mass below 70 kg")
            if "build zone" in (failure_reason or "").lower():
                suggestions.append("- Keep all parts inside build zone x=[2, 12], y=[2, 8]")
        elif failure_reason and "bar" in (failure_reason or "").lower():
            suggestions.append("- Hammer hit the oscillating bar. The bar at x=15 moves up and down; you must time your release or swing speed so the head passes through the gap when the bar is at its highest or lowest point.")
        elif failure_reason and "slot" in (failure_reason or "").lower():
            suggestions.append("- Hammer hit the slot wall at x=15. Design a trajectory that passes through the narrow gap (y ≈ 1.85 to 3.35) to reach the shell.")
        elif failure_reason and "pendulum" in (failure_reason or "").lower():
            suggestions.append("- The hammer must NOT touch the swinging pendulum at x=7. Try different trigger steps so the pendulum rod has swung out of the path when your hammer head passes.")
        elif failure_reason and "shell not broken" in (failure_reason or "").lower():
            suggestions.append("- The shell at (16.0, 2.6) was not broken. Ensure your hammer has enough kinetic energy (high speed + heavy head) to deliver a force > 5000 N.")
            suggestions.append("- Check if you hit the slot wall or oscillating bar first, which drains energy. Thread the needle through the gap at x=15.")
            break_force = metrics.get("shell_break_force", 5000)
            suggestions.append(f"- Shell breaks when impact force exceeds {break_force:.0f} N; use sufficient swing speed.")

    elif not success:
        if not metrics.get("shell_broken", False):
            suggestions.append("- Shell was not broken. Ensure you pass through the slot at x=15 and hit the shell at (16, 2.6) with enough speed.")

    return suggestions
