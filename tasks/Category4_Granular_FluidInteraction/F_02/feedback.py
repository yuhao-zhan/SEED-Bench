"""
Task-specific feedback for Category 4: Granular/Fluid Interaction (F-02: The Amphibian).
Process-aware, diagnostic feedback. Uses only metrics from evaluator.evaluate(); no hallucination.
Dynamic thresholds from metrics (stage-mutation adaptable). No spoilers.
"""
from typing import Dict, Any, List, Optional
import math


def _is_nonfinite(x: Any) -> bool:
    """True if x is a number and is NaN or infinite."""
    if x is None:
        return False
    try:
        return not math.isfinite(float(x))
    except (TypeError, ValueError):
        return False


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Expose high-resolution physical metrics from the evaluator metrics dict only.
    No suggestions; baseline reporting. All thresholds derived from metrics (stage-adaptive).
    Phase-specific segregation: design phase vs. runtime structural / task / kinematics.
    """
    parts: List[str] = []

    # --- Phase 1: Design-phase violations (only when present; no runtime metrics yet) ---
    violations = metrics.get("constraint_violations")
    if isinstance(violations, list) and violations:
        parts.append("### 1. Design Constraint Violations (Build Phase)")
        for v in violations:
            parts.append(f"- {v}")
        return parts

    # --- Phase 2: Structural design & constraints (dynamic limits from metrics) ---
    struct_parts: List[str] = []
    mass = metrics.get("structure_mass")
    max_mass = metrics.get("max_structure_mass")  # stage-adaptive; never hardcode
    if mass is not None:
        limit_str = f" / {max_mass:.2f} kg" if max_mass is not None else ""
        struct_parts.append(f"- Total Structure Mass: {mass:.2f} kg{limit_str}")
        if max_mass is not None and max_mass != float("inf"):
            margin = max_mass - mass
            struct_parts.append(
                f"- Mass Budget Margin: {margin:.2f} kg remaining"
                if margin >= 0
                else f"- Mass Budget Overage: {-margin:.2f} kg"
            )
    if "structure_broken" in metrics:
        struct_parts.append(
            f"- Structural Integrity: {'FAILED (Joints Sheared)' if metrics['structure_broken'] else 'NOMINAL (Intact)'}"
        )
    joint_count = metrics.get("joint_count")
    if joint_count is not None:
        struct_parts.append(f"- Joint Count (current): {joint_count}")
    if struct_parts:
        parts.append("### 1. Structural Design & Constraints")
        parts.extend(struct_parts)

    # --- Phase 3: Task performance & propulsion (dynamic target from metrics) ---
    perf_parts: List[str] = []
    step_count = metrics.get("step_count")
    if step_count is not None:
        perf_parts.append(f"- Steps Elapsed: {step_count}")
    progress = metrics.get("progress")
    if progress is not None:
        perf_parts.append(f"- Completion Progress: {progress:.1f}%")
    target_x = metrics.get("target_x")
    front_x = metrics.get("vehicle_front_x")
    if target_x is not None and front_x is not None:
        perf_parts.append(f"- Vehicle Front X: {front_x:.2f} m (Target: {target_x:.2f} m)")
        distance_to_target = target_x - front_x
        perf_parts.append(f"- Distance to Target: {distance_to_target:.2f} m")
    elif front_x is not None:
        perf_parts.append(f"- Vehicle Front X: {front_x:.2f} m")
    thrust_cooldown = metrics.get("thrust_cooldown_steps")
    if thrust_cooldown is not None:
        perf_parts.append(f"- Propulsion Cooldown: {thrust_cooldown} steps")
    if perf_parts:
        parts.append("\n### 2. Task Performance & Propulsion")
        parts.extend(perf_parts)

    # --- Phase 4: Physical process & kinematics (only what exists) ---
    kin_parts: List[str] = []
    vx, vy = metrics.get("velocity_x"), metrics.get("velocity_y")
    if vx is not None or vy is not None:
        if _is_nonfinite(vx) or _is_nonfinite(vy):
            kin_parts.append("- Velocity State: Non-finite (numerical instability detected)")
        else:
            vx_str = f"{vx:.2f}" if vx is not None else "N/A"
            vy_str = f"{vy:.2f}" if vy is not None else "N/A"
            kin_parts.append(f"- Velocity State (front body): [{vx_str}, {vy_str}] m/s")
    lowest_y = metrics.get("vehicle_lowest_y")
    if lowest_y is not None:
        kin_parts.append(f"- Elevation (Lowest Point): {lowest_y:.2f} m")
    if kin_parts:
        parts.append("\n### 3. Physical Process & Kinematics")
        parts.extend(kin_parts)

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
    Diagnostic warnings only. No spoilers: describe physical mechanism and trade-offs,
    never dictate concrete design or code. All thresholds from metrics (stage-adaptive).
    Only conditions and metrics returned by the evaluator are used.
    """
    suggestions: List[str] = []
    reason = ((error or "") + " " + (failure_reason or "")).strip().lower()

    # --- Numerical instability (only if metrics show non-finite velocity) ---
    vx, vy = metrics.get("velocity_x"), metrics.get("velocity_y")
    if _is_nonfinite(vx) or _is_nonfinite(vy):
        suggestions.append(
            "Diagnostic: Numerical instability detected in velocity state. Consider whether extreme forces or rigid constraints are causing the solver to diverge."
        )

    # --- Design-phase violations (diagnostic only; no code hints) ---
    if "design constraint" in reason or (error and "constraint" in error.lower()):
        violations = metrics.get("constraint_violations", [])
        if violations:
            if any("mass" in str(v).lower() for v in violations):
                suggestions.append(
                    "Diagnostic: Structural mass exceeded the permitted budget. Consider the strength-to-mass trade-off of your components."
                )
            if any("build zone" in str(v).lower() or "outside" in str(v).lower() for v in violations):
                suggestions.append(
                    "Diagnostic: At least one component was placed outside the permitted build zone. Check that no part of the structure lies outside the stated geometric bounds at creation."
                )
        else:
            if "mass" in reason:
                suggestions.append(
                    "Diagnostic: Structural mass limit exceeded. Consider how total mass relates to the permitted budget."
                )
            if "build zone" in reason:
                suggestions.append(
                    "Diagnostic: Geometric boundary violation. The structural layout must remain within the permitted initial zone."
                )
        return suggestions

    if not failed:
        return suggestions

    progress = metrics.get("progress")
    structure_broken = metrics.get("structure_broken", False)
    lowest_y = metrics.get("vehicle_lowest_y")
    # No hardcoded thresholds: use only evaluator-returned metrics
    progress_meaningful = progress is not None and progress > 0
    sank = "sank" in reason or "lowest point" in reason
    reach_fail = "reach" in reason or "did not reach" in reason or "bank" in reason

    # --- Trade-off: progress vs. other objectives (only when evaluator shows both) ---
    if progress_meaningful and (sank or structure_broken):
        suggestions.append(
            "Diagnostic: Forward progress was achieved but failure occurred on another objective (buoyancy or structure). One objective may have been optimized at the expense of the other; consider rebalancing."
        )
    if lowest_y is not None and not _is_nonfinite(lowest_y) and progress_meaningful and sank:
        suggestions.append(
            "Diagnostic: Horizontal propulsion advanced the vehicle, but vertical equilibrium was lost. Consider whether buoyancy, weight distribution, or localized downward forces dominated in the failure zone."
        )

    # --- Root-cause (physical mechanism only; no design spoilers) ---
    if structure_broken:
        suggestions.append(
            "Diagnostic: Structural integrity was lost—one or more joints sheared. Infer whether the cause was sustained dead-load, dynamic impact, or asymmetric loading from the environment."
        )
    if sank:
        suggestions.append(
            "Diagnostic: Vertical equilibrium was lost; the lowest point dropped below the survival threshold. Consider whether buoyancy, propulsion distribution, or external downward forces dominated."
        )
    if reach_fail or not suggestions:
        suggestions.append(
            "Diagnostic: Net forward progress was insufficient. Consider whether propulsion was overcome by resistance, cooldown limited thrust availability, or the vehicle was disabled in a dead zone."
        )

    # --- Combined failure: root-cause ordering (diagnostic only) ---
    if structure_broken and sank and len(suggestions) >= 2:
        suggestions.append(
            "Diagnostic: Both structure failure and sinking occurred. Determine which happened first from the failure reason and kinematics; the primary cause may have led to the other."
        )
    elif structure_broken and reach_fail:
        suggestions.append(
            "Diagnostic: Both structure failure and incomplete reach occurred. Determine which happened first from the failure reason text; that primary cause may have led to the other."
        )

    return suggestions
