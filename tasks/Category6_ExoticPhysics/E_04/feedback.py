"""
Process-aware diagnostic feedback for E-04: Variable Mass.

`format_task_metrics` and `get_improvement_suggestions` only use keys and values
produced by `Evaluator.evaluate()` (see evaluator.py). Limits and budgets are
read from the metrics dict (including `max_structure_mass`, joint reaction peaks,
and effective/nominal limits when present).
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

# Scalar keys evaluator.evaluate() may populate (including early-return design paths).
_KNOWN_SCALAR_KEYS = frozenset(
    {
        "step_count",
        "joint_count",
        "beam_count",
        "initial_joint_count",
        "structure_mass",
        "max_structure_mass",
        "max_joint_reaction_force",
        "max_joint_reaction_torque",
        "joint_break_force_limit",
        "joint_break_torque_limit",
        "effective_joint_force_limit",
        "effective_joint_torque_limit",
        "simulation_time_s",
    }
)


def _as_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        x = float(value)
    except (TypeError, ValueError):
        return None
    return x


def _is_bad_number(x: float) -> bool:
    return not math.isfinite(x)


def _metrics_have_nonfinite_values(metrics: Dict[str, Any]) -> bool:
    for key in _KNOWN_SCALAR_KEYS:
        if key not in metrics:
            continue
        v = _as_float(metrics.get(key))
        if v is not None and _is_bad_number(v):
            return True
    return False


def _effective_force_limit(metrics: Dict[str, Any]) -> Optional[float]:
    v = _as_float(metrics.get("effective_joint_force_limit"))
    if v is not None:
        return v
    return _as_float(metrics.get("joint_break_force_limit"))


def _effective_torque_limit(metrics: Dict[str, Any]) -> Optional[float]:
    v = _as_float(metrics.get("effective_joint_torque_limit"))
    if v is not None:
        return v
    return _as_float(metrics.get("joint_break_torque_limit"))


def _utilization(peak: Optional[float], limit: Optional[float]) -> Optional[float]:
    if peak is None or limit is None:
        return None
    if _is_bad_number(peak) or _is_bad_number(limit):
        return None
    eps = max(abs(limit) * 1e-12, 1e-15)
    if abs(limit) < eps:
        return None
    return peak / limit


def _format_margin_pct(util: Optional[float]) -> str:
    if util is None:
        return "n/a"
    pct = util * 100.0
    if _is_bad_number(pct):
        return "n/a"
    return f"{pct:.1f}% of reference capacity"


def _limit_too_tiny_for_ratio(limit: Optional[float]) -> bool:
    """Skip peak/limit ratio when the reported limit is ~0 (metrics-grounded heuristic)."""
    if limit is None or _is_bad_number(limit):
        return True
    peak_ref = 1e-8
    return abs(limit) < peak_ref


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Readout of evaluator-supplied metrics only (no suggestions).
    """
    parts: List[str] = []

    if not metrics:
        return parts

    if "error" in metrics:
        parts.append(f"**Evaluation**: {metrics['error']}")

    for key in ("success", "failed", "structure_broken"):
        if key in metrics:
            parts.append(f"**{key.replace('_', ' ').title()}**: {metrics[key]}")

    if "step_count" in metrics:
        parts.append(f"**Step index**: {metrics['step_count']}")

    fr = metrics.get("failure_reason")
    if fr:
        parts.append(f"**Stated outcome detail**: {fr}")

    jc = metrics.get("joint_count")
    bc = metrics.get("beam_count")
    ijc = metrics.get("initial_joint_count")
    topo_bits = []
    if jc is not None:
        topo_bits.append(f"{jc} joints")
    if bc is not None:
        topo_bits.append(f"{bc} beams")
    if ijc is not None:
        topo_bits.append(f"{ijc} joints at first dynamics step")
    if topo_bits:
        parts.append("**Topology (reported)**: " + "; ".join(topo_bits))

    sm = _as_float(metrics.get("structure_mass"))
    mm = _as_float(metrics.get("max_structure_mass"))
    if sm is not None and mm is not None and not (_is_bad_number(sm) or _is_bad_number(mm)):
        parts.append(f"**Instantaneous structure mass**: {sm:.4f} kg (budget from evaluation: {mm:.4f} kg)")
        if mm > 0:
            parts.append(f"**Mass budget utilization**: {sm / mm * 100:.1f}% of evaluated limit")
    elif sm is not None and not _is_bad_number(sm):
        parts.append(f"**Instantaneous structure mass**: {sm:.4f} kg")

    f_peak = _as_float(metrics.get("max_joint_reaction_force"))
    f_lim_eff = _effective_force_limit(metrics)
    f_nom = _as_float(metrics.get("joint_break_force_limit"))
    if f_peak is not None and not _is_bad_number(f_peak):
        if _limit_too_tiny_for_ratio(f_lim_eff) and f_lim_eff is not None:
            cap_line = "utilization ratio omitted (reported force limit magnitude is extremely small)"
        else:
            u_f = _utilization(f_peak, f_lim_eff)
            cap_line = _format_margin_pct(u_f)
        extra = ""
        if f_nom is not None and f_lim_eff is not None and not (
            _is_bad_number(f_nom) or _is_bad_number(f_lim_eff)
        ):
            if f_nom > 0:
                extra = f"; nominal reference limit (reported): {f_nom:.6g} N; instantaneous reference limit (reported): {f_lim_eff:.6g} N"
        parts.append(f"**Peak joint reaction force (reported)**: {f_peak:.6g} N ({cap_line}){extra}")

    t_peak = _as_float(metrics.get("max_joint_reaction_torque"))
    t_lim_eff = _effective_torque_limit(metrics)
    t_nom = _as_float(metrics.get("joint_break_torque_limit"))
    if t_peak is not None and not _is_bad_number(t_peak):
        if _limit_too_tiny_for_ratio(t_lim_eff) and t_lim_eff is not None:
            cap_line = "utilization ratio omitted (reported torque limit magnitude is extremely small)"
        else:
            u_t = _utilization(t_peak, t_lim_eff)
            cap_line = _format_margin_pct(u_t)
        extra = ""
        if t_nom is not None and t_lim_eff is not None and not (
            _is_bad_number(t_nom) or _is_bad_number(t_lim_eff)
        ):
            extra = f"; nominal reference limit (reported): {t_nom:.6g} N·m; instantaneous reference limit (reported): {t_lim_eff:.6g} N·m"
        parts.append(f"**Peak joint reaction torque (reported)**: {t_peak:.6g} N·m ({cap_line}){extra}")

    st = _as_float(metrics.get("simulation_time_s"))
    if st is not None and not _is_bad_number(st):
        parts.append(f"**Recorded simulation time**: {st:.4f} s")

    if _metrics_have_nonfinite_values(metrics):
        parts.append("**Numeric integrity**: One or more reported scalar metrics are non-finite (NaN/Inf).")

    return parts


