"""
Task-specific feedback generation for F-01: The Dam (extreme).
Process-aware, diagnostic feedback. No hallucination: only metrics from evaluator.
No spoilers: diagnose physical mechanism, never dictate solution.
Dynamic thresholding: all limits from metrics (stage-mutation adaptable).
"""
from typing import Dict, Any, List
import math


def _safe_float(x: Any, default: float = None) -> float:
    """Return float(x) if valid, else default. Handles NaN/Inf."""
    if x is None:
        return default
    try:
        v = float(x)
        if math.isfinite(v):
            return v
        return default
    except (TypeError, ValueError):
        return default


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Expose high-resolution physical metrics from the Evaluator metrics dict only.
    No suggestions. Phase-segregated: design vs. runtime containment vs. integrity.
    """
    parts = []
    if not metrics:
        return parts

    # --- Design-phase failure: constraint_violations present, other metrics may be absent ---
    if "constraint_violations" in metrics:
        violations = metrics.get("constraint_violations") or []
        parts.append("### 1. Design Constraint Outcome")
        parts.append(f"- Validation: FAILED (design phase)")
        parts.append(f"- Violations Reported: {len(violations)}")
        for i, v in enumerate(violations[:10], 1):  # cap to avoid flood
            parts.append(f"  {i}. {v}")
        if len(violations) > 10:
            parts.append(f"  ... and {len(violations) - 10} more.")
        return parts

    # --- Runtime metrics (from _collect_metrics) ---

    # 1. Structural design & constraints (all from metrics; dynamic limits)
    struct_keys = [
        "structure_mass", "max_structure_mass", "structure_broken",
        "joint_count", "beam_count", "terrain_joint_count", "max_beam_count",
    ]
    if any(k in metrics for k in struct_keys):
        parts.append("### 1. Structural Design & Constraints")
        mass = _safe_float(metrics.get("structure_mass"))
        max_mass = _safe_float(metrics.get("max_structure_mass"))
        if mass is not None:
            limit_str = f" / {max_mass:.2f} kg" if max_mass is not None else ""
            parts.append(f"- Total Structure Mass: {mass:.2f} kg{limit_str}")
            if max_mass is not None and max_mass > 0:
                margin_kg = max_mass - mass
                parts.append(f"- Mass Budget Margin: {margin_kg:.2f} kg remaining")
        if "structure_broken" in metrics:
            parts.append(
                f"- Structural Integrity: {'FAILED (one or more joints broke)' if metrics['structure_broken'] else 'NOMINAL (all joints intact)'}"
            )
        if "joint_count" in metrics:
            parts.append(f"- Active Beam-to-Beam Joints: {metrics['joint_count']}")
        if "terrain_joint_count" in metrics:
            parts.append(f"- Terrain Anchors: {metrics['terrain_joint_count']}")
        if "beam_count" in metrics:
            max_beams = metrics.get("max_beam_count")
            beam_str = f"{metrics['beam_count']} beams"
            if max_beams is not None:
                beam_str += f" (max {max_beams})"
            parts.append(f"- Component Count: {beam_str}")

    # 2. Containment performance (dynamic leakage limit from metrics)
    perf_keys = [
        "leakage_rate_percent", "leakage_limit_percent", "containment_percent",
        "retained_particle_count", "initial_particle_count", "leaked_particle_count",
        "current_particle_count",
    ]
    if any(k in metrics for k in perf_keys):
        parts.append("\n### 2. Containment Performance")
        lr_pct = _safe_float(metrics.get("leakage_rate_percent"))
        limit_pct = _safe_float(metrics.get("leakage_limit_percent"))
        if lr_pct is not None:
            limit_str = f" (Limit: {limit_pct:.2f}%)" if limit_pct is not None else ""
            parts.append(f"- Leakage Rate: {lr_pct:.2f}%{limit_str}")
            if limit_pct is not None and limit_pct > 0:
                margin_pct = limit_pct - lr_pct
                parts.append(f"- Leakage Margin: {margin_pct:.2f} percentage points below limit")
        if "retained_particle_count" in metrics:
            total = metrics.get("initial_particle_count")
            parts.append(f"- Particles Retained: {metrics['retained_particle_count']} / {total}")
        if "containment_percent" in metrics:
            cp = _safe_float(metrics.get("containment_percent"))
            if cp is not None:
                parts.append(f"- Containment Efficiency: {cp:.1f}%")
        if "current_particle_count" in metrics:
            parts.append(f"- Particles Still in Simulation: {metrics['current_particle_count']}")

    # 3. Run summary (step count, outcome)
    if "step_count" in metrics:
        parts.append("\n### 3. Run Summary")
        parts.append(f"- Simulation Steps: {metrics['step_count']}")
    if "success" in metrics:
        parts.append(f"- Outcome: {'SUCCESS' if metrics['success'] else 'FAILED'}")
    if metrics.get("failure_reason"):
        parts.append(f"- Failure Reason: {metrics['failure_reason']}")

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
    Diagnostic suggestions only. No spoilers: describe physical mechanism and
    trade-offs, never prescribe exact design or code.
    All thresholds from metrics (stage-mutation safe).
    """
    suggestions = []
    reason = ((error or "") + " " + (failure_reason or "")).lower()

    # --- Design-phase violations: categorize by mechanism, no solution ---
    if "constraint_violations" in metrics:
        violations = metrics.get("constraint_violations") or []
        v_text = " ".join(violations).lower()
        if "mass" in v_text or "exceeds maximum" in v_text and "kg" in v_text:
            suggestions.append(
                "Diagnostic: Mass budget exceeded. The structure’s total mass is above the allowed limit; consider the strength-to-mass trade-off of your components."
            )
        if "outside build zones" in v_text or "build zone" in v_text:
            suggestions.append(
                "Diagnostic: Geometric boundary violation. Component centers or extents fall outside the permitted build strips; check that every beam lies within the allowed x and y ranges."
            )
        if "underflow" in v_text or "below y=" in v_text:
            suggestions.append(
                "Diagnostic: Mandatory underflow gap violated. Part of the structure extends into the no-build zone; ensure no beam bottom edge lies below the required clearance."
            )
        if "joint" in v_text and ("exceed" in v_text or "maximum" in v_text):
            suggestions.append(
                "Diagnostic: Beam-to-beam joint count over limit. The topology uses more welds than allowed; consider a sparser connection pattern that still preserves connectivity."
            )
        if "connected" in v_text or "fragmentation" in v_text or "isolated" in v_text:
            suggestions.append(
                "Diagnostic: Structural connectivity failure. The dam must form a single connected component via beam-to-beam joints; ensure there are no isolated sub-structures."
            )
        if "span" in v_text or "left strip" in v_text or "right strip" in v_text:
            suggestions.append(
                "Diagnostic: Topological span failure. The dam must occupy both the left and right build strips to span the gate; verify coverage across the full width."
            )
        if "band" in v_text or "vertical" in v_text:
            suggestions.append(
                "Diagnostic: Vertical distribution failure. Each required vertical band must contain enough beam centers; ensure even distribution from base to crest."
            )
        if "middle strip" in v_text or "bridge" in v_text:
            suggestions.append(
                "Diagnostic: Bridge constraint violated. The middle strip must contain exactly one beam to force a bridge topology; check middle-strip occupancy and count."
            )
        if "right strip" in v_text and "at most" in v_text:
            suggestions.append(
                "Diagnostic: Right-strip occupancy exceeded. The right strip allows at most a fixed number of beams; reduce beams in that strip while keeping the structure connected."
            )
        if "height" in v_text and ("maximum" in v_text or "exceed" in v_text):
            suggestions.append(
                "Diagnostic: Beam height limit exceeded. At least one beam exceeds the maximum allowed height; tall beams are more susceptible to surge-induced failure."
            )
        return suggestions

    # --- Runtime failure: multi-objective and root-cause, no hardcoded numbers ---
    max_mass = _safe_float(metrics.get("max_structure_mass"))
    mass = _safe_float(metrics.get("structure_mass"))
    limit_pct = _safe_float(metrics.get("leakage_limit_percent"))
    lr_pct = _safe_float(metrics.get("leakage_rate_percent"))
    structure_broken = metrics.get("structure_broken", False)

    # Multi-objective trade-off: one objective met, the other failed
    if failed:
        leakage_fail = (
            limit_pct is not None and lr_pct is not None and lr_pct > limit_pct
        )
        if structure_broken and leakage_fail:
            suggestions.append(
                "Diagnostic: Dual failure — structural integrity was lost and containment was exceeded. Infer whether joint failure allowed increased leakage or whether leakage and loading both contributed."
            )
        elif structure_broken and not leakage_fail:
            suggestions.append(
                "Diagnostic: Structural integrity lost while containment may still be within limit. Loads (surge, debris, or hydrostatic) exceeded the joint strength; consider how to reduce stress or improve robustness without violating mass or topology constraints."
            )
        elif leakage_fail and not structure_broken:
            suggestions.append(
                "Diagnostic: Containment failure with structure intact. Water is escaping past the dam; consider seepage paths, underflow, or gaps in the structural surface under hydrostatic and dynamic loading."
            )

        # Mass vs. success: stayed under budget but still failed
        if max_mass is not None and mass is not None and mass <= max_mass and failed:
            suggestions.append(
                "Diagnostic: Failure occurred despite staying within the mass budget. Re-evaluate the trade-off between mass, connectivity, and load path; the limiting factor may be topology or load distribution rather than total mass."
            )

    # Root-cause framing (no spoilers)
    if failed and structure_broken:
        suggestions.append(
            "Diagnostic: At least one beam-to-beam joint failed under load. Joints break when reaction forces exceed the environment’s threshold; infer whether the cause is dead load, surge, debris impact, or slosh, and adapt the design accordingly."
        )
    if failed and "leakage" in reason:
        suggestions.append(
            "Diagnostic: Leakage rate exceeded the allowed limit. Use the reported leakage margin and containment efficiency to infer whether the dominant path is full breach, seepage, or both."
        )

    return suggestions
