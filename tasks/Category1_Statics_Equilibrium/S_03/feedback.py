"""
Task-specific feedback for S-03: The Cantilever (Statics / Structural Equilibrium).
Process-aware, diagnostic feedback only. Uses only metrics from evaluator.evaluate();
all limits and thresholds are read from the metrics dict (stage-mutation safe).
No spoilers; no hallucinated constraints or variables.
"""
from typing import Dict, Any, List
import math


def _is_valid_number(x: Any) -> bool:
    """True if x is a finite number (no NaN, no inf)."""
    if x is None:
        return False
    try:
        f = float(x)
        return math.isfinite(f)
    except (TypeError, ValueError):
        return False


# Only numeric keys actually returned by evaluator.evaluate(); used for instability checks.
_EVALUATOR_NUMERIC_KEYS = (
    "tip_x", "max_reach", "target_reach", "current_reach", "min_tip_y", "min_tip_height",
    "structure_mass", "max_structure_mass", "peak_joint_torque", "peak_joint_force",
    "max_anchor_torque_limit", "max_internal_torque_limit",
    "max_anchor_force_limit", "max_internal_force_limit",
    "load_hold_time", "load2_hold_time", "external_force_y", "step_count",
    "reach_tolerance", "joint_count", "initial_joint_count", "anchor_count",
    "max_anchors_limit", "max_anchor_points",
)


