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
    Exposes timeline of failures, stress margins, and structural integrity metrics.
    """
    metric_parts: List[str] = []

    # --- Timeline of Failure ---
    failure_step = metrics.get("failure_step", -1)
    if failure_step != -1:
        metric_parts.append(f"**Timeline of Failure**: First failure detected at step {failure_step}.")
        if metrics.get("failure_reason"):
            metric_parts.append(f"-> **Failure Reason**: {metrics['failure_reason']}")

    # --- Forensic Log: Joint Breakage Events ---
    joint_break_events = metrics.get("joint_break_events", [])
    if joint_break_events:
        metric_parts.append("\n**Forensic Log: Joint Failures**")
        for event in sorted(joint_break_events, key=lambda x: x['step']):
            anchor = event['anchor_point']
            force_ratio = event['force'] / event['limit_force'] if event['limit_force'] > 0 else 0
            torque_ratio = event['torque'] / event['limit_torque'] if event['limit_torque'] > 0 else 0
            metric_parts.append(
                f"- Step {event['step']}: Joint at ({anchor[0]:.2f}, {anchor[1]:.2f}) broke. "
                f"Force: {event['force']:.2f}/{event['limit_force']:.0f}N ({force_ratio:.0%}). "
                f"Torque: {event['torque']:.2f}/{event['limit_torque']:.0f}Nm ({torque_ratio:.0%})."
            )

    # --- Physics Engine Sanity ---
    unstable = False
    for key in ("velocity_x", "velocity_y", "angular_velocity", "max_vertical_accel"):
        val = metrics.get(key)
        if val is not None and not _is_finite(val):
            metric_parts.append(f"**Numerical Instability**: {key} is non-finite ({val}). Solver likely diverged.")
            unstable = True
    if not unstable:
        metric_parts.append("**Numerical Stability**: OK")


    # --- Progress & State Metrics ---
    metric_parts.append("\n**Vehicle & Structure State**")
    
    # Progress
    start_x = metrics.get("vehicle_start_x")
    target_x = metrics.get("target_x")
    vx = metrics.get("vehicle_x")
    if vx is not None and _is_finite(vx) and start_x is not None and target_x is not None:
        span = float(target_x) - float(start_x)
        if span > 0:
            progress_pct = min(max(0.0, (float(vx) - float(start_x)) / span), 1.0) * 100.0
            metric_parts.append(f"- **Progress**: {progress_pct:.1f}% (x={float(vx):.2f}m / {float(target_x):.1f}m)")

    # Elevation
    fail_zone_y = metrics.get("fail_zone_y")
    vy = metrics.get("vehicle_y")
    if vy is not None and _is_finite(vy) and fail_zone_y is not None:
        margin = float(vy) - float(fail_zone_y)
        status = "ABOVE" if margin > 0 else "BELOW"
        metric_parts.append(f"- **Elevation**: y={float(vy):.2f}m ({abs(margin):.2f}m {status} fail zone at y={float(fail_zone_y):.2f}m)")

    # Dynamic Stability
    mva = metrics.get("max_vertical_accel")
    limit_accel = metrics.get("max_vertical_acceleration_limit")
    if mva is not None and limit_accel is not None and float(limit_accel) > 0:
        accel_pct = (float(mva) / float(limit_accel)) * 100
        metric_parts.append(f"- **Peak Vertical Acceleration**: {float(mva):.2f}m/s² ({accel_pct:.1f}% of {float(limit_accel):.2f}m/s² limit)")

    # Rotational Stability
    if metrics.get("normalized_angle") is not None and _is_finite(metrics.get("normalized_angle")):
        angle_deg = math.degrees(float(metrics["normalized_angle"]))
        metric_parts.append(f"- **Vehicle Attitude**: {angle_deg:.1f}°")
    
    if metrics.get("is_airborne") and metrics.get("airborne_rotation_accumulated") is not None:
        rot = metrics["airborne_rotation_accumulated"]
        limit_rot = metrics.get("max_airborne_rotation_limit")
        if _is_finite(rot) and limit_rot is not None and float(limit_rot) > 0:
            rot_deg = math.degrees(float(rot))
            limit_rot_deg = math.degrees(float(limit_rot))
            rot_pct = (rot_deg / limit_rot_deg) * 100
            metric_parts.append(f"- **Airborne Rotation**: {rot_deg:.1f}° ({rot_pct:.1f}% of {limit_rot_deg:.0f}° limit)")

    # --- Structural Integrity Summary ---
    ijc = metrics.get("initial_joint_count", 0)
    jc = metrics.get("joint_count", 0)
    if ijc > 0:
        integrity_pct = (jc / ijc) * 100
        metric_parts.append(f"- **Structural Integrity**: {jc}/{ijc} joints remain ({integrity_pct:.0f}% intact).")

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
