"""
Task-specific feedback generation for C-04: The Escaper
Returns process and outcome physical metrics for feedback (aligned with S_01 style).
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Format task-specific metrics for C-04: The Escaper.
    Include position, velocity, whiskers, progress, and exit-zone distances.
    """
    metric_parts = []

    # Agent position
    if "agent_x" in metrics and "agent_y" in metrics:
        metric_parts.append(
            f"**Agent position**: x={metrics['agent_x']:.2f} m, y={metrics['agent_y']:.2f} m"
        )
    # Exit zone and progress
    if "exit_x_min" in metrics:
        ex = metrics["exit_x_min"]
        ey_min = metrics.get("exit_y_min", 1.0)
        ey_max = metrics.get("exit_y_max", 2.0)
        metric_parts.append(
            f"**Exit zone**: x >= {ex:.1f} m, y in [{ey_min:.1f}, {ey_max:.1f}] m"
        )
    if "progress_x_pct" in metrics:
        metric_parts.append(f"**Progress (x toward exit)**: {metrics['progress_x_pct']:.1f}%")
    if "distance_to_exit_x" in metrics:
        metric_parts.append(
            f"**Distance to exit (x)**: {metrics['distance_to_exit_x']:.2f} m"
        )
    if "distance_y_to_exit_band" in metrics:
        d = metrics["distance_y_to_exit_band"]
        metric_parts.append(
            f"**Distance (y) to exit band**: {d:.2f} m (0 = inside band)"
        )

    # Whisker readings (sensors)
    if "whisker_front" in metrics:
        metric_parts.append(
            f"**Whisker (front, left, right)**: {metrics.get('whisker_front', 0):.2f}, "
            f"{metrics.get('whisker_left', 0):.2f}, {metrics.get('whisker_right', 0):.2f} m"
        )
    # Velocity
    if "agent_vx" in metrics and "agent_vy" in metrics:
        vx, vy = metrics["agent_vx"], metrics["agent_vy"]
        speed = (vx * vx + vy * vy) ** 0.5
        metric_parts.append(
            f"**Agent velocity**: vx={vx:.2f} m/s, vy={vy:.2f} m/s (speed={speed:.2f} m/s)"
        )

    # Outcome
    if "reached_exit" in metrics:
        metric_parts.append(f"**Reached exit**: {metrics['reached_exit']}")
    if "consecutive_steps_in_exit" in metrics:
        metric_parts.append(
            f"**Consecutive steps in exit**: {metrics['consecutive_steps_in_exit']} (need 60 for success)"
        )
    if "step_count" in metrics:
        metric_parts.append(f"**Simulation steps**: {metrics['step_count']}")
    if "success" in metrics:
        metric_parts.append(f"**Success**: {metrics['success']}")
    if "failed" in metrics and metrics["failed"] and metrics.get("failure_reason"):
        metric_parts.append(f"**Failure reason**: {metrics['failure_reason']}")

    # Physical state block (for fine-grained debugging, like S_01)
    if "agent_x" in metrics or "agent_vx" in metrics:
        metric_parts.append("\n**Physical state**")
        if "agent_x" in metrics and "agent_y" in metrics:
            metric_parts.append(
                f"- Position: ({metrics['agent_x']:.3f}, {metrics['agent_y']:.3f}) m"
            )
        if "agent_vx" in metrics and "agent_vy" in metrics:
            metric_parts.append(
                f"- Velocity: vx={metrics['agent_vx']:.3f} m/s, vy={metrics['agent_vy']:.3f} m/s"
            )
        if "whisker_front" in metrics:
            metric_parts.append(
                f"- Whiskers: front={metrics.get('whisker_front', 0):.3f} m, "
                f"left={metrics.get('whisker_left', 0):.3f} m, right={metrics.get('whisker_right', 0):.3f} m"
            )

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
    Generate task-specific improvement suggestions for C-04: The Escaper.
    """
    suggestions = []

    if error:
        error_lower = error.lower()
        if "apply_agent_force" in error_lower or "get_whisker" in error_lower or "sandbox" in error_lower:
            suggestions.append(
                "- Use only the provided API: get_agent_position(), get_whisker_readings(), "
                "get_agent_velocity(), apply_agent_force(force_x, force_y)"
            )
        elif "attribute" in error_lower:
            suggestions.append(
                "- Check that you are calling methods on the sandbox (environment) object correctly"
            )

    elif failed:
        if failure_reason and "timeout" in failure_reason.lower():
            suggestions.append(
                "- Reach the exit zone (x >= 18, y in the narrow band) before the step limit. "
                "Use get_whisker_readings() and get_agent_position() to infer obstacle layout."
            )
            suggestions.append(
                "- The maze has multiple obstacles; passage may require going up in one region "
                "and down in another. Use front/left/right whisker and position to decide when to steer up vs down."
            )
            suggestions.append(
                "- Some regions may resist forward progress or apply vertical/lateral forces. "
                "Use get_agent_velocity() and position to detect and compensate (e.g. stronger forward drive or counter-force)."
            )
            suggestions.append(
                "- The exit y band is narrow; use distance_y_to_exit_band from feedback to learn the exact band and keep y within it."
            )
            suggestions.append(
                "- If you are pushed back when approaching the exit (x near 18), something may be required before the exit can be reached; "
                "the condition may be on your **behavior** (e.g. how you move or apply force for some time), not only on reaching a place — try different behaviors and then attempt the exit."
            )
            suggestions.append(
                "- Success requires holding in the exit zone for 60 consecutive steps, not just reaching it; "
                "use feedback (e.g. consecutive_steps_in_exit) to know when you are holding and when you are pushed out."
            )
            suggestions.append(
                "- If going forward past some point prevents going back, you must satisfy any required condition before crossing that point."
            )
            suggestions.append(
                "- Use position and velocity over time to infer what is required and what must be avoided; "
                "the task is solvable under the given physics."
            )
            suggestions.append(
                "- If velocity readings seem inconsistent with how position changes, "
                "infer velocity from position over time (e.g. store previous position and compute delta)."
            )
            pct = metrics.get("progress_x_pct", 0.0)
            suggestions.append(
                f"- Last progress toward exit was {pct:.1f}%; ensure the agent advances in +x and stays in the exit y band near the exit."
            )
        else:
            suggestions.append(
                "- Use get_whisker_readings() and get_agent_velocity() to infer layout and physics; "
                "apply_agent_force(fx, fy) to move. Goal: reach x >= 18 with y in the exit band."
            )

    elif not success:
        suggestions.append(
            "- Ensure the agent reaches the exit zone (x >= 18, y in narrow band) within the step limit."
        )
        suggestions.append(
            "- Combine whisker-based obstacle avoidance with goal-directed motion toward the exit."
        )

    return suggestions
