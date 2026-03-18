"""
D-04: The Swing — process-aware diagnostic feedback (QA-audited).
- All strings, metrics, and constraints traced to evaluator.evaluate() return dict only.
- No hardcoded physical thresholds; stage parameters from metrics.get().
- Suggestions diagnose failure mechanism / stress; no design or API spoilers.
- Physics domain: Dynamics & Energy (pendulum pumping, energy injection, apex targeting).
"""
from typing import Dict, Any, List
import math


def _is_finite(x: Any) -> bool:
    """True if x is a finite number (no NaN, no inf)."""
    if x is None:
        return False
    try:
        f = float(x)
        return math.isfinite(f)
    except (TypeError, ValueError):
        return False


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Expose physical metrics from the evaluator only.
    Phase-segregated: Outcome → Numerical validity → Trajectory/apex state →
    Boundary proximity → Design constraints → Runtime.
    Every key used is present in evaluator._make_metrics() return.
    """
    parts = []

    # --- 1. Outcome (from metrics only) ---
    if "success" in metrics:
        parts.append(f"**Objective Success**: {'Yes' if metrics['success'] else 'No'}")
    if metrics.get("failed"):
        parts.append("**Run Outcome**: Time/step limit reached without success.")
    if metrics.get("failure_reason"):
        parts.append(f"**Failure Reason (summary)**: {metrics['failure_reason'][:200]}")

    # --- 2. Numerical validity (only observation: non-finite returned values) ---
    key_numeric = [
        "seat_x", "seat_y", "seat_vx", "seat_vy", "seat_speed",
        "max_seat_y_reached", "progress_pct", "height_gap_to_target",
        "distance_to_target_x", "swing_angle_deg",
        "structure_mass", "max_structure_mass", "step_count",
    ]
    non_finite_keys = [k for k in key_numeric if k in metrics and not _is_finite(metrics.get(k))]
    if non_finite_keys:
        parts.append(
            "**Numerical State**: One or more returned metrics are non-finite (NaN or infinite): "
            f"{', '.join(non_finite_keys)}; results may be invalid."
        )

    # --- 3. Trajectory / phase-specific state (only if present and finite) ---
    if "max_seat_y_reached" in metrics and _is_finite(metrics["max_seat_y_reached"]):
        parts.append(f"**Peak Altitude Achieved**: {metrics['max_seat_y_reached']:.2f} m")
    if "progress_pct" in metrics and _is_finite(metrics["progress_pct"]):
        parts.append(f"**Height Progress (toward target)**: {metrics['progress_pct']:.1f}%")
    if "apex_reached" in metrics:
        parts.append(f"**Apex State Detected**: {'Yes' if metrics['apex_reached'] else 'No'}")
    if "touched_target" in metrics:
        parts.append(f"**Target Zone Reached**: {'Yes' if metrics['touched_target'] else 'No'}")

    if all(k in metrics and _is_finite(metrics.get(k)) for k in ("seat_x", "seat_y")):
        parts.append(
            f"**Final Seat Position**: (x: {metrics['seat_x']:.2f} m, y: {metrics['seat_y']:.2f} m)"
        )
    if all(k in metrics and _is_finite(metrics.get(k)) for k in ("seat_vx", "seat_vy")):
        parts.append(
            f"**Final Seat Velocity**: (vx: {metrics['seat_vx']:.2f}, vy: {metrics['seat_vy']:.2f}) m/s"
        )
    if "seat_speed" in metrics and _is_finite(metrics["seat_speed"]):
        parts.append(f"**Final Speed**: {metrics['seat_speed']:.2f} m/s")
    if "swing_angle_deg" in metrics and _is_finite(metrics.get("swing_angle_deg")):
        parts.append(f"**Swing Amplitude (final)**: {metrics['swing_angle_deg']:.1f}°")

    # --- 4. Boundary proximity (all from metrics; dynamic per stage) ---
    target_y = metrics.get("target_y_min")
    if _is_finite(target_y) and "height_gap_to_target" in metrics and _is_finite(
        metrics["height_gap_to_target"]
    ):
        gap = metrics["height_gap_to_target"]
        parts.append(f"**Vertical Gap to Target**: {gap:.2f} m (target y ≥ {target_y:.1f} m)")
    if "distance_to_target_x" in metrics and _is_finite(metrics.get("distance_to_target_x")):
        dx = metrics["distance_to_target_x"]
        if dx > 0:
            parts.append(f"**Lateral Offset from Target Zone**: {dx:.2f} m")
    target_x_min = metrics.get("target_x_min")
    target_x_max = metrics.get("target_x_max")
    if _is_finite(target_x_min) and _is_finite(target_x_max):
        parts.append(f"**Target Zone (x)**: [{target_x_min:.2f}, {target_x_max:.2f}] m")

    # --- 5. Design constraints (from metrics only; stage-mutation adaptable) ---
    mass = metrics.get("structure_mass")
    max_mass = metrics.get("max_structure_mass")
    if _is_finite(mass):
        if _is_finite(max_mass) and max_mass > 0:
            parts.append(f"**Structure Mass**: {mass:.2f} kg / {max_mass:.1f} kg")
        else:
            parts.append(f"**Structure Mass**: {mass:.2f} kg")

    # --- 6. Runtime ---
    if "step_count" in metrics and _is_finite(metrics.get("step_count")):
        parts.append(f"**Steps Used**: {metrics['step_count']}")

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
    Diagnostic feedback only: physical mechanism of failure, no solution spoilers.
    All conditions and thresholds derived from metrics (evaluator return); no hardcoded limits.
    Suggestions describe stress/failure mode, not specific designs or API usage.
    """
    suggestions = []
    msg = (error or failure_reason or "").lower()

    # --- Non-finite returned metrics (evaluator returns these keys) ---
    key_numeric = [
        "seat_x", "seat_y", "seat_vx", "seat_vy", "seat_speed",
        "max_seat_y_reached", "progress_pct",
    ]
    if any(k in metrics and not _is_finite(metrics.get(k)) for k in key_numeric):
        suggestions.append(
            "- **Non-finite Metrics**: One or more returned metrics are non-finite. "
            "This indicates the physics state or integration produced invalid values; "
            "the failure mode is in the dynamics or control regime, not in the reported numbers."
        )

    # --- Root cause: design constraint violated (evaluator returns early with failure_reason) ---
    design_violated = "design constraint" in msg or "constraint violated" in msg
    if design_violated:
        if "mass" in msg:
            suggestions.append(
                "- **Root Cause (Design — Mass)**: The structure exceeded the allowed mass budget "
                "before trajectory was evaluated. The failure is structural (mass constraint "
                "violation), not control or trajectory."
            )
        if "build zone" in msg or "outside" in msg:
            suggestions.append(
                "- **Root Cause (Design — Spatial)**: At least one component was placed outside "
                "the allowed build region before trajectory was evaluated. The failure is "
                "geometric (placement outside bounds), not dynamics."
            )

    # --- Trajectory / control failure (only when design was satisfied) ---
    if (failed or not success) and not design_violated:
        target_y = metrics.get("target_y_min")
        max_y = metrics.get("max_seat_y_reached")
        apex_reached = metrics.get("apex_reached", False)
        dist_x = metrics.get("distance_to_target_x")
        touched = metrics.get("touched_target", False)
        mass = metrics.get("structure_mass")
        max_mass = metrics.get("max_structure_mass")
        added_trajectory_suggestion = False

        if _is_finite(target_y) and target_y > 0:
            if _is_finite(max_y) and max_y < target_y:
                suggestions.append(
                    "- **Energy Deficit**: The swing did not reach the required altitude. "
                    "Consider the timing and magnitude of energy injection relative to the "
                    "pendulum phase and any dissipative effects."
                )
                added_trajectory_suggestion = True
            if _is_finite(max_y) and max_y >= target_y and not apex_reached:
                suggestions.append(
                    "- **Apex Timing**: Target height was reached at least once, but the seat was "
                    "not at rest there. Success requires the target zone to be reached at a "
                    "trajectory apex; review the phase and location of energy transfer."
                )
                added_trajectory_suggestion = True
            if _is_finite(dist_x) and dist_x > 0 and not touched:
                suggestions.append(
                    "- **Lateral Alignment**: The trajectory did not center the apex within the "
                    "target zone horizontally. Consider how pumping direction and timing affect "
                    "where the swing reaches its peak."
                )
                added_trajectory_suggestion = True

        design_ok = (
            _is_finite(mass) and _is_finite(max_mass) and max_mass > 0 and mass <= max_mass
        )
        if (
            not added_trajectory_suggestion
            and design_ok
            and not touched
            and (failed or not success)
        ):
            suggestions.append(
                "- **Trajectory/Control Failure**: Design constraints were satisfied but the "
                "trajectory did not meet success criteria. The failure is in dynamics or control "
                "(energy, apex timing, or lateral alignment), not in the structure."
            )

    return suggestions
