"""
F-05: The Boat task feedback module.
Process-aware, diagnostic feedback for naval/fluid interaction.
Uses only metrics from evaluator.evaluate(); all thresholds are dynamic (stage-mutation safe).
No spoilers: diagnoses physical mechanism and root-cause, never prescribes code or explicit solutions.
"""

import math
from typing import Dict, Any, List


def _safe_float(x: Any, default: float = 0.0) -> float:
    """Return float(x) if x is a valid number, else default. Handles None and NaN."""
    if x is None:
        return default
    try:
        v = float(x)
        return default if math.isnan(v) else v
    except (TypeError, ValueError):
        return default


def _safe_float_or_none(x: Any) -> float | None:
    """Return float(x) if valid, else None. For optional metrics (e.g. boat_max_angle_deg)."""
    if x is None:
        return None
    try:
        v = float(x)
        return None if math.isnan(v) else v
    except (TypeError, ValueError):
        return None


def format_feedback(metrics: Dict[str, Any], score: float, success: bool, failed: bool,
                    failure_reason: str, iteration: int, error: str = None,
                    task_name: str = "F_05") -> str:
    """
    Format a diagnostic feedback report from ground-truth metrics only.
    """
    if error:
        return f"### Iteration {iteration} - Critical Execution Error\n\n**Error**: {error}"

    feedback = f"### Iteration {iteration} - Result: {'SUCCESS' if success else 'FAILURE'}\n"
    feedback += f"**Overall Score**: {score:.2f}/100\n"
    if failure_reason:
        feedback += f"**Failure Reason**: {failure_reason}\n"

    feedback += "\n#### Physical State Analysis\n"
    feedback += format_task_metrics(metrics)

    feedback += "\n#### Structural & Hydrodynamic Diagnostics\n"
    for s in get_improvement_suggestions(metrics, success):
        feedback += f"- {s}\n"

    return feedback


def format_task_metrics(metrics: Dict[str, Any]) -> str:
    """
    Expose high-resolution physical metrics from the evaluator only.
    No invented metrics. All thresholds and limits come from metrics (stage-agnostic).
    Grouped by domain: Cargo/Fluid, Stability, Structure, Mass & Limits, Geometry.
    """
    lines: List[str] = []

    # ---- 1. Cargo / fluid retention (only if present) ----
    initial = metrics.get("initial_cargo_count")
    lost = metrics.get("cargo_in_water", 0)
    retained = metrics.get("cargo_retained")
    ratio = metrics.get("cargo_retained_ratio")
    cargo_water_y = metrics.get("cargo_water_y")

    if initial is not None:
        ratio_val = _safe_float(ratio, 0.0)
        lines.append(
            f"- **Cargo Security Index**: {retained if retained is not None else (initial - lost)}/{initial} particles "
            f"({ratio_val * 100:.1f}%)"
        )
    if cargo_water_y is not None:
        lines.append(f"- **Cargo-in-Water Threshold**: Particles below y = {cargo_water_y:.2f} m are counted as lost.")

    # ---- 2. Vessel stability (only if present; limit from metrics) ----
    boat_angle_deg = metrics.get("boat_angle_deg")
    boat_max_angle_deg = metrics.get("boat_max_angle_deg")
    if boat_angle_deg is not None or boat_max_angle_deg is not None:
        angle_val = _safe_float(boat_angle_deg, 0.0)
        max_angle_val = _safe_float_or_none(boat_max_angle_deg)
        if max_angle_val is not None:
            margin = max_angle_val - abs(angle_val)
            lines.append(
                f"- **Vessel Roll State**: Peak angle {angle_val:.1f}° | "
                f"Limit {max_angle_val:.1f}° | "
                f"Stability margin {margin:.1f}°"
            )
        else:
            lines.append(f"- **Vessel Roll State**: Peak angle {angle_val:.1f}°")

    # ---- 3. Structural integrity (only if present) ----
    structure_broken = metrics.get("structure_broken", False)
    joint_count = metrics.get("joint_count")
    lines.append(
        f"- **Structural Load State**: {'COMPROMISED' if structure_broken else 'INTACT'} "
        f"({joint_count if joint_count is not None else '—'} joints active)"
    )

    # ---- 4. Mass and limits (dynamic from metrics only) ----
    structure_mass = metrics.get("structure_mass")
    max_structure_mass = metrics.get("max_structure_mass")
    mass_val = _safe_float(structure_mass, 0.0)
    max_mass_val = _safe_float(max_structure_mass, float("inf"))
    if max_mass_val == float("inf"):
        lines.append(f"- **Displacement Mass**: {mass_val:.2f} kg (no explicit limit in metrics)")
    else:
        headroom = max_mass_val - mass_val
        lines.append(
            f"- **Displacement Mass**: {mass_val:.2f} kg / {max_mass_val:.2f} kg limit | "
            f"Mass headroom {headroom:.2f} kg"
        )

    # ---- 5. Build zone and hull position (only if present) ----
    bx_min = metrics.get("build_zone_x_min")
    bx_max = metrics.get("build_zone_x_max")
    by_min = metrics.get("build_zone_y_min")
    by_max = metrics.get("build_zone_y_max")
    if bx_min is not None and bx_max is not None and by_min is not None and by_max is not None:
        lines.append(
            f"- **Build Zone (anchor validity)**: x ∈ [{bx_min:.1f}, {bx_max:.1f}], y ∈ [{by_min:.1f}, {by_max:.1f}]"
        )

    boat_x = metrics.get("boat_x")
    boat_y = metrics.get("boat_y")
    if boat_x is not None and boat_y is not None:
        lines.append(f"- **Hull Position**: (x: {boat_x:.2f}, y: {boat_y:.2f})")

    # ---- 6. Design constraint violations (exactly as reported by evaluator) ----
    constraint_violations = metrics.get("constraint_violations") or []
    if constraint_violations:
        lines.append("- **Design Constraint Violations (ground truth)**:")
        for v in constraint_violations:
            lines.append(f"  - {v}")

    # ---- 7. Step count ----
    step_count = metrics.get("step_count")
    if step_count is not None:
        lines.append(f"- **Simulation Steps**: {step_count}")

    return "\n".join(lines) if lines else "(No metrics available)"


