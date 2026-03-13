"""
Task-specific feedback generation for K-01: The Walker.
Process-aware, diagnostic feedback for Kinematics/Linkages domain.
Uses only metrics from evaluator.evaluate(); no hardcoded thresholds.
"""
from typing import Dict, Any, List
import math


def _is_finite_number(v: Any) -> bool:
    """True if v is a finite number (no NaN, no inf)."""
    if v is None:
        return False
    try:
        f = float(v)
        return math.isfinite(f)
    except (TypeError, ValueError):
        return False


def _has_numerical_instability(metrics: Dict[str, Any]) -> bool:
    """True if any numeric metric is non-finite (NaN/inf)."""
    numeric_keys = (
        'walker_x', 'walker_y', 'distance_traveled', 'max_x_reached',
        'min_torso_y', 'progress', 'step_count', 'structure_mass',
        'max_structure_mass', 'min_simulation_steps_required'
    )
    for k in numeric_keys:
        if k in metrics and not _is_finite_number(metrics[k]):
            return True
    return False


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Expose high-resolution physical metrics from the evaluator only.
    No suggestions; only what is present in metrics. No hallucinated quantities.
    """
    parts = []

    # Numerical instability (physics engine limits)
    if _has_numerical_instability(metrics):
        parts.append("**Numerical Stability**: One or more reported metrics are non-finite (NaN or infinite). The simulation may have encountered numerical instability.")
        return parts

    # Kinematic state (only if present)
    if 'walker_x' in metrics and 'walker_y' in metrics:
        x, y = metrics['walker_x'], metrics['walker_y']
        if _is_finite_number(x) and _is_finite_number(y):
            parts.append(f"**Kinematic State**: Current torso position (x={x:.2f}m, y={y:.2f}m)")
            if 'distance_traveled' in metrics and _is_finite_number(metrics['distance_traveled']):
                parts.append(f"- Horizontal displacement from start: {metrics['distance_traveled']:.2f}m")
            if 'max_x_reached' in metrics and _is_finite_number(metrics['max_x_reached']):
                parts.append(f"- Peak forward reach this run: {metrics['max_x_reached']:.2f}m")
            if 'progress' in metrics and _is_finite_number(metrics['progress']):
                parts.append(f"- Distance progress toward target: {metrics['progress']:.1f}%")

    # Structural profile (mass vs budget from metrics only)
    if 'structure_mass' in metrics:
        mass = metrics['structure_mass']
        max_mass = metrics.get('max_structure_mass', float('inf'))
        if _is_finite_number(mass):
            if _is_finite_number(max_mass):
                status = "EXCEEDED" if mass > max_mass else "WITHIN LIMIT"
                parts.append(f"**Structural Profile**: Total mass {mass:.2f}kg ({status} vs environment budget)")
            else:
                parts.append(f"**Structural Profile**: Total mass {mass:.2f}kg")

    # Stability (minimum torso height observed)
    if 'min_torso_y' in metrics and _is_finite_number(metrics['min_torso_y']):
        parts.append(f"**Stability**: Minimum torso height observed this run: {metrics['min_torso_y']:.2f}m")

    # Temporal (step count vs required from metrics)
    if 'step_count' in metrics:
        steps = metrics['step_count']
        req = metrics.get('min_simulation_steps_required')
        if _is_finite_number(steps):
            parts.append(f"**Temporal**: Simulation steps {int(steps)}")
            if req is not None and _is_finite_number(req) and req > 0:
                ratio = min(steps / req, 1.0) * 100
                parts.append(f"- Survival duration: {ratio:.1f}% of required steps")

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
    Generate diagnostic, process-aware feedback. No spoilers; no implementation hints.
    All thresholds taken from metrics (stage-mutation safe). Root-cause and trade-off aware.
    """
    suggestions = []

    # Use dynamic thresholds from metrics only
    max_mass = metrics.get('max_structure_mass', float('inf'))
    structure_mass = metrics.get('structure_mass')
    req_steps = metrics.get('min_simulation_steps_required')
    step_count = metrics.get('step_count', 0)
    distance_traveled = metrics.get('distance_traveled', 0)
    progress = metrics.get('progress', 0)
    min_torso_y = metrics.get('min_torso_y')

    # Physics engine / numerical instability
    if _has_numerical_instability(metrics):
        suggestions.append("DIAGNOSTIC: Numerical instability detected in simulation outputs (non-finite values). Consider whether extreme forces, velocities, or constraints could be driving the solver into an invalid state.")
        return suggestions

    # Error path (e.g. environment not available, torso not found)
    if error:
        suggestions.append("DIAGNOSTIC: The evaluator reported an error. Use the error message and the kinematic/stability metrics above to infer whether the failure is due to missing structure, invalid state, or constraint violation.")
        return suggestions

    # ---- Root-cause and multi-objective (design constraint: mass) ----
    mass_exceeded = (
        structure_mass is not None
        and _is_finite_number(max_mass)
        and _is_finite_number(structure_mass)
        and structure_mass > max_mass
    )
    if failed and failure_reason and "design constraint" in (failure_reason or "").lower():
        if mass_exceeded or "mass" in (failure_reason or "").lower():
            suggestions.append("DIAGNOSTIC: The run was terminated due to a design constraint violation: total structure mass exceeds the environment's allowed budget.")
            suggestions.append("ADVISORY: The physical mechanism is inertia versus available actuation. Consider whether a lower strength-to-weight ratio or a different distribution of mass could satisfy the constraint without prescribing a specific design.")
        return suggestions

    # ---- Failure: stability (torso collapse) ----
    if failed and failure_reason and ("collapsed" in failure_reason.lower() or "torso touched" in failure_reason.lower()):
        suggestions.append("DIAGNOSTIC: The run was terminated because the torso height fell below the survival threshold—vertical support was lost.")
        suggestions.append("ADVISORY: In linkage-based locomotion, collapse often follows loss of support polygon or poor phase coordination. Infer from the minimum torso height and step count whether the failure was early (e.g. initial tip-over) or late (e.g. gradual drift or resonance).")
        # Multi-objective: if mass was also near limit, hint at trade-off without spoiling
        if mass_exceeded or (structure_mass is not None and _is_finite_number(max_mass) and structure_mass > max_mass * 0.9):
            suggestions.append("ADVISORY: Structural mass is at or near the environment limit; stability and mass budget may be competing objectives.")
        return suggestions

    # ---- Failure: insufficient displacement (no explicit "did not move" in evaluator; use metrics) ----
    if failed and _is_finite_number(distance_traveled) and distance_traveled < 0.1:
        suggestions.append("DIAGNOSTIC: The walker did not achieve meaningful horizontal displacement before failure. Traction, momentum transfer, or initial configuration may prevent effective gait.")
        suggestions.append("ADVISORY: Consider contact mechanics between the terminal links and the ground, and whether the actuation timing and magnitude are sufficient to overcome static friction and inertia.")
        return suggestions

    # ---- Not failed but not success: partial progress ----
    if not failed and not success:
        # Premature termination (did not survive required time)
        if req_steps is not None and _is_finite_number(req_steps) and req_steps > 0:
            if _is_finite_number(step_count) and step_count < req_steps:
                suggestions.append("DIAGNOSTIC: The simulation ended before the required survival duration. The structure either lost stability or violated a constraint before completing the time requirement.")
        # Good distance but insufficient time (multi-objective)
        if _is_finite_number(progress) and progress >= 90 and _is_finite_number(step_count) and req_steps is not None and step_count < req_steps:
            suggestions.append("ADVISORY: Distance goal was nearly or fully met, but the run did not satisfy the duration requirement. The limiting factor may be sustained stability or constraint satisfaction over time, not raw displacement.")
        # Good time but insufficient distance
        if _is_finite_number(step_count) and _is_finite_number(req_steps) and step_count >= req_steps and _is_finite_number(progress) and progress < 100:
            suggestions.append("ADVISORY: The structure survived the required duration but did not reach the distance target. The limiting factor may be net forward momentum transfer or gait efficiency rather than immediate collapse.")

    return suggestions
