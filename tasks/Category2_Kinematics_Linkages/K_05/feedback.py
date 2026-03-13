"""
Task-specific feedback generation for K-05: The Lifter.
Process-aware, diagnostic feedback. Uses only metrics from evaluator.evaluate().
Adapts to stage mutations via dynamic thresholds (no hardcoded env values).
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
    Expose high-resolution physical metrics from the evaluator.
    Only reports keys present in metrics; no hallucinated data.
    Organizes by phase (payload state, structure, mass budget, stability).
    """
    parts: List[str] = []

    # --- Numerical sanity: flag impossible values if present ---
    sanity_issues = []
    for key in ("object_y", "object_velocity_x", "object_velocity_y", "height_gained",
                "max_object_y_reached", "progress", "structure_mass", "lifter_x", "lifter_y"):
        v = metrics.get(key)
        if v is not None and not _is_finite(v):
            sanity_issues.append(key)
    if sanity_issues:
        parts.append(f"**Numerical anomaly**: Non-finite values in: {', '.join(sanity_issues)}. Simulation state may be unstable.")

    # --- Payload state (altitude, displacement, velocity) ---
    obj_y = metrics.get("object_y")
    if obj_y is not None and _is_finite(obj_y):
        target_y = metrics.get("target_object_y")
        if target_y is not None and _is_finite(target_y):
            margin_to_target = target_y - obj_y
            parts.append(f"**Payload altitude**: y = {obj_y:.2f} m")
            parts.append(f"- Margin to target height: {margin_to_target:+.2f} m (target y = {target_y:.1f} m)")
        else:
            parts.append(f"**Payload altitude**: y = {obj_y:.2f} m")

    height_gained = metrics.get("height_gained")
    if height_gained is not None and _is_finite(height_gained):
        parts.append(f"- Vertical displacement from start: {height_gained:.2f} m")

    max_y = metrics.get("max_object_y_reached")
    if max_y is not None and _is_finite(max_y):
        parts.append(f"- Peak altitude reached this run: {max_y:.2f} m")

    vx = metrics.get("object_velocity_x")
    vy = metrics.get("object_velocity_y")
    if vx is not None and _is_finite(vx):
        parts.append(f"- Horizontal velocity: {vx:.3f} m/s")
    if vy is not None and _is_finite(vy):
        parts.append(f"- Vertical velocity: {vy:.3f} m/s (negative = descending)")

    progress = metrics.get("progress")
    if progress is not None and _is_finite(progress):
        parts.append(f"- Lift progress toward target displacement: {progress:.1f}%")

    # --- Structural integrity ---
    joint_count = metrics.get("joint_count")
    if joint_count is not None:
        broken = metrics.get("structure_broken", False)
        status = "CRITICAL FAILURE (joints lost)" if broken else "INTACT"
        parts.append(f"**Structural status**: {status}")
        parts.append(f"- Active joints: {joint_count}")

    # --- Mass budget (dynamic threshold from environment/stage) ---
    curr_mass = metrics.get("structure_mass")
    max_mass = metrics.get("max_structure_mass")
    if curr_mass is not None and _is_finite(curr_mass):
        max_m = max_mass if (max_mass is not None and _is_finite(max_mass)) else float("inf")
        parts.append(f"**Mass budget**: {curr_mass:.2f} kg / {max_m:.1f} kg" if math.isfinite(max_m) else f"**Structure mass**: {curr_mass:.2f} kg")
        if _is_finite(max_m) and max_m > 0:
            margin = max_m - curr_mass
            if margin < 0:
                parts.append(f"- Over budget by: {abs(margin):.2f} kg")
            else:
                parts.append(f"- Margin remaining: {margin:.2f} kg")

    # --- Stability / sustain phase (dynamic threshold: min_simulation_steps_required) ---
    steps_held = metrics.get("steps_with_object_above_target")
    req_steps = metrics.get("min_simulation_steps_required")
    if steps_held is not None and req_steps is not None:
        req = int(req_steps) if _is_finite(req_steps) else 0
        parts.append(f"**Sustain phase**: {steps_held} steps at or above target height (required: {req})")
        if req > 0 and steps_held < req:
            parts.append(f"- Shortfall: {req - steps_held} steps")

    # --- Lifter position (for context only) ---
    lx = metrics.get("lifter_x")
    ly = metrics.get("lifter_y")
    if lx is not None and _is_finite(lx) and ly is not None and _is_finite(ly):
        parts.append(f"**Lifter reference position**: ({lx:.2f}, {ly:.2f}) m")

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
    Diagnostic suggestions only. No spoilers (no code or parameter prescriptions).
    Uses dynamic thresholds from metrics so feedback adapts to stage mutations.
    """
    suggestions: List[str] = []

    # Dynamic thresholds (from environment / mutated stages)
    max_mass = metrics.get("max_structure_mass")
    if max_mass is not None and not _is_finite(max_mass):
        max_mass = None
    max_mass_val = float(max_mass) if max_mass is not None else float("inf")

    req_steps = metrics.get("min_simulation_steps_required")
    req_steps_val = int(req_steps) if (req_steps is not None and _is_finite(req_steps)) else 0

    target_y = metrics.get("target_object_y")
    target_y_val = float(target_y) if (target_y is not None and _is_finite(target_y)) else 9.0

    curr_mass = metrics.get("structure_mass", 0.0)
    if not _is_finite(curr_mass):
        curr_mass = 0.0

    # --- Physics engine / numerical instability ---
    for key in ("object_y", "object_velocity_x", "object_velocity_y", "structure_mass", "progress"):
        v = metrics.get(key)
        if v is not None and not _is_finite(v):
            suggestions.append("DIAGNOSTIC: Simulation state contains non-finite values. The physics engine may have become unstable (e.g. extreme forces or overlaps). Consider constraining control inputs or geometry to avoid singularities.")
            break

    # --- Design constraint violations (root-cause: constraint check runs first) ---
    if failed and failure_reason and "design constraint" in failure_reason.lower():
        if "mass" in failure_reason.lower():
            suggestions.append(
                "DIAGNOSTIC: The structure's total mass exceeds this environment's allowed budget. "
                "The load path and weight distribution may need to be reconsidered to meet the current limit."
            )
        elif "build zone" in failure_reason.lower():
            suggestions.append(
                "DIAGNOSTIC: At least one structural component lies outside the permitted build zone. "
                "All parts must remain within the specified spatial boundaries."
            )
        return suggestions

    # --- Structural failure (root-cause: joint breakage) ---
    if metrics.get("structure_broken", False):
        suggestions.append(
            "DIAGNOSTIC: One or more joints failed under load. Reaction forces or torques in the mechanism "
            "exceeded the connectors' capacity. The failure mode is consistent with overload (e.g. dead load, "
            "dynamic impact, or lateral forces) rather than a design-constraint check."
        )

    # --- Multi-objective trade-off: structure intact but other objectives failed ---
    structure_ok = not metrics.get("structure_broken", True)
    progress_pct = metrics.get("progress")
    progress_val = float(progress_pct) if (progress_pct is not None and _is_finite(progress_pct)) else 0.0
    steps_held = metrics.get("steps_with_object_above_target", 0) or 0

    if structure_ok and failed:
        if "not lifted" in (failure_reason or "").lower():
            suggestions.append(
                "DIAGNOSTIC: The object was not lifted meaningfully before the time limit. "
                "The mechanism may be unable to produce sufficient vertical displacement or force transmission."
            )
        elif progress_val >= 99.0 and steps_held < req_steps_val and req_steps_val > 0:
            suggestions.append(
                "DIAGNOSTIC: Target height was reached but the payload was not sustained there long enough. "
                "Stability at the target altitude is failing (e.g. sliding, tipping, or loss of support)."
            )

    # --- Partial success: height reached but sustain or structure failed ---
    if not success and not failed:
        if progress_val > 0 and progress_val < 100 and _is_finite(progress_val):
            suggestions.append(
                "DIAGNOSTIC: Vertical displacement is only partway to the required height. "
                "Lift capacity or stroke may be insufficient for the current target."
            )
        if progress_val >= 99.0 and steps_held < req_steps_val and req_steps_val > 0:
            suggestions.append(
                "DIAGNOSTIC: Altitude was achieved but the sustain criterion was not met. "
                "Payload equilibrium or retention at height is the limiting factor."
            )

    # --- Mass vs. performance trade-off (no spoilers) ---
    if _is_finite(max_mass_val) and max_mass_val > 0 and curr_mass > max_mass_val:
        suggestions.append(
            "DIAGNOSTIC: Mass budget is violated. A design that satisfies the current mass limit "
            "while still achieving the lift and stability objectives may require a different topology or load path."
        )
    elif structure_ok and progress_val < 50 and curr_mass > max_mass_val * 0.9:
        suggestions.append(
            "DIAGNOSTIC: Structure is near the mass limit but lift performance is low. "
            "There may be a trade-off between mass allocation and effective lift capability."
        )

    return suggestions
