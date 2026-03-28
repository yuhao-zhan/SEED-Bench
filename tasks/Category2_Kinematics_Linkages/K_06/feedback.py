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

    # Early exit / error state (evaluator returned error only)
    if "error" in metrics:
        task_metrics.append(f"EVALUATION_ERROR: {metrics['error']}.")
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

    # Residual vs allowed (dynamic threshold from metrics)
    if "residual_percentage" in metrics and "max_residual_percent" in metrics:
        try:
            res = float(metrics["residual_percentage"])
            max_res = float(metrics["max_residual_percent"])
            excess = res - max_res
            if excess > 0:
                task_metrics.append(
                    f"RESIDUAL_EXCESS: Residual exceeds allowed by {excess:.2f} percentage points (allowed: {max_res:.2f}%)."
                )
            else:
                task_metrics.append(
                    f"RESIDUAL_MARGIN: {abs(excess):.2f} percentage points under allowed residual."
                )
        except (TypeError, ValueError):
            pass

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

    # Time / steps (only if present)
    if "step_count" in metrics:
        task_metrics.append(f"SIMULATION_STEPS: {metrics['step_count']}.")
    if "min_simulation_steps_required" in metrics:
        task_metrics.append(
            f"REQUIRED_STEPS: {metrics['min_simulation_steps_required']} (minimum operational duration)."
        )
    if "step_count" in metrics and "min_simulation_steps_required" in metrics:
        try:
            steps = int(metrics["step_count"])
            required = int(metrics["min_simulation_steps_required"])
            if steps < required:
                task_metrics.append(
                    f"STEP_SHORTFALL: Simulation ended {required - steps} steps before required duration."
                )
            else:
                task_metrics.append(
                    f"STEP_MARGIN: {steps - required} steps beyond required duration."
                )
        except (TypeError, ValueError):
            pass

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
    if metrics.get("failed") and metrics.get("failure_reason"):
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

    # Early exit: evaluator returned error only (no physical run)
    if "error" in metrics:
        suggestions.append(
            "DIAGNOSTIC: Evaluation could not run; the reported error indicates a setup or environment condition that must be resolved before physical metrics are available."
        )
        return suggestions

    # Dynamic thresholds only from metrics (no hardcoded mass, residual, or step limits)
    max_mass = metrics.get("max_structure_mass")
    current_mass = metrics.get("structure_mass")
    max_res = metrics.get("max_residual_percent")
    res_percent = metrics.get("residual_percentage")
    min_steps = metrics.get("min_simulation_steps_required")
    step_count = metrics.get("step_count")
    is_failed = metrics.get("failed", False)
    reason = metrics.get("failure_reason") or failure_reason or ""

    # --- 1. Physics engine / numerical instability ---
    numeric_keys = (
        "structure_mass", "cleaning_percentage", "residual_percentage",
        "step_count", "wiper_x", "wiper_y", "progress"
    )
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
            res_f = float(res_percent)
            max_res_f = float(max_res)
            if res_f > max_res_f:
                # Dynamic "almost no clearing" threshold: residual near 100% of the excess range
                range_above_max = 100.0 - max_res_f
                if range_above_max > 0:
                    threshold_almost_none = max_res_f + range_above_max * 0.9
                    if res_f >= threshold_almost_none:
                        suggestions.append(
                            "DIAGNOSTIC: The mechanism is failing to displace particles toward the glass boundaries; almost no clearing is occurring. Consider whether contact, sweep coverage, or actuation limits prevent effective momentum transfer."
                        )
                    else:
                        suggestions.append(
                            "DIAGNOSTIC: Coverage or clearing is insufficient; significant particle load remains in the target area. Consider the trade-off between structural capacity (mass, strength) and the impulse or contact needed to move particles off the glass."
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
    try:
        mass_over = (
            max_mass is not None and current_mass is not None
            and float(current_mass) > float(max_mass)
        )
        removal_fail = (
            max_res is not None and res_percent is not None
            and float(res_percent) > float(max_res)
        )
        if mass_over and removal_fail:
            suggestions.append(
                "DIAGNOSTIC: Multiple constraints are violated (mass budget and removal target). The reported failure reason reflects the first constraint checked in evaluation order (mass budget, then build zone, then particle removal); satisfying the primary failure first is necessary before cleaning performance can count."
            )
        elif mass_over and not removal_fail:
            suggestions.append(
                "DIAGNOSTIC: Cleaning performance may be adequate, but the structure violates the mass budget. The reported failure is due to constraint violation rather than clearing performance; consider the strength-to-weight and actuation-to-weight trade-off."
            )
        elif not mass_over and removal_fail:
            suggestions.append(
                "DIAGNOSTIC: Mass budget is satisfied but particle removal is below the required threshold. The failure is due to insufficient clearing; consider whether sweep coverage, contact force, or environmental conditions (e.g. particle adhesion or mass) limit momentum transfer."
            )
    except (TypeError, ValueError):
        pass

    # --- 6. Root-cause chain: surface the evaluator's primary failure reason (no spoilers) ---
    if is_failed and reason:
        suggestions.append(
            f"DIAGNOSTIC: {reason}"
        )

    return suggestions
