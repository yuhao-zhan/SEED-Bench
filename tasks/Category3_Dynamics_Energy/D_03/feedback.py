"""
D-03: Phase-Locked Gate — process-aware diagnostic feedback.

Physics domain: Dynamics + time-window + phase matching (velocity profile, gate timing,
impulse/damping zones). Feedback is derived only from the metrics dict returned by
evaluator.evaluate(); no hardcoded thresholds; suggestions diagnose mechanism, never
dictate implementation. Adapts to stage mutations (impulse, damping, gravity) via
failure-reason and reported state only.
"""
from typing import Dict, Any, List
import math


def _is_finite(x: Any) -> bool:
    """True if value is numeric and finite (no NaN/inf)."""
    if x is None:
        return False
    try:
        f = float(x)
        return math.isfinite(f)
    except (TypeError, ValueError):
        return False


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Expose high-resolution physical metrics from evaluator output only.
    No invented metrics; phase-segregated for dynamics (spatial, kinematic, termination).
    """
    parts: List[str] = []

    if not metrics:
        return parts

    # --- Phase 1: Outcome / termination ---
    if "success" in metrics:
        parts.append(
            f"**Objective Success**: {'Yes' if metrics.get('success') else 'No'}"
        )
    if "failed" in metrics and metrics.get("failed"):
        parts.append(f"**Run Failed**: True")

    # --- Phase 2: Spatial outcome (only if present and finite) ---
    if "x" in metrics:
        x = metrics["x"]
        if _is_finite(x):
            parts.append(f"**Final Vehicle Position (x)**: {float(x):.2f} m")
        else:
            parts.append(
                "**Final Vehicle Position (x)**: Non-finite (numerical instability detected)."
            )

    # --- Phase 3: Kinematic outcome (only if present and finite) ---
    if "speed" in metrics:
        s = metrics["speed"]
        if _is_finite(s):
            parts.append(f"**Final Vehicle Speed**: {float(s):.2f} m/s")
        else:
            parts.append(
                "**Final Vehicle Speed**: Non-finite (numerical instability detected)."
            )

    # --- Phase 4: Termination reason (exactly as reported) ---
    if "failure_reason" in metrics and metrics.get("failure_reason"):
        parts.append(
            f"**Termination Reason**: {metrics['failure_reason']}"
        )

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
    Diagnostic, process-aware suggestions. No hardcoded thresholds; no spoilers.
    Uses only metrics and failure_reason/error; infers root-cause chain and
    multi-objective trade-offs from the reported outcome.
    """
    suggestions: List[str] = []
    msg = (error or failure_reason or "").strip().lower()
    if not msg and not metrics:
        return suggestions

    # Resolve canonical reason from metrics if not passed
    reason = (failure_reason or metrics.get("failure_reason") or "").strip().lower()
    x = metrics.get("x") if metrics else None
    speed = metrics.get("speed") if metrics else None
    has_finite_x = _is_finite(x)
    has_finite_speed = _is_finite(speed)

    # --- Physics engine / numerical sanity ---
    if metrics and (not has_finite_x or not has_finite_speed):
        if "x" in metrics or "speed" in metrics:
            suggestions.append(
                "- **Numerical Instability**: Simulation state became non-finite. "
                "This can indicate extreme forces, stiffness, or timestep issues; consider constraining applied forces or structure layout."
            )
            return suggestions

    # --- Design constraints (root cause: build-time violation) ---
    if "design constraint" in reason or "design constraint" in msg:
        if "beam count" in reason or "beam count" in msg:
            suggestions.append(
                "- **Complexity Constraint**: The number of structural components does not meet the task requirement. "
                "Reconcile the required component count with your build logic."
            )
        if "outside build zone" in reason or "build zone" in msg:
            suggestions.append(
                "- **Spatial Constraint**: At least one component was placed outside the permitted build region. "
                "Ensure all attachment positions lie within the specified bounds."
            )
        if "mass" in reason or "exceeds limit" in msg:
            suggestions.append(
                "- **Mass Budget**: Total structure mass exceeded the permissible limit. "
                "Consider the strength-to-weight trade-off of your design."
            )
        return suggestions

    # --- Structural integrity (root cause: joint/attachment failure) ---
    if "structure broken" in reason or "structure broken" in msg:
        suggestions.append(
            "- **Structural Failure**: One or more attachments failed under load before the run completed. "
            "Load path and joint stress under impulses and damping may need to be revisited."
        )
        return suggestions

    # --- Gate collision (root cause: phase / timing) ---
    if "gate collision" in reason or "gate collision" in msg:
        suggestions.append(
            "- **Phase Alignment Failure**: The vehicle contacted a rotating gate while it was closed. "
            "Arrival time at the gate is determined by mass, impulses, and damping; adjust the velocity profile so the vehicle passes during the open window."
        )
        return suggestions

    # --- Velocity-profile checkpoints (root cause: momentum / energy at a specific x) ---
    if "speed trap" in reason or "speed trap" in msg:
        suggestions.append(
            "- **Velocity Profile (Early Segment)**: Speed was below the required minimum when first crossing the early measurement point. "
            "Backward impulses and damping reduce momentum; mass and applied force history determine whether the vehicle retains enough speed there."
        )
        return suggestions

    if "checkpoint" in reason and ("speed" in reason or "out of band" in reason):
        suggestions.append(
            "- **Velocity Profile (Mid Segment)**: Speed at the mid-track checkpoint was outside the allowed band. "
            "This band couples to gate timing; deceleration zones and a second impulse affect how quickly speed is shed—tune mass and force profile accordingly."
        )
        return suggestions

    # --- Terminal conditions: multi-objective / root-cause distinction ---
    if "final speed out of band" in reason or "final speed out of band" in msg:
        suggestions.append(
            "- **Terminal Velocity Band**: The run reached the target region but final speed was outside the required band. "
            "Braking and damping near the end determine where speed lands; balance progress with energy dissipation in the final segment."
        )
        return suggestions

    if "reach target zone" in reason or "did not reach" in msg:
        suggestions.append(
            "- **Insufficient Progress**: The vehicle did not reach the target region by the end of the run. "
            "Net forward momentum is reduced by impulses and damping; consider how mass and applied force affect travel distance."
        )
        return suggestions

    # --- Cart not found (environment/state) ---
    if "cart not found" in reason or "cart not found" in msg:
        suggestions.append(
            "- **Vehicle State**: The vehicle body was not available. Check that the simulation and build sequence leave the cart present and active."
        )
        return suggestions

    # --- Generic fallback (no spoilers) ---
    if failed and not suggestions:
        suggestions.append(
            "- **Diagnosis**: The run terminated without success. Use the reported position, speed, and termination reason above to infer which physical constraint or phase was violated, then adjust design or control strategy."
        )

    return suggestions
