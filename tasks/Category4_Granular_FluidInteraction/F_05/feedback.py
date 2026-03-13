"""
F-05: The Boat task feedback module.
Process-aware, diagnostic feedback for naval/fluid interaction.
Uses only metrics from evaluator.evaluate(); all thresholds are dynamic (stage-mutation safe).
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
    """
    lines = []

    # ---- Cargo retention (only if present) ----
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

    # ---- Vessel stability (only if present) ----
    boat_angle_deg = metrics.get("boat_angle_deg")
    boat_max_angle_deg = metrics.get("boat_max_angle_deg")
    angle_val = _safe_float(boat_angle_deg, 0.0)
    max_angle_val = _safe_float(boat_max_angle_deg, 18.0)

    lines.append(
        f"- **Vessel Roll State**: Peak angle {angle_val:.1f}° | "
        f"Limit {max_angle_val:.1f}° | "
        f"Stability margin {max_angle_val - abs(angle_val):.1f}°"
    )

    # ---- Structural integrity (only if present) ----
    structure_broken = metrics.get("structure_broken", False)
    joint_count = metrics.get("joint_count")
    lines.append(
        f"- **Structural Load State**: {'COMPROMISED' if structure_broken else 'INTACT'} "
        f"({joint_count if joint_count is not None else '—'} joints active)"
    )

    # ---- Mass and limits (dynamic from metrics) ----
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

    # ---- Build zone and hull position (only if present) ----
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

    # ---- Step count ----
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
    max_mass = _safe_float(metrics.get("max_structure_mass"), float("inf"))
    mass = _safe_float(metrics.get("structure_mass"), 0.0)
    angle = abs(_safe_float(metrics.get("boat_angle_deg"), 0.0))
    max_angle = _safe_float(metrics.get("boat_max_angle_deg"), 18.0)
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

    # ---- 4. Multi-objective trade-off ----
    if max_mass != float("inf") and mass > max_mass and not structure_broken:
        suggestions.append(
            "The design satisfies structural integrity but violates the mass budget. Improving stability "
            "with more mass can make the design inadmissible; the trade-off between stability and mass "
            "limit must be resolved within the allowed budget."
        )

    # ---- 5. Root-cause chain (multiple failures) ----
    failure_modes = sum([cargo_in_water > 0, structure_broken, (max_angle != float("inf") and angle > max_angle)])
    if failure_modes >= 2:
        suggestions.append(
            "Multiple failure modes are present. Identifying which constraint was exceeded first—cargo loss, "
            "capsize, or joint failure—helps prioritize which physical mechanism to address in the next design."
        )

    # ---- 6. Build zone / integration ----
    if any("outside build zone" in str(v) for v in constraint_violations):
        suggestions.append(
            "Some structural components lie outside the valid anchor zone. Assembly must respect the "
            "reported build zone so that connections attach to the vessel correctly."
        )

    # ---- 7. Numerical instability (only from impossible metrics) ----
    ratio = metrics.get("cargo_retained_ratio")
    if ratio is not None:
        r = _safe_float(ratio, -1.0)
        if r < 0 or r > 1 or math.isnan(r):
            suggestions.append(
                "Metrics show values outside the expected physical range. This may indicate numerical "
                "instability in the simulation; consider whether extreme impulses or geometry could trigger it."
            )
    boat_angle_raw = metrics.get("boat_angle_deg")
    if boat_angle_raw is not None:
        try:
            a = float(boat_angle_raw)
        except (TypeError, ValueError):
            a = 0.0
        if math.isnan(a) or abs(a) > 180:
            suggestions.append(
                "Vessel angle metrics are outside the normal range. Simulation state may be numerically unstable."
            )
    mass_raw = metrics.get("structure_mass")
    if mass_raw is not None:
        try:
            m_val = float(mass_raw)
        except (TypeError, ValueError):
            m_val = 0.0
        if math.isnan(m_val) or m_val < 0:
            suggestions.append(
                "Structure mass is invalid or negative. This may indicate a physics engine anomaly."
            )

    return suggestions
