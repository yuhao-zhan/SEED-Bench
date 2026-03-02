"""
Task-specific feedback generation for E-02: Thick Air.
Returns rich physical metrics (position, velocity, heat, progress, distance to target)
for process and outcome feedback, similar to S_01.
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """Format task-specific metrics for E-02 with process and outcome physical metrics."""
    metric_parts = []

    # Simulation progress
    if "step_count" in metrics:
        metric_parts.append(f"**Simulation steps**: {metrics['step_count']}")

    # Craft position and target zone
    if "craft_x" in metrics:
        metric_parts.append(
            f"**Craft position**: x={metrics['craft_x']:.2f} m, y={metrics.get('craft_y', 0):.2f} m"
        )
    if "target_x_min" in metrics:
        metric_parts.append(
            f"**Target zone**: x=[{metrics.get('target_x_min', 28):.0f}, {metrics.get('target_x_max', 32):.0f}], "
            f"y=[{metrics.get('target_y_min', 2):.0f}, {metrics.get('target_y_max', 5):.0f}] m"
        )
    if "reached_target" in metrics:
        metric_parts.append(f"**Reached target**: {'YES' if metrics['reached_target'] else 'NO'}")

    # Heat (cumulative thrust usage) — critical for success
    if "heat" in metrics:
        metric_parts.append(f"**Heat (cumulative thrust)**: {metrics['heat']:.1f} N·s")
        if "overheat_limit" in metrics:
            metric_parts.append(f"**Overheat limit**: {metrics['overheat_limit']:.0f} N·s")
        if "heat_remaining" in metrics:
            metric_parts.append(f"**Heat remaining**: {metrics['heat_remaining']:.1f} N·s")
    if "overheated" in metrics:
        metric_parts.append(f"**Overheated**: {'YES' if metrics['overheated'] else 'NO'}")

    # Velocity and speed
    if "velocity_x" in metrics:
        vx, vy = metrics.get("velocity_x", 0), metrics.get("velocity_y", 0)
        metric_parts.append(f"**Craft velocity**: vx={vx:.2f} m/s, vy={vy:.2f} m/s")
    if "speed" in metrics:
        metric_parts.append(f"**Craft speed**: {metrics['speed']:.2f} m/s")

    # Progress and distance (process metrics)
    if "progress_x" in metrics:
        metric_parts.append(f"**Progress toward target (x)**: {metrics['progress_x']:.1f}%")
    if "dist_traveled_x" in metrics:
        metric_parts.append(f"**Distance traveled (x)**: {metrics['dist_traveled_x']:.2f} m")
    if "distance_to_target" in metrics:
        metric_parts.append(f"**Distance to target zone center**: {metrics['distance_to_target']:.2f} m")

    # Physical state information (fine-grained debugging, like S_01)
    metric_parts.append("\n**Physical State Information**:")
    if "craft_x" in metrics and "craft_y" in metrics:
        metric_parts.append(
            f"- Craft position: ({metrics['craft_x']:.3f}, {metrics['craft_y']:.3f}) m"
        )
    if "velocity_x" in metrics and "velocity_y" in metrics:
        metric_parts.append(
            f"- Craft velocity: vx={metrics['velocity_x']:.3f} m/s, vy={metrics['velocity_y']:.3f} m/s"
        )
    if "speed" in metrics:
        metric_parts.append(f"- Speed magnitude: {metrics['speed']:.3f} m/s")
    if "heat" in metrics:
        metric_parts.append(f"- Heat (cumulative |F|×dt): {metrics['heat']:.3f} N·s")
    if "heat_remaining" in metrics:
        metric_parts.append(f"- Heat remaining before overheat: {metrics['heat_remaining']:.3f} N·s")
    if "distance_to_target" in metrics:
        metric_parts.append(f"- Distance to target center (30, 3.5): {metrics['distance_to_target']:.3f} m")
    if "progress_x" in metrics:
        metric_parts.append(f"- Horizontal progress (start x=8 → target x≥28): {metrics['progress_x']:.1f}%")

    excluded = {
        "step_count", "craft_x", "craft_y", "target_x_min", "target_x_max",
        "target_y_min", "target_y_max", "reached_target", "heat", "overheat_limit",
        "heat_remaining", "overheated", "velocity_x", "velocity_y", "speed",
        "progress_x", "dist_traveled_x", "distance_to_target",
        "success", "failed", "failure_reason",
    }
    other = {k: v for k, v in metrics.items() if k not in excluded}
    if other:
        metric_parts.append("\n**Additional metrics**:")
        for k, v in other.items():
            if isinstance(v, float):
                metric_parts.append(f"- {k}: {v:.3f}")
            else:
                metric_parts.append(f"- {k}: {v}")

    return metric_parts


def get_improvement_suggestions(
    metrics: Dict[str, Any],
    score: float,
    success: bool,
    failed: bool,
    failure_reason: str = None,
    error: str = None,
) -> List[str]:
    """Generate task-specific improvement suggestions for E-02."""
    suggestions = []

    if error:
        err_lower = error.lower()
        if "overheat" in err_lower or "heat" in err_lower:
            suggestions.append("Use shorter or smaller thrust bursts; heat is cumulative (|F| × time).")
            suggestions.append("Aim for an efficient path to reduce total thrust needed.")
        elif "craft" in err_lower or "target" in err_lower:
            suggestions.append("Ensure you call apply_thrust each step to move the craft toward the target zone.")

    elif failed:
        limit_str = f"{metrics.get('overheat_limit', 72000):.0f} N·s" if isinstance(metrics.get('overheat_limit'), (int, float)) else "the reported limit"
        if failure_reason and "overheat" in failure_reason.lower():
            suggestions.append(f"Reduce thrust magnitude or duration; cumulative thrust usage must stay below {limit_str}.")
            suggestions.append("Use feedback: get_craft_position() and get_craft_velocity() to steer with minimal thrust.")
            suggestions.append("Consider coasting when already moving toward the target.")
        elif failure_reason and "cannot move" in failure_reason.lower():
            suggestions.append("Thrust is needed to overcome high drag; apply thrust toward the target (x in [28, 32], y in [2, 5]).")
            suggestions.append(f"Increase thrust when far from target, but stay under the heat limit ({limit_str}).")
            suggestions.append("Check that you call apply_thrust(fx, fy) every simulation step.")

    elif not success:
        limit_str = f"{metrics.get('overheat_limit', 72000):.0f} N·s" if isinstance(metrics.get('overheat_limit'), (int, float)) else "the reported limit"
        suggestions.append(f"Optimize thrust profile: reach the target zone before time runs out while keeping heat below {limit_str}.")

    return suggestions
