"""
Task-specific feedback generation for F-01: The Dam (extreme).
Process-aware, diagnostic feedback. No hallucination: only metrics from evaluator.evaluate().
No spoilers: diagnose physical mechanism, never dictate solution or code.
Dynamic thresholding: all limits from metrics (stage-mutation adaptable via stages.py).
"""
from typing import Dict, Any, List
import math


def _safe_float(x: Any, default: float = None) -> float:
    """Return float(x) if finite, else default. Handles NaN/Inf."""
    if x is None:
        return default
    try:
        v = float(x)
        if math.isfinite(v):
            return v
        return default
    except (TypeError, ValueError):
        return default


def _is_nonfinite(val: Any) -> bool:
    """True if value is numeric but NaN or Inf."""
    if val is None:
        return False
    try:
        v = float(val)
        return not math.isfinite(v)
    except (TypeError, ValueError):
        return False


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Expose high-resolution physical metrics from the Evaluator metrics dict only.
    No suggestions. Phase-segregated: design → structural → containment → run summary.
    Only keys present in metrics are used; no invented quantities.
    """
    parts = []
    if not metrics:
        return parts

    # --- Phase 1: Design-phase failure (constraint_violations present; other runtime metrics may be absent) ---
    if "constraint_violations" in metrics:
        violations = metrics.get("constraint_violations") or []
        parts.append("### 1. Design Constraint Outcome")
        parts.append("- Validation: FAILED (design phase)")
        parts.append(f"- Violations Reported: {len(violations)}")
        for i, v in enumerate(violations[:10], 1):
            parts.append(f"  {i}. {v}")
        if len(violations) > 10:
            parts.append(f"  ... and {len(violations) - 10} more.")
        return parts

    # --- Phase 2: Structural design & constraints (all from metrics; limits are dynamic from env/stage) ---
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
        if _is_nonfinite(metrics.get("structure_mass")):
            parts.append("- Structure Mass: Non-finite value (numerical instability detected)")
        if "structure_broken" in metrics:
            parts.append(
                "- Structural Integrity: "
                + ("FAILED (one or more beam-to-beam joints broke)" if metrics["structure_broken"] else "NOMINAL (all joints intact)")
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

    # --- Phase 3: Containment performance (leakage limits from metrics = stage-mutation safe) ---
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
        if _is_nonfinite(metrics.get("leakage_rate_percent")):
            parts.append("- Leakage Rate: Non-finite value (numerical instability detected)")
        if "retained_particle_count" in metrics:
            total = metrics.get("initial_particle_count")
            parts.append(f"- Particles Retained: {metrics['retained_particle_count']} / {total}")
        if "containment_percent" in metrics:
            cp = _safe_float(metrics.get("containment_percent"))
            if cp is not None:
                parts.append(f"- Containment Efficiency: {cp:.1f}%")
        if "current_particle_count" in metrics:
            parts.append(f"- Particles Still in Simulation: {metrics['current_particle_count']}")

    # --- Phase 4: Run summary ---
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
    trade-offs; never prescribe exact design, parameters, or code.
    All thresholds from metrics (stage-mutation safe; no hardcoded limits).
    """
    suggestions = []
    reason = ((error or "") + " " + (failure_reason or "")).lower()

    # --- Physics engine / numerical instability (only when metrics show non-finite values) ---
    key_numeric = ["leakage_rate_percent", "structure_mass", "containment_percent"]
    if any(_is_nonfinite(metrics.get(k)) for k in key_numeric if k in metrics):
        suggestions.append(
            "Diagnostic: Numerical instability detected in reported metrics (non-finite values). "
            "The simulation may have encountered extreme forces or invalid state; consider whether "
            "the design could produce singular or ill-conditioned dynamics."
        )

    # --- Design-phase violations: categorize by mechanism, no solution ---
    if "constraint_violations" in metrics:
        violations = metrics.get("constraint_violations") or []
        v_text = " ".join(violations).lower()
        if "mass" in v_text or ("exceeds maximum" in v_text and "kg" in v_text):
            suggestions.append(
                "Diagnostic: Mass budget exceeded. The structure's total mass is above the allowed limit; "
                "consider the strength-to-mass trade-off of your components."
            )
        if "outside build zones" in v_text or "build zone" in v_text:
            suggestions.append(
                "Diagnostic: Geometric boundary violation. Component centers or extents fall outside "
                "the permitted build strips; check that every beam lies within the allowed x and y ranges."
            )
        if "underflow" in v_text or "below y=" in v_text:
            suggestions.append(
                "Diagnostic: Mandatory underflow gap violated. Part of the structure extends into the "
                "no-build zone; ensure no beam bottom edge lies below the required clearance."
            )
        if "joint" in v_text and ("exceed" in v_text or "maximum" in v_text):
            suggestions.append(
                "Diagnostic: Beam-to-beam joint count over limit. The topology exceeds the allowed number of welds; "
                "the constraint limits how many beam-to-beam connections are permitted."
            )
        if "connected" in v_text or "fragmentation" in v_text or "isolated" in v_text:
            suggestions.append(
                "Diagnostic: Structural connectivity failure. The dam must form a single connected component "
                "via beam-to-beam joints; ensure there are no isolated sub-structures."
            )
        if "span" in v_text or "left strip" in v_text or "right strip" in v_text:
            suggestions.append(
                "Diagnostic: Topological span failure. The dam must occupy both the left and right build strips "
                "to span the gate; verify coverage across the full width."
            )
        if "band" in v_text or "vertical" in v_text:
            suggestions.append(
                "Diagnostic: Vertical distribution failure. At least one required vertical band has too few "
                "beam centers; the constraint requires a minimum count per band."
            )
        if "middle strip" in v_text or "bridge" in v_text:
            suggestions.append(
                "Diagnostic: Middle-strip constraint violated. The middle strip has a strict occupancy requirement "
                "(exactly one beam); check middle-strip occupancy and count against the constraint."
            )
        if "right strip" in v_text and "at most" in v_text:
            suggestions.append(
                "Diagnostic: Right-strip occupancy exceeded. The right strip has a fixed maximum beam count; "
                "the reported violation indicates strip occupancy exceeds that limit."
            )
        if "height" in v_text and ("maximum" in v_text or "exceed" in v_text):
            suggestions.append(
                "Diagnostic: Beam height limit exceeded. At least one beam exceeds the maximum allowed height "
                "(constraint violation); check reported beam dimensions against the limit."
            )
        return suggestions

    # --- Runtime failure: root-cause from metrics only (all limits from metrics) ---
    max_mass = _safe_float(metrics.get("max_structure_mass"))
    mass = _safe_float(metrics.get("structure_mass"))
    limit_pct = _safe_float(metrics.get("leakage_limit_percent"))
    lr_pct = _safe_float(metrics.get("leakage_rate_percent"))
    structure_broken = metrics.get("structure_broken", False)

    if failed:
        leakage_fail = limit_pct is not None and lr_pct is not None and lr_pct > limit_pct
        if structure_broken and leakage_fail:
            suggestions.append(
                "Diagnostic: Dual failure — structural integrity was lost and containment was exceeded. "
                "Infer whether joint failure allowed increased leakage or whether leakage and loading both contributed."
            )
        elif structure_broken and not leakage_fail:
            suggestions.append(
                "Diagnostic: Structural integrity lost while containment may still be within limit. "
                "Loads (surge, debris, hydrostatic, or earthquake) exceeded the joint strength; consider how "
                "to reduce stress or improve robustness without violating mass or topology constraints."
            )
        elif leakage_fail and not structure_broken:
            suggestions.append(
                "Diagnostic: Containment failure with structure intact. Fluid is escaping past the dam; "
                "consider seepage paths, underflow, or gaps in the structural surface under hydrostatic and dynamic loading."
            )

        # Within mass budget but still failed (topology or load path may be the bottleneck)
        if max_mass is not None and mass is not None and mass <= max_mass and failed:
            suggestions.append(
                "Diagnostic: Failure occurred despite staying within the mass budget. The limiting factor may be "
                "topology, connectivity, or load distribution rather than total mass; infer from failure reason and metrics."
            )

    # Root-cause chain framing (no spoilers): what broke first is inferred from metrics, not prescribed
    if failed and structure_broken:
        suggestions.append(
            "Diagnostic: At least one beam-to-beam joint failed under load. Joints break when reaction forces "
            "exceed the environment's threshold; infer whether the cause is dead load, surge, debris impact, or slosh."
        )
    if failed and "leakage" in reason:
        suggestions.append(
            "Diagnostic: Leakage rate exceeded the allowed limit. Use the reported leakage margin and "
            "containment efficiency to infer whether the dominant path is full breach, seepage, or both."
        )

    return suggestions
