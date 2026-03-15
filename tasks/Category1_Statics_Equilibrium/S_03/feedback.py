"""
Task-specific feedback generation for S-03: The Cantilever.
Process-aware, diagnostic feedback for statics/structural domain.
Uses only metrics from evaluator.evaluate(); thresholds are dynamic (stage-mutation safe).
No spoilers: diagnoses physical mechanism of failure without prescribing solutions.
"""
from typing import Dict, Any, List
import math

# Diagnostic-only ratio for "close to limit" notes (not a task physical limit)
_HEADROOM_WARNING_RATIO = 0.15


def _is_valid_number(x: Any) -> bool:
    """True if x is a finite number (no NaN, no inf). Used for physics-engine sanity."""
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
    Includes margin/proximity to limits (boundary proximity), phase-segregated load state,
    and torque utilization. No hardcoded thresholds; all limits read from metrics.
    """
    metric_parts = []

    # --- Reach (dynamic target from metrics; margin to goal) ---
    max_reach = metrics.get("max_reach")
    target_reach = metrics.get("target_reach")
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
        shortfall = tr - cr  # positive = how far short of target
        if shortfall > 0:
            metric_parts.append(f"**Reach Shortfall Under Load**: {shortfall:.2f}m (tip x vs target)")
    if _is_valid_number(current_reach):
        metric_parts.append(f"**Current Tip X**: {float(current_reach):.2f}m")
    if _is_valid_number(reach_tolerance) and target_reach is not None:
        tol = float(reach_tolerance)
        metric_parts.append(f"**Reach Deflection Tolerance**: ±{tol:.1f}m under load")

    # --- Tip height / sag (dynamic min_tip_height from metrics; margin to limit) ---
    min_tip_y = metrics.get("min_tip_y")
    min_tip_height = metrics.get("min_tip_height")
    tip_sagged = metrics.get("tip_sagged")

    if _is_valid_number(min_tip_y) and _is_valid_number(min_tip_height):
        mty = float(min_tip_y)
        mth = float(min_tip_height)
        margin = mty - mth  # positive = above limit
        status = "✅" if margin >= 0 else "❌"
        metric_parts.append(
            f"{status} **Tip Clearance Height**: {mty:.2f}m (Minimum: {mth:.1f}m; margin: {margin:+.2f}m)"
        )
    if tip_sagged is True:
        metric_parts.append("**Sag State**: Tip fell below allowed vertical threshold.")

    # --- Structural integrity ---
    anchor_broken = metrics.get("anchor_broken")
    joint_count = metrics.get("joint_count")
    initial_joint_count = metrics.get("initial_joint_count")

    if anchor_broken is not None:
        status = "❌ BROKEN" if anchor_broken else "✅ INTACT"
        metric_parts.append(f"**Structural Integrity**: {status}")
    if _is_valid_number(joint_count) and _is_valid_number(initial_joint_count):
        jc, ijc = int(joint_count), int(initial_joint_count)
        lost = ijc - jc
        if lost > 0:
            metric_parts.append(f"**Joints Lost**: {lost} (from {ijc} → {jc})")

    # --- Torque vs limits (dynamic limits from metrics; margin and utilization) ---
    peak_joint_torque = metrics.get("peak_joint_torque")
    max_anchor_torque_limit = metrics.get("max_anchor_torque_limit")
    max_internal_torque_limit = metrics.get("max_internal_torque_limit")

    if _is_valid_number(peak_joint_torque):
        peak = float(peak_joint_torque)
        anchor_lim = float(max_anchor_torque_limit) if _is_valid_number(max_anchor_torque_limit) else float("inf")
        internal_lim = float(max_internal_torque_limit) if _is_valid_number(max_internal_torque_limit) else float("inf")
        margin_anchor = anchor_lim - peak if math.isfinite(anchor_lim) else None
        margin_internal = internal_lim - peak if math.isfinite(internal_lim) else None
        s_anchor = "✅" if margin_anchor is not None and margin_anchor >= 0 else "❌"
        s_internal = "✅" if margin_internal is not None and margin_internal >= 0 else "❌"
        parts_torque = [f"**Peak Joint Torque**: {peak:.1f} N·m"]
        if math.isfinite(anchor_lim):
            pct_anchor = (peak / anchor_lim * 100) if anchor_lim > 0 else 0
            parts_torque.append(f"Anchor limit: {anchor_lim:.1f} N·m (margin: {margin_anchor:+.1f}, {pct_anchor:.0f}% utilized) {s_anchor}")
        if math.isfinite(internal_lim):
            pct_internal = (peak / internal_lim * 100) if internal_lim > 0 else 0
            parts_torque.append(f"Internal limit: {internal_lim:.1f} N·m (margin: {margin_internal:+.1f}, {pct_internal:.0f}% utilized) {s_internal}")
        metric_parts.append(" | ".join(parts_torque))

    # --- Load phases (phase-specific segregation) ---
    load_hold_time = metrics.get("load_hold_time")
    load2_hold_time = metrics.get("load2_hold_time")
    load_attached = metrics.get("load_attached")
    load2_attached = metrics.get("load2_attached")

    if _is_valid_number(load_hold_time):
        metric_parts.append(f"**Primary Load Hold Duration**: {float(load_hold_time):.2f}s")
    if _is_valid_number(load2_hold_time):
        metric_parts.append(f"**Secondary Load Hold Duration**: {float(load2_hold_time):.2f}s")
    if load_attached is not None or load2_attached is not None:
        ph = []
        if load_attached:
            ph.append("L1 on")
        if load2_attached:
            ph.append("L2 on")
        if ph:
            metric_parts.append(f"**Load Phase**: {' '.join(ph)}")

    # --- Mass (dynamic budget from metrics; margin to limit) ---
    structure_mass = metrics.get("structure_mass")
    max_structure_mass = metrics.get("max_structure_mass")

    if _is_valid_number(structure_mass) and _is_valid_number(max_structure_mass):
        sm = float(structure_mass)
        msm = float(max_structure_mass)
        margin = msm - sm
        status = "✅" if sm <= msm else "❌"
        metric_parts.append(
            f"{status} **Total Structural Mass**: {sm:.2f}kg (Budget: {msm:.0f}kg; margin: {margin:+.2f}kg)"
        )

    # --- Anchors (count vs limit from metrics) ---
    anchor_count = metrics.get("anchor_count")
    max_anchors_limit = metrics.get("max_anchors_limit")

    if _is_valid_number(anchor_count) and _is_valid_number(max_anchors_limit):
        ac = int(anchor_count)
        mal = int(max_anchors_limit)
        status = "✅" if ac <= mal else "❌"
        metric_parts.append(f"{status} **Wall Anchor Count**: {ac} (max: {mal})")

    # --- External force (discovery hint; only if present in metrics) ---
    external_force_y = metrics.get("external_force_y")
    if _is_valid_number(external_force_y) and float(external_force_y) != 0:
        metric_parts.append(f"**Mean External Force (Y) on Structure**: {float(external_force_y):.1f} N (per body)")

    # --- Simulation progress (phase context; only if present) ---
    step_count = metrics.get("step_count")
    if _is_valid_number(step_count):
        metric_parts.append(f"**Simulation Step**: {int(step_count)}")

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
    Diagnostic system feedback: root-cause chain, multi-objective trade-offs, physics-engine sanity.
    Does NOT prescribe solutions or code; only describes physical mechanism of failure.
    All thresholds derived from metrics (stage-mutation safe).
    """
    suggestions = []
    reason_lower = str(failure_reason).lower() if failure_reason else ""

    # --- Physics engine limits: NaN / inf (numerical instability) ---
    critical_keys = (
        "max_reach", "target_reach", "structure_mass", "max_structure_mass",
        "min_tip_y", "peak_joint_torque", "min_tip_height",
        "max_anchor_torque_limit", "max_internal_torque_limit",
    )
    for key in critical_keys:
        val = metrics.get(key)
        if val is not None and not _is_valid_number(val):
            suggestions.append(
                ">> DIAGNOSTIC: Numerical instability detected in simulation (non-finite values). "
                "This may indicate extreme forces, invalid geometry, or solver divergence."
            )
            break

    if error:
        suggestions.append(">> DIAGNOSTIC: Engineering constraints violated at design time.")
        return suggestions

    if not failed:
        # Success path: optional multi-objective note if margins are tight
        max_reach = metrics.get("max_reach")
        target_reach = metrics.get("target_reach")
        structure_mass = metrics.get("structure_mass")
        max_structure_mass = metrics.get("max_structure_mass")
        peak_joint_torque = metrics.get("peak_joint_torque")
        max_anchor_torque_limit = metrics.get("max_anchor_torque_limit")
        max_internal_torque_limit = metrics.get("max_internal_torque_limit")

        reach_tolerance = metrics.get("reach_tolerance")
        if _is_valid_number(max_reach) and _is_valid_number(target_reach) and target_reach > 0:
            margin_r = float(max_reach) - float(target_reach)
            tol = float(reach_tolerance) if _is_valid_number(reach_tolerance) else None
            if tol is not None and 0 <= margin_r < tol:
                suggestions.append(
                    "-> Note: Reach margin was small; small additional load or deflection could compromise success."
                )
        if _is_valid_number(structure_mass) and _is_valid_number(max_structure_mass):
            margin_m = float(max_structure_mass) - float(structure_mass)
            msm = float(max_structure_mass)
            mass_margin_threshold = max(1.0, 0.05 * msm)
            if margin_m >= 0 and margin_m < mass_margin_threshold:
                suggestions.append(
                    "-> Note: Mass budget was nearly exhausted; future stages may impose stricter mass limits."
                )
        # Torque headroom (from metrics; headroom fraction is diagnostic only)
        if _is_valid_number(peak_joint_torque):
            p = float(peak_joint_torque)
            a_lim = float(max_anchor_torque_limit) if _is_valid_number(max_anchor_torque_limit) else None
            i_lim = float(max_internal_torque_limit) if _is_valid_number(max_internal_torque_limit) else None
            for lim, name in [(a_lim, "anchor"), (i_lim, "internal")]:
                if lim is not None and lim > 0:
                    headroom = lim - p
                    if headroom >= 0 and headroom / lim < _HEADROOM_WARNING_RATIO:
                        suggestions.append(
                            f"-> Note: Peak joint torque was close to the {name} limit; little headroom for additional load or dynamics."
                        )
                        break
        return suggestions

    # --- Failure path ---
    suggestions.append(f">> FAILURE MODE: {failure_reason}")

    # --- Multi-objective trade-off paradox: one goal met, another violated ---
    max_reach = metrics.get("max_reach")
    target_reach = metrics.get("target_reach")
    structure_mass = metrics.get("structure_mass")
    max_structure_mass = metrics.get("max_structure_mass")
    tip_sagged = metrics.get("tip_sagged")
    anchor_broken = metrics.get("anchor_broken")

    reach_met = _is_valid_number(max_reach) and _is_valid_number(target_reach) and float(max_reach) >= float(target_reach)
    mass_ok = _is_valid_number(structure_mass) and _is_valid_number(max_structure_mass) and float(structure_mass) <= float(max_structure_mass)

    if reach_met and not mass_ok and "mass" in reason_lower:
        suggestions.append(
            "-> Multi-objective: Horizontal reach was achieved, but total structure mass exceeded the allowed budget. "
            "The failure is resource-limited, not load-bearing."
        )
        return suggestions
    if reach_met and tip_sagged:
        suggestions.append(
            "-> Multi-objective: Reach was achieved but tip clearance was violated (excessive sag). "
            "Bending stiffness was insufficient for the applied loads; deflection exceeded the allowed limit."
        )
        return suggestions
    if reach_met and anchor_broken:
        suggestions.append(
            "-> Multi-objective: Reach was achieved but structural integrity was lost (joint or anchor failure). "
            "Moment or force at the support exceeded the joint capacity."
        )
        return suggestions

    # --- Root-cause chain: what broke first (design vs runtime) ---
    if "design constraint" in reason_lower or "outside build zone" in reason_lower or "too many wall anchors" in reason_lower:
        suggestions.append(
            "-> Root cause: Constraint violation at build time (geometry or anchor count). "
            "The structure was rejected before load testing."
        )
        return suggestions

    if "mass" in reason_lower and "exceeds" in reason_lower:
        suggestions.append(
            "-> Root cause: Total structure mass exceeded the allowed budget. "
            "The failure is due to resource limit, not load-bearing capacity."
        )
        return suggestions

    if "structure integrity lost" in reason_lower or "joints or wall anchors broke" in reason_lower or "anchor" in reason_lower:
        peak = metrics.get("peak_joint_torque")
        anchor_lim = metrics.get("max_anchor_torque_limit")
        internal_lim = metrics.get("max_internal_torque_limit")
        if _is_valid_number(peak):
            p = float(peak)
            a_lim = float(anchor_lim) if _is_valid_number(anchor_lim) else None
            i_lim = float(internal_lim) if _is_valid_number(internal_lim) else None
            if i_lim is not None and p >= i_lim and (a_lim is None or p < a_lim):
                suggestions.append(
                    "-> Root cause: A beam-to-beam joint exceeded its torque capacity (internal joint failure). "
                    "Bending moment or eccentric load likely concentrated at an internal connection."
                )
            elif a_lim is not None and p >= a_lim:
                suggestions.append(
                    "-> Root cause: Wall anchorage exceeded its torque capacity. "
                    "The reactive moment at the wall exceeded the anchor yield limit."
                )
            else:
                suggestions.append(
                    "-> Root cause: Structural integrity lost (joint or anchor failure). "
                    "Compare peak joint torque to anchor and internal limits in the metrics to identify which constraint was exceeded."
                )
        else:
            suggestions.append(
                "-> Root cause: Structural integrity lost. Check peak joint torque vs. anchor and internal limits in the metrics."
            )
        return suggestions

    if "sagged" in reason_lower or ("tip" in reason_lower and "height" in reason_lower):
        suggestions.append(
            "-> Root cause: Excessive vertical deflection (sag). "
            "The bending moment from span length and/or applied loads exceeded the structure's stiffness, "
            "driving the tip below the allowed clearance."
        )
        return suggestions

    if "reach" in reason_lower:
        if "never reached" in reason_lower:
            suggestions.append(
                "-> Root cause: The structure did not achieve the required horizontal extension before or during the test. "
                "The tip did not reach the target distance."
            )
        elif "lost reach" in reason_lower or "under load" in reason_lower:
            suggestions.append(
                "-> Root cause: The structure lost horizontal reach under load (deflection or collapse). "
                "Initial reach may have been sufficient, but load-induced deflection or failure reduced tip position."
            )
        else:
            suggestions.append(
                "-> Root cause: Reach objective not met. "
                "The distal end of the structure did not meet the required horizontal distance criterion."
            )
        return suggestions

    if "hold" in reason_lower and "load" in reason_lower:
        l1 = metrics.get("load_hold_time")
        l2 = metrics.get("load2_hold_time")
        if _is_valid_number(l1) or _is_valid_number(l2):
            suggestions.append(
                "-> Root cause: The structure did not sustain one or both payloads for the required duration. "
                "Failure occurred during the load-holding phase (collapse, joint break, or excessive deflection)."
            )
        else:
            suggestions.append(
                "-> Root cause: Load-bearing duration was insufficient. "
                "The structure failed to hold the applied payload(s) for the required time."
            )
        return suggestions

    # Generic fallback (no spoiler)
    suggestions.append(
        "-> Diagnostic: Analyze the failure mode from the metrics (reach, tip height, joint torque vs limits, "
        "load hold times, mass budget) to infer which physical constraint was violated first."
    )

    return suggestions
