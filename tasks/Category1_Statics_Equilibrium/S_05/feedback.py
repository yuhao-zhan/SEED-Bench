"""
Task-specific feedback generation for S-05: The Shelter.
Process-aware, diagnostic feedback. No spoilers; thresholds from metrics only.
"""
from typing import Dict, Any, List
import math


def _is_finite(x: Any) -> bool:
    """True if x is a finite number (no NaN, no inf)."""
    if x is None:
        return False
    try:
        f = float(x)
        return math.isfinite(f)
    except (TypeError, ValueError):
        return False


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Expose high-resolution physical metrics from evaluator.evaluate() only.
    No suggestions. Uses dynamic thresholds from metrics (stage-mutation safe).
    """
    if not metrics:
        return []

    parts: List[str] = []

    # --- Protection (core impact) ---
    core_force = metrics.get("core_force")
    max_core_force = metrics.get("max_core_force")
    if core_force is not None and max_core_force is not None:
        if not _is_finite(core_force) or not _is_finite(max_core_force):
            parts.append("⚠️ **Peak Core Impact**: Non-finite value detected (numerical instability).")
        else:
            within = core_force <= max_core_force
            status = "✅" if within else "❌"
            margin = (max_core_force - core_force) if within else (core_force - max_core_force)
            parts.append(
                f"{status} **Peak Core Impact**: {float(core_force):.2f} N "
                f"(Threshold: {float(max_core_force):.2f} N) "
                f"— margin {margin:.2f} N {'within' if within else 'over'} limit."
            )

    # --- Mass budget ---
    structure_mass = metrics.get("structure_mass")
    max_mass = metrics.get("max_mass")
    if structure_mass is not None and max_mass is not None:
        if not _is_finite(structure_mass) or not _is_finite(max_mass):
            parts.append("⚠️ **Structural Mass**: Non-finite value detected (numerical instability).")
        else:
            within = structure_mass <= max_mass
            status = "✅" if within else "❌"
            margin = (max_mass - structure_mass) if within else (structure_mass - max_mass)
            parts.append(
                f"{status} **Structural Mass**: {float(structure_mass):.2f} kg / {float(max_mass):.2f} kg "
                f"— margin {margin:.2f} kg {'within' if within else 'over'} budget."
            )

    # --- Structural clearance (collapse proxy) ---
    min_body_y = metrics.get("min_body_y")
    if min_body_y is not None:
        if not _is_finite(min_body_y):
            parts.append("⚠️ **Lowest Beam Height**: Non-finite value detected (numerical instability).")
        else:
            # Pass/fail from evaluator; threshold not in metrics so we show value only (no hardcode)
            failed = metrics.get("failed", False)
            failure_reason = (metrics.get("failure_reason") or "").lower()
            is_collapse = "collapse" in failure_reason or "below ground" in failure_reason
            status = "❌" if is_collapse else "✅"
            parts.append(
                f"{status} **Lowest Beam Height**: {float(min_body_y):.2f} m "
                "(structural collapse if below safe clearance)."
            )

    # --- Height limit ---
    max_height_limit = metrics.get("max_height_limit")
    if max_height_limit is not None and _is_finite(max_height_limit):
        parts.append(f"**Height Limit**: No beam above y = {float(max_height_limit):.2f} m.")

    # --- Core position (context for mutated stages) ---
    core_x = metrics.get("core_x")
    core_y = metrics.get("core_y")
    if core_x is not None and core_y is not None and _is_finite(core_x) and _is_finite(core_y):
        parts.append(f"**Core Position**: ({float(core_x):.2f}, {float(core_y):.2f}).")

    # --- Bombardment intensity ---
    meteor_count = metrics.get("meteor_count")
    if meteor_count is not None:
        parts.append(f"**Meteor Count**: {meteor_count}.")

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
    Diagnostic, process-aware suggestions. No spoilers; no hardcoded thresholds.
    Root-cause chain, multi-objective trade-offs, numerical stability.
    """
    suggestions: List[str] = []

    if error:
        suggestions.append(">> DIAGNOSTIC: A constraint was violated during build or simulation. Use the error and metrics to infer which physical rule was breached.")
        return suggestions

    # Dynamic thresholds from metrics only (stage-mutation safe)
    max_core_force = metrics.get("max_core_force")
    max_mass = metrics.get("max_mass")
    core_force = metrics.get("core_force")
    structure_mass = metrics.get("structure_mass")
    min_body_y = metrics.get("min_body_y")
    reason_lower = (failure_reason or "").lower()

    # --- Physics engine / numerical instability ---
    for key, val in [("core_force", core_force), ("structure_mass", structure_mass), ("min_body_y", min_body_y)]:
        if val is not None and not _is_finite(val):
            suggestions.append(">> PHYSICS ENGINE: A measured quantity is non-finite (NaN or infinite). This may indicate numerical instability or an invalid configuration; check that all constraints are physically consistent.")
            break

    if not failed:
        return suggestions

    suggestions.append(f">> FAILURE MODE: {failure_reason}")

    # --- Root-cause chain (evaluator order: collapse → core force → mass → height) ---
    if "collapse" in reason_lower or "below ground" in reason_lower:
        suggestions.append(
            "-> Root cause: Structural stability failed first. The load path lost vertical clearance "
            "(lowest beam fell below the collapse threshold). Consider whether dead load, lateral forces, "
            "or impact-induced collapse broke the structure before other limits were reached."
        )
    elif "core protection failed" in reason_lower or ("force" in reason_lower and "core" in reason_lower):
        suggestions.append(
            "-> Root cause: Core protection failed. Peak impact on the core exceeded the allowed force. "
            "Consider whether the failure is due to insufficient kinetic isolation (geometry/coverage), "
            "or whether structural collapse allowed debris or beams to contact the core."
        )
    elif "mass budget" in reason_lower or "mass" in reason_lower:
        suggestions.append(
            "-> Root cause: Mass budget was exceeded. The structure used more material than the "
            "allowed limit. Consider improving strength-to-weight ratio or reducing redundant mass."
        )
    elif "height" in reason_lower:
        suggestions.append(
            "-> Root cause: A structural element extended above the permitted height. Consider "
            "reconfiguring vertical extent while preserving protection and stability."
        )

    # --- Multi-objective trade-off paradox ---
    if max_core_force is not None and max_mass is not None and core_force is not None and structure_mass is not None:
        core_ok = _is_finite(core_force) and core_force <= max_core_force
        mass_ok = _is_finite(structure_mass) and structure_mass <= max_mass
        if core_ok and not mass_ok:
            suggestions.append(
                "-> Trade-off: Protection was within limit, but mass budget was violated. One objective "
                "was satisfied at the expense of another; consider whether the same protection can be "
                "achieved with less material."
            )
        elif not core_ok and mass_ok:
            suggestions.append(
                "-> Trade-off: Mass budget was satisfied, but core impact exceeded the threshold. "
                "Consider whether geometry or coverage (rather than added mass) can improve isolation."
            )

    return suggestions