def get_improvement_suggestions(metrics: Dict[str, Any], success: bool) -> List[str]:
    """
    Diagnostic suggestions from physical state only. No spoilers: no code or explicit solutions.
    All thresholds read from metrics (dynamic for mutated stages).
    """
    if success:
        return ["Structural design and mass distribution are consistent with the current environmental constraints."]

    suggestions: List[str] = []
    angle = abs(_safe_float(metrics.get("boat_angle_deg"), 0.0))
    max_angle = _safe_float(metrics.get("boat_max_angle_deg"), float("inf"))
    cargo_in_water = metrics.get("cargo_in_water", 0) or 0
    structure_broken = metrics.get("structure_broken", False)
    constraint_violations = metrics.get("constraint_violations") or []

    # ---- 1. Cargo retention (fluid/granular) ----
    if cargo_in_water > 0:
        suggestions.append(
            "Cargo particles have left the vessel. Kinetic energy transfer from vessel motion is exceeding "
            "the retention capacity of the current containment; the physical mechanism is loss of constraint "
            "before particles are fully retained."
        )

    # ---- 2. Stability / capsize (dynamics) ----
    if max_angle != float("inf") and angle > max_angle:
        suggestions.append(
            "The vessel has exceeded the safe roll limit. This indicates a mismatch between restoring moments "
            "and the combined center of mass and buoyancy. The structure may be contributing to unstable "
            "rotational coupling under wave and lateral loading."
        )

    # ---- 3. Structural failure (joint load tolerance) ----
    if structure_broken:
        suggestions.append(
            "Structural integrity was lost: one or more joints failed. Load at anchor points has exceeded "
            "the environment's structural capacity. The relationship between mass distribution, number of "
            "anchor points, and peak reaction forces determines which constraint is exceeded first."
        )

    # ---- 4. Root-cause chain (multiple failures) ----
    has_constraint_violations = bool(constraint_violations)
    failure_modes = sum([
        cargo_in_water > 0,
        structure_broken,
        (max_angle != float("inf") and angle > max_angle),
        has_constraint_violations,
    ])
    if failure_modes >= 2:
        suggestions.append(
            "Multiple failure modes are present. Identifying which constraint was exceeded first—cargo loss, "
            "capsize, joint failure, mass budget, or build zone—helps prioritize which physical mechanism "
            "to address in the next design. Joint failure may precede or follow cargo loss depending on load path."
        )

    # ---- 5. Build zone / integration ----
    if any("outside build zone" in str(v) for v in constraint_violations):
        suggestions.append(
            "Some structural components lie outside the valid anchor zone. Assembly must respect the "
            "reported build zone so that connections attach to the vessel correctly."
        )

    # ---- 6. Mass budget (design constraint; from evaluator-reported violations only) ----
    if "mass" in str(constraint_violations).lower():
        suggestions.append(
            "Total structure mass exceeds the environment's budget. The strength-to-weight ratio of the "
            "design determines whether the same function can be achieved within the mass limit."
        )

    return suggestions
