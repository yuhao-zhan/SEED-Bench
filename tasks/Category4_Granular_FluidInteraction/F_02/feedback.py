"""
Task-specific feedback for Category 4: Granular/Fluid Interaction (F-02: The Amphibian).
Process-aware, diagnostic feedback. Uses only metrics from evaluator.evaluate(); no hallucination.
Dynamic thresholds from metrics (stage-mutation adaptable). No spoilers.
"""
from typing import Dict, Any, List
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
    """
    parts = []

    # --- 1. Design-phase violations (only when present) ---
    violations = metrics.get("constraint_violations")
    if isinstance(violations, list) and violations:
        parts.append("### 1. Design Constraint Violations (Build Phase)")
        for v in violations:
            parts.append(f"- {v}")
        return parts  # Early exit: no runtime metrics yet

    # --- 2. Structural design & constraints (dynamic limits) ---
    struct_parts = []
    mass = metrics.get("structure_mass")
    max_mass = metrics.get("max_structure_mass")
    if mass is not None:
        limit_str = f" / {max_mass:.2f} kg" if max_mass is not None else ""
        struct_parts.append(f"- Total Structure Mass: {mass:.2f} kg{limit_str}")
        if max_mass is not None and max_mass != float("inf"):
            margin = max_mass - mass
            struct_parts.append(f"- Mass Budget Margin: {margin:.2f} kg remaining" if margin >= 0 else f"- Mass Budget Overage: {-margin:.2f} kg")
    if "structure_broken" in metrics:
        struct_parts.append(
            f"- Structural Integrity: {'FAILED (Joints Sheared)' if metrics['structure_broken'] else 'NOMINAL (Intact)'}"
        )
    if "joint_count" in metrics:
        struct_parts.append(f"- Active Joint Count: {metrics['joint_count']}")
    if struct_parts:
        parts.append("### 1. Structural Design & Constraints")
        parts.extend(struct_parts)

    # --- 3. Task performance & propulsion (dynamic target) ---
    perf_parts = []
    if metrics.get("progress") is not None:
        perf_parts.append(f"- Completion Progress: {metrics['progress']:.1f}%")
    target_x = metrics.get("target_x")
    front_x = metrics.get("vehicle_front_x")
    if target_x is not None and front_x is not None:
        perf_parts.append(f"- Vehicle Front X: {front_x:.2f} m (Target: {target_x:.2f} m)")
        distance_to_target = target_x - front_x
        perf_parts.append(f"- Distance to Target: {distance_to_target:.2f} m")
    elif front_x is not None:
        perf_parts.append(f"- Vehicle Front X: {front_x:.2f} m")
    if "thrust_cooldown_steps" in metrics:
        perf_parts.append(f"- Propulsion Cooldown: {metrics['thrust_cooldown_steps']} steps")
    if perf_parts:
        parts.append("\n### 2. Task Performance & Propulsion")
        parts.extend(perf_parts)

    # --- 4. Physical process & kinematics (only what exists) ---
    kin_parts = []
    vx, vy = metrics.get("velocity_x"), metrics.get("velocity_y")
    if vx is not None or vy is not None:
        if _is_nonfinite(vx) or _is_nonfinite(vy):
            kin_parts.append("- Velocity State: Non-finite (numerical instability detected)")
        else:
            kin_parts.append(f"- Velocity State (front body): [{vx:.2f if vx is not None else 'N/A'}, {vy:.2f if vy is not None else 'N/A'}] m/s")
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
    failure_reason: str = None,
    error: str = None,
) -> List[str]:
    """
    Diagnostic warnings only. No spoilers: describe physical mechanism and trade-offs,
    never dictate concrete design or code. All thresholds from metrics (stage-adaptive).
    """
    suggestions = []
    reason = ((error or "") + " " + (failure_reason or "")).lower()

    # --- Physics engine / numerical instability (only if metrics show it) ---
    vx, vy = metrics.get("velocity_x"), metrics.get("velocity_y")
    if _is_nonfinite(vx) or _is_nonfinite(vy):
        suggestions.append(
            "Diagnostic: Numerical instability detected in velocity state. Consider whether extreme forces or rigid constraints are causing the solver to diverge."
        )

    # --- Design-phase violations (diagnostic only; no code hints) ---
    if "design constraint" in reason or error:
        violations = metrics.get("constraint_violations", [])
        if violations:
            if any("mass" in str(v).lower() for v in violations):
                suggestions.append(
                    "Diagnostic: Structural mass exceeded the permitted budget. Consider the strength-to-mass trade-off of your components."
                )
            if any("build zone" in str(v).lower() or "outside" in str(v).lower() for v in violations):
                suggestions.append(
                    "Diagnostic: At least one component was placed outside the permitted build zone. Ensure the entire structure lies within the stated geometric bounds at creation."
                )
        else:
            if "mass" in reason:
                suggestions.append(
                    "Diagnostic: Structural mass limit exceeded. Analyze component density and dimensions to meet the budget."
                )
            if "build zone" in reason:
                suggestions.append(
                    "Diagnostic: Geometric boundary violation. Ensure the structural layout remains within the permitted initial zone."
                )
        return suggestions

    if not failed:
        return suggestions

    # --- Multi-objective trade-off paradox ---
    max_mass = metrics.get("max_structure_mass")
    mass = metrics.get("structure_mass")
    progress = metrics.get("progress")
    structure_broken = metrics.get("structure_broken", False)

    if mass is not None and max_mass is not None and mass > max_mass and (progress is None or progress > 50):
        suggestions.append(
            "Diagnostic: Mass budget was exceeded while the vehicle made significant progress. One objective (reach) may be achievable at the cost of another (mass); consider rebalancing."
        )
    if structure_broken and progress is not None and progress > 70:
        suggestions.append(
            "Diagnostic: Structure failed late in the crossing. High progress with joint failure suggests environmental loads (current, vortices, or impact) exceeded connection strength rather than initial design limits."
        )

    # --- Root-cause chain (physical mechanism, not solution) ---
    if structure_broken:
        suggestions.append(
            "Diagnostic: Structural integrity was lost—one or more joints sheared. Infer whether the cause was sustained dead-load, dynamic impact, or asymmetric loading from the environment."
        )
    if "sank" in reason:
        suggestions.append(
            "Diagnostic: Vertical equilibrium was lost; the lowest point dropped below the survival threshold. Consider whether buoyancy, propulsion distribution, or external downward forces dominated."
        )
    if "reach" in reason or ("progress" in reason and (progress is None or progress < 100)):
        suggestions.append(
            "Diagnostic: Net forward progress was insufficient. Consider whether propulsion was overcome by resistance, cooldown limited thrust availability, or the vehicle was disabled in a dead zone."
        )

    # --- Combined failure: order possible causes without spoiling ---
    if structure_broken and "sank" in reason and len(suggestions) >= 2:
        # Avoid duplicate phrasing; already added both. Optionally add one chain hint.
        pass  # Root-cause messages above already cover both; no need to say "joints broke then sank" explicitly unless we want one line
    elif structure_broken and "reach" in reason:
        suggestions.append(
            "Diagnostic: Both structure failure and incomplete reach occurred. Determine which happened first from the failure reason text; that primary cause may have led to the other."
        )

    return suggestions
