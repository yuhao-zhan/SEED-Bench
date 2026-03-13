"""
Task-specific feedback generation for F-04: The Filter (Three-way).
Process-aware, diagnostic feedback. Zero hallucinations: only metrics from evaluator.evaluate().
Adapts to stage mutations via dynamic thresholds (max_structure_mass, max_beams, min_purity from metrics).
"""
from typing import Dict, Any, List
import math


def _is_finite(x: Any) -> bool:
    """True if x is a finite number (no NaN, no inf)."""
    if x is None:
        return True
    try:
        f = float(x)
        return math.isfinite(f)
    except (TypeError, ValueError):
        return True


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Expose high-resolution physical metrics from the Evaluator metrics dict only.
    No invented metrics. Includes constraint margins and phase segregation when data exists.
    """
    parts = []

    # Design-constraint early exit: only constraint_violations and step_count may be present
    if "constraint_violations" in metrics:
        parts.append("### 1. Design Constraint Violations (Build Phase)")
        parts.append(f"- Step: {metrics.get('step_count', 'N/A')}")
        for v in metrics["constraint_violations"]:
            parts.append(f"- Violation: {v}")
        return parts

    # 1. Structural Design & Constraints (with margin proximity)
    if "structure_mass" in metrics or "beam_count" in metrics:
        parts.append("### 1. Structural Design & Constraints")
        max_mass = metrics.get("max_structure_mass")
        mass = metrics.get("structure_mass")
        if mass is not None:
            limit_str = f" / {max_mass:.2f} kg" if max_mass is not None else ""
            parts.append(f"- Total Structure Mass: {mass:.2f} kg{limit_str}")
            if max_mass is not None and _is_finite(mass) and _is_finite(max_mass):
                margin = max_mass - mass
                if margin < 0:
                    parts.append(f"- Mass Budget Margin: Exceeded by {abs(margin):.2f} kg")
                else:
                    parts.append(f"- Mass Budget Margin: {margin:.2f} kg remaining")

        if "structure_broken" in metrics:
            parts.append(f"- Structural Integrity: {'FAILED (Joints Snapped)' if metrics['structure_broken'] else 'NOMINAL (Intact)'}")

        max_b = metrics.get("max_beams")
        bc = metrics.get("beam_count")
        if bc is not None:
            max_str = f" / {max_b}" if max_b is not None else ""
            parts.append(f"- Component Count: {bc}{max_str} beams")
            if max_b is not None and _is_finite(bc) and _is_finite(max_b):
                beam_margin = int(max_b) - int(bc)
                if beam_margin < 0:
                    parts.append(f"- Beam Count Margin: Exceeded by {abs(beam_margin)}")
                else:
                    parts.append(f"- Beam Count Margin: {beam_margin} beam(s) remaining")

        if "joint_count" in metrics:
            parts.append(f"- Joint Count: {metrics['joint_count']} connections")

    # 2. Sorting Performance & Phase-Specific Segregation
    if "purity_percent" in metrics or "initial_particle_count" in metrics:
        parts.append("\n### 2. Sorting Performance (Phase-Specific)")
        min_pct = metrics.get("min_purity_percent")
        pct = metrics.get("purity_percent")
        if pct is not None:
            limit_str = f" (Target: >= {min_pct:.1f}%)" if min_pct is not None else ""
            parts.append(f"- Overall Sorting Purity: {pct:.1f}%{limit_str}")
            if min_pct is not None and _is_finite(pct) and _is_finite(min_pct):
                shortfall = min_pct - pct
                if shortfall > 0:
                    parts.append(f"- Purity Shortfall: {shortfall:.1f} percentage points below target")
                else:
                    parts.append(f"- Purity Margin: {abs(shortfall):.1f} percentage points above target")

        if "initial_particle_count" in metrics:
            parts.append(f"- Total Particles Fed: {metrics['initial_particle_count']}")

        # Phase segregation: correctly sorted per size class
        if any(k in metrics for k in ("small_in_small_zone", "medium_in_medium_zone", "large_in_large_zone")):
            parts.append("- Correctly Sorted by Phase:")
            if "small_in_small_zone" in metrics:
                parts.append(f"  - Small → bottom zone: {metrics['small_in_small_zone']}")
            if "medium_in_medium_zone" in metrics:
                parts.append(f"  - Medium → middle zone: {metrics['medium_in_medium_zone']}")
            if "large_in_large_zone" in metrics:
                parts.append(f"  - Large → top zone: {metrics['large_in_large_zone']}")

        # In-band (sieve) and misrouted counts
        if any(k in metrics for k in ("small_above_sieve", "small_in_sieve_band", "large_below_sieve", "large_in_sieve_band")):
            parts.append("- Sieve / Transit State:")
            if "small_above_sieve" in metrics:
                parts.append(f"  - Small particles above sieve band: {metrics['small_above_sieve']}")
            if "small_in_sieve_band" in metrics:
                parts.append(f"  - Small particles in sieve band: {metrics['small_in_sieve_band']}")
            if "large_below_sieve" in metrics:
                parts.append(f"  - Large particles below sieve band: {metrics['large_below_sieve']}")
            if "large_in_sieve_band" in metrics:
                parts.append(f"  - Large particles in sieve band: {metrics['large_in_sieve_band']}")

    # 3. Contamination Analysis (cross-zone misplacement)
    contamination_keys = ["large_in_small_zone", "small_in_large_zone", "medium_in_small_zone", "medium_in_large_zone"]
    if any(k in metrics for k in contamination_keys):
        parts.append("\n### 3. Contamination Analysis")
        if "large_in_small_zone" in metrics:
            parts.append(f"- Large particles in Small zone: {metrics['large_in_small_zone']}")
        if "small_in_large_zone" in metrics:
            parts.append(f"- Small particles in Large zone: {metrics['small_in_large_zone']}")
        if "medium_in_small_zone" in metrics:
            parts.append(f"- Medium particles in Small zone: {metrics['medium_in_small_zone']}")
        if "medium_in_large_zone" in metrics:
            parts.append(f"- Medium particles in Large zone: {metrics['medium_in_large_zone']}")
        if "contaminated" in metrics:
            parts.append(f"- Any contamination (zero-tolerance): {'Yes' if metrics['contaminated'] else 'No'}")

    # 4. Numerical sanity (only if we have numeric metrics)
    numerics = ["structure_mass", "purity_percent", "classification_purity"]
    if any(k in metrics for k in numerics):
        non_finite = []
        for k in numerics:
            v = metrics.get(k)
            if v is not None and not _is_finite(v):
                non_finite.append(k)
        if non_finite:
            parts.append("\n### 4. Numerical Stability")
            parts.append(f"- Non-finite or invalid values detected in: {', '.join(non_finite)}. Simulation state may be unstable.")

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
    Diagnostic suggestions only. No spoilers: describe the physical/systemic problem,
    never dictate exact design or code. All thresholds from metrics (stage-mutation safe).
    """
    suggestions = []
    reason = ((error or "") + " " + (failure_reason or "")).lower()

    # Physics engine / numerical instability
    for key in ("structure_mass", "purity_percent", "classification_purity"):
        v = metrics.get(key)
        if v is not None and not _is_finite(v):
            suggestions.append("Diagnostic: Numerical instability detected in simulation outputs. Check for extreme forces or invalid state that could cause non-finite values.")
            break

    # Design constraint violations (build phase) — root-cause: constraint violated before run
    if "design constraint" in reason or (error and "constraint" in error.lower()):
        max_mass = metrics.get("max_structure_mass")
        mass = metrics.get("structure_mass")
        max_beams = metrics.get("max_beams")
        beam_count = metrics.get("beam_count")
        violations = metrics.get("constraint_violations", [])

        if violations:
            for v in violations:
                v_lower = v.lower()
                if "mass" in v_lower and max_mass is not None:
                    suggestions.append("Diagnostic: Structural mass exceeds the allowed budget for this environment. The design must achieve separation performance within a stricter mass limit.")
                    break
                if "beam" in v_lower and max_beams is not None:
                    suggestions.append("Diagnostic: Component count exceeds the allowed beam limit. Fewer, more effective structural elements are required.")
                    break
                if "build zone" in v_lower or "outside" in v_lower:
                    suggestions.append("Diagnostic: At least one component lies outside the permitted build zone. All structure must be contained within the designated construction bounds.")
                    break
        else:
            if mass is not None and max_mass is not None and mass > max_mass:
                suggestions.append("Diagnostic: Structural mass exceeds the allowed budget for this environment. The design must achieve separation performance within a stricter mass limit.")
            if beam_count is not None and max_beams is not None and beam_count > max_beams:
                suggestions.append("Diagnostic: Component count exceeds the allowed beam limit. Fewer, more effective structural elements are required.")
            if "build zone" in reason or "outside" in reason:
                suggestions.append("Diagnostic: At least one component lies outside the permitted build zone. All structure must be contained within the designated construction bounds.")

        return suggestions

    # Runtime failure: multi-objective and root-cause
    if failed:
        structure_broken = metrics.get("structure_broken", False)
        min_purity = metrics.get("min_purity")
        purity = metrics.get("classification_purity")
        purity_ok = purity is not None and min_purity is not None and purity >= min_purity
        integrity_ok = not structure_broken

        # Multi-objective trade-off: one objective met, the other severely failed
        if purity_ok and not integrity_ok:
            suggestions.append("Diagnostic: Sorting purity met the target, but structural integrity was lost during the run. Load or environmental forces may have exceeded what the current geometry can sustain.")
        elif integrity_ok and not purity_ok:
            suggestions.append("Diagnostic: Structure remained intact, but sorting purity fell below the required threshold. Particle routing or size separation is insufficient for the current flow and environment.")
        elif not purity_ok and not integrity_ok:
            # Root-cause chain: which failed first is not in metrics; suggest both
            suggestions.append("Diagnostic: Both structural integrity and sorting purity failed. Structural failure (e.g. joint breakage under load) can alter the effective sieve geometry and thus purity; consider whether integrity must be addressed first.")

        # Purity-specific diagnostics (no spoilers)
        if "purity" in reason or (purity is not None and min_purity is not None and purity < min_purity):
            suggestions.append("Diagnostic: Separation performance is below the required purity. Particle flow and size-dependent routing (apertures, barriers, or active forcing) may be misaligned with the target zones.")

            large_in_small = metrics.get("large_in_small_zone", 0) or 0
            large_in_band = metrics.get("large_in_sieve_band", 0) or 0
            if large_in_small > 0 or large_in_band > 0:
                suggestions.append("Diagnostic: Coarse material is reaching regions intended for smaller fractions. The boundary between coarse and fine pathways may be too permissive or poorly oriented.")

            small_above = metrics.get("small_above_sieve", 0) or 0
            small_in_band = metrics.get("small_in_sieve_band", 0) or 0
            if small_above > 0 or small_in_band > 0:
                suggestions.append("Diagnostic: Fine material is being retained or diverted away from the bottom zone. Downward passage or active assistance for small particles may be insufficient.")

        if structure_broken:
            suggestions.append("Diagnostic: Structural integrity was lost (e.g. joints or connections failed). The filter geometry may be overstressed by dead load, particle impact, or environmental forces.")

    return suggestions
