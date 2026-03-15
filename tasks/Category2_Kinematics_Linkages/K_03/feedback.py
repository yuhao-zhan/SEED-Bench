"""
Task-specific feedback generation for K-03: The Gripper.
Process-aware, diagnostic feedback aligned with evaluator metrics only.
No spoilers; all thresholds derived dynamically from metrics (stage-mutation safe).
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


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Expose high-resolution physical metrics from the evaluator only.
    No suggestions; purely what is measured. Phase-segregated and boundary-aware.
    All values from metrics dict; no hallucinated keys.
    """
    if not metrics:
        return []

    metric_parts = []

    # --- Numerical sanity (report only; interpretation in suggestions) ---
    numeric_keys = [
        'object_y', 'object_x', 'height_gained', 'max_object_y_reached', 'progress',
        'structure_mass', 'gripper_x', 'gripper_y', 'min_object_y_seen',
        'steps_with_object_above_target', 'step_count'
    ]
    has_nan_or_inf = False
    for key in numeric_keys:
        if key in metrics and not _is_finite_number(metrics[key]):
            has_nan_or_inf = True
            break
    if has_nan_or_inf:
        metric_parts.append("**Numerical Stability**: Non-finite values detected in simulation output (possible numerical instability).")

    # --- Phase 1: Grasp / contact (only if present) ---
    if 'object_grasped' in metrics:
        status = "SECURED" if metrics.get('object_grasped') else "NONE"
        metric_parts.append(f"**Phase — Grasp**: {status}")
        if 'object_contact_points' in metrics:
            metric_parts.append(f"- Contact Points: {metrics['object_contact_points']}")
        if 'gripper_bodies_touching_object' in metrics:
            metric_parts.append(f"- Gripper Bodies in Contact: {metrics['gripper_bodies_touching_object']}")

    # --- Phase 2: Payload kinematics (Lift) — only keys that exist ---
    if 'object_y' in metrics and _is_finite_number(metrics.get('object_y')):
        metric_parts.append(f"**Phase — Lift**: Current altitude y={metrics['object_y']:.2f}m")
        if 'object_x' in metrics and _is_finite_number(metrics.get('object_x')):
            metric_parts.append(f"- Current position: x={metrics['object_x']:.2f}m")
        if 'height_gained' in metrics and _is_finite_number(metrics.get('height_gained')):
            metric_parts.append(f"- Elevation change from start: {metrics['height_gained']:.2f}m")
        if 'max_object_y_reached' in metrics and _is_finite_number(metrics.get('max_object_y_reached')):
            metric_parts.append(f"- Peak altitude reached: {metrics['max_object_y_reached']:.2f}m")
        if 'min_object_y_seen' in metrics and _is_finite_number(metrics.get('min_object_y_seen')):
            metric_parts.append(f"- Minimum altitude observed: {metrics['min_object_y_seen']:.2f}m")
        target_y = metrics.get('target_object_y')
        if target_y is not None and _is_finite_number(target_y):
            ty = float(target_y)
            metric_parts.append(f"- Target threshold: y >= {ty:.2f}m")
            if _is_finite_number(metrics.get('object_y')):
                margin = metrics['object_y'] - ty
                metric_parts.append(f"- Boundary margin to target: {margin:+.2f}m (positive = above target)")
        if 'progress' in metrics and _is_finite_number(metrics.get('progress')):
            metric_parts.append(f"- Completion progress: {metrics['progress']:.1f}%")

    # --- Gripper pose (if present) ---
    if 'gripper_x' in metrics and 'gripper_y' in metrics:
        if _is_finite_number(metrics.get('gripper_x')) and _is_finite_number(metrics.get('gripper_y')):
            metric_parts.append(f"**Gripper Pose**: x={metrics['gripper_x']:.2f}m, y={metrics['gripper_y']:.2f}m")

    # --- Phase 3: Sustain / temporal — dynamic required steps from metrics ---
    if 'steps_with_object_above_target' in metrics:
        held = metrics['steps_with_object_above_target']
        req = metrics.get('min_simulation_steps_required')
        metric_parts.append(f"**Phase — Sustain**: {held} steps at or above target altitude")
        if req is not None and _is_finite_number(req) and float(req) > 0:
            ratio = min(held / float(req), 1.0) * 100
            metric_parts.append(f"- Required duration progress: {ratio:.1f}%")

    # --- Structural budget (dynamic threshold from metrics only) ---
    if 'structure_mass' in metrics and _is_finite_number(metrics.get('structure_mass')):
        max_mass = metrics.get('max_structure_mass')
        if max_mass is not None and _is_finite_number(max_mass):
            max_mass = float(max_mass)
            utilization = (float(metrics['structure_mass']) / max_mass) * 100 if max_mass > 0 else 0.0
            metric_parts.append(f"**Structural Profile**: Mass {metrics['structure_mass']:.2f}kg (budget: {max_mass:.1f}kg)")
            metric_parts.append(f"- Mass budget utilization: {utilization:.1f}%")
        else:
            metric_parts.append(f"**Structural Profile**: Mass {metrics['structure_mass']:.2f}kg")

    # --- Simulation progress ---
    if 'step_count' in metrics and _is_finite_number(metrics.get('step_count')):
        metric_parts.append(f"**Simulation**: Ended at step {int(metrics['step_count'])}")

    return metric_parts


