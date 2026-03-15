"""
Task-specific feedback for K-04: The Pusher.
Process-aware, diagnostic feedback grounded only in evaluator metrics.
No hallucination, no spoilers, dynamic thresholds for stage mutations.
Physics domain: Kinematics / rigid-body contact (pusher–payload–terrain).
"""
import math
from typing import Dict, Any, List


def _safe_float(v: Any, default: float = None) -> float:
    """Return float if v is finite, else default. Used to avoid reporting NaN/inf."""
    if default is None:
        default = 0.0
    try:
        x = float(v)
        return x if math.isfinite(x) else default
    except (TypeError, ValueError):
        return default


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Expose high-resolution physical metrics from the evaluator only.
    No suggestions; only what is present in metrics. Phase and boundary
    proximity derived from existing keys (target_object_x, max_structure_mass, etc.).
    """
    parts = []

    # --- Error / missing environment (evaluator returns dict with "error" key) ---
    if metrics.get("error"):
        parts.append(f"**Terminal State**: {metrics.get('error')}")
        return parts

    # --- Payload state (object to push) ---
    if "object_x" in metrics:
        ox = _safe_float(metrics.get("object_x"))
        parts.append(f"**Payload State**: Position x={ox:.2f}m")
        if "object_y" in metrics:
            oy = _safe_float(metrics.get("object_y"))
            parts.append(f"- Vertical position y={oy:.2f}m")
        if "distance_pushed" in metrics:
            dp = _safe_float(metrics.get("distance_pushed"))
            parts.append(f"- Net displacement: {dp:.2f}m")
        if "object_velocity_x" in metrics:
            ovx = _safe_float(metrics.get("object_velocity_x"))
            parts.append(f"- Current velocity (x): {ovx:.3f} m/s")
        target_x = metrics.get("target_object_x")
        if target_x is not None:
            tx = _safe_float(target_x, default=float("nan"))
            if math.isfinite(tx):
                shortfall = tx - ox
                if shortfall > 0:
                    parts.append(f"- Shortfall to target x: {shortfall:.2f}m")
                else:
                    parts.append(f"- Target x reached or exceeded")

    # --- Actuator / pusher state ---
    if "pusher_x" in metrics:
        px = _safe_float(metrics.get("pusher_x"))
        parts.append(f"**Actuator State**: Position x={px:.2f}m")
        if "pusher_y" in metrics:
            py = _safe_float(metrics.get("pusher_y"))
            parts.append(f"- Vertical position y={py:.2f}m")
        if "pusher_angle" in metrics:
            pa = _safe_float(metrics.get("pusher_angle"))
            parts.append(f"- Chassis orientation (tilt): {pa:.3f} rad")
        if "max_pusher_tilt" in metrics:
            pmax = _safe_float(metrics.get("max_pusher_tilt"))
            parts.append(f"- Peak tilt observed: {pmax:.3f} rad")
        if "pusher_velocity_x" in metrics:
            pvx = _safe_float(metrics.get("pusher_velocity_x"))
            parts.append(f"- Velocity (x): {pvx:.3f} m/s")
        if "pusher_velocity_y" in metrics:
            pvy = _safe_float(metrics.get("pusher_velocity_y"))
            parts.append(f"- Velocity (y): {pvy:.3f} m/s")
        if metrics.get("pusher_tipped") is True:
            parts.append(f"- Stability: tilt exceeded threshold (failure)")

    # --- Displacement / progress (phase-aware) ---
    if "max_distance_pushed" in metrics:
        mdp = _safe_float(metrics.get("max_distance_pushed"))
        parts.append(f"**Displacement**: Best distance pushed: {mdp:.2f}m")
    if "progress" in metrics:
        prog = _safe_float(metrics.get("progress"), default=0.0)
        parts.append(f"- Distance progress: {prog:.1f}%")
    if "step_count" in metrics and "min_simulation_steps_required" in metrics:
        steps = metrics.get("step_count", 0)
        req = metrics.get("min_simulation_steps_required")
        if req is not None and isinstance(steps, (int, float)) and isinstance(req, (int, float)):
            req = int(req)
            steps = int(steps)
            parts.append(f"- Time phase: {steps} / {req} steps (motion duration requirement)")

    # --- Boundary / limit proximity (derived from metrics only; no raw values) ---
    boundary_parts = []
    if "object_x" in metrics and "target_object_x" in metrics:
        ox = _safe_float(metrics.get("object_x"))
        tx = _safe_float(metrics.get("target_object_x"), default=float("nan"))
        if math.isfinite(tx) and tx > 0:
            shortfall = tx - ox
            boundary_parts.append(f"target x shortfall: {shortfall:.2f}m")
    if "structure_mass" in metrics and "max_structure_mass" in metrics:
        mass = _safe_float(metrics.get("structure_mass"))
        max_m = _safe_float(metrics.get("max_structure_mass"), default=float("inf"))
        if max_m != float("inf") and max_m > 0:
            boundary_parts.append(f"mass margin to limit: {max_m - mass:.2f} kg")
    if boundary_parts:
        parts.append(f"**Boundary / limit proximity**: " + "; ".join(boundary_parts))

    # --- Structural profile (dynamic threshold from metrics) ---
    if "structure_mass" in metrics:
        mass = _safe_float(metrics.get("structure_mass"))
        max_m = metrics.get("max_structure_mass")
        if max_m is not None:
            max_m = _safe_float(max_m, default=float("inf"))
        else:
            max_m = float("inf")
        parts.append(f"**Structural Profile**: Mass {mass:.2f} kg")
        if max_m != float("inf") and max_m > 0:
            utilization = (mass / max_m) * 100
            parts.append(f"- Mass budget utilization: {utilization:.1f}%")
            parts.append(f"- Margin to mass limit: {max_m - mass:.2f} kg")

    # --- Outcome flags (no interpretation) ---
    if metrics.get("failed") and metrics.get("failure_reason"):
        parts.append(f"**Terminal State**: {metrics.get('failure_reason')}")

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
    Diagnostic, process-aware suggestions. No spoilers; no hardcoded env thresholds.
    Root-cause ordering: design constraint first, then runtime physics failures.
    Multi-objective: highlight trade-offs (e.g. good on one objective, fail on another).
    """
    suggestions = []

    # Early exit when evaluation could not run (no environment / no object)
    if metrics.get("error"):
        suggestions.append(
            "DIAGNOSTIC: Evaluation could not complete; the reported error indicates a setup or environment issue."
        )
        return suggestions

    reason_str = (failure_reason or "").lower()
    error_str = (error or "").lower()

    # Dynamic thresholds from metrics (stage-mutation safe; no hardcoded 18, 40, 12 s, etc.)
    max_mass = metrics.get("max_structure_mass")
    if max_mass is not None:
        max_mass = _safe_float(max_mass, default=float("inf"))
    else:
        max_mass = float("inf")
    structure_mass = _safe_float(metrics.get("structure_mass"), default=0.0)
    target_x_val = metrics.get("target_object_x")
    target_x = _safe_float(target_x_val, default=float("nan")) if target_x_val is not None else float("nan")
    object_x = _safe_float(metrics.get("object_x"), default=0.0)
    progress_pct = _safe_float(metrics.get("progress"), default=0.0)
    min_steps = metrics.get("min_simulation_steps_required")

    # --- Physics engine limits: numerical instability ---
    for key in (
        "object_x", "object_y", "pusher_x", "pusher_y", "pusher_angle",
        "distance_pushed", "structure_mass", "progress", "pusher_velocity_x", "object_velocity_x"
    ):
        if key not in metrics:
            continue
        try:
            f = float(metrics[key])
            if not math.isfinite(f):
                suggestions.append(
                    "DIAGNOSTIC: Numerical instability detected in simulation state (non-finite values). "
                    "Consider more conservative control or structure parameters."
                )
                break
        except (TypeError, ValueError):
            pass

    # --- Root-cause 1: Design constraint violated (checked first at step 0) ---
    if error_str or (failed and "design constraint" in reason_str):
        if "mass" in error_str or "mass" in reason_str:
            suggestions.append(
                "DIAGNOSTIC: The structure mass exceeds the allowed budget for this environment. "
                "The evaluator rejects the design before simulation."
            )
            suggestions.append(
                "ADVISORY: The strength-to-weight ratio of the assembly may be suboptimal; "
                "excessive mass can also limit the ability of the actuator to accelerate the system."
            )
        if "outside" in reason_str or "build zone" in reason_str:
            suggestions.append(
                "DIAGNOSTIC: At least one component was placed outside the permitted build zone. "
                "Design constraints are enforced at initialization."
            )
            suggestions.append(
                "ADVISORY: Verify that all body positions lie within the task's spatial bounds."
            )
        if suggestions:
            suggestions.append(
                "ROOT-CAUSE CHAIN: The failure reason above indicates the first limit exceeded; "
                "address this before other objectives."
            )
        return suggestions

    # --- Root-cause 2: Runtime physics failures (order by typical causal chain) ---
    if failed:
        if "tipped over" in reason_str or metrics.get("pusher_tipped") is True:
            suggestions.append(
                "DIAGNOSTIC: Loss of rotational equilibrium. The pusher chassis tilt exceeded "
                "the stability threshold for this environment."
            )
            suggestions.append(
                "ADVISORY: Consider how the center of mass and ground contact geometry affect "
                "resistance to overturning under forward thrust or contact forces."
            )
        elif "fell off" in reason_str:
            suggestions.append(
                "DIAGNOSTIC: The payload left the support surface (vertical constraint violated). "
                "The applied force or contact geometry led to loss of support."
            )
            suggestions.append(
                "ADVISORY: Consider the line of action of the pushing force relative to the "
                "payload's center of mass and base of support to maintain stable contact."
            )
        elif "wheel spinning" in reason_str:
            suggestions.append(
                "DIAGNOSTIC: Traction saturation—rotational motion at the wheels is not "
                "translating into sufficient forward motion of the vehicle."
            )
            suggestions.append(
                "ADVISORY: Consider the friction and normal force at the wheel–ground interface "
                "and how drive torque relates to linear acceleration in this environment."
            )
        elif "wheels suspended" in reason_str:
            suggestions.append(
                "DIAGNOSTIC: Drive components lost contact with the terrain (suspension or "
                "geometry failure)."
            )
            suggestions.append(
                "ADVISORY: Consider the kinematic layout and ground clearance so that driving "
                "elements remain in contact with the surface."
            )
        elif "not pushed effectively" in reason_str:
            suggestions.append(
                "DIAGNOSTIC: The actuator is moving but the payload is not being driven effectively— "
                "possible slip or poor force transmission at the contact."
            )
            suggestions.append(
                "ADVISORY: Consider contact geometry, friction, and alignment between pusher "
                "and payload to improve force transfer."
            )
        else:
            suggestions.append(
                "DIAGNOSTIC: The run terminated with a failure. The reported terminal state "
                "indicates the first physical limit exceeded; use it to identify the primary mechanism."
            )
        suggestions.append(
            "ROOT-CAUSE CHAIN: Address the failure mode indicated above before optimizing "
            "distance or time; stability and support constraints are checked before success."
        )

    # --- Multi-objective trade-off paradox ---
    if not success and not failed:
        distance_ok = math.isfinite(target_x) and object_x >= target_x
        if progress_pct >= 99.0 and not distance_ok:
            suggestions.append(
                "DIAGNOSTIC: Distance progress is high but the run ended before meeting the "
                "full target or time requirement. Check whether time or step limit was reached."
            )
        if min_steps is not None and isinstance(metrics.get("step_count"), (int, float)):
            steps_done = int(metrics.get("step_count", 0))
            req = int(min_steps)
            if steps_done < req and progress_pct > 0:
                suggestions.append(
                    "DIAGNOSTIC: Motion was achieved but the required sustained-motion duration "
                    "was not reached. The task requires both displacement and minimum time."
                )
        suggestions.append(
            "MULTI-OBJECTIVE: This run satisfied neither full distance nor full time; "
            "identify which constraint (target x or minimum steps) was missed and why."
        )

    # --- Paradox: good on one axis, fail on another ---
    if failed and progress_pct > 50.0:
        suggestions.append(
            "DIAGNOSTIC: Substantial displacement was achieved before failure. The primary "
            "failure mode (e.g. tip, payload loss, or traction) may be addressable without "
            "redesigning the entire propulsion strategy."
        )
    if failed and max_mass != float("inf") and structure_mass < max_mass:
        suggestions.append(
            "ADVISORY: Mass budget is satisfied; the failure is likely due to dynamics or "
            "stability rather than an overweight structure."
        )

    return suggestions
