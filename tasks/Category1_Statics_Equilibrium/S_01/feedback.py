"""
Task-specific feedback generation for S-01: The Bridge.
Process-aware, diagnostic feedback derived only from evaluator.evaluate() metrics.
No spoilers: diagnoses physical mechanism, never dictates solution or implementation.
Dynamic thresholds: all limits from metrics (stage-mutation safe).
"""
from typing import Dict, Any, List, Optional
import math


def _is_finite(x: Any) -> bool:
    """True if value is numeric and finite (no NaN/inf)."""
    if x is None:
        return True
    try:
        f = float(x)
        return math.isfinite(f)
    except (TypeError, ValueError):
        return True


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Format high-resolution physical metrics for S-01: The Bridge.
    Exposes only what evaluator.evaluate() returns; no hallucinated variables.
    Phase-specific segregation, boundary margins, and numerical sanity only from metrics.
    """
    metric_parts: List[str] = []

    # --- Physics engine sanity (non-finite values in evaluator-returned metrics) ---
    vx = metrics.get("vehicle_x")
    vy = metrics.get("vehicle_y")
    if vx is not None and not _is_finite(vx):
        metric_parts.append("**Numerical state**: vehicle_x is non-finite.")
    if vy is not None and not _is_finite(vy):
        metric_parts.append("**Numerical state**: vehicle_y is non-finite.")
    for key in ("velocity_x", "velocity_y", "angular_velocity", "max_vertical_accel", "structure_mass"):
        val = metrics.get(key)
        if val is not None and not _is_finite(val):
            metric_parts.append(f"**Numerical state**: {key} is non-finite.")

    # --- Phase-specific segregation (only from existing metrics) ---
    start_x = metrics.get("vehicle_start_x")
    target_x = metrics.get("target_x")
    stall_x = metrics.get("stall_threshold_x")
    if vx is not None and start_x is not None and target_x is not None and _is_finite(vx) and _is_finite(target_x):
        total_dist = float(target_x) - float(start_x)
        if total_dist != 0:
            progress_pct = min(max(0.0, (float(vx) - float(start_x)) / total_dist), 1.0) * 100.0
        else:
            progress_pct = 100.0 if float(vx) >= float(target_x) else 0.0
        phase = "pre-gap"
        if stall_x is not None and _is_finite(stall_x):
            if float(vx) >= float(stall_x):
                phase = "on-gap" if float(vx) < float(target_x) else "post-gap"
        metric_parts.append(
            f"**Phase**: {phase} | **Spatial progress**: x={float(vx):.2f}m → target {float(target_x):.2f}m ({progress_pct:.1f}%)"
        )

    # --- Boundary margin proximity (elevation and target; only from metrics) ---
    fail_zone_y = metrics.get("fail_zone_y")
    if vy is not None and _is_finite(vy):
        margin_water = float(vy) - float(fail_zone_y) if fail_zone_y is not None and _is_finite(fail_zone_y) else None
        s = f"**Elevation**: y={float(vy):.2f}m"
        if margin_water is not None:
            s += f" (margin above fail zone: {margin_water:.2f}m)"
        metric_parts.append(s)

    if vx is not None and target_x is not None and _is_finite(vx) and _is_finite(target_x):
        margin_target = float(target_x) - float(vx)
        metric_parts.append(f"**Target margin**: {margin_target:.2f}m to reach x>={float(target_x):.2f}m")

    # --- Structural integrity & resource (dynamic thresholds from metrics) ---
    sm = metrics.get("structure_mass")
    msm = metrics.get("max_structure_mass")
    if sm is not None and _is_finite(sm):
        s = f"**Mass budget**: {float(sm):.2f}kg"
        if msm is not None and _is_finite(msm) and float(msm) > 0:
            ratio = (float(sm) / float(msm)) * 100.0
            margin_mass = float(msm) - float(sm)
            s += f" / {float(msm):.0f}kg ({ratio:.1f}% used, margin {margin_mass:.2f}kg)"
        metric_parts.append(s)

    jc = metrics.get("joint_count")
    ijc = metrics.get("initial_joint_count")
    if jc is not None and ijc is not None and int(ijc) > 0:
        metric_parts.append(f"**Active joints**: {jc} / {ijc}")

    # --- Dynamic stress & stability (limits from metrics only) ---
    mva = metrics.get("max_vertical_accel")
    limit_accel = metrics.get("max_vertical_acceleration_limit")
    if mva is not None and _is_finite(mva):
        s = f"**Peak vertical acceleration**: {float(mva):.2f} m/s²"
        if limit_accel is not None and _is_finite(limit_accel):
            margin_accel = float(limit_accel) - float(mva)
            s += f" (limit: {float(limit_accel):.2f}, margin: {margin_accel:.2f})"
        metric_parts.append(s)

    if metrics.get("normalized_angle") is not None and _is_finite(metrics.get("normalized_angle")):
        angle_deg = math.degrees(float(metrics["normalized_angle"]))
        metric_parts.append(f"**Vehicle attitude**: {angle_deg:.1f}°")

    if metrics.get("is_airborne") and metrics.get("airborne_rotation_accumulated") is not None:
        rot = metrics["airborne_rotation_accumulated"]
        if _is_finite(rot):
            rot_deg = math.degrees(float(rot))
            s = f"**Airborne rotation accumulated**: {rot_deg:.1f}°"
            limit_rot = metrics.get("max_airborne_rotation_limit")
            if limit_rot is not None and _is_finite(limit_rot):
                limit_deg = math.degrees(float(limit_rot))
                s += f" (limit: {limit_deg:.1f}°)"
            metric_parts.append(s)

    havc = metrics.get("high_angular_velocity_count")
    if havc is not None:
        metric_parts.append(f"**Stability**: high-angular-velocity exceedance count: {havc}")

    if metrics.get("velocity_x") is not None and metrics.get("velocity_y") is not None:
        vvx, vvy = metrics["velocity_x"], metrics["velocity_y"]
        if _is_finite(vvx) and _is_finite(vvy):
            metric_parts.append(f"**Velocity**: vx={float(vvx):.2f}, vy={float(vvy):.2f} m/s")
    if metrics.get("angular_velocity") is not None and _is_finite(metrics.get("angular_velocity")):
        metric_parts.append(f"**Angular velocity**: {float(metrics['angular_velocity']):.2f} rad/s")

    if metrics.get("step_count") is not None:
        metric_parts.append(f"**Simulation step**: {metrics['step_count']}")

    return metric_parts


def get_improvement_suggestions(
    metrics: Dict[str, Any],
    score: float,
    success: bool,
    failed: bool,
    failure_reason: Optional[str] = None,
    error: Optional[str] = None,
) -> List[str]:
    """
    Generate diagnostic suggestions for S-01. No spoilers: physical mechanism only,
    never solution or code. All thresholds from metrics (stage-mutation safe).
    Covers only root-cause chain and failure modes present in evaluator logic.
    """
    suggestions: List[str] = []
    reason_lower = str(failure_reason or "").lower()
    error_str = str(error or "").strip().lower()

    # --- System / initialization error ---
    if error and error_str:
        suggestions.append(
            ">> SYSTEM ERROR: Initialization or constraint check failed. "
            "Review design constraints and mass budget against the current environment limits."
        )
        return suggestions

    # --- Non-finite metrics (solver divergence) ---
    for key in ("vehicle_x", "vehicle_y", "velocity_x", "velocity_y", "max_vertical_accel", "structure_mass"):
        val = metrics.get(key)
        if val is not None and not _is_finite(val):
            suggestions.append(
                ">> NUMERICAL INSTABILITY: Simulation produced non-finite values. "
                "The structure or loading may be causing solver divergence."
            )
            break

    if failed:
        suggestions.append(f">> FAILURE MODE: {failure_reason}")

        # --- Root-cause chain: what broke first (diagnostic only) ---
        structure_broken = metrics.get("structure_broken", False)
        current_y = metrics.get("vehicle_y")
        mass = metrics.get("structure_mass")
        max_mass = metrics.get("max_structure_mass")
        fail_zone_y = metrics.get("fail_zone_y")
        if fail_zone_y is not None and not _is_finite(fail_zone_y):
            fail_zone_y = None

        if "integrity" in reason_lower or "joints broke" in reason_lower:
            suggestions.append(
                "-> Diagnostic: Structural connections exceeded their load capacity. "
                "Load path and stress concentration likely drove one or more joints past their strength limit."
            )
            if structure_broken and current_y is not None and _is_finite(current_y) and fail_zone_y is not None and _is_finite(fail_zone_y):
                if float(current_y) <= float(fail_zone_y):
                    suggestions.append(
                        "-> Root-cause chain: Joint failure preceded loss of support; "
                        "the vehicle then lost elevation and entered the fail zone."
                    )

        if "fell into water" in reason_lower:
            if not structure_broken:
                suggestions.append(
                    "-> Diagnostic: Support manifold discontinuity. "
                    "The vehicle left the supported path without prior joint failure—loss of continuous support or reaction path."
                )
            else:
                suggestions.append(
                    "-> Diagnostic: Support manifold collapse. "
                    "Joint failure removed the reaction path needed to maintain elevation."
                )

        if "structural component" in reason_lower and ("fail zone" in reason_lower or "entered" in reason_lower):
            y_val = f"y={float(fail_zone_y):.2f}m" if (fail_zone_y is not None and _is_finite(fail_zone_y)) else "fail zone"
            suggestions.append(
                f"-> Diagnostic: At least one structural element reached or went below the fail zone ({y_val}). "
                "The task fails if the vehicle or any part of the structure enters the fail zone—check support and deflection."
            )

        if "vertical acceleration" in reason_lower:
            suggestions.append(
                "-> Diagnostic: Vertical impulse or shock loading exceeded the smoothness limit. "
                "Stress or loading path may be inducing large vertical force spikes."
            )

        if "rotated" in reason_lower or "flipped" in reason_lower or "unstable" in reason_lower:
            suggestions.append(
                "-> Diagnostic: Rotational instability—excess angular momentum or loss of a level support plane. "
                "Loading or contact conditions may be creating torque or uneven reaction."
            )

        if "mass" in reason_lower or "design constraint" in reason_lower:
            if mass is not None and max_mass is not None and _is_finite(mass) and _is_finite(max_mass):
                if float(mass) > float(max_mass):
                    suggestions.append(
                        "-> Diagnostic: Total structure mass exceeds the environment limit. "
                        "The configuration is over the allowed budget."
                    )

        if "outside build zone" in reason_lower or "build zone" in reason_lower:
            suggestions.append(
                "-> Diagnostic: At least one structural element lies outside the permitted build volume. "
                "Placement must respect the stated spatial bounds."
            )

        if "friction" in reason_lower:
            suggestions.append(
                "-> Diagnostic: Deck traction below the required minimum. "
                "Surface contact properties affect the vehicle's ability to maintain grip."
            )

    else:
        # --- Not failed but not success: stall before target (vehicle_x < target_x) ---
        vx = metrics.get("vehicle_x")
        stall_x = metrics.get("stall_threshold_x")
        target_x = metrics.get("target_x")

        if not success and vx is not None and _is_finite(vx) and target_x is not None and _is_finite(target_x):
            vx_f, tx_f = float(vx), float(target_x)
            if vx_f < tx_f:
                stall_val = float(stall_x) if (stall_x is not None and _is_finite(stall_x)) else None
                if stall_val is not None and stall_val > 0 and vx_f < stall_val:
                    suggestions.append(
                        "-> Diagnostic: Traversal stall. Forward progress stopped before the gap. "
                        "Support continuity or friction on the approach may be limiting motion."
                    )

    return suggestions
