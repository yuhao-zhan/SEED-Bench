"""
F-06: The Pipeline — process-aware diagnostic feedback.
Category: Granular/Fluid Interaction.
Ground truth: metrics from evaluator.evaluate() only. No hallucinated fields.
Dynamic thresholds: all limits from metrics (max_structure_mass, min_delivery_ratio_percent, force_budget).
No spoilers: diagnose physical mechanism and trade-offs, never dictate design or code.
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
    Expose high-resolution physical metrics from the evaluator metrics dict only.
    No suggestions. Handles design-constraint early return (fewer keys) and full run.
    """
    if not metrics:
        return []

    parts = []

    # Numerical sanity (physics engine limits)
    numeric_keys = [
        "delivery_ratio", "delivery_ratio_percent", "min_delivery_ratio_percent",
        "structure_mass", "max_structure_mass", "force_budget", "step_count",
        "particles_in_target", "initial_particle_count",
    ]
    non_finite = []
    for k in numeric_keys:
        if k in metrics and not _is_finite(metrics[k]):
            non_finite.append(k)
    if non_finite:
        parts.append("### 0. Numerical Stability")
        parts.append("- **Warning:** Non-finite values detected in metrics; simulation may have encountered numerical instability.")

    # Constraint violations (present only on design-constraint failure at step 0)
    if "constraint_violations" in metrics:
        viols = metrics["constraint_violations"]
        if isinstance(viols, list) and viols:
            parts.append("### 1. Design Constraint Violations (Build Phase)")
            for v in viols:
                parts.append(f"- {v}")
            if "failure_reason" in metrics:
                parts.append(f"- **Outcome:** {metrics['failure_reason']}")
            return parts  # No further metrics on early exit

    # --- Full run metrics (structure + delivery + resources) ---

    # 1. Structural design & constraints (dynamic limits from metrics)
    struct_keys = ["structure_mass", "max_structure_mass", "structure_broken"]
    if any(k in metrics for k in struct_keys):
        parts.append("### 1. Structural Design & Constraints")
        mass = metrics.get("structure_mass")
        max_mass = metrics.get("max_structure_mass")
        if mass is not None:
            limit_str = f" / {max_mass:.2f} kg limit" if max_mass is not None and _is_finite(max_mass) else ""
            parts.append(f"- Total Structure Mass: {mass:.2f} kg{limit_str}")
            if max_mass is not None and _is_finite(max_mass) and _is_finite(mass):
                margin_kg = max_mass - mass
                if margin_kg < 0:
                    parts.append(f"- Mass Overrun: {abs(margin_kg):.2f} kg beyond limit.")
                else:
                    parts.append(f"- Mass Margin: {margin_kg:.2f} kg below limit.")
        if "structure_broken" in metrics:
            parts.append(f"- Structural Integrity: {'FAILED (joint(s) lost)' if metrics['structure_broken'] else 'NOMINAL (intact)'}.")

    # 2. Task performance & delivery (dynamic target from metrics)
    perf_keys = ["delivery_ratio_percent", "particles_in_target", "initial_particle_count", "min_delivery_ratio_percent"]
    if any(k in metrics for k in perf_keys):
        parts.append("\n### 2. Task Performance & Delivery")
        in_target = metrics.get("particles_in_target")
        initial = metrics.get("initial_particle_count")
        if in_target is not None and initial is not None:
            parts.append(f"- Particles in Target: {in_target} / {initial}")
        delivery_pct = metrics.get("delivery_ratio_percent")
        target_pct = metrics.get("min_delivery_ratio_percent")
        if delivery_pct is not None:
            target_str = f" (Target: {target_pct:.1f}%)" if target_pct is not None and _is_finite(target_pct) else ""
            parts.append(f"- Delivery Efficiency: {delivery_pct:.1f}%{target_str}")
            if target_pct is not None and _is_finite(target_pct) and _is_finite(delivery_pct):
                shortfall_pct = target_pct - delivery_pct
                if shortfall_pct > 0:
                    parts.append(f"- Delivery Shortfall: {shortfall_pct:.1f}% below target.")
                else:
                    parts.append(f"- Delivery Margin: {abs(shortfall_pct):.1f}% above target.")
        budget = metrics.get("force_budget")
        if budget is not None and _is_finite(budget):
            parts.append(f"- Per-Step Force Budget: {budget:.2f} N (environment limit).")
        steps = metrics.get("step_count")
        if steps is not None:
            parts.append(f"- Simulation Steps: {steps}.")

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
    Actionable diagnostic feedback without design spoilers.
    Uses only metrics and failure_reason/error. All thresholds from metrics.
    """
    suggestions = []
    reason = ((error or "") + " " + (failure_reason or "")).lower()

    # Physics engine / numerical instability
    numeric_keys = [
        "delivery_ratio", "delivery_ratio_percent", "structure_mass", "max_structure_mass",
        "force_budget", "particles_in_target", "initial_particle_count",
    ]
    if any(k in metrics and not _is_finite(metrics.get(k)) for k in numeric_keys):
        suggestions.append("Diagnostic: Numerical instability detected in simulation results. Consider whether contact or force magnitudes could be causing extreme values.")

    # Design constraint failure (build phase)
    if "design constraint" in reason or (metrics.get("constraint_violations")):
        viols = metrics.get("constraint_violations") or []
        if "mass" in reason or any("mass" in str(v).lower() for v in viols):
            max_m = metrics.get("max_structure_mass")
            mass = metrics.get("structure_mass")
            if max_m is not None and _is_finite(max_m):
                suggestions.append("Diagnostic: Structural mass exceeded the environment limit. Consider how component count and density contribute to total mass and how to improve strength-to-weight ratio without prescribing specific values.")
            else:
                suggestions.append("Diagnostic: Structural mass limit exceeded. Optimize the trade-off between structural capacity and mass budget.")
        if "build zone" in reason or any("build zone" in str(v).lower() or "outside" in str(v).lower() for v in viols):
            suggestions.append("Diagnostic: At least one component lies outside the permitted build zone. Ensure the entire structural topology is contained within the task's spatial boundaries.")
        if "anchor" in reason or "ground" in reason or "joint" in reason or any("anchor" in str(v).lower() or "joint" in str(v).lower() for v in viols):
            suggestions.append("Diagnostic: The structure must be anchored to the environment (e.g. via joints to the ground). Check that the design has at least one such connection.")

    else:
        # Full run: multi-objective and root-cause style (no spoilers)
        structure_broken = metrics.get("structure_broken", False)
        delivery_pct = metrics.get("delivery_ratio_percent")
        target_pct = metrics.get("min_delivery_ratio_percent")
        delivery_failed = target_pct is not None and delivery_pct is not None and _is_finite(target_pct) and _is_finite(delivery_pct) and delivery_pct < target_pct

        # Multi-objective trade-off
        if structure_broken and delivery_failed:
            suggestions.append("Diagnostic: Both structural integrity and delivery efficiency failed. Infer whether joint failure occurred first (e.g. under environmental loads) or whether delivery failed despite an intact structure; that order informs whether to prioritize structural robustness or flow/trajectory control.")
        elif structure_broken and not delivery_failed:
            suggestions.append("Diagnostic: Structure integrity was lost (joint(s) failed) while delivery may have been sufficient. Focus on what environmental loads or stress concentrations could have caused the failure.")
        elif delivery_failed and not structure_broken:
            suggestions.append("Diagnostic: Structure remained intact but delivery fell short of the target. Consider momentum transfer to particles, trajectory through hazards (e.g. pits, headwind, gravity wells), and whether the per-step force budget or control strategy limited effective relocation.")

        # Root-cause style (single failure)
        if failed and structure_broken:
            suggestions.append("Diagnostic: Structural integrity failure indicates that stress at one or more joints exceeded the environment's capacity. Loads can come from self-weight, particle impacts, or external fields; identify the dominant load path.")

        if failed and ("delivery" in reason or "efficiency" in reason or "particles" in reason or delivery_failed):
            suggestions.append("Diagnostic: Delivery shortfall suggests insufficient net transport of fluid into the target zone. Possible causes include loss into hazards, opposing forces (e.g. headwind, gravity well), or control strategy that did not direct enough particles into the target in the available time.")

    return suggestions
