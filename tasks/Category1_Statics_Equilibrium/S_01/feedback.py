"""
Task-specific feedback generation for S-01: The Bridge.
Process-aware, diagnostic feedback derived only from evaluator.evaluate() metrics.
No spoilers: diagnoses physical mechanism, never dictates solution or implementation.
Dynamic thresholds: all limits from metrics (stage-mutation safe).
"""
from typing import Dict, Any, List
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
    """
    metric_parts: List[str] = []

    # --- Physics engine sanity (numerical instability) ---
    vx = metrics.get("vehicle_x")
    vy = metrics.get("vehicle_y")
    if not _is_finite(vx) or not _is_finite(vy):
        metric_parts.append("**Numerical state**: Vehicle position contains non-finite values.")
    for key in ("velocity_x", "velocity_y", "angular_velocity", "max_vertical_accel", "structure_mass"):
        val = metrics.get(key)
        if val is not None and not _is_finite(val):
            metric_parts.append(f"**Numerical state**: {key} is non-finite.")

    # --- Phase-specific segregation (only from existing metrics) ---
    start_x = metrics.get("vehicle_start_x")
    target_x = metrics.get("target_x", float("inf"))
    stall_x = metrics.get("stall_threshold_x")
    if vx is not None and start_x is not None and target_x != start_x:
        total_dist = target_x - start_x
        progress_pct = min(max(0, (vx - start_x) / total_dist), 1.0) * 100.0
        phase = "pre-gap"
        if stall_x is not None and vx >= stall_x:
            phase = "on-gap" if vx < target_x else "post-gap"
        metric_parts.append(f"**Phase**: {phase} | **Spatial progress**: x={vx:.2f}m → target {target_x:.2f}m ({progress_pct:.1f}%)")

    # --- Boundary margin proximity (how close to limits) ---
    if "vehicle_y" in metrics and metrics.get("vehicle_y") is not None:
        water_level = 0.5  # failure threshold from evaluator (current_y < 0.5)
        margin_water = metrics["vehicle_y"] - water_level
        metric_parts.append(f"**Elevation**: y={metrics['vehicle_y']:.2f}m (margin above water: {margin_water:.2f}m)")

    if "vehicle_x" in metrics and "target_x" in metrics:
        vx_val = metrics["vehicle_x"]
        tx_val = metrics["target_x"]
        if _is_finite(vx_val) and _is_finite(tx_val):
            margin_target = tx_val - vx_val
            metric_parts.append(f"**Target margin**: {margin_target:.2f}m to reach x>={tx_val:.2f}m")

    # --- Structural integrity & resource (dynamic thresholds from metrics) ---
    sm = metrics.get("structure_mass")
    msm = metrics.get("max_structure_mass", float("inf"))
    if sm is not None and msm is not None and _is_finite(sm) and _is_finite(msm):
        ratio = (sm / msm * 100.0) if msm > 0 else 0.0
        margin_mass = msm - sm
        metric_parts.append(f"**Mass budget**: {sm:.2f}kg / {msm:.0f}kg ({ratio:.1f}% used, margin {margin_mass:.2f}kg)")

    jc = metrics.get("joint_count")
    ijc = metrics.get("initial_joint_count")
    if jc is not None and ijc is not None and ijc > 0:
        metric_parts.append(f"**Active joints**: {jc} / {ijc}")

    # --- Dynamic stress & stability (dynamic limit from metrics) ---
    mva = metrics.get("max_vertical_accel")
    limit_accel = metrics.get("max_vertical_acceleration_limit", float("inf"))
    if mva is not None and _is_finite(mva):
        margin_accel = (limit_accel - mva) if limit_accel != float("inf") else None
        s = f"**Peak vertical acceleration**: {mva:.2f} m/s² (limit: {limit_accel:.2f})"
        if margin_accel is not None:
            s += f" (margin: {margin_accel:.2f})"
        metric_parts.append(s)

    if "normalized_angle" in metrics and metrics["normalized_angle"] is not None:
        angle_deg = math.degrees(metrics["normalized_angle"])
        metric_parts.append(f"**Vehicle attitude**: {angle_deg:.1f}°")

    if metrics.get("is_airborne") and "airborne_rotation_accumulated" in metrics:
        rot = metrics["airborne_rotation_accumulated"]
        limit_rot = metrics.get("max_airborne_rotation_limit")
        if limit_rot is not None and _is_finite(rot):
            rot_deg = math.degrees(rot)
            limit_deg = math.degrees(limit_rot) if limit_rot is not None else None
            s = f"**Airborne rotation**: {rot_deg:.1f}° accumulated"
            if limit_deg is not None:
                s += f" (limit: {limit_deg:.1f}°)"
            metric_parts.append(s)

    if "velocity_x" in metrics and "velocity_y" in metrics:
        vvx, vvy = metrics["velocity_x"], metrics["velocity_y"]
        if _is_finite(vvx) and _is_finite(vvy):
            metric_parts.append(f"**Velocity**: vx={vvx:.2f}, vy={vvy:.2f} m/s")
    if "angular_velocity" in metrics and metrics["angular_velocity"] is not None and _is_finite(metrics["angular_velocity"]):
        metric_parts.append(f"**Angular velocity**: {metrics['angular_velocity']:.2f} rad/s")

    if "step_count" in metrics and metrics["step_count"] is not None:
        metric_parts.append(f"**Simulation step**: {metrics['step_count']}")

    return metric_parts


def get_improvement_suggestions(
    metrics: Dict[str, Any],
    score: float,
    success: bool,
    failed: bool,
    failure_reason: str = None,
    error: str = None,
) -> List[str]:
    """
    Generate diagnostic suggestions for S-01. No spoilers: physical mechanism only,
    never solution or code. All thresholds from metrics (stage-mutation safe).
    """
    suggestions: List[str] = []
    reason_lower = str(failure_reason or "").lower()
    error_str = str(error or "").lower()

    # --- System / initialization error ---
    if error and not error_str.isspace():
        suggestions.append(">> SYSTEM ERROR: Initialization or constraint check failed. Review design constraints and mass budget against the current environment limits.")
        return suggestions

    # --- Physics engine numerical instability ---
    for key in ("vehicle_x", "vehicle_y", "velocity_x", "velocity_y", "max_vertical_accel", "structure_mass"):
        val = metrics.get(key)
        if val is not None and not _is_finite(val):
            suggestions.append(">> NUMERICAL INSTABILITY: Simulation produced non-finite values. The structure or loading may be causing solver divergence.")
            break

    if failed:
        suggestions.append(f">> FAILURE MODE: {failure_reason}")

        # --- Root-cause chain: what broke first (diagnostic only) ---
        structure_broken = metrics.get("structure_broken", False)
        current_y = metrics.get("vehicle_y")
        mass = metrics.get("structure_mass")
        max_mass = metrics.get("max_structure_mass", float("inf"))

        if "integrity" in reason_lower or "joints broke" in reason_lower:
            suggestions.append("-> Diagnostic: Structural connections exceeded their load capacity. Load path and stress concentration likely drove one or more joints past their strength limit.")
            if structure_broken and current_y is not None and _is_finite(current_y):
                if current_y < 0.5:
                    suggestions.append("-> Root-cause chain: Joint failure preceded loss of support; the vehicle then lost elevation and entered the fail zone.")

        if "fell into water" in reason_lower:
            if not structure_broken:
                suggestions.append("-> Diagnostic: Support manifold discontinuity. The vehicle left the supported path without prior joint failure—check deck continuity and lateral support.")
            else:
                suggestions.append("-> Diagnostic: Support manifold collapse. Joint failure removed the reaction path needed to maintain elevation.")

        if "vertical acceleration" in reason_lower:
            suggestions.append("-> Diagnostic: Vertical impulse or shock loading exceeded the smoothness limit. Deck geometry or transitions may be inducing large vertical force spikes.")

        if "rotated" in reason_lower or "flipped" in reason_lower or "unstable" in reason_lower:
            suggestions.append("-> Diagnostic: Rotational instability—excess angular momentum or loss of a level support plane. Load path or deck geometry may be creating torque or uneven contact.")

        if "mass" in reason_lower or "design constraint" in reason_lower:
            if mass is not None and max_mass != float("inf") and mass > max_mass:
                suggestions.append("-> Diagnostic: Total structure mass exceeds the environment limit. The configuration is over the allowed budget; mass distribution or topology may need to be revisited.")

        # --- Build zone (from evaluator: beam outside zone) ---
        if "outside build zone" in reason_lower or "build zone" in reason_lower:
            suggestions.append("-> Diagnostic: At least one structural element lies outside the permitted build volume. Placement must respect the stated spatial bounds.")

    else:
        # --- No failure but not success: multi-objective / stall ---
        vx = metrics.get("vehicle_x")
        stall_x = metrics.get("stall_threshold_x")
        target_x = metrics.get("target_x")
        mass = metrics.get("structure_mass")
        max_mass = metrics.get("max_structure_mass", float("inf"))

        # Multi-objective trade-off: e.g. perfect stability but over mass
        if not success and vx is not None and _is_finite(vx) and target_x is not None and _is_finite(target_x):
            if vx >= target_x and mass is not None and max_mass != float("inf") and mass > max_mass:
                suggestions.append("-> Trade-off: Spatial target was reached but mass budget was exceeded. One objective was satisfied at the expense of another constraint.")
            elif stall_x is not None and vx < stall_x and stall_x > 0:
                suggestions.append("-> Diagnostic: Traversal stall. Forward progress stopped before the gap. Support continuity or friction on the approach may be limiting motion.")

    return suggestions
