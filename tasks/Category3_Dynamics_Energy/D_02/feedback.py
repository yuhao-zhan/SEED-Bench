"""
D-02: The Jumper — process-aware diagnostic feedback.
Exposes only metrics provided by evaluator.evaluate(); no hallucination.
Diagnostic suggestions identify physical failure mechanisms without prescribing solutions.
All thresholds are read from metrics (stage-mutation adaptable).
Physics domain: Dynamics/Energy (projectile motion, impulse launch, trajectory clearance).
"""
from typing import Dict, Any, List, Optional
import math


def _is_nonfinite(x: Any) -> bool:
    """True if value is NaN or infinite (physics engine instability)."""
    if x is None:
        return False
    try:
        f = float(x)
        return not math.isfinite(f)
    except (TypeError, ValueError):
        return False


def _safe_float(val: Any, default: Optional[float] = None) -> Optional[float]:
    """Coerce to float if possible; return default on failure."""
    if val is None:
        return default
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Expose high-resolution physical metrics from evaluator output only.
    No suggestions; phase-segregated: outcome → state → progress/boundary → structure → failure.
    Boundary proximity and margins derived only from existing metric keys.
    """
    if not metrics:
        return []

    parts = []

    # --- Phase 1: Outcome (from metrics) ---
    if "success" in metrics:
        parts.append(f"**Outcome**: {'Success' if metrics['success'] else 'Failure'}")
    if "landed" in metrics:
        parts.append(f"**Landed on platform**: {'Yes' if metrics['landed'] else 'No'}")
    step_count = metrics.get("step_count")
    if step_count is not None:
        parts.append(f"**Simulation steps**: {step_count}")

    # --- Phase 2: Jumper kinematic state (position, velocity, orientation) ---
    px = _safe_float(metrics.get("jumper_x"))
    py = _safe_float(metrics.get("jumper_y"))
    if px is not None and py is not None:
        parts.append(f"**Final jumper position**: (x: {px:.2f} m, y: {py:.2f} m)")
    if "jumper_vx" in metrics and "jumper_vy" in metrics:
        vx, vy = metrics["jumper_vx"], metrics["jumper_vy"]
        parts.append(f"**Final velocity**: (vx: {vx:.2f}, vy: {vy:.2f}) m/s")
    if "jumper_speed" in metrics:
        parts.append(f"**Final speed**: {metrics['jumper_speed']:.2f} m/s")
    if "angle" in metrics:
        parts.append(f"**Orientation**: {metrics['angle']:.2f} rad")
    if "angular_velocity" in metrics:
        parts.append(f"**Angular velocity**: {metrics['angular_velocity']:.2f} rad/s")

    # --- Phase 3: Progress and boundary proximity (from existing metrics only) ---
    if "progress" in metrics:
        parts.append(f"**Horizontal progress toward target**: {metrics['progress']:.1f}%")
    if "distance_from_platform" in metrics:
        d = metrics["distance_from_platform"]
        parts.append(f"**Distance remaining to platform (x)**: {d:.2f} m")
    target_x = metrics.get("right_platform_start_x")
    if target_x is not None and px is not None:
        margin_x = px - target_x
        parts.append(f"**Target x threshold**: {target_x:.2f} m (jumper at x: {px:.2f} m; margin: {margin_x:+.2f} m)")

    # --- Vertical safety margins (stage-agnostic; from metrics) ---
    pit_fail_y = _safe_float(metrics.get("pit_fail_y"))
    landing_min_y = _safe_float(metrics.get("landing_min_y"))
    if pit_fail_y is not None and py is not None:
        margin_pit = py - pit_fail_y
        parts.append(f"**Margin above pit failure (y - pit_fail_y)**: {margin_pit:.2f} m")
    if landing_min_y is not None and py is not None and px is not None and target_x is not None:
        if px >= target_x:
            margin_land = py - landing_min_y
            parts.append(f"**Landing clearance (y - landing_min_y)**: {margin_land:.2f} m")

    # --- Phase 4: Structure (mass vs limit; dynamic threshold from metrics) ---
    if "structure_mass" in metrics:
        mass = metrics["structure_mass"]
        max_mass = metrics.get("max_structure_mass")
        if max_mass is not None:
            parts.append(f"**Structure mass**: {mass:.2f} kg / {max_mass:.2f} kg (budget)")
        else:
            parts.append(f"**Structure mass**: {mass:.2f} kg")

    # --- Phase 5: Failure reason (exactly as reported) ---
    if "failure_reason" in metrics and metrics["failure_reason"]:
        parts.append(f"**Reported failure**: {metrics['failure_reason']}")
    if "error" in metrics and metrics["error"]:
        parts.append(f"**Error**: {metrics['error']}")

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
    Diagnostic feedback: physical mechanism and root-cause hints.
    No spoilers: never prescribe concrete design or code.
    All thresholds from metrics (adapts to stage mutations in gravity, wind, slots, mass budget).
    """
    suggestions: List[str] = []
    msg = (error or failure_reason or "").lower()

    # --- Physics engine limits (numerical instability) ---
    scalar_keys = (
        "jumper_x", "jumper_y", "jumper_speed", "jumper_vx", "jumper_vy",
        "progress", "structure_mass", "angular_velocity", "angle",
        "distance_from_platform", "max_structure_mass", "pit_fail_y", "landing_min_y",
    )
    for key in scalar_keys:
        if key in metrics and _is_nonfinite(metrics[key]):
            suggestions.append(
                "- **Numerical instability**: A measured quantity is non-finite (NaN or infinite). "
                "The simulation may have become unstable; consider whether initial conditions or "
                "extreme parameters could cause singular behavior."
            )
            break

    # --- Dynamic thresholds (never hardcoded; from metrics / stage-mutated env) ---
    max_mass = _safe_float(metrics.get("max_structure_mass"))
    pit_fail_y = _safe_float(metrics.get("pit_fail_y"))
    landing_min_y = _safe_float(metrics.get("landing_min_y"))
    target_x = _safe_float(metrics.get("right_platform_start_x"))
    structure_mass = _safe_float(metrics.get("structure_mass"), 0.0) or 0.0
    step_count = metrics.get("step_count")
    px = _safe_float(metrics.get("jumper_x"), 0.0) or 0.0
    py = _safe_float(metrics.get("jumper_y"), 0.0) or 0.0

    # --- Root-cause ordering: design constraints are checked before simulation ---
    if failed and "design constraint" in msg:
        suggestions.append(
            "- **Root cause: build-time constraint**: Failure was triggered at build/design time "
            "(e.g. mass or build zone). Address these before trajectory or launch tuning."
        )

    # --- Design constraint: mass budget (threshold from metrics only) ---
    if max_mass is not None and max_mass > 0 and structure_mass >= max_mass:
        suggestions.append(
            "- **Design constraint violation**: The structure mass exceeds or meets the permitted budget "
            "(structure_mass vs max_structure_mass in metrics). The failure is at build time; "
            "reconcile the design with the allowed mass limit before trajectory tuning."
        )

    # --- Spatial constraint (build zone) ---
    if "build zone" in msg or "outside" in msg:
        suggestions.append(
            "- **Spatial constraint violation**: At least one structural component lies outside the "
            "designated build zone. The physical layout must respect the allowed construction region."
        )

    # --- Early termination: suggests design-time or immediate runtime failure ---
    if failed and step_count is not None and step_count <= 1 and "design constraint" not in msg:
        suggestions.append(
            "- **Early termination**: The simulation ended at the first evaluation step. This may "
            "indicate an immediate physical failure (e.g. pit or collision) or that the run was "
            "cut short before trajectory could develop; use the reported failure and state metrics "
            "to identify the first failing condition."
        )

    # --- Trajectory vs obstacle (slot/barrier) ---
    if "barrier" in msg or "slot" in msg or "red bar" in msg or "gap" in msg:
        suggestions.append(
            "- **Trajectory–obstacle conflict**: The flight path intersected a barrier or failed "
            "to pass through a required clearance. The trajectory must satisfy both horizontal "
            "range and vertical clearance through each obstacle slot; environmental changes can "
            "alter slot geometry and required apex."
        )

    # --- Vertical failure (pit) ---
    if (failed or not success) and pit_fail_y is not None and py < pit_fail_y:
        suggestions.append(
            "- **Vertical failure (pit)**: The jumper's altitude dropped below the pit safety "
            "threshold. Re-evaluate the vertical component of the launch and the effect of "
            "environmental forces (e.g. gravity, wind, damping) on time-of-flight and apex."
        )

    # --- Insufficient horizontal range ---
    if (failed or not success) and target_x is not None and px < target_x:
        suggestions.append(
            "- **Insufficient horizontal range**: The jumper did not reach the target platform's "
            "horizontal distance. Analyze the horizontal momentum and how environmental "
            "conditions (e.g. headwind, damping) may reduce effective range."
        )

    # --- Landing clearance (reached x but not minimum y) ---
    if (
        (failed or not success)
        and target_x is not None
        and landing_min_y is not None
        and px >= target_x
        and py < landing_min_y
    ):
        suggestions.append(
            "- **Landing clearance failure**: The jumper reached the target horizontal distance "
            "but did not meet the minimum height for a valid landing. Consider trajectory "
            "shape and touchdown conditions relative to the platform."
        )

    return suggestions
