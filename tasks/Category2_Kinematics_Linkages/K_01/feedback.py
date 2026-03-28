"""
Task-specific feedback generation for K-01: The Walker.
Uses only metrics from evaluator.evaluate(); no hardcoded thresholds.
Strictly diagnostic; no design or API spoilers.
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
    """True if any numeric metric in metrics is non-finite (evaluator can return such values)."""
    numeric_keys = (
        'walker_x', 'walker_y', 'distance_traveled', 'max_x_reached',
        'min_torso_y', 'progress', 'step_count', 'structure_mass',
        'max_structure_mass', 'min_simulation_steps_required', 'target_x'
    )
    for k in numeric_keys:
        if k in metrics and not _is_finite_number(metrics[k]):
            return True
    return False


def _parse_failure_reasons(failure_reason: str) -> List[str]:
    """Split concatenated failure_reason (evaluator uses '; ')."""
    if not failure_reason or not isinstance(failure_reason, str):
        return []
    return [s.strip() for s in failure_reason.split(";") if s.strip()]


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Expose only physical quantities present in the metrics dict from evaluator.evaluate().
    No suggestions; no invented metrics or limits.
    """
    parts = []

    if _has_numerical_instability(metrics):
        parts.append(
            "**Numerical Stability**: One or more reported metrics are non-finite (NaN or infinite). "
            "The simulation may have encountered numerical instability."
        )
        return parts

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
            target_x = metrics.get('target_x')
            if target_x is not None and _is_finite_number(target_x):
                gap = target_x - x
                parts.append(f"- Remaining distance to target x: {gap:.2f}m")

    if 'structure_mass' in metrics:
        mass = metrics['structure_mass']
        max_mass = metrics.get('max_structure_mass', float('inf'))
        if _is_finite_number(mass):
            if _is_finite_number(max_mass):
                status = "EXCEEDED" if mass > max_mass else "WITHIN LIMIT"
                parts.append(
                    f"**Structural Profile**: Total mass {mass:.2f}kg ({status} vs environment budget {max_mass:.2f}kg)"
                )
            else:
                parts.append(f"**Structural Profile**: Total mass {mass:.2f}kg")

    if 'min_torso_y' in metrics and _is_finite_number(metrics['min_torso_y']):
        parts.append(
            f"**Stability**: Minimum torso height observed this run: {metrics['min_torso_y']:.2f}m"
        )

    if 'step_count' in metrics:
        steps = metrics['step_count']
        req = metrics.get('min_simulation_steps_required')
        if _is_finite_number(steps):
            parts.append(f"**Temporal**: Simulation steps {int(steps)}")
            if req is not None and _is_finite_number(req) and req > 0:
                ratio = min(steps / req, 1.0) * 100
                parts.append(f"- Survival duration: {ratio:.1f}% of required steps")

    if metrics.get('failed') and metrics.get('failure_reason'):
        parts.append(f"**Run Outcome**: Failed — {metrics['failure_reason']}")

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
    Diagnostic feedback from evaluator metrics and failure_reason only.
    All thresholds from metrics (stage-mutation safe). No design or API spoilers.
    """
    suggestions = []

    max_mass = metrics.get('max_structure_mass', float('inf'))
    structure_mass = metrics.get('structure_mass')
    req_steps = metrics.get('min_simulation_steps_required')
    step_count = metrics.get('step_count', 0)
    progress = metrics.get('progress', 0)
    reason = failure_reason or metrics.get('failure_reason') or ""

    if _has_numerical_instability(metrics):
        suggestions.append(
            "DIAGNOSTIC: Numerical instability detected in simulation outputs (non-finite values). "
            "Consider whether extreme forces, velocities, or constraints could be driving the solver "
            "into an invalid state."
        )
        return suggestions

    err = error or metrics.get('error')
    if err:
        suggestions.append(
            "DIAGNOSTIC: The evaluator reported an error. Use the error message and the kinematic/stability "
            "metrics above to infer whether the failure is due to missing structure, invalid state, or constraint violation."
        )
        return suggestions

    reasons = _parse_failure_reasons(reason)
    if failed and len(reasons) > 1:
        suggestions.append(
            "DIAGNOSTIC: More than one constraint was violated in this run. Consider which physical limit "
            "was exceeded first (e.g. loss of vertical support vs. design budget vs. allowed region)."
        )

    mass_exceeded = (
        structure_mass is not None
        and _is_finite_number(max_mass)
        and _is_finite_number(structure_mass)
        and structure_mass > max_mass
    )
    if failed and ("design constraint" in reason.lower() or "mass" in reason.lower() or mass_exceeded):
        suggestions.append(
            "DIAGNOSTIC: The run was terminated due to a design constraint violation: total structure mass "
            "exceeds the environment's allowed budget (reported in metrics)."
        )
        suggestions.append(
            "ADVISORY: The physical mechanism is inertia versus available actuation. Consider how total mass "
            "and load-carrying capacity interact under the budget."
        )
        return suggestions

    if failed and ("collapsed" in reason.lower() or "torso touched" in reason.lower() or "height" in reason.lower()):
        suggestions.append(
            "DIAGNOSTIC: The run was terminated because the torso height fell below the survival threshold—"
            "vertical support was lost."
        )
        suggestions.append(
            "ADVISORY: In linkage-based locomotion, collapse often follows loss of support polygon or poor "
            "phase coordination. Use minimum torso height and step count to infer whether failure was early "
            "(e.g. initial tip-over) or late (e.g. gradual drift or resonance)."
        )
        if mass_exceeded:
            suggestions.append(
                "ADVISORY: Structural mass is at or over the environment limit; stability and mass budget "
                "may be competing objectives."
            )
        return suggestions

    if failed and "build zone" in reason.lower():
        suggestions.append(
            "DIAGNOSTIC: The run was terminated because the torso left the allowed spatial region."
        )
        suggestions.append(
            "ADVISORY: Consider whether the failure was due to trajectory leaving the allowed region "
            "(e.g. lateral/vertical drift or forward overshoot)."
        )
        return suggestions

    # Not failed but not success: run ended without meeting success criteria (evaluator: success = distance + duration)
    if not failed and not success:
        if req_steps is not None and _is_finite_number(req_steps) and req_steps > 0:
            if _is_finite_number(step_count) and step_count < req_steps:
                suggestions.append(
                    "DIAGNOSTIC: The simulation ended without meeting the required survival duration."
                )
        if _is_finite_number(step_count) and _is_finite_number(req_steps) and req_steps > 0:
            if step_count >= req_steps and _is_finite_number(progress) and progress < 100:
                suggestions.append(
                    "ADVISORY: The structure survived the required duration but did not reach the distance target. "
                    "The limiting factor may be net forward momentum transfer or gait efficiency."
                )
            elif step_count < req_steps and _is_finite_number(progress):
                suggestions.append(
                    "ADVISORY: The run did not meet both success criteria (distance and duration). "
                    "Use the reported progress and survival ratio to identify the limiting factor."
                )

    return suggestions
