"""
Task-specific feedback generation for C-03: The Seeker (Rendezvous then Track)
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Format task-specific metrics for C-03: The Seeker (rendezvous then track).
    """
    metric_parts = []

    if "seeker_x" in metrics and "seeker_y" in metrics:
        metric_parts.append(
            f"**Seeker position**: x={metrics['seeker_x']:.2f} m, y={metrics['seeker_y']:.2f} m"
        )
    if "target_x" in metrics and "target_y" in metrics:
        metric_parts.append(
            f"**Target position**: x={metrics['target_x']:.2f} m, y={metrics['target_y']:.2f} m"
        )
    if "distance_to_target" in metrics:
        metric_parts.append(
            f"**Distance to target**: {metrics['distance_to_target']:.2f} m"
        )
    if "activation_achieved" in metrics:
        metric_parts.append(
            f"**Activation condition** (pre-condition for rendezvous to count): {metrics['activation_achieved']}"
        )
    if "rendezvous_count" in metrics:
        metric_parts.append(
            f"**Rendezvous count** (must reach 2; close + match velocity + heading aligned, in narrow time slots): {metrics['rendezvous_count']}/2"
        )
    if "heading_aligned" in metrics:
        metric_parts.append(f"**Heading aligned with target velocity** (required at rendezvous): {metrics['heading_aligned']}")
    if metrics.get("heading_error_deg") is not None:
        metric_parts.append(f"**Heading error vs target velocity**: {metrics['heading_error_deg']:.1f}°")
    if "relative_speed" in metrics:
        metric_parts.append(f"**Relative speed** (|seeker_vel − target_vel|): {metrics['relative_speed']:.3f} m/s")
    if "remaining_impulse_budget" in metrics:
        metric_parts.append(f"**Remaining thrust budget**: {metrics['remaining_impulse_budget']:.1f} N·s")
    if metrics.get("corridor_violation"):
        metric_parts.append("**Corridor**: left allowed bounds")
    track = metrics.get("track_distance", 7.5)
    if "distance_margin" in metrics:
        margin = metrics["distance_margin"]
        status = "within track limit" if margin >= 0 else "EXCEEDED"
        metric_parts.append(f"**Track margin** (limit {track:.1f} m): {margin:.2f} m ({status})")

    if "seeker_vx" in metrics or "seeker_speed" in metrics:
        metric_parts.append("\n**Physical State Information**:")
        if "seeker_vx" in metrics and "seeker_vy" in metrics:
            vx, vy = metrics["seeker_vx"], metrics["seeker_vy"]
            metric_parts.append(f"- Seeker velocity: vx={vx:.3f} m/s, vy={vy:.3f} m/s")
        if "seeker_speed" in metrics:
            metric_parts.append(f"- Seeker speed: {metrics['seeker_speed']:.3f} m/s")
        if "position_error_x" in metrics and "position_error_y" in metrics:
            ex, ey = metrics["position_error_x"], metrics["position_error_y"]
            metric_parts.append(f"- Position error (target - seeker): dx={ex:.3f} m, dy={ey:.3f} m")

    if "step_count" in metrics:
        metric_parts.append(f"\n**Simulation steps**: {metrics['step_count']}")
    if "progress_pct" in metrics:
        metric_parts.append(f"**Progress**: {metrics['progress_pct']:.1f}%")

    if "success" in metrics:
        metric_parts.append(f"**Success**: {metrics['success']}")
    if "failed" in metrics and metrics["failed"] and metrics.get("failure_reason"):
        metric_parts.append(f"**Failure reason**: {metrics['failure_reason']}")

    return metric_parts


