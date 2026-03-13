"""
Task-specific feedback for S-06: The Overhang.
Process-aware, diagnostic feedback grounded exclusively in evaluator metrics.
No spoilers; dynamic thresholds aligned with stages.py mutations.
"""
import math
from typing import Dict, Any, List


def _is_finite_number(x: Any) -> bool:
    """True if x is a real number (no NaN, no inf)."""
    if x is None:
        return False
    try:
        f = float(x)
        return math.isfinite(f)
    except (TypeError, ValueError):
        return False


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Format high-resolution physical metrics for S-06 (Statics / Overhang).
    Exposes only what evaluator.evaluate() returns. No hardcoded thresholds.
    """
    parts = []

    # --- Dynamic limits (from metrics; adapt to stage mutations) ---
    target_overhang = metrics.get("target_overhang")
    target_stability_time = metrics.get("target_stability_time")
    max_total_mass_limit = metrics.get("max_total_mass_limit")
    max_block_count_limit = metrics.get("max_block_count_limit")
    ceiling_y_limit = metrics.get("ceiling_y_limit")

    # --- Overhang (reach vs target) ---
    max_x = metrics.get("max_x_position")
    if _is_finite_number(max_x):
        to = target_overhang if _is_finite_number(target_overhang) else None
        overhang_ok = metrics.get("overhang_ok", False)
        status = "✅" if overhang_ok else "❌"
        parts.append(f"{status} **Maximum horizontal reach**: {float(max_x):.2f}m")
        if to is not None:
            parts.append(f"   Target: {float(to):.2f}m | Shortfall: {max(0.0, float(to) - float(max_x)):.2f}m")

    # --- Stability (duration vs required) ---
    stable_duration = metrics.get("stable_duration")
    if _is_finite_number(stable_duration):
        ts = target_stability_time if _is_finite_number(target_stability_time) else 10.0
        stability_ok = metrics.get("stability_ok", False)
        status = "✅" if stability_ok else "❌"
        parts.append(f"{status} **Static stability duration**: {float(stable_duration):.2f}s")
        if _is_finite_number(ts):
            deficit = max(0.0, float(ts) - float(stable_duration))
            parts.append(f"   Required: {float(ts):.2f}s | Deficit: {deficit:.2f}s")

    # --- Mass (utilization vs limit) ---
    structure_mass = metrics.get("structure_mass")
    if _is_finite_number(structure_mass) and _is_finite_number(max_total_mass_limit):
        m = float(structure_mass)
        limit = float(max_total_mass_limit)
        ok = m <= limit
        status = "✅" if ok else "❌"
        parts.append(f"{status} **Total mass**: {m:.2f} / {limit:.2f} units")
        if ok:
            parts.append(f"   Headroom: {limit - m:.2f} units")
        else:
            parts.append(f"   Overrun: {m - limit:.2f} units")

    # --- Block count (vs limit) ---
    block_count = metrics.get("block_count")
    if block_count is not None and _is_finite_number(max_block_count_limit):
        bc = int(block_count) if isinstance(block_count, (int, float)) else 0
        mcl = int(max_block_count_limit)
        ok = bc <= mcl
        status = "✅" if ok else "❌"
        parts.append(f"{status} **Block count**: {bc} / {mcl}")

    # --- Kinematic state (from evaluator only) ---
    if _is_finite_number(metrics.get("total_kinetic_energy")):
        parts.append(f"**System kinetic energy**: {float(metrics['total_kinetic_energy']):.2e} J")
    if _is_finite_number(metrics.get("max_velocity")):
        parts.append(f"**Peak velocity magnitude**: {float(metrics['max_velocity']):.2f} m/s")

    # --- Vertical extent and boundary proximity ---
    min_y = metrics.get("min_y_position")
    max_y = metrics.get("max_y_position")
    if _is_finite_number(min_y):
        parts.append(f"**Vertical extent (min y)**: {float(min_y):.2f}m")
        if float(min_y) < -5.0:
            parts.append(f"   Below table support level (y < -5m); structure has left the support.")
    if _is_finite_number(max_y):
        parts.append(f"**Vertical extent (max y)**: {float(max_y):.2f}m")
        if ceiling_y_limit is not None and _is_finite_number(ceiling_y_limit):
            cy = float(ceiling_y_limit)
            margin = cy - float(max_y)
            parts.append(f"   Ceiling at y={cy:.2f}m | Clearance margin: {margin:.2f}m")

    # --- Center of mass (when present) ---
    com_x = metrics.get("center_of_mass_x")
    com_y = metrics.get("center_of_mass_y")
    if _is_finite_number(com_x):
        parts.append(f"**Center of mass (x)**: {float(com_x):.2f}m (positive = past table edge)")
    if _is_finite_number(com_y):
        parts.append(f"**Center of mass (y)**: {float(com_y):.2f}m")

    # --- Simulation phase (step_count is available) ---
    step_count = metrics.get("step_count")
    if step_count is not None and isinstance(step_count, (int, float)):
        t_sim = step_count / 60.0
        parts.append(f"**Simulation time**: {t_sim:.2f}s (step {int(step_count)})")

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
    Aligns with evaluator failure modes and stage-mutated limits.
    """
    suggestions = []
    reason = (failure_reason or "").strip().lower()

    # --- Physics engine / numerical instability ---
    numeric_keys = [
        "max_x_position", "stable_duration", "structure_mass",
        "total_kinetic_energy", "max_velocity", "min_y_position", "max_y_position",
        "center_of_mass_x", "center_of_mass_y",
    ]
    for key in numeric_keys:
        val = metrics.get(key)
        if val is not None and not _is_finite_number(val):
            suggestions.append(">> Numerical instability detected: one or more physical quantities are non-finite (NaN or infinite). The simulation state may be invalid; consider whether initial conditions or structure layout could trigger numerical blow-up.")
            break

    # --- Persistent failure: root-cause mechanism (no solution prescribed) ---
    if failed and failure_reason:
        suggestions.append(f">> FAILURE MODE: {failure_reason}")

        if "fell off table" in reason:
            suggestions.append("-> Diagnostic: Equilibrium / support failure. The assembly’s support base (e.g. center of mass relative to the table edge) has crossed a stability boundary; loads or geometry have caused the structure to leave the support.")
        elif "ceiling" in reason:
            suggestions.append("-> Diagnostic: Vertical clearance breach. The structure’s vertical extent has exceeded the environment’s upper boundary; height or stacking strategy is constrained by this limit.")
        elif "maximum mass" in reason or "exceeds maximum mass" in reason:
            suggestions.append("-> Diagnostic: Mass budget violation. Total structure mass has exceeded the allowed limit for this environment; the trade-off between mass and strength or reach may need to be revisited.")
        elif "design constraint" in reason:
            suggestions.append("-> Diagnostic: Initialization / design constraint violation. One or more blocks violate rules on dimensions, count, or permitted placement zone at build time; check geometry and spawn bounds.")
        else:
            # Fallback: use stability/overhang from metrics to hint mechanism
            stability_ok = metrics.get("stability_ok", True)
            overhang_ok = metrics.get("overhang_ok", True)
            if not stability_ok:
                suggestions.append("-> Diagnostic: Static equilibrium not achieved; the structure retains motion or kinetic energy beyond the required stability duration.")
            if not overhang_ok:
                suggestions.append("-> Diagnostic: Horizontal reach is below the required overhang target; the tip of the structure does not extend far enough beyond the support edge.")

    # --- Multi-objective trade-off (no failure flag but conflicting objectives) ---
    if not failed and not success:
        stability_ok = metrics.get("stability_ok", True)
        overhang_ok = metrics.get("overhang_ok", True)
        max_mass_limit = metrics.get("max_total_mass_limit")
        mass = metrics.get("structure_mass")

        if stability_ok and not overhang_ok:
            suggestions.append("-> Trade-off: Stability is satisfied but horizontal reach is below target; the limiting factor is geometric extension rather than equilibrium duration.")
        elif not stability_ok and overhang_ok:
            suggestions.append("-> Trade-off: Reach meets target but the structure does not remain static long enough; the limiting factor is dynamic stability rather than reach.")
        elif stability_ok and overhang_ok and _is_finite_number(mass) and _is_finite_number(max_mass_limit):
            if float(mass) > float(max_mass_limit):
                suggestions.append("-> Trade-off: Reach and stability criteria could be met in principle, but total mass exceeds the environment’s budget; the design trades off mass against performance.")

    # --- Partial success: near-miss diagnostics (dynamic thresholds) ---
    target_overhang = metrics.get("target_overhang")
    target_stability_time = metrics.get("target_stability_time")
    if not success and not failed and failure_reason is None:
        mx = metrics.get("max_x_position")
        sd = metrics.get("stable_duration")
        if _is_finite_number(mx) and _is_finite_number(target_overhang):
            gap = float(target_overhang) - float(mx)
            if gap > 0.01:
                suggestions.append(f"-> Reach shortfall: tip is {gap:.2f}m short of the required overhang.")
        if _is_finite_number(sd) and _is_finite_number(target_stability_time):
            gap_t = float(target_stability_time) - float(sd)
            if gap_t > 0.01:
                suggestions.append(f"-> Stability shortfall: structure was static for {float(sd):.2f}s; {gap_t:.2f}s more were required.")

    return suggestions
