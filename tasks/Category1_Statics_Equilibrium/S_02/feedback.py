"""
Task-specific diagnostic feedback for S-02: The Skyscraper.
Process-aware, physics-diagnostic feedback. Uses only metrics returned by the evaluator.
No hardcoded thresholds; no solution spoilers.
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Exposes high-resolution physical metrics from the evaluator's metrics dict only.
    Phase-segregated (pre-seismic vs during quake), boundary margins, no suggestions.
    """
    if not metrics or metrics.get("error"):
        return []

    parts = []
    th = metrics.get("target_height")
    st = metrics.get("survival_threshold")
    sz = metrics.get("stability_zone")
    ihl = metrics.get("instability_height_limit")
    max_w = metrics.get("max_width_limit")

    # --- Phase 1: Pre-seismic (vertical reach) ---
    if "initial_height" in metrics:
        ih = metrics["initial_height"]
        if th is not None:
            margin = ih - th
            status = "✅" if ih >= th else "❌"
            parts.append(
                f"{status} **Pre-seismic peak height**: {ih:.2f}m "
                f"(target: >{th:.1f}m, margin: {margin:+.2f}m)"
            )
        else:
            parts.append(f"**Pre-seismic peak height**: {ih:.2f}m")

    # --- Phase 2: During quake (survival) ---
    mh = metrics.get("min_height_during_quake")
    if mh is not None:
        if st is not None:
            margin = mh - st
            status = "✅" if mh >= st else "❌"
            parts.append(
                f"{status} **Min height during seismic phase**: {mh:.2f}m "
                f"(survival limit: >{st:.1f}m, margin: {margin:+.2f}m)"
            )
        else:
            parts.append(f"**Min height during seismic phase**: {mh:.2f}m")

    # --- Lateral equilibrium (stability zone utilization) ---
    if "rel_com_x" in metrics:
        rcx = metrics["rel_com_x"]
        abs_rcx = abs(rcx)
        if sz is not None and sz > 0:
            pct = (abs_rcx / sz) * 100
            status = "✅" if abs_rcx <= sz else "❌"
            margin = sz - abs_rcx
            parts.append(
                f"{status} **Lateral COM deviation**: {rcx:+.3f}m "
                f"({pct:.1f}% of stability zone; margin to limit: {margin:+.2f}m)"
            )
        else:
            parts.append(f"**Lateral COM deviation**: {rcx:+.3f}m")

    # --- Final structural state ---
    if "current_height" in metrics:
        ch = metrics["current_height"]
        if ihl is not None and ihl > 0:
            pct = (ch / ihl) * 100
            parts.append(
                f"**Final top height**: {ch:.2f}m "
                f"({pct:.1f}% of instability threshold)"
            )
        else:
            parts.append(f"**Final top height**: {ch:.2f}m")

    # --- Constraint limits (informational; from metrics only) ---
    limits = []
    if max_w is not None:
        limits.append(f"width≤{max_w}m")
    if th is not None:
        limits.append(f"height>{th}m")
    if st is not None:
        limits.append(f"survival>{st}m")
    if limits:
        parts.append(f"**Active limits**: {', '.join(limits)}")

    return parts


def _reason_category(reason: str) -> str:
    """Maps failure_reason text to a canonical category (root-cause)."""
    if not reason:
        return ""
    r = reason.lower()
    if "width" in r and ">" in r:
        return "width"
    if "beam dimensions" in r or "outside [0.1, 10.0]" in r:
        return "beam_dimensions"
    if "foundation contact" in r or "limit: ±" in r:
        return "foundation"
    if "collapsed" in r or "fell too low" in r:
        return "collapse"
    if "tipped" in r or "rel_com_x" in r:
        return "stability"
    if "explosion" in r or "instability" in r:
        return "numerical"
    if "target height not reached" in r or "target: " in r:
        return "target_height"
    return "other"