def get_improvement_suggestions(
    metrics: Dict[str, Any],
    score: float,
    success: bool,
    failed: bool,
    failure_reason: str = None,
    error: str = None,
) -> List[str]:
    """
    Generate task-specific improvement suggestions for C-03 (rendezvous then track).
    """
    suggestions = []

    if error:
        error_lower = error.lower()
        if "apply_seeker_force" in error_lower or "sandbox" in error_lower:
            suggestions.append(
                "- Use only the provided API: get_seeker_position(), get_seeker_heading(), get_target_position(), "
                "get_seeker_velocity(), apply_seeker_force(force_x, force_y)"
            )
        elif "attribute" in error_lower:
            suggestions.append(
                "- Check that you are calling methods on the sandbox (environment) object correctly"
            )

    elif failed:
        if failure_reason:
            if "thrust budget" in failure_reason.lower() or "out of fuel" in failure_reason.lower():
                suggestions.append(
                    "- You exceeded the thrust impulse budget. Use get_remaining_impulse_budget() every step; "
                    "reduce thrust when close to the target and avoid sustained full thrust to conserve budget."
                )
                suggestions.append(
                    "- Thrust is applied **only along the seeker's current heading**; heading turns toward your commanded direction at a limited rate. Use get_seeker_heading(); command (fx, fy) toward the target so heading aligns — you cannot instantly point the thruster, so plan turn-then-thrust."
                )
            elif "corridor" in failure_reason.lower():
                suggestions.append(
                    "- You left the allowed moving corridor. Use get_corridor_bounds() every step and keep seeker x within (x_min, x_max); "
                    "the bounds change over time, so plan your path accordingly."
                )
            elif "activation condition not satisfied" in failure_reason.lower() or "activation condition" in failure_reason.lower():
                suggestions.append(
                    "- Rendezvous **only counts** after a certain **pre-condition** is satisfied during the run. "
                    "The evaluator reports whether this pre-condition was met. You must discover what action or state "
                    "satisfies it (e.g. staying in a certain region for a sustained period) and do it **before** attempting rendezvous."
                )
            elif "first rendezvous slot missed" in failure_reason.lower():
                suggestions.append(
                    "- Rendezvous counts only in **narrow time slots** (not continuous windows). You must achieve first rendezvous in one of the first-phase slots: close + match velocity + **align seeker heading with target velocity direction** at that moment. Use get_seeker_heading() and estimate target velocity; command thrust direction so heading aligns before/during the slot."
                )
                suggestions.append(
                    "- Phase your approach so you are in the central region, close, velocity-matched, and heading-aligned during one of the slots. Discover slot timing via feedback."
                )
            elif "second rendezvous slot missed" in failure_reason.lower():
                suggestions.append(
                    "- You must achieve rendezvous **again** in one of the **second-phase** time slots (same requirements: close + match velocity + heading aligned with target). Use step_count and feedback to discover the second set of slots; plan two separate rendezvous events."
                )
            elif "rendezvous slot missed" in failure_reason.lower() or "rendezvous window missed" in failure_reason.lower():
                suggestions.append(
                    "- Rendezvous counts only in **narrow time slots**; you need **two** such events (first phase and second phase). At each moment of rendezvous, **seeker heading must be aligned with target velocity direction** — use get_seeker_heading() and target velocity estimate to align."
                )
                suggestions.append(
                    "- The target may react when you get very close; closing too aggressively can make matching velocity harder. Approach while matching velocity from a distance, then close gently."
                )
            elif "rendezvous" in failure_reason.lower() and "not achieved" in failure_reason.lower():
                suggestions.append(
                    "- Achieve rendezvous (very close to target AND matched velocity) within the valid step window. "
                    "Rendezvous **counts only in the central region** of the track and **only during a certain step range** — not near the edges or outside the window. "
                    "Estimate target velocity from position history; when close, thrust to match target velocity."
                )
                suggestions.append(
                    "- Thrust is applied **only along the seeker's current heading**; heading turns toward your commanded direction at a limited rate. Use get_seeker_heading(); command (fx, fy) toward the target so heading aligns — plan turn-then-thrust, not instant direction change."
                )
                suggestions.append(
                    "- Thrust may have temporary cooldown after heavy use; avoid sustained full thrust so you have thrust available when you need it. Use get_remaining_impulse_budget() and get_corridor_bounds()."
                )
            elif "after second rendezvous" in failure_reason.lower() or ("lost" in failure_reason.lower() and "second" in failure_reason.lower()):
                track = metrics.get("track_distance", 8.5)
                suggestions.append(
                    "- After achieving the **second** rendezvous, keep distance within the track limit until the end. "
                    "Use your position history to estimate target velocity and anticipate motion; avoid overshooting."
                )
                dist = metrics.get("distance_to_target")
                if dist is not None:
                    suggestions.append(
                        f"- Last distance was {dist:.2f} m (track limit {track:.1f} m). Tighten control after second rendezvous."
                    )
            elif "after rendezvous" in failure_reason.lower() or "lost" in failure_reason.lower():
                track = metrics.get("track_distance", 8.5)
                suggestions.append(
                    "- After achieving the second rendezvous, keep distance within the track limit until the end. "
                    "Use your position history to estimate target velocity and anticipate motion; avoid overshooting."
                )
                dist = metrics.get("distance_to_target")
                if dist is not None:
                    suggestions.append(
                        f"- Last distance was {dist:.2f} m (track limit {track:.1f} m). Tighten control after second rendezvous."
                    )
        else:
            suggestions.append(
                "- Task requires **two** rendezvous events in **narrow time slots** (discover via feedback), each with close + match velocity + **heading aligned with target velocity**, then track until end."
            )

    elif not success:
        suggestions.append(
            "- Ensure you achieve **two** rendezvous events (close + match velocity + **heading aligned with target velocity**) in two separate time slots (discover via feedback), then maintain distance within the track limit until the end."
        )
        suggestions.append(
            "- Use position history to estimate target velocity; when close, apply control to reduce relative velocity (match target velocity), not just position error."
        )

    return suggestions
