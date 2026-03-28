"""
Process-aware diagnostic feedback for E-01: Inverted Gravity.

`format_task_metrics` and `get_improvement_suggestions` only interpret keys
and values produced by `Evaluator.evaluate()` in evaluator.py (and numeric
derivations from those values, e.g. AABB margins). No extra failure channels,
ratio heuristics, or stage-specific numeric thresholds are introduced here.
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
    """Find NaN/inf in nested structures (metrics only)."""
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


def _fmt_float(x: Any, nd: int = 2) -> str:
    try:
        xf = float(x)
        if not math.isfinite(xf):
            return str(xf)
        return f"{xf:.{nd}f}"
    except (TypeError, ValueError):
        return str(x)


def _arena_margins(metrics: Dict[str, Any]) -> Optional[Tuple[float, float, float, float]]:
    """
    Returns (left, right, bottom, top) clearance: positive = inside arena
    on that side for the axis-aligned bounding box of reported body positions.
    """
    keys = (
        "body_x_min", "body_x_max", "body_y_min", "body_y_max",
        "arena_x_min", "arena_x_max", "arena_y_min", "arena_y_max",
    )
    if not all(k in metrics and metrics[k] is not None for k in keys):
        return None
    try:
        bx0, bx1 = float(metrics["body_x_min"]), float(metrics["body_x_max"])
        by0, by1 = float(metrics["body_y_min"]), float(metrics["body_y_max"])
        ax0, ax1 = float(metrics["arena_x_min"]), float(metrics["arena_x_max"])
        ay0, ay1 = float(metrics["arena_y_min"]), float(metrics["arena_y_max"])
    except (TypeError, ValueError):
        return None
    left = bx0 - ax0
    right = ax1 - bx1
    bottom = by0 - ay0
    top = ay1 - by1
    return (left, right, bottom, top)


def _gravity_vector(metrics: Dict[str, Any]) -> Optional[Tuple[float, float]]:
    g = metrics.get("gravity_current")
    if g is None:
        return None
    if not isinstance(g, (list, tuple)) or len(g) < 2:
        return None
    try:
        return (float(g[0]), float(g[1]))
    except (TypeError, ValueError):
        return None


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

    for key in ("success", "failed"):
        if key in metrics:
            parts.append(f"**{key.replace('_', ' ').title()}**: {metrics[key]}")

    if "failure_reason" in metrics and metrics["failure_reason"] is not None:
        parts.append(f"**Failure Reason (evaluator)**: {metrics['failure_reason']}")

    if "step_count" in metrics:
        parts.append(f"**Simulation Step**: {metrics['step_count']}")

    if "progress_pct" in metrics:
        try:
            parts.append(f"**Temporal Progress**: {float(metrics['progress_pct']):.1f}%")
        except (TypeError, ValueError):
            parts.append(f"**Temporal Progress**: {metrics['progress_pct']}")

    if "structure_mass" in metrics:
        mass_s = _fmt_float(metrics["structure_mass"], 2)
        max_m = metrics.get("max_structure_mass")
        if max_m is not None and math.isfinite(float(max_m)):
            parts.append(
                f"**Structural Mass**: {mass_s} kg (budget `max_structure_mass` = {_fmt_float(max_m, 2)} kg)"
            )
        else:
            parts.append(f"**Structural Mass**: {mass_s} kg")

    if "beam_count" in metrics or "max_beam_count" in metrics:
        bc = metrics.get("beam_count", "—")
        mb = metrics.get("max_beam_count", "—")
        parts.append(f"**Beam Count**: {bc} / max {mb}")

    if "joint_count" in metrics:
        parts.append(f"**Joint Count (current)**: {metrics['joint_count']}")

    if "body_count" in metrics:
        parts.append(f"**Dynamic Body Count (tracked)**: {metrics['body_count']}")

    g = _gravity_vector(metrics)
    if g is not None:
        gx, gy = g
        mag = math.hypot(gx, gy)
        parts.append(
            f"**Instantaneous Gravity** (at evaluation step): "
            f"({_fmt_float(gx, 2)}, {_fmt_float(gy, 2)}) m/s², |g| = {_fmt_float(mag, 2)} m/s²"
        )
        if gy > 0 and abs(gy) >= abs(gx):
            parts.append(
                "**Gravity-Vector Regime (vertical-dominant)**: positive y-component "
                "(upward component dominates over lateral at this instant)."
            )
        elif gy < 0 and abs(gy) >= abs(gx):
            parts.append(
                "**Gravity-Vector Regime (vertical-dominant)**: negative y-component "
                "(downward component dominates over lateral at this instant)."
            )
        elif abs(gx) > abs(gy):
            parts.append("**Gravity-Vector Regime (lateral-dominant)**: |g_x| > |g_y| at this instant.")

    arena_keys = ("arena_x_min", "arena_x_max", "arena_y_min", "arena_y_max")
    if all(k in metrics for k in arena_keys):
        parts.append(
            f"**Arena Bounds**: x ∈ [{_fmt_float(metrics['arena_x_min'], 1)}, {_fmt_float(metrics['arena_x_max'], 1)}], "
            f"y ∈ [{_fmt_float(metrics['arena_y_min'], 1)}, {_fmt_float(metrics['arena_y_max'], 1)}] m"
        )

    if all(k in metrics and metrics[k] is not None for k in ("body_x_min", "body_x_max", "body_y_min", "body_y_max")):
        parts.append(
            f"**Body AABB** (tracked dynamics): "
            f"x ∈ [{_fmt_float(metrics['body_x_min'], 2)}, {_fmt_float(metrics['body_x_max'], 2)}], "
            f"y ∈ [{_fmt_float(metrics['body_y_min'], 2)}, {_fmt_float(metrics['body_y_max'], 2)}] m"
        )

    margs = _arena_margins(metrics)
    if margs is not None:
        left, right, bottom, top = margs
        parts.append(
            "**Boundary Margin (AABB vs arena)** — positive means inside on that side; "
            f"left {_fmt_float(left, 2)} m, right {_fmt_float(right, 2)} m, "
            f"bottom {_fmt_float(bottom, 2)} m, top {_fmt_float(top, 2)} m"
        )

    for label, key in (
        ("Out of bounds", "out_of_bounds"),
        ("Obstacle overlap (agent body centers)", "obstacle_overlap"),
        ("Forbidden zone (rule)", "forbidden_zone_violation"),
        ("Structure broken (joint count dropped)", "structure_broken"),
    ):
        if key in metrics:
            parts.append(f"**{label}**: {metrics[key]}")

    def _fmt_pos_list(seq: Any, name: str, limit: int = 5) -> None:
        if not seq:
            return
        if not isinstance(seq, (list, tuple)):
            return
        items = []
        for p in seq[:limit]:
            if isinstance(p, (list, tuple)) and len(p) >= 2:
                items.append(f"({_fmt_float(p[0], 2)}, {_fmt_float(p[1], 2)})")
        if items:
            parts.append(f"**{name}** (up to {limit}): " + "; ".join(items))

    _fmt_pos_list(metrics.get("offending_positions"), "Out-of-bounds sample positions")
    _fmt_pos_list(metrics.get("obstacle_offending"), "Obstacle overlap sample positions")
    _fmt_pos_list(metrics.get("forbidden_offending"), "Forbidden-zone sample positions")

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
    Diagnostic feedback from evaluator flags and reported numeric state only,
    without prescribing a specific structure or API usage.
    """
    suggestions: List[str] = []

    if not metrics:
        return suggestions

    bad_paths = _collect_bad_numeric_paths(metrics)
    if bad_paths:
        suggestions.append(
            "- **Metric numeric domain**: Non-finite floating-point values appear in the reported metrics "
            f"at {', '.join(bad_paths[:6])}"
            + ("; …" if len(bad_paths) > 6 else "")
            + ". Treat other numeric fields from this snapshot as potentially unreliable."
        )

    if metrics.get("error"):
        suggestions.append(
            "- **Evaluation pipeline**: The evaluator returned an error state; physical conclusions from "
            "metrics may be incomplete until the environment is available for stepping."
        )

    if success and not failed:
        return suggestions

    fr = (failure_reason or metrics.get("failure_reason") or "") or ""
    fr_lower = fr.lower()
    err = (error or "") or ""

    if "design constraint violated" in fr_lower:
        mass = metrics.get("structure_mass")
        max_mass = metrics.get("max_structure_mass", float("inf"))
        beams = metrics.get("beam_count")
        max_beams = metrics.get("max_beam_count", float("inf"))
        n_design = len(suggestions)

        try:
            if mass is not None and math.isfinite(float(max_mass)) and float(mass) > float(max_mass):
                suggestions.append(
                    "- **Budget violation (mass)**: Reported structure mass exceeds `max_structure_mass` "
                    "from metrics — the design violates the mass ceiling before dynamics run."
                )
        except (TypeError, ValueError):
            pass

        try:
            if beams is not None and math.isfinite(float(max_beams)) and float(beams) > float(max_beams):
                suggestions.append(
                    "- **Budget violation (component count)**: Beam count exceeds `max_beam_count` from "
                    "metrics — the layout violates the component limit before simulation."
                )
        except (TypeError, ValueError):
            pass

        if "outside build zone" in fr_lower:
            suggestions.append(
                "- **Geometric feasibility (build envelope)**: The evaluator reports at least one beam "
                "center outside the build zone — placement is inconsistent with the static rules before "
                "any time-varying load is applied."
            )

        if len(suggestions) == n_design:
            suggestions.append(
                "- **Design constraint (unspecified branch)**: The evaluator listed a static violation in "
                "`failure_reason` that was not classified from mass, beam count, or build-zone substrings "
                "alone — reconcile the full message with `structure_mass`, `max_structure_mass`, "
                "`beam_count`, `max_beam_count`, and the build-zone bounds from task configuration."
            )
        elif len(suggestions) - n_design >= 2:
            suggestions.append(
                "- **Design-phase coupling**: Multiple static checks failed together at step 0; the combined "
                "`failure_reason` may bundle several rule violations."
            )

    oob = bool(metrics.get("out_of_bounds"))
    obs = bool(metrics.get("obstacle_overlap"))
    fz = bool(metrics.get("forbidden_zone_violation"))
    brk = bool(metrics.get("structure_broken"))
    active = sum(1 for x in (oob, obs, fz, brk) if x)

    if failed and active >= 2:
        suggestions.append(
            "- **Concurrent failure flags**: More than one of "
            "`out_of_bounds`, `obstacle_overlap`, `forbidden_zone_violation`, and `structure_broken` is "
            "true. The evaluator sets `failure_reason` in a fixed priority order and does not separate "
            "interaction between mechanisms in that string."
        )

    g = _gravity_vector(metrics)

    if oob:
        if g is not None:
            gx, gy = g
            if gy > 0:
                suggestions.append(
                    "- **Containment vs gravity vector**: At the reported instant, gravity has a positive "
                    "vertical component — net apparent acceleration includes an upward component relative "
                    "to the arena axes."
                )
            elif gy < 0:
                suggestions.append(
                    "- **Containment vs gravity vector**: At the reported instant, gravity has a negative "
                    "vertical component — net apparent acceleration includes a downward component relative "
                    "to the arena axes."
                )
            if abs(gx) > abs(gy):
                suggestions.append(
                    "- **Lateral gravity component**: The reported gravity vector is lateral-dominant at "
                    "this instant — horizontal drift can reduce clearance even when vertical motion is small."
                )
        else:
            suggestions.append(
                "- **Containment**: At least one tracked dynamic body left the arena AABB; `gravity_current` "
                "was not present in metrics — compare `body_*` bounds to `arena_*` in this snapshot for "
                "which sides were exceeded."
            )

    margs = _arena_margins(metrics)
    if oob and margs is not None:
        left, right, bottom, top = margs
        smallest = min(left, right, bottom, top)
        if math.isfinite(smallest) and smallest < 0:
            suggestions.append(
                "- **AABB vs arena**: The axis-aligned envelope of reported body positions extends outside "
                "the arena bounds on at least one side (negative margin in the boundary-margin line above)."
            )

    if brk:
        suggestions.append(
            "- **Integrity**: `structure_broken` is true when joint count drops below the count recorded at "
            "step 0 — the simulator no longer represents the same connected assembly as at initialization."
        )
        if oob:
            suggestions.append(
                "- **Multiple terminal conditions**: Both `structure_broken` and `out_of_bounds` are true; "
                "the metrics snapshot does not encode event ordering between them."
            )

    if obs:
        suggestions.append(
            "- **Obstacle overlap**: The evaluator flags agent body centers inside obstacle AABBs — this "
            "is distinct from merely touching arena walls."
        )

    if fz:
        suggestions.append(
            "- **Forbidden zone**: Failure is driven by rule geometry on agent body centers, independent of "
            "whether the structure would otherwise stay inside the arena AABB."
        )

    if err and not suggestions:
        suggestions.append(
            "- **Execution context**: An execution error was reported upstream; reconcile stderr with "
            "evaluator metrics before attributing failure to simulation outcomes."
        )

    return suggestions
