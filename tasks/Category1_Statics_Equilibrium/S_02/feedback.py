"""
Task-specific diagnostic feedback for S-02: The Skyscraper.
Process-aware, physics-diagnostic feedback. Uses only metrics returned by the evaluator.
No hardcoded thresholds; no solution spoilers.
"""
from typing import Dict, Any, List
import math


def _is_finite(x: Any) -> bool:
    """True if x is a finite number."""
    if x is None:
        return True
    try:
        return math.isfinite(float(x))
    except (TypeError, ValueError):
        return True


def _has_numerical_anomaly(metrics: Dict[str, Any]) -> List[str]:
    """Returns list of metric keys that are non-finite (NaN/Inf). Only checks keys that exist."""
    numeric_keys = (
        "initial_height", "min_height_during_quake", "rel_com_x",
        "current_height"
    )
    anomalous = []
    for k in numeric_keys:
        if k not in metrics:
            continue
        v = metrics[k]
        if v is not None and not _is_finite(v):
            anomalous.append(k)
    return anomalous


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Exposes high-resolution physical metrics from the evaluator's metrics dict only.
    Phase-segregated (pre-seismic vs during quake), boundary margins, no suggestions.
    Reports numerical anomalies when present. Does not invent or assume metrics.
    """
    if not metrics or metrics.get("error"):
        return []

    parts = []
    th = metrics.get("target_height")
    st = metrics.get("survival_threshold")
    sz = metrics.get("stability_zone")
    ihl = metrics.get("instability_height_limit")
    max_w = metrics.get("max_width_limit")

    # --- Numerical anomaly (only if present in metrics) ---
    anomalous = _has_numerical_anomaly(metrics)
    if anomalous:
        parts.append(
            "⚠ **Numerical anomaly**: Non-finite values in "
            f"{', '.join(anomalous)}. Physics solver may have diverged."
        )

    # --- Phase 1: Pre-seismic (vertical reach) ---
    if "initial_height" in metrics:
        ih = metrics["initial_height"]
        if ih is not None and _is_finite(ih):
            if th is not None and _is_finite(th):
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
    if mh is not None and _is_finite(mh):
        if st is not None and _is_finite(st):
            margin = mh - st
            status = "✅" if mh >= st else "❌"
            parts.append(
                f"{status} **Min height during seismic phase**: {mh:.2f}m "
                f"(survival limit: ≥{st:.1f}m, margin: {margin:+.2f}m)"
            )
        else:
            parts.append(f"**Min height during seismic phase**: {mh:.2f}m")
    elif "min_height_during_quake" in metrics and metrics["min_height_during_quake"] is None:
        parts.append("**Min height during seismic phase**: N/A (evaluation ended before seismic phase)")

    # --- Lateral equilibrium (stability zone utilization) ---
    if "rel_com_x" in metrics:
        rcx = metrics["rel_com_x"]
        if rcx is not None and _is_finite(rcx):
            abs_rcx = abs(rcx)
            if sz is not None and _is_finite(sz) and sz > 0:
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
        if ch is not None and _is_finite(ch):
            if ihl is not None and _is_finite(ihl) and ihl > 0:
                pct = (ch / ihl) * 100
                parts.append(
                    f"**Final top height**: {ch:.2f}m "
                    f"({pct:.1f}% of instability threshold)"
                )
            else:
                parts.append(f"**Final top height**: {ch:.2f}m")

    # --- Active limits (informational; from metrics only) ---
    limits = []
    if max_w is not None and _is_finite(max_w):
        limits.append(f"width≤{max_w}m")
    if th is not None and _is_finite(th):
        limits.append(f"height>{th}m")
    if st is not None and _is_finite(st):
        limits.append(f"survival≥{st}m")
    if sz is not None and _is_finite(sz):
        limits.append(f"COM within ±{sz}m")
    if ihl is not None and _is_finite(ihl):
        limits.append(f"top≤{ihl}m")
    if limits:
        parts.append(f"**Active limits**: {', '.join(limits)}")

    return parts


def _reason_category(reason: str) -> str:
    """Maps failure_reason text to a canonical category. Uses only strings produced by evaluator."""
    if not reason:
        return ""
    r = reason.lower()
    if "width" in r and ">" in r:
        return "width"
    if "beam dimensions" in r:
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

    if error:
        suggestions.append(
            ">> SYSTEM: Simulation ended due to an internal error or invalid construction. "
            "Check that all construction steps and parameters are valid."
        )
        return suggestions

    # All thresholds from metrics only (no hardcoding)
    th = metrics.get("target_height")
    st = metrics.get("survival_threshold")
    sz = metrics.get("stability_zone")
    ihl = metrics.get("instability_height_limit")
    max_w = metrics.get("max_width_limit")
    ih = metrics.get("initial_height")
    mh = metrics.get("min_height_during_quake")
    rcx = metrics.get("rel_com_x", 0.0)
    ch = metrics.get("current_height", 0.0)

    # Helper: use limit only if present and finite
    def _ok(val):
        return val is not None and _is_finite(val)

    if failed:
        suggestions.append(f">> FAILURE: {reason}")

        # Root-cause chain: evaluation order is design constraints first, then
        # runtime collapse/tipping/explosion, then final height/survival check.
        suggestions.append(
            "-> Root-cause order: The reported failure is the first constraint violated "
            "in evaluation (geometry/width/foundation → collapse/stability/instability → "
            "height/survival). Identifying which group failed narrows the physical cause."
        )

        category = _reason_category(reason)

        if category == "width":
            suggestions.append(
                "-> Root cause: Lateral envelope exceeded. The structure's sway or spread "
                "crossed the allowed width limit under loading; dynamic response determines "
                "when the limit is violated."
            )
        elif category == "beam_dimensions":
            suggestions.append(
                "-> Root cause: A beam's dimensions violated the allowed range. The failure "
                "message indicates which constraint was exceeded."
            )
        elif category == "foundation":
            suggestions.append(
                "-> Root cause: Ground contact outside the allowed zone. Some part of the "
                "structure or debris ended up outside the permitted lateral contact band. "
                "Overturning or detachment can move contact points beyond the limit."
            )
        elif category == "collapse":
            suggestions.append(
                "-> Root cause: Loss of vertical extent during or after the seismic phase. "
                "The structure could not sustain the dynamic loading or structural continuity "
                "was lost; whether height dropped suddenly or gradually indicates the mechanism."
            )
        elif category == "stability":
            suggestions.append(
                "-> Root cause: Center of mass moved beyond the stability boundary. Lateral "
                "loading produced an overturning moment that the base could not resist."
            )
        elif category == "numerical":
            suggestions.append(
                "-> Root cause: Physics solver instability (e.g. explosion). Extreme motion "
                "or invalid geometry can trigger unbounded forces and solver divergence."
            )
        elif category == "target_height":
            suggestions.append(
                "-> Root cause: Peak height before the earthquake did not reach the required "
                "target. Either vertical reach was insufficient in the build phase or height "
                "was lost before the seismic phase (e.g. self-weight or settling)."
            )
        else:
            suggestions.append(
                "-> Root cause: Failure was reported; use the failure message and the "
                "reported metrics to identify which constraint was violated first."
            )

        # Trade-off diagnostics: only when all limits exist in metrics
        if _ok(th) and _ok(st) and _ok(sz):
            height_ok = _ok(ih) and ih >= th
            survival_ok = _ok(mh) and mh >= st
            stability_ok = _is_finite(rcx) and abs(rcx) <= sz
            if height_ok and not survival_ok:
                suggestions.append(
                    "-> Trade-off: Height was achieved before the quake but not maintained "
                    "during dynamic loading; the bottleneck is seismic resilience."
                )
            if height_ok and survival_ok and not stability_ok:
                suggestions.append(
                    "-> Trade-off: Height and survival were met but lateral equilibrium was "
                    "lost; vertical performance was achieved at the cost of stability under load."
                )
            if (category == "width" or category == "foundation") and height_ok:
                suggestions.append(
                    "-> Trade-off: Vertical target was met but a lateral or geometric "
                    "constraint was violated."
                )

        # Numerical: only when metrics support it (instability_height_limit, current_height)
        if _ok(ihl) and _ok(ch) and ch > ihl:
            suggestions.append(
                "-> Numerical: Final height exceeded the instability threshold; the solver "
                "may have diverged."
            )

        anomalous = _has_numerical_anomaly(metrics)
        if anomalous:
            suggestions.append(
                "-> Numerical: Non-finite values in key metrics suggest solver divergence."
            )

    elif not success:
        suggestions.append(
            "-> Diagnostic: Run did not fail but did not meet full success criteria. "
            "Use the reported margins and utilization percentages to identify which "
            "limits are closest to violation."
        )

    return suggestions
