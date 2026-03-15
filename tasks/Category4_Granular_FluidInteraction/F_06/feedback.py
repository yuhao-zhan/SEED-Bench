"""
F-06: The Pipeline — process-aware diagnostic feedback grounded in evaluator metrics only.
Category: Granular/Fluid Interaction.
Ground truth: metrics from evaluator.evaluate() only; no hallucinated fields or limits.
Dynamic thresholds: all limits from metrics (max_structure_mass, min_delivery_ratio_percent, force_budget).
No spoilers: diagnose physical mechanism and trade-offs, never dictate design or API usage.
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
    All limits and targets are read dynamically from metrics (stage-mutation safe).
    """
    if not metrics:
        return []

    parts = []

    # --- 0. Physics engine / numerical sanity ---
    numeric_keys = [
        "delivery_ratio", "delivery_ratio_percent", "min_delivery_ratio_percent",
        "structure_mass", "max_structure_mass", "force_budget", "step_count",
        "particles_in_target", "initial_particle_count",
    ]
    non_finite = [k for k in numeric_keys if k in metrics and not _is_finite(metrics[k])]
    if non_finite:
        parts.append("### 0. Numerical / Physics Engine")
        parts.append("- **Warning:** One or more metrics are non-finite (NaN or infinite); simulation outputs may be invalid.")

    # --- Design-constraint failure (build phase): early return ---
    if "constraint_violations" in metrics:
        viols = metrics["constraint_violations"]
        if isinstance(viols, list) and viols:
            parts.append("### 1. Design Constraint Violations (Build Phase)")
            for v in viols:
                parts.append(f"- {v}")
            if "failure_reason" in metrics:
                parts.append(f"- **Outcome:** {metrics['failure_reason']}")
            return parts

    # --- Full run: structural, delivery, and resource metrics ---

    # 1. Structural design & constraints (dynamic limits from metrics)
    struct_keys = ["structure_mass", "max_structure_mass", "structure_broken"]
    if any(k in metrics for k in struct_keys):
        parts.append("### 1. Structural Design & Constraints")
        mass = metrics.get("structure_mass")
        max_mass = metrics.get("max_structure_mass")
        if mass is not None and _is_finite(mass):
            limit_str = ""
            if max_mass is not None and _is_finite(max_mass):
                limit_str = f" / {max_mass:.2f} kg limit"
                margin_kg = max_mass - mass
                if margin_kg < 0:
                    parts.append(f"- Total Structure Mass: {mass:.2f} kg{limit_str}")
                    parts.append(f"- Mass Overrun: {abs(margin_kg):.2f} kg beyond limit.")
                else:
                    parts.append(f"- Total Structure Mass: {mass:.2f} kg{limit_str}")
                    parts.append(f"- Mass Margin: {margin_kg:.2f} kg below limit.")
            else:
                parts.append(f"- Total Structure Mass: {mass:.2f} kg")
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
        if delivery_pct is not None and _is_finite(delivery_pct):
            target_str = f" (Target: {target_pct:.1f}%)" if target_pct is not None and _is_finite(target_pct) else ""
            parts.append(f"- Delivery Efficiency: {delivery_pct:.1f}%{target_str}")
            if target_pct is not None and _is_finite(target_pct):
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
    Uses only metrics and failure_reason/error. All thresholds from metrics (stage-mutation safe).
    """
    suggestions = []
    reason = ((error or "") + " " + (failure_reason or "")).strip().lower()

    # --- Physics engine limits: numerical instability ---
    numeric_keys = [
        "delivery_ratio", "delivery_ratio_percent", "structure_mass", "max_structure_mass",
        "force_budget", "particles_in_target", "initial_particle_count",
    ]
    if any(k in metrics and not _is_finite(metrics.get(k)) for k in numeric_keys):
        suggestions.append(
            "Diagnostic: One or more metrics are non-finite (NaN or infinite); simulation outputs may be invalid. "
            "Consider whether extreme forces or invalid state could have produced such values."
        )

    # --- Design constraint failure (build phase) ---
    if "design constraint" in reason or metrics.get("constraint_violations"):
        viols = metrics.get("constraint_violations") or []
        viol_str = " ".join(str(v).lower() for v in viols)

        if "mass" in reason or "mass" in viol_str:
            suggestions.append(
                "Diagnostic: Structural mass exceeded the environment limit (reported in metrics as max_structure_mass). "
                "Consider how component count and density contribute to total mass and where stress or failure occurred."
            )
        if "build zone" in reason or "outside" in viol_str:
            suggestions.append(
                "Diagnostic: At least one component lies outside the permitted build zone. "
                "Ensure the entire structural topology is contained within the task's spatial boundaries."
            )
        if "anchor" in reason or "ground" in reason or "joint" in reason or "anchor" in viol_str or "joint" in viol_str:
            suggestions.append(
                "Diagnostic: Anchoring constraint was violated. "
                "The environment requires at least one fixed connection to the ground so the structure cannot drift or float."
            )
        return suggestions

    # --- Full run: structural vs delivery failure (diagnostic only; no redundant root-cause blocks) ---
    structure_broken = metrics.get("structure_broken", False)
    delivery_pct = metrics.get("delivery_ratio_percent")
    target_pct = metrics.get("min_delivery_ratio_percent")
    delivery_failed = (
        target_pct is not None and delivery_pct is not None
        and _is_finite(target_pct) and _is_finite(delivery_pct)
        and delivery_pct < target_pct
    )

    if structure_broken and delivery_failed:
        suggestions.append(
            "Diagnostic: Both structural integrity and delivery efficiency failed. "
            "Infer whether joint failure occurred first (e.g. under environmental loads) or delivery fell short despite an intact structure; "
            "that order informs whether to prioritize structural robustness or flow/trajectory control."
        )
    elif structure_broken and not delivery_failed:
        suggestions.append(
            "Diagnostic: Structure integrity was lost (joint(s) failed) while delivery may have been sufficient. "
            "Focus on what environmental loads or stress concentrations could have caused the failure—e.g. self-weight, particle impacts, or external fields."
        )
    elif delivery_failed and not structure_broken:
        suggestions.append(
            "Diagnostic: Structure remained intact but delivery fell short of the target. "
            "Consider momentum transfer to particles, trajectory through hazards, "
            "and whether the per-step force budget or control strategy limited effective relocation."
        )

    return suggestions
