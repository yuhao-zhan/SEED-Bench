"""
Task-specific feedback generation for C-02: The Lander (hard variant)
Returns rich physical metrics: position, velocity, angle, zone, height, landing outcome.
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Format task-specific metrics for C-02: Box lander with zone and attitude.
    """
    metric_parts = []

    if "lander_x" in metrics and "lander_y" in metrics:
        metric_parts.append(
            f"**Lander position**: x={metrics['lander_x']:.2f} m, y={metrics['lander_y']:.2f} m"
        )
    if "zone_x_min" in metrics and "zone_x_max" in metrics:
        metric_parts.append(
            f"**Landing zone (x) at this step**: [{metrics['zone_x_min']:.2f}, {metrics['zone_x_max']:.2f}] m"
        )
    if "height_above_ground" in metrics:
        h = metrics["height_above_ground"]
        metric_parts.append(
            f"**Height above ground**: {h:.2f} m"
            + (" (landed)" if h <= 0 else " (in flight)")
        )

    if "lander_vx" in metrics and "lander_vy" in metrics:
        metric_parts.append(
            f"**Lander velocity**: vx={metrics['lander_vx']:.2f} m/s, vy={metrics['lander_vy']:.2f} m/s"
        )
    if "lander_angle" in metrics:
        a = metrics["lander_angle"]
        a_deg = a * 180 / 3.14159
        metric_parts.append(f"**Lander angle**: {a:.3f} rad ({a_deg:.1f}°)")
    if "lander_angular_velocity" in metrics:
        metric_parts.append(
            f"**Angular velocity**: {metrics['lander_angular_velocity']:.3f} rad/s"
        )
    if "speed" in metrics:
        metric_parts.append(f"**Speed (magnitude)**: {metrics['speed']:.2f} m/s")
    if "max_safe_vertical_speed" in metrics:
        metric_parts.append(
            f"**Max safe vertical speed at landing**: {metrics['max_safe_vertical_speed']:.1f} m/s"
        )
    if "max_landing_angle" in metrics:
        a_lim = metrics["max_landing_angle"]
        metric_parts.append(
            f"**Max landing tilt (upright)**: {a_lim:.2f} rad ({a_lim*180/3.14159:.1f}°)"
        )
    if "remaining_fuel" in metrics and metrics["remaining_fuel"] is not None:
        metric_parts.append(f"**Remaining fuel**: {metrics['remaining_fuel']:.1f} N·s")
    if "min_fuel_remaining_at_landing" in metrics and metrics["min_fuel_remaining_at_landing"] is not None:
        metric_parts.append(
            f"**Min fuel required at landing**: {metrics['min_fuel_remaining_at_landing']:.0f} N·s "
            "(land with at least this much fuel to pass)"
        )

    if "landed" in metrics:
        metric_parts.append(f"**Landed**: {metrics['landed']}")
    if "landing_vy" in metrics and metrics["landing_vy"] is not None:
        vy = metrics["landing_vy"]
        limit = metrics.get("max_safe_vertical_speed", 5.0)
        metric_parts.append(
            f"**Landing vertical speed**: {vy:.2f} m/s "
            f"(limit {limit:.1f} m/s, {'OK' if abs(vy) <= limit else 'EXCEEDED'})"
        )
    if "landing_x" in metrics and metrics["landing_x"] is not None:
        lx = metrics["landing_x"]
        zmin = metrics.get("zone_x_min", 12.0)
        zmax = metrics.get("zone_x_max", 18.0)
        in_zone = zmin <= lx <= zmax
        ls = metrics.get("landing_step")
        step_note = f" at step {ls}" if ls is not None else ""
        metric_parts.append(
            f"**Landing x**: {lx:.2f} m (valid zone{step_note} [{zmin:.2f}, {zmax:.2f}] m, {'OK' if in_zone else 'OUT OF ZONE'})"
        )
    if "landing_angle" in metrics and metrics["landing_angle"] is not None:
        la = metrics["landing_angle"]
        a_lim = metrics.get("max_landing_angle", 0.25)
        metric_parts.append(
            f"**Landing angle**: {la:.3f} rad (limit ±{a_lim:.2f} rad, {'OK' if abs(la) <= a_lim else 'CAPSIZED'})"
        )
    if "landing_step" in metrics and metrics["landing_step"] is not None:
        metric_parts.append(f"**Landing step**: {metrics['landing_step']} (valid zone at this step is time-dependent)")

    if "step_count" in metrics:
        metric_parts.append(f"**Simulation steps**: {metrics['step_count']}")
    if "success" in metrics:
        metric_parts.append(f"**Success**: {metrics['success']}")
    if "failed" in metrics and metrics["failed"] and metrics.get("failure_reason"):
        metric_parts.append(f"**Failure reason**: {metrics['failure_reason']}")

    metric_parts.append("\n**Physical State (detail)**")
    if "lander_x" in metrics and "lander_y" in metrics:
        metric_parts.append(
            f"- Position: ({metrics['lander_x']:.3f}, {metrics['lander_y']:.3f}) m"
        )
    if "lander_vx" in metrics and "lander_vy" in metrics:
        metric_parts.append(
            f"- Velocity: vx={metrics['lander_vx']:.3f} m/s, vy={metrics['lander_vy']:.3f} m/s"
        )
    if "lander_angle" in metrics:
        metric_parts.append(f"- Angle: {metrics['lander_angle']:.3f} rad")
    if "height_above_ground" in metrics:
        metric_parts.append(f"- Height above ground: {metrics['height_above_ground']:.3f} m")

    return metric_parts


