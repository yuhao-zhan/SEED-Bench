"""
Process-aware / diagnostic feedback for E-06: Cantilever Endurance.

Quantitative lines use only keys produced by evaluator.evaluate() (see evaluator.py).
Limits (mass, joint break, damage, tip band) come from the metrics dict so they track
terrain_bounds / environment fields used by the evaluator, including stage mutations
that change physics_config-driven limits surfaced in metrics.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple


def _is_finite_number(x: Any) -> bool:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return False
    return math.isfinite(v)


def _fmt_float(x: Any, nd: int = 2) -> str:
    if not _is_finite_number(x):
        return "non-finite"
    return f"{float(x):.{nd}f}"


def _ratio(numer: float, denom: float) -> Optional[float]:
    if denom == 0 or not math.isfinite(denom):
        return None
    if not math.isfinite(numer):
        return None
    return numer / denom


def _band_margin_y(y: float, band: Any) -> Optional[Tuple[str, float]]:
    """Distance to nearest band edge; negative if outside."""
    if not isinstance(band, (list, tuple)) or len(band) != 2:
        return None
    lo, hi = float(band[0]), float(band[1])
    if not (math.isfinite(lo) and math.isfinite(hi) and lo < hi):
        return None
    if y < lo:
        return ("below_band", lo - y)
    if y > hi:
        return ("above_band", y - hi)
    return ("inside_band", min(y - lo, hi - y))


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Reporting of whatever the evaluator measured — no recommendations.
    """
    parts: List[str] = []

    if not metrics:
        return parts

    if metrics.get("error"):
        parts.append(f"**Evaluator status**: {metrics['error']}")
        return parts

    if "success" in metrics:
        parts.append(f"**Run outcome (evaluator)**: success={metrics['success']}")
    if "failed" in metrics:
        parts.append(f"**Structural failure flag**: {metrics['failed']}")
    if "structure_broken" in metrics:
        parts.append(f"**Topology break detected**: {metrics['structure_broken']}")
    if metrics.get("failure_reason"):
        parts.append(f"**Failure reason (evaluator)**: {metrics['failure_reason']}")

    if "step_count" in metrics:
        parts.append(f"**Simulation step index (last report)**: {metrics['step_count']}")

    jc = metrics.get("joint_count")
    ij = metrics.get("initial_joint_count")
    bc = metrics.get("body_count")
    ib = metrics.get("initial_body_count")
    if jc is not None or bc is not None:
        line = f"**Topology**: beams={bc}, joints={jc}"
        if ib is not None and bc is not None:
            line += f" (initial beams={ib}"
            if ib != bc:
                line += f", Δbeams={bc - ib:+d}"
            line += ")"
        if ij is not None and jc is not None:
            line += f"; initial joints={ij}"
            if ij != jc:
                line += f", Δjoints={jc - ij:+d}"
        parts.append(line + ".")

    sm = metrics.get("structure_mass")
    mm = metrics.get("max_structure_mass")
    if sm is not None and _is_finite_number(sm):
        if mm is not None and _is_finite_number(mm) and math.isfinite(float(mm)):
            head = float(mm) - float(sm)
            parts.append(
                f"**Mass**: {_fmt_float(sm)} kg vs budget {_fmt_float(mm, 1)} kg "
                f"(headroom {_fmt_float(max(0.0, head), 2)} kg)."
            )
        else:
            parts.append(f"**Mass**: {_fmt_float(sm)} kg (no finite budget in metrics).")

    jbf = metrics.get("joint_break_force")
    jbt = metrics.get("joint_break_torque")
    mjf = metrics.get("max_joint_force")
    mjt = metrics.get("max_joint_torque")

    if mjf is not None and _is_finite_number(mjf) and jbf is not None and _is_finite_number(jbf):
        r = _ratio(float(mjf), float(jbf))
        if r is not None:
            parts.append(
                f"**Peak joint reaction force**: {_fmt_float(mjf)} N "
                f"vs instantaneous limit {_fmt_float(jbf)} N "
                f"(ratio {r * 100:.1f}%)."
            )
        else:
            parts.append(f"**Peak joint reaction force**: {_fmt_float(mjf)} N.")
    elif mjf is not None:
        parts.append(f"**Peak joint reaction force**: {_fmt_float(mjf)} N.")

    if mjt is not None and _is_finite_number(mjt) and jbt is not None and _is_finite_number(jbt):
        r = _ratio(float(mjt), float(jbt))
        if r is not None:
            parts.append(
                f"**Peak joint reaction torque**: {_fmt_float(mjt)} N·m "
                f"vs instantaneous limit {_fmt_float(jbt)} N·m "
                f"(ratio {r * 100:.1f}%)."
            )
        else:
            parts.append(f"**Peak joint reaction torque**: {_fmt_float(mjt)} N·m.")
    elif mjt is not None:
        parts.append(f"**Peak joint reaction torque**: {_fmt_float(mjt)} N·m.")

    dmg = metrics.get("max_joint_damage")
    dlim = metrics.get("damage_limit")
    if dmg is not None and _is_finite_number(dmg) and dlim is not None and _is_finite_number(dlim):
        dl = float(dlim)
        if dl > 0:
            parts.append(
                f"**Peak cumulative joint damage**: {_fmt_float(dmg, 1)} / {_fmt_float(dl, 1)} pts "
                f"({(float(dmg) / dl) * 100:.1f}% of reported limit)."
            )
        else:
            parts.append(
                f"**Peak cumulative joint damage**: {_fmt_float(dmg, 1)} pts "
                f"(reported limit {_fmt_float(dl, 1)} pts)."
            )
    elif dmg is not None:
        parts.append(f"**Peak cumulative joint damage**: {_fmt_float(dmg, 1)} pts.")

    if "span_check_passed" in metrics or metrics.get("span_check_message") is not None:
        scp = metrics.get("span_check_passed")
        scm = metrics.get("span_check_message", "")
        parts.append(f"**Span / height requirement (design-time check)**: passed={scp}; {scm}")

    tsr = metrics.get("tip_stability_ratio")
    tsq = metrics.get("tip_stability_required")
    if tsr is not None and _is_finite_number(tsr):
        if tsq is not None and _is_finite_number(tsq):
            parts.append(
                f"**Tip vertical band occupancy (diagnostic)**: "
                f"{float(tsr) * 100:.1f}% of elapsed steps vs stated requirement {float(tsq) * 100:.1f}%."
            )
        else:
            parts.append(
                f"**Tip vertical band occupancy (diagnostic)**: {float(tsr) * 100:.1f}% of elapsed steps."
            )

    tip_y = metrics.get("tip_y_last")
    band = metrics.get("tip_y_band")
    if tip_y is not None and _is_finite_number(tip_y):
        bm = _band_margin_y(float(tip_y), band)
        if bm:
            state, dist = bm
            parts.append(
                f"**Tip centroid height (last sample)**: y = {_fmt_float(tip_y)} m; "
                f"relation to reported band {band}: {state}, edge clearance {_fmt_float(dist, 3)} m."
            )
        else:
            parts.append(f"**Tip centroid height (last sample)**: y = {_fmt_float(tip_y)} m.")
    elif tip_y is not None:
        parts.append("**Tip centroid height (last sample)**: non-finite or missing numeric value.")

    bad = []
    for label, key in (
        ("mass", "structure_mass"),
        ("peak force", "max_joint_force"),
        ("peak torque", "max_joint_torque"),
        ("damage", "max_joint_damage"),
        ("tip y", "tip_y_last"),
    ):
        v = metrics.get(key)
        if v is not None and not _is_finite_number(v):
            bad.append(label)
    if bad:
        parts.append(
            "**Metric value note**: non-finite values in: " + ", ".join(bad) + "."
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
    Diagnostic hints using evaluator metrics only for limits and peaks.
    Does not prescribe geometry or API choices.
    """
    suggestions: List[str] = []

    if error:
        return ["Execution / build issue (not scored as physics trial): review the error above."]

    if not metrics:
        return suggestions

    if metrics.get("error"):
        return [f"Evaluator could not complete: {metrics['error']}"]

    fr = (failure_reason or metrics.get("failure_reason") or "") or ""
    fr_l = fr.lower()

    for key in ("structure_mass", "max_joint_force", "max_joint_torque", "max_joint_damage", "tip_y_last"):
        v = metrics.get(key)
        if v is not None and not _is_finite_number(v):
            suggestions.append(
                "- **Non-finite metrics**: At least one reported scalar is not finite; treat peak ratios "
                "and comparisons as unreliable until values are bounded."
            )
            break

    jbf = metrics.get("joint_break_force")
    jbt = metrics.get("joint_break_torque")
    dlim = metrics.get("damage_limit")
    mjf = metrics.get("max_joint_force")
    mjt = metrics.get("max_joint_torque")
    dmg = metrics.get("max_joint_damage")

    jbf_f = float(jbf) if jbf is not None and _is_finite_number(jbf) else None
    jbt_f = float(jbt) if jbt is not None and _is_finite_number(jbt) else None
    dlim_f = float(dlim) if dlim is not None and _is_finite_number(dlim) else None

    f_ratio = _ratio(float(mjf), jbf_f) if mjf is not None and _is_finite_number(mjf) and jbf_f is not None and jbf_f > 0 else None
    t_ratio = _ratio(float(mjt), jbt_f) if mjt is not None and _is_finite_number(mjt) and jbt_f is not None and jbt_f > 0 else None
    d_ratio = _ratio(float(dmg), dlim_f) if dmg is not None and _is_finite_number(dmg) and dlim_f is not None and dlim_f > 0 else None

    if failed or metrics.get("structure_broken"):
        modes: List[Tuple[str, float]] = []
        if f_ratio is not None:
            modes.append(("peak recorded joint reaction force vs instantaneous force limit", f_ratio))
        if t_ratio is not None:
            modes.append(("peak recorded joint reaction torque vs instantaneous torque limit", t_ratio))
        if d_ratio is not None:
            modes.append(("peak recorded cumulative joint damage vs stated damage limit", d_ratio))

        modes.sort(key=lambda x: x[1], reverse=True)
        if modes:
            primary, pr = modes[0]
            suggestions.append(
                f"- **Largest normalized load among reported peaks**: **{primary}** "
                f"(≈ {pr * 100:.1f}% of the corresponding limit in metrics)."
            )
            if len(modes) > 1:
                secondary, sr = modes[1][0], modes[1][1]
                suggestions.append(
                    f"- **Next-highest normalized load**: **{secondary}** (≈ {sr * 100:.1f}% of limit). "
                    f"Multiple channels near limits can interact under the task loading."
                )

        ib = metrics.get("initial_body_count")
        bc = metrics.get("body_count")
        ij = metrics.get("initial_joint_count")
        jc = metrics.get("joint_count")
        beam_loss = (
            ib is not None and bc is not None and _is_finite_number(ib) and _is_finite_number(bc) and bc < ib
        )
        joint_loss = (
            ij is not None and jc is not None and _is_finite_number(ij) and _is_finite_number(jc) and jc < ij
        )
        if beam_loss and not joint_loss:
            suggestions.append(
                "- **Topology change**: Beam count decreased while joint count did not in the reported snapshot. "
                "The evaluator flags beam loss separately from joint rupture; align this with the stated failure reason."
            )
        elif joint_loss and not beam_loss:
            suggestions.append(
                "- **Topology change**: Joint count decreased while beam count was unchanged in the reported snapshot."
            )
        elif beam_loss and joint_loss:
            suggestions.append(
                "- **Topology change**: Both joints and beams decreased relative to the initial counts in the reported snapshot."
            )

        if failed and modes and max(m[1] for m in modes) < 1.0:
            suggestions.append(
                "- **Peaks vs limits**: Reported maxima stayed below the instantaneous force/torque/damage limits "
                "in metrics while the run still failed. Compare this with the evaluator failure text (joint vs beam removal)."
            )

    if "design constraint" in fr_l or (metrics.get("failed") and metrics.get("structure_broken") is False and fr):
        if "mass" in fr_l:
            mm = metrics.get("max_structure_mass")
            sm = metrics.get("structure_mass")
            if sm is not None and _is_finite_number(sm) and mm is not None and _is_finite_number(mm):
                over = float(sm) - float(mm)
                if over > 0:
                    suggestions.append(
                        f"- **Mass budget**: Reported mass exceeds the evaluator-stated budget by {_fmt_float(over, 2)} kg."
                    )
        if "build zone" in fr_l or "outside" in fr_l:
            suggestions.append(
                "- **Build zone**: The evaluator reported at least one member centroid outside the build bounds it uses."
            )
        if "span" in fr_l or "extend" in fr_l or "height" in fr_l:
            suggestions.append(
                "- **Span / height check**: The design-time span/height message from the evaluator did not pass; "
                "all required extent conditions must be met jointly."
            )

    sm = metrics.get("structure_mass")
    mm = metrics.get("max_structure_mass")
    if sm is not None and mm is not None and _is_finite_number(sm) and _is_finite_number(mm):
        if float(sm) > float(mm) and failed:
            suggestions.append(
                "- **Mass vs outcome**: Reported mass is above the evaluator mass field while the run is marked failed; "
                "dynamic results are not meaningful until the static mass constraint in metrics is satisfied."
            )

    tip_y = metrics.get("tip_y_last")
    band = metrics.get("tip_y_band")
    if tip_y is not None and _is_finite_number(tip_y):
        bm = _band_margin_y(float(tip_y), band)
        if bm and bm[0] != "inside_band":
            suggestions.append(
                "- **Tip sample vs band**: The last reported tip centroid lies outside the evaluator's diagnostic "
                "vertical band; large end motion can coincide with higher moment demand for cantilever-like loading."
            )

    return suggestions