def get_improvement_suggestions(
    metrics: Dict[str, Any],
    score: float,
    success: bool,
    failed: bool,
    failure_reason: str = None,
    error: str = None,
) -> List[str]:
    """
    Diagnostic, process-aware suggestions. Explains physical mechanism and root-cause
    chain; never dictates implementation. All thresholds from metrics (stage-adaptive).
    """
    suggestions = []
    reason = (failure_reason or "").strip()
    reason_lower = reason.lower()

    if error:
        suggestions.append(
            ">> SYSTEM: Simulation ended due to an internal error or invalid construction. "
            "Check that all construction steps and parameters are valid."
        )
        return suggestions

    # Thresholds only from metrics (no hardcoding)
    th = metrics.get("target_height")
    st = metrics.get("survival_threshold")
    sz = metrics.get("stability_zone")
    ihl = metrics.get("instability_height_limit")
    ih = metrics.get("initial_height")
    mh = metrics.get("min_height_during_quake")
    rcx = metrics.get("rel_com_x", 0.0)
    ch = metrics.get("current_height", 0.0)

    if failed:
        suggestions.append(f">> FAILURE: {reason}")

        category = _reason_category(reason)

        # --- Root-cause: what broke first (design-constraint order in evaluator) ---
        if category == "width":
            suggestions.append(
                "-> Root cause: Lateral envelope exceeded. The structure's sway or spread "
                "crossed the allowed width limit. This often reflects insufficient lateral "
                "stiffness or damping under dynamic loading rather than static geometry alone."
            )
        elif category == "beam_dimensions":
            suggestions.append(
                "-> Root cause: A beam violated the allowed dimension range. Check that every "
                "beam's width and height lie within the stated bounds; the simulator enforces this."
            )
        elif category == "foundation":
            suggestions.append(
                "-> Root cause: Ground contact outside the allowed zone. Some part of the "
                "structure (or debris) ended up outside the permitted lateral contact band. "
                "Consider how overturning or detachment can move contact points."
            )
        elif category == "collapse":
            suggestions.append(
                "-> Root cause: Loss of vertical extent during or after the seismic phase. "
                "Either the structure could not sustain the dynamic loading (resonance, "
                "insufficient energy dissipation) or structural continuity was lost (e.g. "
                "joint failure). Infer which from whether height dropped suddenly or gradually."
            )
        elif category == "stability":
            suggestions.append(
                "-> Root cause: Center of mass moved beyond the stability boundary. Lateral "
                "loading (seismic and/or wind) produced an overturning moment that the base "
                "could not resist. Mass distribution and base geometry both affect this."
            )
        elif category == "numerical":
            suggestions.append(
                "-> Root cause: Physics solver instability (e.g. explosion). Extreme motion "
                "or invalid geometry can trigger this. Avoid overlapping fixtures, extreme "
                "density ratios, or configurations that produce unbounded forces."
            )
        elif category == "target_height":
            suggestions.append(
                "-> Root cause: Peak height before the earthquake did not reach the required "
                "target. The structure either did not extend high enough in the build phase "
                "or lost height before the seismic phase began (e.g. self-weight or settling)."
            )
        else:
            suggestions.append(
                "-> Root cause: Failure was reported; use the failure message and the "
                "reported metrics to identify which constraint was violated first."
            )

        # --- Multi-objective trade-off paradox ---
        if th is not None and st is not None and sz is not None:
            height_ok = ih is not None and ih >= th
            survival_ok = mh is not None and mh >= st
            stability_ok = abs(rcx) <= sz
            if height_ok and not survival_ok:
                suggestions.append(
                    "-> Trade-off: Height was achieved before the quake but the structure "
                    "could not maintain it during dynamic loading. The bottleneck is "
                    "seismic resilience, not static reach."
                )
            if height_ok and survival_ok and not stability_ok:
                suggestions.append(
                    "-> Trade-off: Height and survival were met but lateral equilibrium was "
                    "lost. The design may be optimizing vertical performance at the cost of "
                    "lateral stability under combined loading."
                )
            if (category == "width" or category == "foundation") and height_ok:
                suggestions.append(
                    "-> Trade-off: Vertical target was met but a lateral or geometric "
                    "constraint was violated. Consider the balance between height, mass "
                    "distribution, and lateral response (stiffness/damping)."
                )

        # --- Physics-engine / numerical (only when metrics support it) ---
        if ihl is not None and ch > ihl:
            suggestions.append(
                "-> Numerical: Final height exceeded the instability threshold. The solver "
                "may have diverged; review geometry and loading for unrealistic behavior."
            )

    elif not success:
        suggestions.append(
            "-> Diagnostic: Run did not fail but did not meet full success criteria. "
            "Use the reported margins and utilization percentages to see which limits "
            "are closest and strengthen the design there."
        )

    return suggestions
