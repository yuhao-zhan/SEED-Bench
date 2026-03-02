"""
Task-specific feedback for D-04: The Swing
Returns process and result physical metrics for refinement (aligned with S_01 style).
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    parts = []
    # Seat position and target (always show if available)
    if "seat_x" in metrics:
        parts.append(f"**Swing seat position**: x={metrics['seat_x']:.2f} m, y={metrics['seat_y']:.2f} m")
        if "target_y_min" in metrics:
            parts.append(
                f"**Target zone**: y >= {metrics['target_y_min']:.1f} m, "
                f"x in [{metrics.get('target_x_min', 9):.1f}, {metrics.get('target_x_max', 11):.1f}] m"
            )
        if "max_seat_y_reached" in metrics:
            parts.append(f"**Max height reached (so far)**: {metrics['max_seat_y_reached']:.2f} m")
    elif "target_y_min" in metrics:
        parts.append(
            f"**Target zone**: y >= {metrics['target_y_min']:.1f} m, "
            f"x in [{metrics.get('target_x_min', 9):.1f}, {metrics.get('target_x_max', 11):.1f}] m"
        )

    # Velocity and speed
    if "seat_speed" in metrics:
        parts.append(f"**Seat speed**: {metrics['seat_speed']:.2f} m/s")
        if "seat_vx" in metrics and "seat_vy" in metrics:
            parts.append(
                f"**Velocity components**: vx={metrics['seat_vx']:.2f} m/s, vy={metrics['seat_vy']:.2f} m/s"
            )

    # Progress and gap to target
    if "progress_pct" in metrics:
        parts.append(f"**Height progress toward target**: {metrics['progress_pct']:.1f}%")
    if "height_gap_to_target" in metrics:
        parts.append(f"**Height gap to target**: {metrics['height_gap_to_target']:.2f} m")
    if "distance_to_target_x" in metrics and metrics.get("distance_to_target_x", 0) > 0:
        parts.append(f"**Horizontal distance to target zone**: {metrics['distance_to_target_x']:.2f} m")

    # Swing angle (physical state)
    if "swing_angle_deg" in metrics:
        parts.append(f"**Swing angle (from vertical)**: {metrics['swing_angle_deg']:.1f}°")

    # Structure mass and limit
    if "structure_mass" in metrics:
        parts.append(f"**Mechanism mass**: {metrics['structure_mass']:.2f} kg")
        if "max_structure_mass" in metrics:
            parts.append(f"**Mass limit**: {metrics['max_structure_mass']:.0f} kg")

    # Simulation and outcome
    if "step_count" in metrics:
        parts.append(f"**Simulation steps**: {metrics['step_count']}")
    if "touched_target" in metrics:
        parts.append(f"**Target touched**: {'Yes' if metrics['touched_target'] else 'No'}")

    # Physical state block (like S_01)
    if any(k in metrics for k in ("seat_x", "seat_y", "seat_vx", "seat_vy", "swing_angle_deg")):
        parts.append("\n**Physical state**")
        if "seat_x" in metrics and "seat_y" in metrics:
            parts.append(f"- Seat position: ({metrics['seat_x']:.3f}, {metrics['seat_y']:.3f}) m")
        if "seat_vx" in metrics and "seat_vy" in metrics:
            parts.append(
                f"- Seat velocity: vx={metrics['seat_vx']:.3f} m/s, vy={metrics['seat_vy']:.3f} m/s"
            )
        if "swing_angle_deg" in metrics:
            parts.append(f"- Swing angle: {metrics['swing_angle_deg']:.2f}° from vertical")

    excluded = {
        "seat_x", "seat_y", "seat_vx", "seat_vy", "seat_speed",
        "target_y_min", "target_x_min", "target_x_max",
        "success", "failed", "failure_reason", "step_count",
        "structure_mass", "max_structure_mass", "touched_target",
        "max_seat_y_reached", "height_gap_to_target", "swing_angle_deg",
        "progress_pct", "distance_to_target_x",
    }
    other = {k: v for k, v in metrics.items() if k not in excluded}
    if other:
        parts.append("\n**Other metrics**")
        for k, v in other.items():
            parts.append(f"- {k}: {v:.3f}" if isinstance(v, float) else f"- {k}: {v}")
    return parts


def get_improvement_suggestions(
    metrics: Dict[str, Any],
    score: float,
    success: bool,
    failed: bool,
    failure_reason: str = None,
    error: str = None,
) -> List[str]:
    suggestions = []
    if error:
        if "structure mass" in error.lower() and "exceeds" in error.lower():
            suggestions.append("- Reduce mechanism mass to stay within 150 kg")
        if "build zone" in error.lower() or "outside" in error.lower():
            suggestions.append("- Place all beam centers inside build zone x=[6, 14], y=[4, 10]")
    elif failed:
        if failure_reason and "design constraint" in (failure_reason or "").lower():
            if "mass" in (failure_reason or "").lower():
                suggestions.append("- Reduce total mass below 150 kg")
            if "build zone" in (failure_reason or "").lower():
                suggestions.append("- Keep all parts inside build zone x=[6, 14], y=[4, 10]")
        elif failure_reason and ("did not succeed" in (failure_reason or "").lower() or "apex" in (failure_reason or "").lower() or "vertical" in (failure_reason or "").lower()):
            suggestions.append(
                "- Success requires (1) apex in zone: seat in red zone with speed < 1.0 m/s, OR "
                "(2) vertical fall into zone: in red zone with vy < 0 and |vx| < 1.35 m/s after an apex."
            )
            suggestions.append(
                "- Control energy so the highest point (apex, v≈0) lands inside the red zone; "
                "stop or reduce pumping when high so you do not over-pump past the zone."
            )
            suggestions.append(
                "- Use wind-aware pumping (get_wind_force_at_time) and phase-correct pumping; "
                "avoid pumping when wind strongly opposes."
            )
            max_y = metrics.get("max_seat_y_reached", 0)
            target_y = metrics.get("target_y_min", 11.7)
            if max_y < target_y and max_y > 0:
                suggestions.append(f"- Max height reached was {max_y:.1f} m; need apex or vertical fall in zone (y >= {target_y} m).")
    elif not success:
        target_y = metrics.get("target_y_min", 11.7)
        if metrics.get("seat_y", 0) < target_y:
            suggestions.append(f"- Reach zone (y >= {target_y} m) at apex (speed < 1.0 m/s) or while falling vertically (|vx| < 1.35 m/s, vy < 0).")
        if metrics.get("max_seat_y_reached", 0) < target_y and metrics.get("max_seat_y_reached", 0) > 0:
            suggestions.append(
                f"- Max height so far: {metrics['max_seat_y_reached']:.1f} m; use wind-aware pumping or tune phase"
            )
    return suggestions