def get_improvement_suggestions(
    metrics: Dict[str, Any],
    score: float,
    success: bool,
    failed: bool,
    failure_reason: str = None,
    error: str = None,
) -> List[str]:
    """
    Generate process-aware diagnostic feedback. No spoilers: diagnose mechanism
    and root cause, never dictate concrete design or code. All thresholds
    from metrics (stage-mutation safe). Root-cause chain and multi-objective aware.
    """
    suggestions = []

    def _any_nonfinite(*keys):
        for k in keys:
            if k in metrics and not _is_finite_number(metrics.get(k)):
                return True
        return False

    # --- Physics engine limits: numerical instability ---
    if _any_nonfinite('object_y', 'height_gained', 'structure_mass', 'max_object_y_reached'):
        suggestions.append("DIAGNOSTIC: Simulation produced non-finite values; numerical instability or extreme dynamics may have occurred.")
        suggestions.append("ADVISORY: Consider whether forces, velocities, or time steps could lead to ill-conditioned or explosive behavior in the solver.")
        return suggestions

    # --- Resolve dynamic thresholds (never hardcode; stage-mutation safe) ---
    max_mass = metrics.get('max_structure_mass')
    if max_mass is not None:
        try:
            max_mass = float(max_mass)
        except (TypeError, ValueError):
            max_mass = None
    target_y = metrics.get('target_object_y')
    if target_y is not None:
        try:
            target_y = float(target_y)
        except (TypeError, ValueError):
            target_y = None
    req_steps = metrics.get('min_simulation_steps_required')
    if req_steps is not None:
        try:
            req_steps = int(req_steps)
        except (TypeError, ValueError):
            req_steps = None

    # --- Root-cause chain: design constraints (checked first, at step 0) ---
    if failed and failure_reason and "design constraint" in failure_reason.lower():
        if "mass" in failure_reason.lower() and max_mass is not None:
            mass = metrics.get('structure_mass')
            if mass is not None and _is_finite_number(mass) and float(mass) > max_mass:
                suggestions.append("DIAGNOSTIC: Design constraint violated — total structure mass exceeds the permitted budget for this environment.")
                suggestions.append("ADVISORY: The mechanism must satisfy the mass limit while still achieving grasp and lift; consider the strength-to-weight trade-off.")
        elif "zone" in failure_reason.lower():
            suggestions.append("DIAGNOSTIC: Design constraint violated — at least one component lies outside the permitted build zone.")
            suggestions.append("ADVISORY: All structural elements must be placed within the allowed spatial bounds.")
        return suggestions

    # --- Root-cause: runtime — object fell (payload equilibrium broken) ---
    if failed and (metrics.get('object_fell', False) or (failure_reason and "fell" in failure_reason.lower())):
        suggestions.append("DIAGNOSTIC: Payload equilibrium was lost after lift; the object descended below the required minimum altitude.")
        suggestions.append("ADVISORY: Loss of grip or load stability can follow from insufficient normal force, slip under acceleration, or geometry that cannot sustain the payload in this environment. Analyze contact and load path rather than a single parameter.")
        return suggestions

    # --- Root-cause: runtime — object not lifted (insufficient vertical work) ---
    if failed and failure_reason and "not lifted" in failure_reason.lower():
        suggestions.append("DIAGNOSTIC: Insufficient vertical work — object altitude did not increase significantly before timeout.")
        suggestions.append("ADVISORY: Possible causes include inadequate grasp before lift, actuator capacity or range insufficient for the load, or kinematic sequence that never engages the payload. Infer from grasp state and peak altitude in the metrics.")
        return suggestions

    # --- Multi-objective trade-off: one objective met, another constraint violated ---
    if failed:
        mass = metrics.get('structure_mass')
        grasped = metrics.get('object_grasped', False)
        max_y = metrics.get('max_object_y_reached')
        if max_mass is not None and mass is not None and _is_finite_number(mass) and float(mass) > max_mass:
            if grasped or (max_y is not None and target_y is not None and _is_finite_number(max_y) and float(max_y) >= target_y):
                suggestions.append("DIAGNOSTIC: At least one objective (grasp or lift) was achieved, but a design constraint (mass budget) was violated — a multi-objective trade-off failure.")
                suggestions.append("ADVISORY: Satisfy all constraints simultaneously; improving grasp or lift at the cost of exceeding the mass limit still results in failure.")
        if suggestions:
            return suggestions

    # --- Partial success: not failed but not full success (no spoilers) ---
    if not success and not failed:
        max_y = metrics.get('max_object_y_reached')
        held_steps = metrics.get('steps_with_object_above_target', 0)
        if target_y is not None and max_y is not None and _is_finite_number(max_y) and float(max_y) >= target_y:
            if req_steps is not None and held_steps is not None and int(held_steps) < req_steps:
                suggestions.append("DIAGNOSTIC: Target altitude was reached, but the payload was not held there for the required duration.")
                suggestions.append("ADVISORY: Temporal stability failed — grip or load path may be marginal; consider what could cause late slip or release after initial lift.")
        elif metrics.get('object_grasped', False):
            suggestions.append("DIAGNOSTIC: Payload was secured but vertical displacement or sustained height did not meet the task requirements.")
            suggestions.append("ADVISORY: Lifting capability (actuator force, range, or sequence) may be the bottleneck rather than grasp alone.")
        else:
            suggestions.append("DIAGNOSTIC: Task objectives were not met; grasp, lift, or sustain criteria are below threshold.")
            suggestions.append("ADVISORY: Use the reported metrics (grasp state, peak altitude, minimum altitude, duration at target) to identify which phase of the task is failing.")

    return suggestions