def get_improvement_suggestions(
    metrics: Dict[str, Any],
    score: float,
    success: bool,
    failed: bool,
    failure_reason: str = None,
    error: str = None,
) -> List[str]:
    """Generate task-specific improvement suggestions for C-02 (hard variant)."""
    suggestions = []

    if error:
        error_lower = error.lower()
        if "apply_thrust" in error_lower or "get_lander" in error_lower:
            suggestions.append(
                "- Use only the provided API: get_lander_position(), get_lander_angle(), "
                "get_lander_angular_velocity(), get_remaining_fuel(), apply_thrust(main_thrust, steering_torque). "
                "Velocity is not in the API; infer it from position history if needed."
            )
        elif "attribute" in error_lower:
            suggestions.append(
                "- Check that you are calling methods on the sandbox (environment) object correctly"
            )

    elif failed:
        if failure_reason:
            fr = failure_reason.lower()
            if "impact speed" in fr:
                suggestions.append(
                    "- Velocity is not directly observable; **estimate vertical velocity from position history** "
                    "(e.g. (y - y_prev) / (step_delta * dt)) and use that estimate to control descent."
                )
                suggestions.append(
                    "- Reduce vertical speed at touchdown: use main thrust to slow descent; "
                    "keep craft upright for effective braking. Use your velocity estimate for feedback."
                )
            elif "out of landing zone" in fr or "zone" in fr:
                suggestions.append(
                    "- The valid landing zone may depend on **when** you touch down (e.g. on step/time). "
                    "Use feedback: compare landing_step and the reported zone to infer how zone position relates to time."
                )
                suggestions.append(
                    "- You may need to **predict** where the valid zone will be at your expected touchdown time "
                    "and steer the lander to that position (trajectory prediction + moving target)."
                )
            elif "forbidden zone" in fr or "obstacle" in fr:
                suggestions.append(
                    "- There is a **no-fly zone** between start and the landing area. "
                    "You must **go around** it: climb above a safe height first, then move to the landing side, then descend."
                )
                suggestions.append(
                    "- Do not fly directly toward the landing zone at low altitude; that path enters the obstacle. "
                    "Use a multi-phase trajectory: (1) climb, (2) cross above/around the obstacle, (3) descend and land."
                )
            elif "insufficient fuel" in fr or "fuel remaining" in fr:
                suggestions.append(
                    "- Success requires landing with **at least a minimum amount of fuel remaining** (fuel-efficient trajectory). "
                    "Use feedback to see the required minimum and your remaining fuel at landing."
                )
                suggestions.append(
                    "- Reduce thrust when possible: coast during fall, use moderate thrust for climb/cross, "
                    "and avoid continuous high thrust; plan a trajectory that conserves fuel."
                )
            elif "fuel exhausted" in fr.lower():
                suggestions.append(
                    "- Fuel is limited; use fuel-efficient descent: fall when high, burn only when close to ground."
                )
                suggestions.append("- Check get_remaining_fuel() and avoid continuous high thrust during fall.")
            elif "capsized" in fr or "angle" in fr:
                suggestions.append(
                    "- Land roughly upright: use steering torque to keep angle near zero; "
                    "excessive tilt at touchdown fails (capsized)."
                )
                suggestions.append(
                    "- PD control on angle: steering_torque = -Kp*angle - Kd*angular_velocity."
                )
        else:
            suggestions.append(
                "- Soft land within the zone and upright; use get_lander_angle() and steering, "
                "and main thrust for vertical control; infer limits from feedback."
            )

    elif not success:
        suggestions.append(
            "- Ensure the craft reaches the ground with vertical speed within limit, "
            "x within zone, and angle within limit; use feedback metrics to tune."
        )
        suggestions.append(
            "- Control attitude (angle) with steering_torque; control position with main thrust and attitude."
        )

    return suggestions
