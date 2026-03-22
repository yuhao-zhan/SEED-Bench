"""
Process-aware diagnostic feedback for E-03: Slippery World.

Quantitative reporting and suggestions use only keys produced by
`Evaluator.evaluate()` (evaluator.py) plus outcome flags and `score`
from the harness. No hardcoded stage or world physics constants.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional


def _as_float(x: Any) -> Optional[float]:
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _finite(x: Optional[float]) -> bool:
    return x is not None and math.isfinite(x)


def _metrics_numeric_health(metrics: Dict[str, Any]) -> List[str]:
    """Flag non-finite kinematic scalars when present in metrics."""
    issues: List[str] = []
    for key in ("velocity_x", "velocity_y", "velocity_magnitude", "sled_x", "sled_y"):
        if key not in metrics:
            continue
        v = _as_float(metrics.get(key))
        if v is not None and not math.isfinite(v):
            issues.append(f"{key} is non-finite ({metrics.get(key)!r})")
    return issues


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Readout of evaluator-exposed fields only.
    No recommendations—facts and sequence state only.
    """
    parts: List[str] = []

    if not metrics:
        return parts

    if "error" in metrics:
        parts.append(f"**Evaluator state**: {metrics['error']}")
        return parts

    if "checkpoint_a_reached" in metrics or "checkpoint_b_reached" in metrics:
        a = metrics.get("checkpoint_a_reached")
        b = metrics.get("checkpoint_b_reached")
        seq = metrics.get("checkpoint_reached")
        parts.append("**Phase segregation (checkpoints)**")
        parts.append(
            f"- Alpha (first gate): {'cleared' if a else 'not cleared'}"
        )
        parts.append(
            f"- Beta (second gate): {'cleared' if b else 'not cleared'}"
        )
        if seq is not None:
            parts.append(
                f"- Ordered requirement (both gates): {'satisfied' if seq else 'not satisfied'}"
            )

    if "reached_target" in metrics:
        parts.append(
            f"- Final target zone: {'entered' if metrics['reached_target'] else 'not entered'}"
        )

    if "success" in metrics:
        parts.append(f"**Success flag**: {bool(metrics['success'])}")
    if "failed" in metrics:
        parts.append(f"**Run exhausted (failed flag)**: {bool(metrics['failed'])}")
    if metrics.get("failure_reason"):
        parts.append(f"**Stated failure reason**: {metrics['failure_reason']}")

    if "step_count" in metrics:
        parts.append(f"**Simulation step index (at evaluation)**: {metrics['step_count']}")

    sx = _as_float(metrics.get("sled_x"))
    sy = _as_float(metrics.get("sled_y"))
    if sx is not None and sy is not None:
        parts.append(f"**Sled center position**: x = {sx:.4f} m, y = {sy:.4f} m")

    vx = _as_float(metrics.get("velocity_x"))
    vy = _as_float(metrics.get("velocity_y"))
    vm = _as_float(metrics.get("velocity_magnitude"))
    if vx is not None and vy is not None:
        parts.append(f"**Velocity components**: vx = {vx:.4f} m/s, vy = {vy:.4f} m/s")
    if vm is not None:
        parts.append(f"**Speed magnitude**: {vm:.4f} m/s")

    tx0 = _as_float(metrics.get("target_x_min"))
    tx1 = _as_float(metrics.get("target_x_max"))
    ty0 = _as_float(metrics.get("target_y_min"))
    ty1 = _as_float(metrics.get("target_y_max"))
    if all(_finite(v) for v in (tx0, tx1, ty0, ty1)):
        w = tx1 - tx0
        h = ty1 - ty0
        parts.append(
            f"**Final target axis-aligned bounds (from metrics)**: "
            f"x ∈ [{tx0:.4f}, {tx1:.4f}] m, y ∈ [{ty0:.4f}, {ty1:.4f}] m "
            f"(span Δx = {w:.4f} m, Δy = {h:.4f} m)"
        )

    if "distance_to_target" in metrics:
        dt = _as_float(metrics.get("distance_to_target"))
        if dt is not None:
            parts.append(f"**Distance to nearest point on final target rectangle**: {dt:.4f} m")

    if "progress_pct" in metrics:
        pp = _as_float(metrics.get("progress_pct"))
        if pp is not None:
            parts.append(
                f"**Horizontal progress metric (evaluator)**: {pp:.2f}% "
                f"(from `sled_start_x` toward `target_x_min`; see metrics keys)"
            )

    ssx = _as_float(metrics.get("sled_start_x"))
    if ssx is not None and sx is not None:
        parts.append(f"**Horizontal displacement from start x**: {sx - ssx:.4f} m")

    numeric_issues = _metrics_numeric_health(metrics)
    if numeric_issues:
        parts.append("**Numeric / kinematic anomalies detected in metrics**")
        for msg in numeric_issues:
            parts.append(f"- {msg}")

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
    Diagnostic feedback from evaluator metrics and harness outcome only.
    No controller recipes or mechanical prescriptions.
    """
    suggestions: List[str] = []

    if error:
        return suggestions

    if not metrics:
        return suggestions

    if metrics.get("error"):
        suggestions.append(
            "- **Execution chain**: Evaluation could not access a live environment state; "
            "the physical trajectory was not scored—verify that the simulation and sled "
            "body are constructed before the control loop runs."
        )
        return suggestions

    for msg in _metrics_numeric_health(metrics):
        suggestions.append(
            f"- **Invalid reported kinematics**: {msg}. Subsequent metrics may be unreliable."
        )

    sx = _as_float(metrics.get("sled_x"))
    sy = _as_float(metrics.get("sled_y"))
    tx0 = _as_float(metrics.get("target_x_min"))
    tx1 = _as_float(metrics.get("target_x_max"))
    ty0 = _as_float(metrics.get("target_y_min"))
    ty1 = _as_float(metrics.get("target_y_max"))

    reached_a = bool(metrics.get("checkpoint_a_reached"))
    reached_b = bool(metrics.get("checkpoint_b_reached"))
    seq_ok = bool(metrics.get("checkpoint_reached"))
    reached_target = bool(metrics.get("reached_target"))

    if not success and seq_ok and not reached_target:
        suggestions.append(
            "- **Sequence vs. terminal state**: `checkpoint_reached` is true but "
            "`reached_target` is false—inspect `distance_to_target`, position relative to "
            "`target_*` bounds, and velocity components in metrics for the approach phase."
        )

    if (
        all(_finite(v) for v in (sx, tx0, tx1))
        and (sx < tx0 or sx > tx1)
        and seq_ok
        and not reached_target
    ):
        suggestions.append(
            "- **Longitudinal placement**: With checkpoints cleared, the sled center lies "
            "outside the final target x-interval in metrics."
        )

    if (
        all(_finite(v) for v in (sy, ty0, ty1))
        and seq_ok
        and not reached_target
        and (sy < ty0 or sy > ty1)
    ):
        suggestions.append(
            "- **Lateral / vertical placement**: With checkpoints cleared, the sled center "
            "lies outside the final target y-interval in metrics."
        )

    if failed and failure_reason:
        fr = failure_reason.lower()
        if "alpha" in fr or "first checkpoint" in fr:
            suggestions.append(
                "- **Evaluator attribution**: The run ended before the first required "
                "checkpoint was satisfied; later objectives are not credited until that gate "
                "is cleared."
            )
        elif "beta" in fr or "second checkpoint" in fr:
            suggestions.append(
                "- **Evaluator attribution**: The first checkpoint cleared, but the second "
                "did not—the failure is attributed to that segment of the required order."
            )
        elif "final target" in fr:
            suggestions.append(
                "- **Evaluator attribution**: Checkpoints are satisfied, but the final "
                "target condition was not met before the horizon."
            )

    if failed:
        if not reached_a:
            suggestions.append(
                "- **Mechanism hint**: Early failure with the first checkpoint uncleared "
                "often reflects insufficient motion toward that gate’s required region "
                "within the available horizon (global dissipation and effective propulsion "
                "can vary between runs)."
            )
        elif not reached_b:
            suggestions.append(
                "- **Mechanism hint**: First checkpoint cleared but second uncleared "
                "suggests the trajectory did not satisfy the middle segment of the ordered "
                "requirement before steps ran out."
            )
        elif seq_ok and not reached_target:
            suggestions.append(
                "- **Mechanism hint**: Ordered gates satisfied but the terminal condition "
                "failed—late-horizon motion relative to the final bounds in metrics is the "
                "remaining gap."
            )

    elif not success:
        suggestions.append(
            "- **In-flight**: The task is not yet successful; `step_count`, separation "
            "(`distance_to_target`), and target bounds in metrics describe the current state."
        )

    return suggestions
