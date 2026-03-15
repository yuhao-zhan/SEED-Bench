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
    All limits (max_structure_mass, max_beams, min_purity_percent) come from metrics for stage-mutation adaptability.
    """
    parts = []

    # Design-constraint early exit: only constraint_violations and step_count may be present
    if "constraint_violations" in metrics:
        parts.append("### 1. Design Constraint Violations (Build Phase)")
        parts.append(f"- Step: {metrics.get('step_count', 'N/A')}")
        for v in metrics["constraint_violations"]:
            parts.append(f"- Violation: {v}")
        return parts

    # 1. Structural Design & Constraints (with margin proximity from metrics only)
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

    # 2. Sorting Performance & Phase-Specific Segregation (all from metrics)
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

        initial_total = metrics.get("initial_particle_count")
        if initial_total is not None and initial_total > 0:
            parts.append(f"- Total Particles Fed: {initial_total}")
            # Derived routing summary (only from existing metrics)
            s_ok = metrics.get("small_in_small_zone", 0) or 0
            m_ok = metrics.get("medium_in_medium_zone", 0) or 0
            l_ok = metrics.get("large_in_large_zone", 0) or 0
            correct = s_ok + m_ok + l_ok
            in_transit_or_misrouted = initial_total - correct
            parts.append(f"- Correctly Placed: {correct} / {initial_total}; In transit or misrouted: {in_transit_or_misrouted}")

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
    Diagnostic suggestions only. No spoilers: describe the physical or systemic failure,
    never dictate exact design or code. All thresholds from metrics (stage-mutation safe).
    """
    suggestions = []
    reason = ((error or "") + " " + (failure_reason or "")).lower()

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
                    suggestions.append("Diagnostic: Structural mass exceeds the allowed budget for this environment.")
                    break
                if "beam" in v_lower and max_beams is not None:
                    suggestions.append("Diagnostic: Component count exceeds the allowed beam limit for this environment.")
                    break
                if "build zone" in v_lower or "outside" in v_lower:
                    suggestions.append("Diagnostic: At least one component lies outside the permitted build zone. All structure must be contained within the designated construction bounds.")
                    break
        else:
            if mass is not None and max_mass is not None and _is_finite(mass) and mass > max_mass:
                suggestions.append("Diagnostic: Structural mass exceeds the allowed budget for this environment.")
            if beam_count is not None and max_beams is not None and beam_count > max_beams:
                suggestions.append("Diagnostic: Component count exceeds the allowed beam limit for this environment.")
            if "build zone" in reason or "outside" in reason:
                suggestions.append("Diagnostic: At least one component lies outside the permitted build zone. All structure must be contained within the designated construction bounds.")

        return suggestions

    if failed:
        structure_broken = metrics.get("structure_broken", False)
        min_purity = metrics.get("min_purity")  # from metrics (stage-mutable)
        purity = metrics.get("classification_purity")
        purity_ok = purity is not None and min_purity is not None and _is_finite(purity) and purity >= min_purity
        integrity_ok = not structure_broken

        if purity_ok and not integrity_ok:
            suggestions.append("Diagnostic: Sorting purity met the target, but structural integrity was lost during the run. Load or environmental forces exceeded what the geometry could sustain.")
        elif integrity_ok and not purity_ok:
            suggestions.append("Diagnostic: Structure remained intact, but sorting purity fell below the required threshold. Separation performance is insufficient for the current flow and environment.")
        elif not purity_ok and not integrity_ok:
            suggestions.append("Diagnostic: Both structural integrity and sorting purity failed. Structural failure (e.g. joint breakage) can alter the effective geometry and thus measured purity.")

        # Purity-specific diagnostics (no spoilers)
        purity_below = purity is not None and min_purity is not None and _is_finite(purity) and purity < min_purity
        if purity_below:
            large_in_small = metrics.get("large_in_small_zone", 0) or 0
            large_in_band = metrics.get("large_in_sieve_band", 0) or 0
            if large_in_small > 0 or large_in_band > 0:
                suggestions.append("Diagnostic: Coarse material is reaching regions intended for smaller fractions; separation between size classes is failing.")
            small_above = metrics.get("small_above_sieve", 0) or 0
            small_in_band = metrics.get("small_in_sieve_band", 0) or 0
            if small_above > 0 or small_in_band > 0:
                suggestions.append("Diagnostic: Fine material is not reaching the bottom zone; downward flow or retention in upper regions indicates a systemic routing failure for small particles.")

        # Contamination (zero-tolerance): diagnostic without spoiling design
        if metrics.get("contaminated", False):
            suggestions.append("Diagnostic: Cross-zone contamination occurred (zero tolerance). Material is crossing the intended zone boundaries.")

        if structure_broken:
            suggestions.append("Diagnostic: Structural integrity was lost (e.g. joints or connections failed). The geometry was overstressed by dead load, particle impact, or environmental forces.")

    return suggestions
