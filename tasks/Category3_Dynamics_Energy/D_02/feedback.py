"""
D-02: The Jumper — process-aware diagnostic feedback.
Exposes only metrics provided by evaluator.evaluate(); no hallucination.
Diagnostic suggestions identify physical failure mechanisms without prescribing solutions.
All thresholds are read from metrics (stage-mutation adaptable).
"""
from typing import Dict, Any, List
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


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Expose high-resolution physical metrics from evaluator output only.
    No suggestions; phase-segregated and boundary-proximity derived from existing keys.
    """
    if not metrics:
        return []

    parts = []

    # --- Outcome (from metrics) ---
    if "success" in metrics:
        parts.append(f"**Outcome**: {'Success' if metrics['success'] else 'Failure'}")
    if "landed" in metrics:
        parts.append(f"**Landed on platform**: {'Yes' if metrics['landed'] else 'No'}")
    if "step_count" in metrics:
        parts.append(f"**Simulation steps**: {metrics['step_count']}")

    # --- Jumper state (position, velocity, orientation) ---
    if "jumper_x" in metrics and "jumper_y" in metrics:
        px = metrics["jumper_x"]
        py = metrics["jumper_y"]
        parts.append(f"**Final jumper position**: (x: {px:.2f} m, y: {py:.2f} m)")
    if "jumper_vx" in metrics and "jumper_vy" in metrics:
        parts.append(f"**Final velocity**: (vx: {metrics['jumper_vx']:.2f}, vy: {metrics['jumper_vy']:.2f}) m/s")
    if "jumper_speed" in metrics:
        parts.append(f"**Final speed**: {metrics['jumper_speed']:.2f} m/s")
    if "angle" in metrics:
        parts.append(f"**Orientation**: {metrics['angle']:.2f} rad")
    if "angular_velocity" in metrics:
        parts.append(f"**Angular velocity**: {metrics['angular_velocity']:.2f} rad/s")

    # --- Progress and boundary proximity (derived from existing metrics) ---
    if "progress" in metrics:
        parts.append(f"**Horizontal progress toward target**: {metrics['progress']:.1f}%")
    if "distance_from_platform" in metrics:
        d = metrics["distance_from_platform"]
        parts.append(f"**Distance remaining to platform (x)**: {d:.2f} m")
    if "right_platform_start_x" in metrics and "jumper_x" in metrics:
        target_x = metrics["right_platform_start_x"]
        px = metrics["jumper_x"]
        margin_x = px - target_x
        parts.append(f"**Target x threshold**: {target_x:.2f} m (jumper at x: {px:.2f} m)")

    # --- Vertical safety margins (from metrics; stage-agnostic) ---
    pit_fail_y = metrics.get("pit_fail_y")
    landing_min_y = metrics.get("landing_min_y")
    if pit_fail_y is not None and "jumper_y" in metrics:
        py = metrics["jumper_y"]
        margin_pit = py - pit_fail_y
        parts.append(f"**Margin above pit failure (y - pit_fail_y)**: {margin_pit:.2f} m")
    if landing_min_y is not None and "jumper_y" in metrics and "jumper_x" in metrics:
        px, py = metrics["jumper_x"], metrics["jumper_y"]
        target_x = metrics.get("right_platform_start_x")
        if target_x is not None and px >= target_x:
            margin_land = py - landing_min_y
            parts.append(f"**Landing clearance (y - landing_min_y)**: {margin_land:.2f} m")

    # --- Structure (mass vs limit; dynamic threshold) ---
    if "structure_mass" in metrics:
        mass = metrics["structure_mass"]
        max_mass = metrics.get("max_structure_mass")
        if max_mass is not None:
            parts.append(f"**Structure mass**: {mass:.2f} kg / {max_mass:.2f} kg (budget)")
        else:
            parts.append(f"**Structure mass**: {mass:.2f} kg")

    # --- Failure reason (exactly as reported) ---
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
    failure_reason: str = None,
    error: str = None,
) -> List[str]:
    """
    Diagnostic feedback: physical mechanism and root-cause hints.
    No spoilers: never prescribe concrete design or code.
    All thresholds from metrics (adapts to stage mutations).
    """
    suggestions = []
    msg = (error or failure_reason or "").lower()

    # --- Physics engine limits (numerical instability) ---
    for key in ("jumper_x", "jumper_y", "jumper_speed", "jumper_vx", "jumper_vy",
                "progress", "structure_mass", "angular_velocity", "angle"):
        if key in metrics and _is_nonfinite(metrics[key]):
            suggestions.append(
                "- **Numerical instability**: A measured quantity is non-finite (NaN or infinite). "
                "The simulation may have become unstable; consider whether initial conditions or "
                "extreme parameters could cause singular behavior."
            )
            break

    # --- Dynamic thresholds (never hardcoded) ---
    max_mass = metrics.get("max_structure_mass")
    pit_fail_y = metrics.get("pit_fail_y")
    landing_min_y = metrics.get("landing_min_y")
    target_x = metrics.get("right_platform_start_x")

    # --- Multi-objective trade-off: design constraint vs trajectory performance ---
    structure_mass = metrics.get("structure_mass", 0.0)
    if max_mass is not None and max_mass > 0 and structure_mass > max_mass:
        progress = metrics.get("progress", 0.0)
        if progress > 50.0:
            suggestions.append(
                "- **Multi-objective conflict**: Trajectory achieved substantial horizontal progress "
                "but the design violated a structural constraint (mass budget). Consider how to "
                "satisfy the constraint without sacrificing the launch mechanism’s effectiveness."
            )
        else:
            suggestions.append(
                "- **Design constraint violation**: The structure exceeds the permitted mass budget. "
                "Consider optimizing the strength-to-weight ratio of the launch system."
            )

    if "build zone" in msg or "outside" in msg:
        suggestions.append(
            "- **Spatial constraint violation**: At least one structural component lies outside the "
            "designated build zone. The physical layout must respect the allowed construction region."
        )

    # --- Root-cause chain (diagnostic only; no solution prescription) ---
    if failed or not success:
        px = metrics.get("jumper_x", 0.0)
        py = metrics.get("jumper_y", 0.0)

        if pit_fail_y is not None and py < pit_fail_y:
            suggestions.append(
                "- **Vertical failure (pit)**: The jumper’s altitude dropped below the pit safety "
                "threshold. Re-evaluate the vertical component of the launch and the effect of "
                "environmental forces on time-of-flight and apex."
            )

        if target_x is not None and px < target_x:
            suggestions.append(
                "- **Insufficient horizontal range**: The jumper did not reach the target platform’s "
                "horizontal distance. Analyze the horizontal momentum and how environmental "
                "conditions may reduce effective range."
            )

        if (target_x is not None and landing_min_y is not None and
                px >= target_x and py < landing_min_y and not success):
            suggestions.append(
                "- **Landing clearance failure**: The jumper reached the target horizontal distance "
                "but did not meet the minimum height for a valid landing. Consider trajectory "
                "shape and touchdown conditions."
            )

    if "barrier" in msg or "slot" in msg or "red bar" in msg:
        suggestions.append(
            "- **Trajectory–obstacle conflict**: The flight path intersected a barrier or failed "
            "to pass through a required clearance. The trajectory must satisfy both horizontal "
            "range and vertical clearance through each obstacle slot."
        )

    if "design constraint" in msg:
        suggestions.append(
            "- **Root cause: build-time constraint**: Failure was triggered at build/design time "
            "(e.g. mass or build zone). Address these before trajectory tuning."
        )

    return suggestions
