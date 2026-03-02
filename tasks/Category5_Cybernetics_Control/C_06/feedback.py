"""
Task-specific feedback generation for C-06: The Governor
Returns rich physical metrics for process and result (aligned with S_01 style).
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Format task-specific metrics for C-06: The Governor.
    Provides process and result physical metrics for feedback.
    """
    metric_parts = []

    # Primary process/result metrics (always show when available)
    if "wheel_angular_velocity" in metrics:
        omega = metrics["wheel_angular_velocity"]
        metric_parts.append(
            f"**Wheel angular velocity (omega)**: {omega:.3f} rad/s"
        )
    if "target_speed" in metrics:
        metric_parts.append(f"**Target speed**: {metrics['target_speed']:.2f} rad/s")
    if "speed_error" in metrics:
        metric_parts.append(
            f"**Speed error (|omega - target|)**: {metrics['speed_error']:.3f} rad/s"
        )
    if "mean_speed_error" in metrics:
        metric_parts.append(
            f"**Mean speed error (over regulation phase)**: {metrics['mean_speed_error']:.3f} rad/s"
        )
    if "stall_count" in metrics:
        metric_parts.append(
            f"**Stall count (consecutive steps below threshold)**: {metrics['stall_count']}"
        )
    if "step_count" in metrics:
        metric_parts.append(f"**Simulation steps**: {metrics['step_count']}")

    # Physical state block (for debugging and process insight)
    if "wheel_angular_velocity" in metrics or "target_speed" in metrics:
        metric_parts.append("\n**Physical State (Governor)**:")
        if "wheel_angular_velocity" in metrics:
            metric_parts.append(
                f"- Current angular velocity: {metrics['wheel_angular_velocity']:.3f} rad/s"
            )
        if "target_speed" in metrics:
            metric_parts.append(
                f"- Target angular velocity: {metrics['target_speed']:.2f} rad/s"
            )
        if "speed_error" in metrics:
            metric_parts.append(
                f"- Speed error magnitude: {metrics['speed_error']:.3f} rad/s"
            )
        if "stall_speed_threshold" in metrics:
            metric_parts.append(
                f"- Stall threshold: {metrics['stall_speed_threshold']:.2f} rad/s (below this for 60 steps = stall)"
            )

    # Outcome
    if "success" in metrics:
        metric_parts.append(f"\n**Success**: {metrics['success']}")
    if "failed" in metrics and metrics["failed"] and metrics.get("failure_reason"):
        metric_parts.append(f"**Failure reason**: {metrics['failure_reason']}")

    # Extra metrics if present (e.g. from evaluator)
    excluded = {
        "wheel_angular_velocity", "target_speed", "speed_error", "mean_speed_error",
        "stall_count", "step_count", "success", "failed", "failure_reason", "stall_speed_threshold",
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
    """
    Generate task-specific improvement suggestions for C-06: The Governor.
    """
    suggestions = []

    if error:
        error_lower = error.lower()
        if "apply_motor_torque" in error_lower or "get_wheel" in error_lower or "sandbox" in error_lower:
            suggestions.append(
                "- Use only the provided API: get_wheel_angular_velocity(), get_target_speed(), "
                "apply_motor_torque(torque)"
            )
        elif "attribute" in error_lower:
            suggestions.append(
                "- Check that you are calling methods on the sandbox (environment) object correctly"
            )

    elif failed:
        if failure_reason and "stall" in failure_reason.lower():
            omega = metrics.get("wheel_angular_velocity")
            target = metrics.get("target_speed")
            suggestions.append(
                "- Avoid stall: apply enough motor torque to keep wheel speed above the stall threshold. "
                "Load opposes motion; counteract it with motor torque."
            )
            suggestions.append(
                "- Use closed-loop control: torque = Kp * (target_speed - omega). "
                "When omega is below target, apply positive torque; when omega is above target, reduce or reverse torque."
            )
            if omega is not None and target is not None:
                suggestions.append(
                    f"- Last speed was {omega:.3f} rad/s (target {target:.2f} rad/s). "
                    "Increase motor torque when speed is low."
                )
        elif failure_reason and "regulation" in failure_reason.lower():
            mean_err = metrics.get("mean_speed_error")
            suggestions.append(
                "- Regulation too poor: mean speed error is too high. The wheel must be kept near the target speed "
                "over the run, not just avoid stall."
            )
            suggestions.append(
                "- Load may depend on speed or change over time; target may change over time; load may have a "
                "periodic component (e.g. with rotation). Use feedback (omega, speed error, mean speed error) to "
                "infer behavior and adapt: e.g. feedforward that increases with speed, integral term, or tracking "
                "get_target_speed() each step."
            )
            suggestions.append(
                "- If response seems sluggish or overshoots, the measurement or actuation may have limitations "
                "(e.g. delay or speed-dependent torque limit)—infer from feedback and compensate (e.g. prediction, "
                "anti-windup, or requesting max torque when speed is very low)."
            )
            suggestions.append(
                "- If small torque corrections seem to have no effect, there may be a deadzone—ensure correction "
                "magnitude exceeds it when you need to correct (e.g. scale up gain or add a minimum step)."
            )
            if mean_err is not None:
                suggestions.append(
                    f"- Your mean speed error was {mean_err:.3f} rad/s; it must stay below the required threshold."
                )
        else:
            suggestions.append(
                "- Maintain wheel speed near target using get_wheel_angular_velocity() "
                "and apply_motor_torque(torque). Load may vary with speed and time—infer from metrics and adapt."
            )

    elif not success:
        suggestions.append(
            "- Keep wheel speed near the target (from get_target_speed() each step) for the full run without stalling."
        )
        suggestions.append(
            "- Use closed-loop control and adapt to load, target changes, and any measurement/actuation limitations."
        )

    return suggestions
