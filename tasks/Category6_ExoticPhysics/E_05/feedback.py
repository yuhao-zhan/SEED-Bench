"""
Process-aware diagnostic feedback for E-05: The Magnet.

`format_task_metrics` and `get_improvement_suggestions` use only keys produced by
`Evaluator.evaluate()` in evaluator.py, plus derivations from those values (axis
clearance to the target AABB, displacement from reported start). VISIBLE physical limits
(pit bounds, thrust cap) are included in `metrics` for transparency, while INVISIBLE 
environmental constants (gravity, damping, magnet layout) are not.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple


def _is_bad_number(x: Any) -> bool:
    if x is None:
        return False
    if isinstance(x, (int, float)):
        return not math.isfinite(float(x))
    return False


def _collect_bad_numeric_paths(obj: Any, prefix: str = "") -> List[str]:
    bad: List[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{prefix}.{k}" if prefix else str(k)
            bad.extend(_collect_bad_numeric_paths(v, p))
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            bad.extend(_collect_bad_numeric_paths(v, f"{prefix}[{i}]"))
    elif _is_bad_number(obj):
        bad.append(prefix or "value")
    return bad


def _fmt_float(x: Any, nd: int = 3) -> str:
    try:
        xf = float(x)
        if not math.isfinite(xf):
            return str(xf)
        return f"{xf:.{nd}f}"
    except (TypeError, ValueError):
        return str(x)


def _axis_clearance_to_target(metrics: Dict[str, Any]) -> Optional[Tuple[float, float]]:
    """
    (horizontal_clearance_m, vertical_clearance_m): distance outside the target
    rectangle along each axis; 0 if that coordinate lies inside the interval.
    """
    keys = (
        "body_x",
        "body_y",
        "target_x_min",
        "target_x_max",
        "target_y_min",
        "target_y_max",
    )
    if not all(k in metrics for k in keys):
        return None
    try:
        x = float(metrics["body_x"])
        y = float(metrics["body_y"])
        tx0 = float(metrics["target_x_min"])
        tx1 = float(metrics["target_x_max"])
        ty0 = float(metrics["target_y_min"])
        ty1 = float(metrics["target_y_max"])
    except (TypeError, ValueError):
        return None
    if tx0 <= x <= tx1:
        hx = 0.0
    elif x < tx0:
        hx = tx0 - x
    else:
        hx = x - tx1
    if ty0 <= y <= ty1:
        vy_clear = 0.0
    elif y < ty0:
        vy_clear = ty0 - y
    else:
        vy_clear = y - ty1
    return (hx, vy_clear)


def _displacement_from_start(metrics: Dict[str, Any]) -> Optional[Tuple[float, float]]:
    if not all(k in metrics for k in ("body_x", "body_y", "start_x", "start_y")):
        return None
    try:
        dx = float(metrics["body_x"]) - float(metrics["start_x"])
        dy = float(metrics["body_y"]) - float(metrics["start_y"])
    except (TypeError, ValueError):
        return None
    return (dx, dy)


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    High-resolution readout of evaluator-supplied state only (no suggestions).
    """
    parts: List[str] = []

    if not metrics:
        parts.append("**Metrics**: (empty)")
        return parts

    if "error" in metrics:
        parts.append(f"**Evaluation Error**: {metrics['error']}")
        return parts

    parts.append("### Terminal evaluation snapshot")

    for key in ("success", "failed", "reached_target"):
        if key in metrics:
            parts.append(f"**{key.replace('_', ' ').title()}**: {metrics[key]}")

    if "failure_reason" in metrics and metrics["failure_reason"] is not None:
        parts.append(f"**Failure reason (evaluator)**: {metrics['failure_reason']}")

    if "step_count" in metrics:
        parts.append(f"**Simulation step index**: {metrics['step_count']}")

    parts.append("### Kinematic state (final sample)")

    if all(k in metrics for k in ("body_x", "body_y")):
        parts.append(
            f"**Body position**: ({_fmt_float(metrics['body_x'])}, "
            f"{_fmt_float(metrics['body_y'])}) m"
        )

    if all(k in metrics for k in ("velocity_x", "velocity_y", "speed")):
        parts.append(
            f"**Velocity**: (vx={_fmt_float(metrics['velocity_x'])}, "
            f"vy={_fmt_float(metrics['velocity_y'])}) m/s; "
            f"**speed**: {_fmt_float(metrics['speed'])} m/s"
        )

    disp = _displacement_from_start(metrics)
    if disp is not None:
        parts.append(
            f"**Displacement from reported start**: "
            f"Δx={_fmt_float(disp[0])} m, Δy={_fmt_float(disp[1])} m"
        )

    parts.append("### Target geometry and membership (evaluator coordinates)")

    if all(
        k in metrics
        for k in (
            "target_x_min",
            "target_x_max",
            "target_y_min",
            "target_y_max",
        )
    ):
        parts.append(
            f"**Target axis-aligned bounds**: "
            f"x ∈ [{_fmt_float(metrics['target_x_min'])}, {_fmt_float(metrics['target_x_max'])}], "
            f"y ∈ [{_fmt_float(metrics['target_y_min'])}, {_fmt_float(metrics['target_y_max'])}] m"
        )

    for key in ("in_target_x", "in_target_y"):
        if key in metrics:
            parts.append(f"**{key.replace('_', ' ').title()}**: {metrics[key]}")

    gaps = _axis_clearance_to_target(metrics)
    if gaps is not None:
        parts.append(
            f"**Clearance outside target (axis-separated)**: "
            f"horizontal {_fmt_float(gaps[0])} m, vertical {_fmt_float(gaps[1])} m "
            f"(0 means inside on that axis)"
        )

    if "dist_to_target" in metrics:
        parts.append(
            f"**Distance to nearest point in target rectangle**: "
            f"{_fmt_float(metrics['dist_to_target'])} m"
        )

    if "progress_x" in metrics:
        try:
            px = float(metrics["progress_x"])
            parts.append(
                f"**Horizontal progress metric (evaluator)**: "
                f"{max(0.0, min(1.0, px)) * 100:.1f}% of start→target_x_min span"
            )
        except (TypeError, ValueError):
            parts.append(f"**Horizontal progress metric (evaluator)**: {metrics['progress_x']}")

    bad_paths = _collect_bad_numeric_paths(metrics)
    if bad_paths:
        parts.append(
            "**Numeric integrity (metrics tree)**: non-finite values at: "
            + ", ".join(bad_paths)
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
    Diagnostic feedback from evaluator metrics and outcome flags only.
    """
    suggestions: List[str] = []

    if error:
        return suggestions

    if not metrics:
        return suggestions

    if "error" in metrics:
        return suggestions

    bad_paths = _collect_bad_numeric_paths(metrics)
    if bad_paths:
        suggestions.append(
            "- **Numeric integrity**: The evaluation snapshot contains non-finite "
            "values in the reported fields. Treat position, velocity, and derived "
            "quantities as unreliable until the underlying state is finite."
        )

    fr = (failure_reason or metrics.get("failure_reason") or "") or ""
    fr_l = fr.lower()

    speed = metrics.get("speed")
    vx = metrics.get("velocity_x")
    vy_vel = metrics.get("velocity_y")
    speed_f: Optional[float] = None
    try:
        if speed is not None and math.isfinite(float(speed)):
            speed_f = float(speed)
    except (TypeError, ValueError):
        speed_f = None

    mobility_dead = False
    if speed_f is not None and math.isfinite(speed_f):
        mobility_dead = math.isclose(speed_f, 0.0, abs_tol=1e-12, rel_tol=0.0)
    elif vx is not None and vy_vel is not None:
        try:
            vxf, vyf = float(vx), float(vy_vel)
            if math.isfinite(vxf) and math.isfinite(vyf):
                mobility_dead = vxf == 0.0 and vyf == 0.0
        except (TypeError, ValueError):
            pass

    gaps = _axis_clearance_to_target(metrics)
    hx: Optional[float] = None
    vy_clear: Optional[float] = None
    if gaps is not None:
        hx, vy_clear = gaps[0], gaps[1]

    in_tx = metrics.get("in_target_x")
    in_ty = metrics.get("in_target_y")

    if failed and "pit" in fr_l:
        suggestions.append(
            "- **Primary failure channel (evaluator)**: The run ended because the "
            "body entered a forbidden region before the target condition was met. "
            "That is a kinematic constraint violation relative to the evaluator’s "
            "failure rule, not merely slow convergence toward the goal."
        )
        if mobility_dead:
            suggestions.append(
                "- **Terminal motion**: Reported speed is effectively zero at "
                "termination — consistent with the body having little or no residual "
                "motion when the failure was recorded."
            )

    elif failed and ("local minimum" in fr_l or "time ran out" in fr_l or "stuck" in fr_l):
        suggestions.append(
            "- **Primary failure channel (evaluator)**: The horizon expired without "
            "the body entering the target zone. The task description for this "
            "benchmark class emphasizes navigation under position-dependent forces "
            "and the risk of getting stuck short of the goal."
        )
        if mobility_dead:
            suggestions.append(
                "- **Terminal motion**: Near-zero terminal velocity suggests little "
                "net motion at the end of the run — consistent with a force balance "
                "or repeated cancellation of intended motion rather than sustained "
                "progress."
            )

    if failed and not success:
        try:
            px = float(metrics.get("progress_x", 0.0))
        except (TypeError, ValueError):
            px = 0.0
        px = max(0.0, min(1.0, px))
        if (
            px >= 1.0
            and gaps is not None
            and hx is not None
            and vy_clear is not None
            and (hx > 0.0 or vy_clear > 0.0)
        ):
            suggestions.append(
                "- **Progress metric vs. target membership**: The evaluator’s "
                "horizontal progress scalar is saturated while the body remains "
                "outside the target rectangle on at least one axis. Improving only "
                "that scalar can leave a remaining registration error in the full "
                "2D acceptance test."
            )
        if in_tx is True and in_ty is False:
            suggestions.append(
                "- **Axis residual**: The body lies inside the target span on x but "
                "not on y; the remaining error is primarily in vertical alignment "
                "relative to the evaluator band."
            )
        elif in_ty is True and in_tx is False:
            suggestions.append(
                "- **Axis residual**: The body lies inside the target span on y but "
                "not on x; the remaining error is primarily in horizontal alignment "
                "relative to the evaluator window."
            )
        elif (
            gaps is not None
            and hx is not None
            and vy_clear is not None
            and (hx > 0 or vy_clear > 0)
        ):
            if hx > vy_clear:
                suggestions.append(
                    "- **Dominant clearance (axis-separated)**: Horizontal "
                    "clearance to the target interval exceeds vertical clearance — "
                    "the larger gap to the band is along x."
                )
            elif vy_clear > hx:
                suggestions.append(
                    "- **Dominant clearance (axis-separated)**: Vertical "
                    "clearance to the target interval exceeds horizontal clearance — "
                    "the larger gap to the band is along y."
                )

    if not success and not failed:
        try:
            sc = float(score)
        except (TypeError, ValueError):
            sc = 0.0
        if (
            sc > 0.0
            and gaps is not None
            and hx is not None
            and vy_clear is not None
            and (hx > 0.0 or vy_clear > 0.0)
        ):
            suggestions.append(
                "- **Partial score vs. full goal**: Score is positive while the "
                "target rectangle is still not satisfied. The scoring rule uses a "
                "longitudinal proxy; both axes may still need to close before the "
                "run ends."
            )
        elif not suggestions:
            suggestions.append(
                "- **In progress**: Continue closing distance and alignment to the "
                "evaluator target bounds while the episode remains open."
            )

    return suggestions
