"""
Process-aware diagnostic feedback for E-02: Thick Air.

Ground truth: metrics keys and semantics come solely from evaluator.Evaluator.evaluate().
Suggestions diagnose observed outcomes without prescribing mechanisms or control implementations.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional


def _fmetrics(value: Any) -> Optional[float]:
    """Best-effort float for metric values; None if not numeric."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _nonfinite_fields(metrics: Dict[str, Any]) -> List[str]:
    """Flag metric fields whose values are NaN/inf (only keys the evaluator may emit)."""
    bad: List[str] = []
    for key in (
        "craft_x",
        "craft_y",
        "heat",
        "overheat_limit",
        "heat_remaining",
        "velocity_x",
        "velocity_y",
        "speed",
        "distance_to_target",
        "progress_x",
        "dist_traveled_x",
        "step_count",
    ):
        if key not in metrics:
            continue
        v = _fmetrics(metrics.get(key))
        if v is not None and (math.isnan(v) or math.isinf(v)):
            bad.append(key)
    return bad


def _target_zone_proximity_lines(metrics: Dict[str, Any]) -> List[str]:
    """
    Boundary margin / range to axis-aligned target box using only evaluator-provided
    craft position and target bounds.
    """
    cx = _fmetrics(metrics.get("craft_x"))
    cy = _fmetrics(metrics.get("craft_y"))
    x0 = _fmetrics(metrics.get("target_x_min"))
    x1 = _fmetrics(metrics.get("target_x_max"))
    y0 = _fmetrics(metrics.get("target_y_min"))
    y1 = _fmetrics(metrics.get("target_y_max"))
    if None in (cx, cy, x0, x1, y0, y1):
        return []
    if x1 < x0:
        x0, x1 = x1, x0
    if y1 < y0:
        y0, y1 = y1, y0
    dx_lo = cx - x0
    dx_hi = x1 - cx
    dy_lo = cy - y0
    dy_hi = y1 - cy
    inside = min(dx_lo, dx_hi, dy_lo, dy_hi) >= 0.0
    if inside:
        margin = min(dx_lo, dx_hi, dy_lo, dy_hi)
        return [
            f"**Target zone containment**: inside (inset distance to nearest face ≈ {margin:.3f} m)."
        ]
    ax = x0 if cx < x0 else (x1 if cx > x1 else cx)
    ay = y0 if cy < y0 else (y1 if cy > y1 else cy)
    dist = math.hypot(cx - ax, cy - ay)
    return [
        "**Target zone containment**: outside the reported axis-aligned target bounds.",
        f"**Closest approach to target box (metric-derived)**: ≈ {dist:.3f} m.",
    ]


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    High-resolution readout of what the evaluator measured — no recommendations.
    """
    if not metrics:
        return ["**Metrics**: (empty)"]

    if "error" in metrics:
        return [f"**Evaluator error**: {metrics.get('error')!s}"]

    parts: List[str] = []

    if "success" in metrics:
        parts.append(f"**Success flag**: {bool(metrics.get('success'))}")
    if "failed" in metrics:
        parts.append(f"**Failed flag**: {bool(metrics.get('failed'))}")
    if "reached_target" in metrics:
        parts.append(f"**Reached target zone**: {bool(metrics.get('reached_target'))}")
    if "overheated" in metrics:
        parts.append(f"**Overheated flag**: {bool(metrics.get('overheated'))}")
    if metrics.get("failure_reason") is not None:
        parts.append(f"**Failure reason (evaluator)**: {metrics.get('failure_reason')}")
    if "step_count" in metrics:
        sc = metrics.get("step_count")
        parts.append(f"**Simulation step index**: {sc!s}")

    if "craft_x" in metrics and "craft_y" in metrics:
        parts.append(
            f"**Craft position (m)**: x={metrics['craft_x']!s}, y={metrics['craft_y']!s}"
        )
    if all(k in metrics for k in ("target_x_min", "target_x_max", "target_y_min", "target_y_max")):
        parts.append(
            "**Target zone (evaluator bounds)**: "
            f"x∈[{metrics['target_x_min']!s}, {metrics['target_x_max']!s}], "
            f"y∈[{metrics['target_y_min']!s}, {metrics['target_y_max']!s}]"
        )
    parts.extend(_target_zone_proximity_lines(metrics))

    if all(k in metrics for k in ("velocity_x", "velocity_y", "speed")):
        parts.append(
            "**Craft kinematic state**: "
            f"v_x={metrics['velocity_x']!s} m/s, v_y={metrics['velocity_y']!s} m/s, "
            f"|v|={metrics['speed']!s} m/s"
        )

    if "dist_traveled_x" in metrics:
        parts.append(f"**Horizontal displacement from start (evaluator)**: {metrics['dist_traveled_x']!s} m")
    if "progress_x" in metrics:
        parts.append(f"**Horizontal progress index**: {metrics['progress_x']!s} % (evaluator-defined)")
    if "distance_to_target" in metrics:
        parts.append(
            f"**Distance to target-zone centroid (evaluator)**: {metrics['distance_to_target']!s} m"
        )

    if "heat" in metrics:
        line = f"**Cumulative thrust-time (heat)**: {metrics['heat']!s} N·s"
        limit = _fmetrics(metrics.get("overheat_limit"))
        if limit is not None and limit > 0:
            util = float(metrics["heat"]) / limit * 100.0
            line += f" ({util:.1f}% of reported `overheat_limit`)"
        parts.append(line)
    if "overheat_limit" in metrics:
        parts.append(f"**Overheat limit (this run)**: {metrics['overheat_limit']!s} N·s")
    if "heat_remaining" in metrics:
        parts.append(f"**Heat remaining to limit**: {metrics['heat_remaining']!s} N·s")

    nf = _nonfinite_fields(metrics)
    if nf:
        parts.append("**Non-finite metric values**: " + ", ".join(f"`{k}`" for k in nf))

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
    Diagnostic feedback from evaluator-emitted fields only; no design or API prescriptions.
    """
    suggestions: List[str] = []
    m = metrics or {}

    if error:
        return suggestions

    if "error" in m:
        suggestions.append(
            "- **Telemetry gap**: The evaluator returned an error-style payload; physical diagnostics "
            "are unavailable until a full metric record is produced."
        )
        return suggestions

    if success:
        return suggestions

    nf = _nonfinite_fields(m)
    if nf:
        suggestions.append(
            "- **Metric integrity**: The evaluator reported non-finite values in "
            f"{', '.join('`' + k + '`' for k in nf)}; treat measured state as unreliable for this run."
        )
        return suggestions

    overheated = bool(m.get("overheated"))
    reached = bool(m.get("reached_target"))

    if failed and overheated:
        suggestions.append(
            "- **Failure mode (evaluator)**: Episode failed with `overheated` true — the evaluator "
            "classifies this as thermal failure (see `heat`, `heat_remaining`, and `overheat_limit` in metrics)."
        )
        if reached:
            suggestions.append(
                "- **Success vs failure**: `reached_target` is true, but `success` is false because "
                "overheating disqualifies success in this evaluator’s criteria."
            )

    elif failed and not overheated:
        fr = m.get("failure_reason")
        if fr == "Craft not found":
            suggestions.append(
                "- **Failure mode (evaluator)**: `failure_reason` reports the craft was not found — "
                "the evaluator could not read position; heat, target, and kinematic fields are absent "
                "or incomplete in this payload."
            )
        else:
            suggestions.append(
                "- **Failure mode (evaluator)**: Episode failed with `overheated` false — per "
                "the evaluator, that corresponds to exhausting the step budget without entering the "
                "target zone (thermal cut-off is not the recorded failure driver)."
            )

    # Sign-only kinematic hint from evaluator positions/velocity (no distance/speed thresholds)
    if failed:
        vx = _fmetrics(m.get("velocity_x"))
        xmn = _fmetrics(m.get("target_x_min"))
        cx = _fmetrics(m.get("craft_x"))
        if xmn is not None and cx is not None and vx is not None:
            if cx < xmn and vx <= 0.0:
                suggestions.append(
                    "- **Horizontal motion vs target window**: Craft x is below the reported "
                    "`target_x_min` while horizontal velocity is not positive — the recorded state is not "
                    "closing the gap along +x toward that bound."
                )

    if failure_reason and not suggestions:
        suggestions.append(
            "- **Evaluator narrative**: Compare `failure_reason` to `overheated`, `reached_target`, "
            "`heat`, `overheat_limit`, and kinematic fields to see which outcome the evaluator assigned."
        )

    return suggestions