def _has_numerical_instability(metrics: Dict[str, Any]) -> List[str]:
    """Report non-finite values only for metrics actually returned by evaluator."""
    warnings = []
    for key in _EVALUATOR_NUMERIC_KEYS:
        v = metrics.get(key)
        if v is None:
            continue
        try:
            f = float(v)
            if not math.isfinite(f):
                warnings.append(f"Numerical instability: '{key}' = {v} (non-finite).")
        except (TypeError, ValueError):
            pass
    return warnings


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Expose high-resolution physical metrics from evaluator output only.
    No suggestions. All limits/thresholds read from metrics (dynamic, stage-mutation safe).
    Includes phase-specific segregation where metrics provide it.
    """
    metric_parts = []

    # --- Physics engine limits: numerical instability ---
    instability = _has_numerical_instability(metrics)
    if instability:
        metric_parts.append("**Physics engine limits**: " + " ".join(instability))

    # --- Boundary proximity (only keys present in metrics) ---
    margin_parts = []
    max_reach = metrics.get("max_reach")
    target_reach = metrics.get("target_reach")
    if _is_valid_number(max_reach) and _is_valid_number(target_reach):
        tr, mr = float(target_reach), float(max_reach)
        margin_parts.append(f"reach {mr - tr:+.2f}m")
    min_tip_y = metrics.get("min_tip_y")
    min_tip_height = metrics.get("min_tip_height")
    if _is_valid_number(min_tip_y) and _is_valid_number(min_tip_height):
        margin_parts.append(f"tip height {float(min_tip_y) - float(min_tip_height):+.2f}m")
    structure_mass = metrics.get("structure_mass")
    max_structure_mass = metrics.get("max_structure_mass")
    if _is_valid_number(structure_mass) and _is_valid_number(max_structure_mass):
        margin_parts.append(f"mass {float(max_structure_mass) - float(structure_mass):+.2f}kg")
    peak_joint_torque = metrics.get("peak_joint_torque")
    max_anchor_torque_limit = metrics.get("max_anchor_torque_limit")
    max_internal_torque_limit = metrics.get("max_internal_torque_limit")
    peak_joint_force = metrics.get("peak_joint_force")
    max_anchor_force_limit = metrics.get("max_anchor_force_limit")
    max_internal_force_limit = metrics.get("max_internal_force_limit")
    if _is_valid_number(peak_joint_torque):
        p = float(peak_joint_torque)
        for lim, name in [(max_anchor_torque_limit, "anchor"), (max_internal_torque_limit, "internal")]:
            if _is_valid_number(lim) and float(lim) != float("inf"):
                L = float(lim)
                margin_parts.append(f"torque({name}) {L - p:+.1f} N·m")
                break
    if _is_valid_number(peak_joint_force):
        pf = float(peak_joint_force)
        for lim, name in [(max_anchor_force_limit, "anchor"), (max_internal_force_limit, "internal")]:
            if _is_valid_number(lim) and float(lim) != float("inf"):
                L = float(lim)
                margin_parts.append(f"force({name}) {L - pf:+.1f} N")
                break
    if margin_parts:
        metric_parts.append("**Boundary proximity**: " + "; ".join(margin_parts))

    # --- Reach ---
    current_reach = metrics.get("current_reach") or metrics.get("tip_x")
    reach_tolerance = metrics.get("reach_tolerance")

    if _is_valid_number(max_reach) and _is_valid_number(target_reach):
        tr = float(target_reach)
        mr = float(max_reach)
        margin = mr - tr if tr > 0 else 0.0
        status = "✅" if mr >= tr else "❌"
        metric_parts.append(
            f"{status} **Maximum Horizontal Reach**: {mr:.2f}m (Target: {tr:.2f}m; margin: {margin:+.2f}m)"
        )
    if _is_valid_number(current_reach) and _is_valid_number(target_reach):
        cr, tr = float(current_reach), float(target_reach)
        shortfall = tr - cr
        if shortfall > 0:
            metric_parts.append(f"**Reach shortfall under load**: {shortfall:.2f}m (tip x vs target)")
    if _is_valid_number(current_reach):
        metric_parts.append(f"**Current tip x**: {float(current_reach):.2f}m")
    if _is_valid_number(reach_tolerance) and target_reach is not None:
        tol = float(reach_tolerance)
        metric_parts.append(f"**Reach deflection tolerance**: ±{tol:.1f}m under load")

    # --- Tip height / sag ---
    min_tip_y = metrics.get("min_tip_y")
    min_tip_height = metrics.get("min_tip_height")
    tip_sagged = metrics.get("tip_sagged")

    if _is_valid_number(min_tip_y) and _is_valid_number(min_tip_height):
        mty = float(min_tip_y)
        mth = float(min_tip_height)
        margin = mty - mth
        status = "✅" if margin >= 0 else "❌"
        metric_parts.append(
            f"{status} **Tip clearance height**: {mty:.2f}m (Minimum: {mth:.1f}m; margin: {margin:+.2f}m)"
        )
    if tip_sagged is True:
        metric_parts.append("**Sag state**: Tip fell below allowed vertical threshold.")

    # --- Structural integrity ---
    anchor_broken = metrics.get("anchor_broken")
    joint_count = metrics.get("joint_count")
    initial_joint_count = metrics.get("initial_joint_count")

    if anchor_broken is not None:
        status = "❌ BROKEN" if anchor_broken else "✅ INTACT"
        metric_parts.append(f"**Structural integrity**: {status}")
    if _is_valid_number(joint_count) and _is_valid_number(initial_joint_count):
        jc, ijc = int(joint_count), int(initial_joint_count)
        lost = ijc - jc
        if lost > 0:
            metric_parts.append(f"**Joints lost**: {lost} (from {ijc} → {jc})")

    # --- Peak forces and torques vs limits (from metrics only) ---
    if _is_valid_number(peak_joint_torque):
        peak = float(peak_joint_torque)
        anchor_lim = float(max_anchor_torque_limit) if _is_valid_number(max_anchor_torque_limit) else float("inf")
        internal_lim = float(max_internal_torque_limit) if _is_valid_number(max_internal_torque_limit) else float("inf")
        margin_anchor = anchor_lim - peak if math.isfinite(anchor_lim) else None
        margin_internal = internal_lim - peak if math.isfinite(internal_lim) else None
        s_anchor = "✅" if margin_anchor is not None and margin_anchor >= 0 else "❌"
        s_internal = "✅" if margin_internal is not None and margin_internal >= 0 else "❌"
        parts_torque = [f"**Peak joint torque**: {peak:.1f} N·m"]
        if math.isfinite(anchor_lim):
            pct_anchor = (peak / anchor_lim * 100) if anchor_lim > 0 else 0
            parts_torque.append(f"Anchor limit: {anchor_lim:.1f} N·m (margin: {margin_anchor:+.1f}, {pct_anchor:.0f}% utilized) {s_anchor}")
        if math.isfinite(internal_lim):
            pct_internal = (peak / internal_lim * 100) if internal_lim > 0 else 0
            parts_torque.append(f"Internal limit: {internal_lim:.1f} N·m (margin: {margin_internal:+.1f}, {pct_internal:.0f}% utilized) {s_internal}")
        metric_parts.append(" | ".join(parts_torque))

    if _is_valid_number(peak_joint_force):
        peak_f = float(peak_joint_force)
        anchor_f_lim = float(max_anchor_force_limit) if _is_valid_number(max_anchor_force_limit) else float("inf")
        internal_f_lim = float(max_internal_force_limit) if _is_valid_number(max_internal_force_limit) else float("inf")
        margin_anchor_f = anchor_f_lim - peak_f if math.isfinite(anchor_f_lim) else None
        margin_internal_f = internal_f_lim - peak_f if math.isfinite(internal_f_lim) else None
        s_anchor_f = "✅" if margin_anchor_f is not None and margin_anchor_f >= 0 else "❌"
        s_internal_f = "✅" if margin_internal_f is not None and margin_internal_f >= 0 else "❌"
        parts_force = [f"**Peak joint force**: {peak_f:.1f} N"]
        if math.isfinite(anchor_f_lim):
            pct_anchor_f = (peak_f / anchor_f_lim * 100) if anchor_f_lim > 0 else 0
            parts_force.append(f"Anchor limit: {anchor_f_lim:.1f} N (margin: {margin_anchor_f:+.1f}, {pct_anchor_f:.0f}% utilized) {s_anchor_f}")
        if math.isfinite(internal_f_lim):
            pct_internal_f = (peak_f / internal_f_lim * 100) if internal_f_lim > 0 else 0
            parts_force.append(f"Internal limit: {internal_f_lim:.1f} N (margin: {margin_internal_f:+.1f}, {pct_internal_f:.0f}% utilized) {s_internal_f}")
        metric_parts.append(" | ".join(parts_force))

    # --- Phase-specific segregation (load phases and hold times from metrics only) ---
    load_hold_time = metrics.get("load_hold_time")
    load2_hold_time = metrics.get("load2_hold_time")
    load_attached = metrics.get("load_attached")
    load2_attached = metrics.get("load2_attached")

    phase_lines = []
    if load_attached is not None or load2_attached is not None:
        ph = []
        if load_attached:
            ph.append("L1 on")
        if load2_attached:
            ph.append("L2 on")
        if ph:
            phase_lines.append(f"Load phase at report: {' '.join(ph)}")
    if _is_valid_number(load_hold_time):
        phase_lines.append(f"Primary load hold: {float(load_hold_time):.2f}s")
    if _is_valid_number(load2_hold_time):
        phase_lines.append(f"Secondary load hold: {float(load2_hold_time):.2f}s")
    if phase_lines:
        metric_parts.append("**Phase-specific**: " + "; ".join(phase_lines))

    # --- Mass ---
    if _is_valid_number(structure_mass) and _is_valid_number(max_structure_mass):
        sm = float(structure_mass)
        msm = float(max_structure_mass)
        margin = msm - sm
        status = "✅" if sm <= msm else "❌"
        metric_parts.append(
            f"{status} **Total structural mass**: {sm:.2f}kg (Budget: {msm:.0f}kg; margin: {margin:+.2f}kg)"
        )

    # --- Anchors ---
    anchor_count = metrics.get("anchor_count")
    max_anchors_limit = metrics.get("max_anchors_limit")

    if _is_valid_number(anchor_count) and _is_valid_number(max_anchors_limit):
        ac = int(anchor_count)
        mal = int(max_anchors_limit)
        status = "✅" if ac <= mal else "❌"
        metric_parts.append(f"{status} **Wall anchor count**: {ac} (max: {mal})")

    # --- External force (only if in metrics) ---
    external_force_y = metrics.get("external_force_y")
    if _is_valid_number(external_force_y) and float(external_force_y) != 0:
        metric_parts.append(f"**Mean external force (Y) on structure**: {float(external_force_y):.1f} N (per body)")

    # --- Step count (only if in metrics) ---
    step_count = metrics.get("step_count")
    if _is_valid_number(step_count):
        metric_parts.append(f"**Simulation step**: {int(step_count)}")

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
    Diagnostic suggestions only, derived from evaluator metrics.
    No design/API spoilers; no hardcoded physical limits; all thresholds from metrics.
    Emphasizes multi-objective trade-offs and root-cause chain (what broke first).
    """
    suggestions = []
    reason_lower = str(failure_reason).lower() if failure_reason else ""

    if error:
        suggestions.append(">> DIAGNOSTIC: Engineering constraints violated at design time.")
        return suggestions

    # --- Physics engine limits: numerical instability ---
    instability = _has_numerical_instability(metrics)
    if instability:
        suggestions.append(
            ">> Physics engine limits: Numerical instability detected (non-finite values). "
            "Simulation state may be invalid; consider whether geometry or loading produced impossible forces or velocities."
        )

    if not failed:
        # Success: optional tight-margin notes using only metrics (dynamic thresholds)
        max_reach = metrics.get("max_reach")
        target_reach = metrics.get("target_reach")
        reach_tolerance = metrics.get("reach_tolerance")
        if _is_valid_number(max_reach) and _is_valid_number(target_reach) and float(target_reach) > 0:
            margin_r = float(max_reach) - float(target_reach)
            tol = float(reach_tolerance) if _is_valid_number(reach_tolerance) else None
            if tol is not None and 0 <= margin_r < tol:
                suggestions.append(
                    "-> Note: Reach margin was small; additional load or deflection could compromise success."
                )
        peak_joint_torque = metrics.get("peak_joint_torque")
        max_anchor_torque_limit = metrics.get("max_anchor_torque_limit")
        max_internal_torque_limit = metrics.get("max_internal_torque_limit")
        peak_joint_force = metrics.get("peak_joint_force")
        max_anchor_force_limit = metrics.get("max_anchor_force_limit")
        max_internal_force_limit = metrics.get("max_internal_force_limit")
        for (peak_key, anchor_lim_key, internal_lim_key, name) in [
            (peak_joint_torque, max_anchor_torque_limit, max_internal_torque_limit, "torque"),
            (peak_joint_force, max_anchor_force_limit, max_internal_force_limit, "force"),
        ]:
            p = metrics.get(peak_key)
            if not _is_valid_number(p):
                continue
            p_val = float(p)
            for lim_key in (anchor_lim_key, internal_lim_key):
                lim = metrics.get(lim_key)
                if _is_valid_number(lim) and float(lim) > 0:
                    headroom = float(lim) - p_val
                    if headroom >= 0 and headroom / float(lim) < 0.15:
                        suggestions.append(
                            f"-> Note: Peak joint {name} was close to the limit; little headroom for additional load."
                        )
                        break
            else:
                continue
            break
        return suggestions

    suggestions.append(f">> FAILURE MODE: {failure_reason}")

    # --- Multi-objective trade-off paradox ---
    max_reach = metrics.get("max_reach")
    target_reach = metrics.get("target_reach")
    structure_mass = metrics.get("structure_mass")
    max_structure_mass = metrics.get("max_structure_mass")
    tip_sagged = metrics.get("tip_sagged")
    anchor_broken = metrics.get("anchor_broken")

    reach_met = _is_valid_number(max_reach) and _is_valid_number(target_reach) and float(max_reach) >= float(target_reach)
    mass_ok = _is_valid_number(structure_mass) and _is_valid_number(max_structure_mass) and float(structure_mass) <= float(max_structure_mass)

    if reach_met and not mass_ok:
        suggestions.append(
            "-> Horizontal reach was achieved, but structure mass exceeded the budget. "
            "Consider the strength-to-weight trade-off."
        )
        return suggestions
    if reach_met and tip_sagged:
        suggestions.append(
            "-> Reach was achieved but tip clearance was violated (excessive sag). "
            "Deflection exceeded the allowed limit; stiffness or load distribution may be the limiting factor."
        )
        return suggestions
    if reach_met and anchor_broken:
        suggestions.append(
            "-> Reach was achieved but structural integrity was lost. "
            "Load-bearing capacity at joints or anchors was exceeded; consider where moments and forces concentrate."
        )
        return suggestions
    if not reach_met and mass_ok and not tip_sagged and not anchor_broken:
        suggestions.append(
            "-> The limiting factor was horizontal extension; load-bearing and integrity were sufficient. "
            "Consider how to extend reach within the same mass and integrity constraints."
        )
        return suggestions

    # --- Root-cause chain identification (what broke first) ---
    if "design constraint" in reason_lower or "outside build zone" in reason_lower or "too many wall anchors" in reason_lower:
        suggestions.append(
            "-> Root cause: Constraint violation at build time (geometry or anchor count). "
            "Structure was rejected before load test; no physical failure sequence to infer."
        )
        return suggestions

    if "mass" in reason_lower and "exceeds" in reason_lower:
        suggestions.append(
            "-> Root cause: Total structure mass exceeded the allowed budget. "
            "Failure is resource limit, not load-bearing; consider optimizing the strength-to-weight ratio."
        )
        return suggestions

    if "structure integrity lost" in reason_lower or "joints or wall anchors broke" in reason_lower:
        peak = metrics.get("peak_joint_torque")
        anchor_lim = metrics.get("max_anchor_torque_limit")
        internal_lim = metrics.get("max_internal_torque_limit")
        peak_f = metrics.get("peak_joint_force")
        anchor_f_lim = metrics.get("max_anchor_force_limit")
        internal_f_lim = metrics.get("max_internal_force_limit")
        load_hold_time = metrics.get("load_hold_time")
        load2_hold_time = metrics.get("load2_hold_time")
        if _is_valid_number(peak) or _is_valid_number(peak_f):
            p = float(peak) if _is_valid_number(peak) else 0.0
            a_lim = float(anchor_lim) if _is_valid_number(anchor_lim) else None
            i_lim = float(internal_lim) if _is_valid_number(internal_lim) else None
            pf = float(peak_f) if _is_valid_number(peak_f) else 0.0
            a_f_lim = float(anchor_f_lim) if _is_valid_number(anchor_f_lim) else None
            i_f_lim = float(internal_f_lim) if _is_valid_number(internal_f_lim) else None
            # Identify which constraint was exceeded first (anchor vs internal; torque vs force)
            if i_lim is not None and p >= i_lim and (a_lim is None or p < a_lim):
                suggestions.append(
                    "-> Root cause: A beam-to-beam joint exceeded its torque capacity. "
                    "Bending moment or eccentric load concentrated at an internal connection; "
                    "the failure likely occurred at an internal joint first."
                )
            elif a_lim is not None and p >= a_lim:
                suggestions.append(
                    "-> Root cause: Wall anchorage exceeded its torque capacity. "
                    "The wall connection was the weak link in the load path."
                )
            elif i_f_lim is not None and pf >= i_f_lim and (a_f_lim is None or pf < a_f_lim):
                suggestions.append(
                    "-> Root cause: A beam-to-beam joint exceeded its force capacity. "
                    "Axial or shear load at an internal connection exceeded the limit."
                )
            elif a_f_lim is not None and pf >= a_f_lim:
                suggestions.append(
                    "-> Root cause: Wall anchorage exceeded its force capacity. "
                    "The wall connection was the weak link."
                )
            else:
                suggestions.append(
                    "-> Root cause: Structural integrity lost. "
                    "Compare peak joint torque and force to anchor and internal limits in the metrics to identify which constraint was exceeded first."
                )
        else:
            suggestions.append(
                "-> Root cause: Structural integrity lost. "
                "Check peak joint torque and force vs. anchor and internal limits in the metrics to identify the failing component."
            )
        # Which load phase: only from metrics (hold times)
        if _is_valid_number(load_hold_time) and _is_valid_number(load2_hold_time):
            t1, t2 = float(load_hold_time), float(load2_hold_time)
            if t1 >= 0 and t2 <= 0:
                suggestions.append(
                    "-> Failure occurred during or before the first load phase; the second load was not yet sustained."
                )
            elif t1 > 0 and t2 > 0:
                suggestions.append(
                    "-> Both load phases were partially sustained before failure; "
                    "compare hold durations in the metrics to the required duration for this environment."
                )
        return suggestions

    if "sagged" in reason_lower or ("tip" in reason_lower and "height" in reason_lower):
        suggestions.append(
            "-> Root cause: Excessive vertical deflection. "
            "Bending from span and/or loads exceeded the structure's stiffness; tip went below allowed clearance. "
            "Consider how bending moment and stiffness interact along the span."
        )
        return suggestions

    if "never reached" in reason_lower:
        suggestions.append(
            "-> Root cause: The structure did not achieve the required horizontal extension before or during the test."
        )
        return suggestions
    if "lost reach" in reason_lower or ("reach" in reason_lower and "under load" in reason_lower):
        suggestions.append(
            "-> Root cause: The structure lost horizontal reach under load (deflection or collapse). "
            "Extension was achieved initially but not maintained; load-bearing or stiffness became insufficient."
        )
        return suggestions
    if "reach" in reason_lower:
        suggestions.append("-> Root cause: Reach objective not met.")
        return suggestions

    if "hold" in reason_lower and "load" in reason_lower:
        l1 = metrics.get("load_hold_time")
        l2 = metrics.get("load2_hold_time")
        if _is_valid_number(l1) or _is_valid_number(l2):
            t1 = float(l1) if _is_valid_number(l1) else 0.0
            t2 = float(l2) if _is_valid_number(l2) else 0.0
            suggestions.append(
                "-> Root cause: The structure did not sustain one or both payloads for the required duration. "
                f"Primary load held {t1:.2f}s; secondary {t2:.2f}s. "
                "Compare these to the required hold duration for this environment (stage-dependent)."
            )
        else:
            suggestions.append(
                "-> Root cause: Load-bearing duration was insufficient. "
                "Check phase-specific hold times in the metrics against the required duration for this environment."
            )
        return suggestions

    suggestions.append(
        "-> Diagnostic: Use the metrics (reach, tip height, joint torque and force vs limits, load hold times, mass budget) "
        "to identify which physical constraint was violated first."
    )
    return suggestions