def _design_constraint_failure(failure_reason: Optional[str]) -> bool:
    if not failure_reason:
        return False
    return failure_reason.lower().startswith("design constraint violated")


def _joint_failure_dominance(
    metrics: Dict[str, Any],
) -> Tuple[Optional[str], Optional[float], Optional[float]]:
    """Return ('force'|'torque'|None, u_force, u_torque) using only metrics."""
    f_peak = _as_float(metrics.get("max_joint_reaction_force"))
    t_peak = _as_float(metrics.get("max_joint_reaction_torque"))
    f_lim = _effective_force_limit(metrics)
    t_lim = _effective_torque_limit(metrics)
    u_f = None if _limit_too_tiny_for_ratio(f_lim) else _utilization(f_peak, f_lim)
    u_t = None if _limit_too_tiny_for_ratio(t_lim) else _utilization(t_peak, t_lim)
    if u_f is None and u_t is None:
        return None, u_f, u_t
    if u_f is None:
        return "torque", u_f, u_t
    if u_t is None:
        return "force", u_f, u_t
    if u_t > u_f:
        return "torque", u_f, u_t
    if u_f > u_t:
        return "force", u_f, u_t
    return "balanced", u_f, u_t


def get_improvement_suggestions(
    metrics: Dict[str, Any],
    score: float,
    success: bool,
    failed: bool,
    failure_reason: str = None,
    error: str = None,
) -> List[str]:
    """
    Diagnostic feedback from evaluator metrics only: failure mechanisms, not designs.
    """
    suggestions: List[str] = []

    if metrics.get("error"):
        suggestions.append(
            "- **Evaluation gap**: The evaluator did not produce a full metric bundle; treat dynamic diagnosis as unavailable until execution returns normal metrics."
        )
        return suggestions

    if error:
        return suggestions

    fr = failure_reason if failure_reason is not None else metrics.get("failure_reason")

    if _metrics_have_nonfinite_values(metrics):
        suggestions.append(
            "- **Non-finite reported scalars**: At least one evaluator-reported numeric field is NaN or infinite; "
            "peak-to-limit ratios and utilization comparisons that rely on those fields are not meaningful until the reported values are finite."
        )

    if success:
        return suggestions

    # Design-time failures (evaluator returns with constraint violations)
    if failed and not metrics.get("structure_broken") and _design_constraint_failure(fr):
        suggestions.append(
            "- **Failure stage (reported)**: The outcome is attributed to design checks before or at the start of dynamics; "
            "connection reaction histories may not apply to this failure mode."
        )
        if fr and ";" in fr:
            suggestions.append(
                "- **Multiple reported violations**: The failure string concatenates several clauses; each reported requirement must be satisfied independently."
            )
        sm = _as_float(metrics.get("structure_mass"))
        mm = _as_float(metrics.get("max_structure_mass"))
        if sm is not None and mm is not None and mm > 0 and sm > mm:
            suggestions.append(
                "- **Mass vs. evaluated cap**: Reported instantaneous mass exceeds `max_structure_mass` from the same metric bundle."
            )
        if fr:
            low = fr.lower()
            if "span" in low and sm is not None and mm is not None and mm > 0 and sm <= mm:
                suggestions.append(
                    "- **Span (reported)**: The failure text references span while mass is within the evaluated cap; "
                    "the reported issue concerns horizontal coverage relative to the evaluator's span checks, not mass alone."
                )
            if "pivot" in low or "revolute" in low:
                suggestions.append(
                    "- **Joint-type rule (reported)**: The failure text references pivot/revolute connectivity; "
                    "that is separate from whether reaction peaks stayed within reported limits."
                )

    # Dynamic disintegration (joint count dropped)
    if failed and metrics.get("structure_broken"):
        suggestions.append(
            "- **Failure mode (reported)**: Joint count dropped relative to the start of evaluation; "
            "the stated failure reason attributes this to reaction force or torque exceeding limits."
        )
        t_lim_r = _effective_torque_limit(metrics)
        f_lim_r = _effective_force_limit(metrics)
        if _limit_too_tiny_for_ratio(t_lim_r) and t_lim_r is not None:
            suggestions.append(
                "- **Near-zero reported torque limit**: The instantaneous torque limit in the metrics is extremely small; "
                "moment demand at connections operates against that reported ceiling."
            )
        if _limit_too_tiny_for_ratio(f_lim_r) and f_lim_r is not None:
            suggestions.append(
                "- **Near-zero reported force limit**: The instantaneous force limit in the metrics is extremely small; "
                "force demand at connections operates against that reported ceiling."
            )

        dom, u_f, u_t = _joint_failure_dominance(metrics)
        if dom == "torque":
            suggestions.append(
                "- **Relative utilization (reported peaks vs. reported instantaneous limits)**: "
                "Torque ratio appears higher than force ratio at the recorded extremes—moment transfer at connections dominates the comparison."
            )
        elif dom == "force":
            suggestions.append(
                "- **Relative utilization (reported peaks vs. reported instantaneous limits)**: "
                "Force ratio appears higher than torque ratio at the recorded extremes—force transfer at connections dominates the comparison."
            )
        elif dom == "balanced":
            suggestions.append(
                "- **Coupled demand (reported)**: Force and torque utilization ratios are comparably high at the recorded extremes."
            )

        f_nom = _as_float(metrics.get("joint_break_force_limit"))
        f_eff = _as_float(metrics.get("effective_joint_force_limit"))
        t_nom = _as_float(metrics.get("joint_break_torque_limit"))
        t_eff = _as_float(metrics.get("effective_joint_torque_limit"))
        if (
            f_nom is not None
            and f_eff is not None
            and f_nom > 0
            and f_eff < f_nom
            and not (_is_bad_number(f_nom) or _is_bad_number(f_eff))
        ):
            suggestions.append(
                "- **Reported capacity drift (force)**: The reported instantaneous force limit is below the reported nominal force limit in the same bundle."
            )
        if (
            t_nom is not None
            and t_eff is not None
            and t_nom > 0
            and t_eff < t_nom
            and not (_is_bad_number(t_nom) or _is_bad_number(t_eff))
        ):
            suggestions.append(
                "- **Reported capacity drift (torque)**: The reported instantaneous torque limit is below the reported nominal torque limit in the same bundle."
            )

        st = _as_float(metrics.get("simulation_time_s"))
        if st is not None and not _is_bad_number(st):
            suggestions.append(
                f"- **Reported simulation time at outcome**: {st:.4f} s (from metrics)."
            )

        sm = _as_float(metrics.get("structure_mass"))
        mm = _as_float(metrics.get("max_structure_mass"))
        if sm is not None and mm is not None and mm > 0 and sm <= mm:
            suggestions.append(
                "- **Mass cap vs. integrity**: Mass is within the evaluated `max_structure_mass` while connections still failed—integrity is not implied by mass compliance alone in these metrics."
            )

    # Not failed and not successful (e.g. partial evaluation horizon)
    if not failed and not success:
        suggestions.append(
            "- **Non-terminal outcome**: Failure is not flagged and success is false; "
            "the metric bundle reflects a state before the evaluator's full-run success condition."
        )

    return suggestions
