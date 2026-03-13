"""
Task-specific feedback for K-06: The Wiper (Kinematics / Linkages).
Process-aware, diagnostic feedback grounded only in metrics from evaluator.evaluate().
No spoilers; all thresholds derived dynamically from metrics (stage-mutation adaptive).
"""
from typing import Dict, Any, List
import math


def _is_numerically_invalid(value: Any) -> bool:
    """True if value is NaN or infinite (physics engine instability)."""
    if value is None:
        return False
    try:
        f = float(value)
        return not math.isfinite(f)
    except (TypeError, ValueError):
        return False


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Expose high-resolution physical metrics from evaluator.evaluate() only.
    No suggestions; purely what is measured. All keys must exist in metrics.
    """
    task_metrics: List[str] = []

    if not metrics:
        return task_metrics

    # Particle removal (only if present)
    if "cleaning_percentage" in metrics:
        task_metrics.append(
            f"CLEANING_PROGRESS: {metrics['cleaning_percentage']:.2f}% of particles removed from glass."
        )
    if "residual_percentage" in metrics:
        task_metrics.append(
            f"RESIDUAL_LOAD: {metrics['residual_percentage']:.2f}% of particles remains in target area."
        )
    if "initial_particle_count" in metrics and "current_particle_count" in metrics:
        task_metrics.append(
            f"PARTICLE_COUNT: {metrics['current_particle_count']} / {metrics['initial_particle_count']} particles remaining."
        )
    if "particles_removed" in metrics:
        task_metrics.append(
            f"PARTICLES_REMOVED: {metrics['particles_removed']} pushed off glass."
        )

    # Mass budget (dynamic: limit comes from metrics for stage adaptability)
    if "structure_mass" in metrics and "max_structure_mass" in metrics:
        mass = metrics["structure_mass"]
        max_mass = metrics["max_structure_mass"]
        task_metrics.append(
            f"STRUCTURAL_MASS: {mass:.2f} kg (Limit: {max_mass:.2f} kg)."
        )
        try:
            margin = float(max_mass) - float(mass)
            if margin >= 0:
                task_metrics.append(
                    f"MASS_BUDGET_MARGIN: {margin:.2f} kg under limit."
                )
            else:
                task_metrics.append(
                    f"MASS_BUDGET_OVERAGE: {abs(margin):.2f} kg over limit."
                )
        except (TypeError, ValueError):
            pass

    # Removal shortfall vs required residual (dynamic threshold from metrics)
    if "residual_percentage" in metrics and "max_residual_percent" in metrics:
        res = metrics["residual_percentage"]
        max_res = metrics["max_residual_percent"]
        try:
            shortfall = float(res) - float(max_res)
            if shortfall > 0:
                task_metrics.append(
                    f"REMOVAL_SHORTFALL: Residual exceeds allowed by {shortfall:.2f} percentage points (allowed residual: {max_res:.2f}%)."
                )
        except (TypeError, ValueError):
            pass

    # Time / steps (only if present)
    if "step_count" in metrics:
        task_metrics.append(f"SIMULATION_STEPS: {metrics['step_count']}.")
    if "min_simulation_steps_required" in metrics:
        task_metrics.append(
            f"REQUIRED_STEPS: {metrics['min_simulation_steps_required']} (minimum operational duration)."
        )

    # Wiper position (spatial state; only if present)
    if "wiper_x" in metrics and "wiper_y" in metrics:
        task_metrics.append(
            f"WIPER_POSITION: (x={metrics['wiper_x']:.2f}, y={metrics['wiper_y']:.2f}) m."
        )

    # Progress (only if present, e.g. partial run)
    if "progress" in metrics:
        task_metrics.append(
            f"PROGRESS: {metrics['progress']:.2f}% toward removal target."
        )

    # Outcome state (what the evaluator concluded)
    if "success" in metrics:
        task_metrics.append(
            f"SUCCESS: {metrics['success']}."
        )
    if "failed" in metrics and metrics.get("failed") and "failure_reason" in metrics and metrics.get("failure_reason"):
        task_metrics.append(
            f"FAILURE_REASON: {metrics['failure_reason']}."
        )

    return task_metrics


def get_improvement_suggestions(
    metrics: Dict[str, Any],
    score: float = None,
    success: bool = None,
    failed: bool = None,
    failure_reason: str = None,
    error: str = None,
) -> List[str]:
    """
    Diagnostic system feedback: physical mechanism and root-cause framing.
    No implementation spoilers. All thresholds from metrics (stage-adaptive).
    """
    suggestions: List[str] = []

    if not metrics:
        return suggestions

    # Dynamic thresholds only from metrics (no hardcoded 15.0, 20.0, etc.)
    max_mass = metrics.get("max_structure_mass")
    current_mass = metrics.get("structure_mass")
    max_res = metrics.get("max_residual_percent")
    res_percent = metrics.get("residual_percentage")
    min_steps = metrics.get("min_simulation_steps_required")
    step_count = metrics.get("step_count")
    is_failed = metrics.get("failed", False)
    reason = metrics.get("failure_reason") or failure_reason or ""

    # --- 1. Physics engine / numerical instability ---
    numeric_keys = ("structure_mass", "cleaning_percentage", "residual_percentage", "step_count", "wiper_x", "wiper_y", "progress")
    for key in numeric_keys:
        if key in metrics and _is_numerically_invalid(metrics[key]):
            suggestions.append(
                "DIAGNOSTIC: Numerical instability detected in simulation output (non-finite values). Consider whether the mechanism or control leads to extreme forces or velocities."
            )
            break

    # --- 2. Mass constraint (root-cause: constraint violation) ---
    if max_mass is not None and current_mass is not None:
        try:
            if float(current_mass) > float(max_mass):
                suggestions.append(
                    "DIAGNOSTIC: Structural mass exceeds the permitted budget for this environment. The evaluator treats this as a hard constraint failure regardless of cleaning performance."
                )
        except (TypeError, ValueError):
            pass

    # --- 3. Removal / coverage (root-cause: insufficient clearing) ---
    if max_res is not None and res_percent is not None:
        try:
            if float(res_percent) > float(max_res):
                if float(res_percent) > 95.0:
                    suggestions.append(
                        "DIAGNOSTIC: The mechanism is failing to displace particles toward the glass boundaries; almost no clearing is occurring. Consider whether contact, sweep coverage, or actuation limits prevent effective momentum transfer."
                    )
                else:
                    suggestions.append(
                        "DIAGNOSTIC: Coverage or clearing is insufficient; significant particle load remains in the target area. Consider the trade-off between structural capacity (mass, strength) and the impulse or contact needed to move particles off the glass."
                    )
        except (TypeError, ValueError):
            pass

    # --- 4. Temporal / operational (did the run complete the required duration?) ---
    if min_steps is not None and step_count is not None and not metrics.get("success", False):
        try:
            if int(step_count) < int(min_steps):
                suggestions.append(
                    "DIAGNOSTIC: Simulation ended before the required operational duration. This may indicate early termination or a constraint failure; relate this to whether cleaning or mass was the primary failure mode."
                )
        except (TypeError, ValueError):
            pass

    # --- 5. Multi-objective trade-off paradox ---
    mass_over = max_mass is not None and current_mass is not None and float(current_mass) > float(max_mass)
    removal_fail = max_res is not None and res_percent is not None and float(res_percent) > float(max_res)
    if mass_over and removal_fail:
        suggestions.append(
            "DIAGNOSTIC: Multiple constraints are violated (mass budget and removal target). Identify which limit is primary: if mass is over budget, that is typically the first failure; improving cleaning alone will not pass until the mass constraint is satisfied."
        )
    elif mass_over and not removal_fail:
        suggestions.append(
            "DIAGNOSTIC: Cleaning performance may be adequate, but the structure violates the mass budget. The reported failure is due to constraint violation rather than clearing performance; consider the strength-to-weight and actuation-to-weight trade-off."
        )
    elif not mass_over and removal_fail:
        suggestions.append(
            "DIAGNOSTIC: Mass budget is satisfied but particle removal is below the required threshold. The failure is due to insufficient clearing; consider whether sweep coverage, contact force, or environmental conditions (e.g. particle adhesion or mass) limit momentum transfer."
        )

    # --- 6. Root-cause chain: surface the evaluator’s primary failure reason (no spoilers) ---
    if is_failed and reason:
        suggestions.append(
            f"DIAGNOSTIC: {reason}"
        )

    return suggestions
