"""
Task-specific feedback generation for C-05: The Logic Lock
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Format task-specific metrics for C-05: The Logic Lock.
    Returns process and result physical metrics for feedback (aligned with S_01 style).
    """
    metric_parts = []

    # Primary state
    if "agent_x" in metrics and "agent_y" in metrics:
        metric_parts.append(
            f"**Agent position**: x={metrics['agent_x']:.2f} m, y={metrics['agent_y']:.2f} m"
        )
    if "triggered_switches" in metrics:
        metric_parts.append(
            f"**Triggered switches (order)**: {metrics['triggered_switches']}"
        )
    if "next_required" in metrics:
        metric_parts.append(f"**Next required switch**: {metrics['next_required']}")
    if "progress_percent" in metrics:
        metric_parts.append(f"**Progress**: {metrics['progress_percent']:.1f}% (1/3 = A, 2/3 = B, 3/3 = C)")
    if "sequence_correct" in metrics:
        metric_parts.append(f"**Sequence correct (A->B->C)**: {metrics['sequence_correct']}")
    if "wrong_order" in metrics:
        metric_parts.append(f"**Wrong order**: {metrics['wrong_order']}")
    if "step_count" in metrics:
        metric_parts.append(f"**Simulation steps**: {metrics['step_count']}")
    if "success" in metrics:
        metric_parts.append(f"**Success**: {metrics['success']}")
    if "failed" in metrics and metrics["failed"] and metrics.get("failure_reason"):
        metric_parts.append(f"**Failure reason**: {metrics['failure_reason']}")

    # Physical state block (process/result metrics for debugging)
    metric_parts.append("\n**Physical State Information**:")
    if "agent_x" in metrics and "agent_y" in metrics:
        metric_parts.append(
            f"- Agent position: ({metrics['agent_x']:.3f}, {metrics['agent_y']:.3f}) m"
        )
    if "agent_vx" in metrics and "agent_vy" in metrics:
        metric_parts.append(
            f"- Agent velocity: vx={metrics['agent_vx']:.3f} m/s, vy={metrics['agent_vy']:.3f} m/s"
        )
    if "speed" in metrics:
        metric_parts.append(f"- Speed (magnitude): {metrics['speed']:.3f} m/s")
    if "distance_to_next_zone" in metrics and metrics.get("distance_to_next_zone") is not None:
        metric_parts.append(
            f"- Distance to next required zone: {metrics['distance_to_next_zone']:.3f} m"
        )
    if "steps_in_current_zone" in metrics and "steps_required_to_trigger" in metrics:
        metric_parts.append(
            f"- Steps inside current target zone: {metrics['steps_in_current_zone']} / {metrics['steps_required_to_trigger']} (trigger requires staying)"
        )
    if "cooldown_remaining" in metrics and metrics.get("cooldown_remaining", 0) > 0:
        metric_parts.append(
            f"- Cooldown remaining: {metrics['cooldown_remaining']} steps until next zone can accept"
        )
    metric_parts.append("- Zone centers: A=(2, 2) m, B≈(5, 3.2) m, C=(8, 2) m")

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
    Generate task-specific improvement suggestions for C-05: The Logic Lock.
    """
    suggestions = []

    if error:
        error_lower = error.lower()
        if "apply_agent_force" in error_lower or "get_next_required" in error_lower or "sandbox" in error_lower:
            suggestions.append(
                "- Use only the provided API: get_agent_position(), get_next_required_switch(), "
                "get_triggered_switches(), get_agent_velocity(), apply_agent_force(force_x, force_y)"
            )
        elif "attribute" in error_lower:
            suggestions.append(
                "- Check that you are calling methods on the sandbox (environment) object correctly"
            )

    elif failed:
        if failure_reason and "wrong order" in failure_reason.lower():
            triggered = metrics.get("triggered_switches", [])
            suggestions.append(
                "- You must trigger switches in order: A first, then B, then C. "
                "Do not enter zone B before A, or C before B."
            )
            suggestions.append(
                "- Use get_next_required_switch() to know which zone to go to next. "
                "Use feedback (position, velocity, distance to next zone, zone centers) to move the agent to each zone in order."
            )
            if triggered:
                suggestions.append(
                    f"- Triggered so far: {triggered}. Ensure the next zone you enter is the required one."
                )
        else:
            suggestions.append(
                "- Trigger A, then B, then C in that order. Use get_next_required_switch() and move to the corresponding zone."
            )

    elif not success:
        steps_in = metrics.get("steps_in_current_zone", 0)
        steps_req = metrics.get("steps_required_to_trigger", 1)
        if steps_req > 1 and steps_in < steps_req:
            suggestions.append(
                "- A zone counts as triggered only after the agent remains inside it for enough consecutive steps. "
                "Observe the feedback metric 'Steps inside current target zone' and hold position until the zone registers."
            )
            suggestions.append(
                "- Use apply_agent_force to counteract sliding (e.g. small corrective force toward zone center and strong damping) so you stay inside the zone. If the step count inside the zone resets, try reducing speed while inside."
            )
        suggestions.append(
            "- Implement control: move toward the next_required zone (use feedback for positions); remain inside until it triggers; then proceed. Do not enter B before A or C before B."
        )
        suggestions.append(
            "- Terrain and zone behavior may vary; use feedback (position, velocity, steps inside zone) to infer how to succeed."
        )

    # Stage-aware suggestions based on hidden environment diagnostics (if provided)
    # These metrics are not shown to the agent but are used to craft hints for humans reviewing training runs.
    if metrics.get("env_flag_tight_a_to_b"):
        suggestions.append(
            "- Timing hint: The allowed window between A→B is tight in this stage. Move quickly from A to B after triggering A to ensure B accepts the trigger."
        )
    if metrics.get("env_flag_long_barrier_delay"):
        suggestions.append(
            "- Barrier hint: The gate opens much later after A in this mutation. Consider waiting near the gate (but outside) until the barrier clears, then enter B when allowed. Use cooldown_remaining and steps feedback to time entry."
        )
    if metrics.get("env_flag_strong_repulsion"):
        suggestions.append(
            "- Disturbance hint: There is strong repulsion near targets or gusting forces. Approach zones slowly and aim for low speed when entering; use small corrective forces to stay centered."
        )
    # If stay requirement increased, advise holding longer
    env_trig_steps = metrics.get("env_trigger_stay_steps")
    if env_trig_steps and env_trig_steps > 25:
        suggestions.append(
            f"- Trigger hold hint: This mutation requires staying inside a zone for {env_trig_steps} steps to register a trigger. Hold position steadily until 'Steps inside current target zone' reaches that count."
        )
    # If the C high-path requirement increased, suggest taking elevated path
    if metrics.get("env_c_required_max_y"):
        c_req = metrics.get("env_c_required_max_y")
        suggestions.append(
            f"- Path hint: To trigger C, you may need to reach a higher elevation (max recent y >= {c_req}). Use the ramp to go over B and ensure you hit the elevated path before descending to C."
        )

    return suggestions
