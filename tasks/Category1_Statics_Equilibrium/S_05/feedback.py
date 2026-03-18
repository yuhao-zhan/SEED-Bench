"""
Task-specific feedback generation for S-05: The Shelter.
Process-aware, diagnostic feedback only. All limits and thresholds from the
metrics dict returned by evaluator.evaluate() (stage-mutation safe).
Domain: Statics + impact dynamics (shelter under bombardment).
"""
from typing import Dict, Any, List, Optional
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


def _check_numerical_stability(metrics: Dict[str, Any], keys: List[str]) -> bool:
    """Return True if all given metric values are finite."""
    for k in keys:
        v = metrics.get(k)
        if v is not None and not _is_finite(v):
            return False
    return True


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Expose high-resolution physical metrics from evaluator.evaluate() only.
    No suggestions. All values and limits come from the metrics dict
    (dynamic; adapts to stage mutations in stages.py).
    """
    if not metrics:
        return []

    parts: List[str] = []

    # ---- Numerical stability (finite-ness of core metrics) ----
    key_quantities = ["core_force", "structure_mass", "min_body_y"]
    if not _check_numerical_stability(metrics, key_quantities):
        parts.append(
            "⚠️ **Physics engine**: One or more core quantities are non-finite (NaN or infinity). "
            "This may indicate numerical instability from extreme geometry or impacts."
        )

    # ---- Peak core impact (metrics: core_force, max_core_force) ----
    core_force = metrics.get("core_force")
    max_core_force = metrics.get("max_core_force")
    if core_force is not None and max_core_force is not None:
        if not _is_finite(core_force) or not _is_finite(max_core_force):
            parts.append("⚠️ **Peak core impact**: Non-finite value detected.")
        else:
            cf, mcf = float(core_force), float(max_core_force)
            within = cf <= mcf
            status = "✅" if within else "❌"
            margin = (mcf - cf) if within else (cf - mcf)
            pct = (cf / mcf * 100) if mcf > 0 else 0
            parts.append(
                f"{status} **Peak core impact**: {cf:.2f} N "
                f"(limit: {mcf:.2f} N) — margin {margin:.2f} N {'within' if within else 'over'} "
                f"({pct:.0f}% of limit)."
            )

    # ---- Mass budget (metrics: structure_mass, max_mass) ----
    structure_mass = metrics.get("structure_mass")
    max_mass = metrics.get("max_mass")
    if structure_mass is not None and max_mass is not None:
        if not _is_finite(structure_mass) or not _is_finite(max_mass):
            parts.append("⚠️ **Structural mass**: Non-finite value detected.")
        else:
            sm, mm = float(structure_mass), float(max_mass)
            within = sm <= mm
            status = "✅" if within else "❌"
            margin = (mm - sm) if within else (sm - mm)
            pct = (sm / mm * 100) if mm > 0 else 0
            parts.append(
                f"{status} **Structural mass**: {sm:.2f} kg / {mm:.2f} kg "
                f"— margin {margin:.2f} kg {'within' if within else 'over'} budget ({pct:.0f}% of limit)."
            )

    # ---- Lowest beam height (metrics: min_body_y); collapse is evaluator-defined ----
    min_body_y = metrics.get("min_body_y")
    if min_body_y is not None:
        if not _is_finite(min_body_y):
            parts.append("⚠️ **Lowest beam height**: Non-finite value detected.")
        else:
            failure_reason = (metrics.get("failure_reason") or "").lower()
            is_collapse = "collapse" in failure_reason or "below ground" in failure_reason
            status = "❌" if is_collapse else "✅"
            parts.append(
                f"{status} **Lowest beam height**: {float(min_body_y):.2f} m "
                "(structural stability requires beams to remain above the collapse threshold)."
            )

    # ---- Height limit (metrics: max_height_limit) ----
    max_height_limit = metrics.get("max_height_limit")
    if max_height_limit is not None and _is_finite(max_height_limit):
        parts.append(
            f"**Height limit**: No beam above y = {float(max_height_limit):.2f} m."
        )

    # ---- Joint load (observed peaks; metrics: max_joint_force_seen, max_joint_torque_seen) ----
    max_joint_force_seen = metrics.get("max_joint_force_seen")
    max_joint_torque_seen = metrics.get("max_joint_torque_seen")
    if max_joint_force_seen is not None and _is_finite(max_joint_force_seen):
        parts.append(
            f"**Peak joint reaction force observed**: {float(max_joint_force_seen):.2f} N."
        )
    if max_joint_torque_seen is not None and _is_finite(max_joint_torque_seen):
        parts.append(
            f"**Peak joint reaction torque observed**: {float(max_joint_torque_seen):.2f} Nm."
        )

    # ---- Core position (metrics: core_x, core_y) ----
    core_x = metrics.get("core_x")
    core_y = metrics.get("core_y")
    if core_x is not None and core_y is not None and _is_finite(core_x) and _is_finite(core_y):
        parts.append(f"**Core position**: ({float(core_x):.2f}, {float(core_y):.2f}).")

    # ---- Bombardment (metrics: meteor_count) ----
    meteor_count = metrics.get("meteor_count")
    if meteor_count is not None:
        parts.append(f"**Meteor count**: {meteor_count}.")

    # ---- Outcome (metrics: success, failed, failure_reason) ----
    success = metrics.get("success")
    failed = metrics.get("failed")
    if success is not None:
        parts.append(f"**Success**: {'Yes' if success else 'No'}.")
    if failed is not None and failed:
        fr = metrics.get("failure_reason")
        if fr:
            parts.append(f"**Reported failure**: {fr}")

    return parts


def get_improvement_suggestions(
    metrics: Dict[str, Any],
    score: float,
    success: bool,
    failed: bool,
    failure_reason: Optional[str] = None,
    error: Optional[str] = None,
) -> List[str]:
    """
    Diagnostic system feedback only. No spoilers: diagnose physical/systemic
    cause, never dictate concrete design or code. All thresholds from metrics
    (stage-mutation safe). Evaluator failure order: joint → collapse → core
    force → mass → height (first breach is reported).
    """
    suggestions: List[str] = []

    if error:
        suggestions.append(
            ">> DIAGNOSTIC: A constraint was violated during build or simulation. "
            "Use the error and metrics to infer which physical rule was breached."
        )
        return suggestions

    # ---- Non-finite core metrics (physics engine) ----
    key_quantities = ["core_force", "structure_mass", "min_body_y"]
    if not _check_numerical_stability(metrics, key_quantities):
        suggestions.append(
            ">> PHYSICS ENGINE: Non-finite values detected. Consider whether extreme "
            "geometry, velocities, or impacts could have caused numerical instability."
        )

    # ---- Incomplete evaluation: success only after full run ----
    if not failed and not success and score is not None and score < 100:
        suggestions.append(
            ">> EVALUATION: Success is evaluated only after the full impact sequence. "
            "Partial runs do not qualify as success."
        )

    if not failed:
        return suggestions

    # ---- Root-cause chain: evaluator checks in order; reported failure is the first breach ----
    suggestions.append(
        ">> FAILURE MODE: Evaluation checks constraints in order; the reported failure "
        "is the first breach: joint capacity → structural collapse → core protection → "
        "mass budget → height limit."
    )
    suggestions.append(f">> REPORTED FAILURE: {failure_reason}")

    reason_lower = (failure_reason or "").lower()
    max_core_force = metrics.get("max_core_force")
    max_mass = metrics.get("max_mass")
    core_force = metrics.get("core_force")
    structure_mass = metrics.get("structure_mass")

    # ---- Root-cause diagnostics (no spoilers) ----
    if "collapse" in reason_lower or "below ground" in reason_lower:
        suggestions.append(
            "-> Root cause: Structural stability failed; lowest beam fell below the "
            "collapse threshold. Consider whether self-weight, lateral loading, or "
            "impact caused the failure (e.g. strength-to-weight or load path)."
        )
    elif "core protection failed" in reason_lower or ("force" in reason_lower and "core" in reason_lower):
        suggestions.append(
            "-> Root cause: Peak impact on the core exceeded the allowed force. "
            "Consider whether direct impact or structural failure allowed load to "
            "reach the core (e.g. deflection vs. absorption, load path to ground)."
        )
    elif "mass budget" in reason_lower or "mass" in reason_lower:
        suggestions.append(
            "-> Root cause: Mass budget was exceeded. Consider whether the same "
            "structural role could be achieved with a better strength-to-weight ratio."
        )
    elif "height" in reason_lower:
        suggestions.append(
            "-> Root cause: A structural element exceeded the permitted height. "
            "Relate vertical extent to the height limit in the metrics."
        )
    elif "joint failure" in reason_lower or ("joint" in reason_lower and "force" in reason_lower):
        suggestions.append(
            "-> Root cause: A connection exceeded its force or torque capacity. "
            "Consider whether load concentration at connections led to reaction "
            "forces or torques exceeding the connection limit."
        )

    # ---- Joint failed first while other constraints were satisfied ----
    core_ok = (
        max_core_force is not None
        and core_force is not None
        and _is_finite(core_force)
        and core_force <= max_core_force
    )
    mass_ok = (
        max_mass is not None
        and structure_mass is not None
        and _is_finite(structure_mass)
        and structure_mass <= max_mass
    )
    if "joint" in reason_lower and (core_ok or mass_ok):
        suggestions.append(
            "-> Trade-off: Joint capacity was the first bottleneck; other constraints "
            "(e.g. core force or mass) may still be within limits. Consider load "
            "concentration and reaction magnitude at connections."
        )

    return suggestions
