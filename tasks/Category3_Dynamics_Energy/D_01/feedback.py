"""
D-01: The Launcher task feedback module.
Process-aware, diagnostic feedback for Dynamics/Energy domain.
Exposes only metrics provided by evaluator.evaluate(); uses dynamic thresholds from metrics.
"""
from typing import Dict, Any, List
import math


def _is_finite(x: Any) -> bool:
    """True if x is a finite number (no NaN, no inf)."""
    if x is None:
        return True
    try:
        f = float(x)
        return math.isfinite(f)
    except (TypeError, ValueError):
        return True


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Expose high-resolution physical metrics from evaluator output only.
    No suggestions; baseline data for the agent to reason about trajectory and constraints.
    """
    parts = []

    # --- Outcome and hit state (exactly from metrics) ---
    if "hit_occurred" in metrics:
        parts.append(f"**Target Hit**: {'Yes' if metrics['hit_occurred'] else 'No'}")
    if "success" in metrics:
        parts.append(f"**Success**: {metrics['success']}")
    if "failed" in metrics:
        parts.append(f"**Failed**: {metrics['failed']}")
    if metrics.get("failure_reason"):
        parts.append(f"**Failure Reason**: {metrics['failure_reason']}")
    if "error" in metrics and metrics["error"]:
        parts.append(f"**Error**: {metrics['error']}")

    # --- Numerical stability (physics engine limits) ---
    px = metrics.get("projectile_x")
    py = metrics.get("projectile_y")
    vx = metrics.get("projectile_vx")
    vy = metrics.get("projectile_vy")
    speed = metrics.get("projectile_speed")
    if not all(_is_finite(x) for x in (px, py, vx, vy, speed) if x is not None):
        parts.append("**Numerical Instability**: Projectile state contains non-finite values (NaN or infinity); simulation may be unstable.")

    # --- Position and velocity (trajectory diagnostics) ---
    if px is not None and py is not None and _is_finite(px) and _is_finite(py):
        parts.append(f"**Final Position**: (x: {px:.2f} m, y: {py:.2f} m)")
    if vx is not None and vy is not None and _is_finite(vx) and _is_finite(vy):
        parts.append(f"**Final Velocity**: (vx: {vx:.2f} m/s, vy: {vy:.2f} m/s)")
    if speed is not None and _is_finite(speed):
        parts.append(f"**Final Speed**: {speed:.2f} m/s")

    # --- Progress and range (from metrics) ---
    if "progress" in metrics and _is_finite(metrics.get("progress")):
        parts.append(f"**Horizontal Progress**: {metrics['progress']:.1f}%")

    # --- Target zone and boundary margin proximity ---
    tx_min = metrics.get("target_x_min")
    tx_max = metrics.get("target_x_max")
    ty_min = metrics.get("target_y_min")
    ty_max = metrics.get("target_y_max")
    if tx_min is not None and tx_max is not None and px is not None and _is_finite(px):
        if px < tx_min:
            gap = tx_min - px
            parts.append(f"**Shortfall (x)**: Projectile stopped {gap:.2f} m before target x-min ({tx_min:.1f} m).")
        elif px > tx_max:
            overshoot = px - tx_max
            parts.append(f"**Overshoot (x)**: Projectile passed target x-max by {overshoot:.2f} m (target x-max: {tx_max:.1f} m).")
        else:
            parts.append(f"**Horizontal Band**: Projectile x ({px:.2f} m) is inside target x-range [{tx_min:.1f}, {tx_max:.1f}] m.")

    if "max_y_in_target_x" in metrics and metrics["max_y_in_target_x"] is not None:
        y_peak = metrics["max_y_in_target_x"]
        if _is_finite(y_peak):
            parts.append(f"**Peak Altitude in Target x-Band**: {y_peak:.2f} m")
            if ty_min is not None and ty_max is not None:
                if y_peak < ty_min:
                    parts.append(f"**Vertical Shortfall**: Peak y in band ({y_peak:.2f} m) is below target y-min ({ty_min:.1f} m).")
                elif y_peak > ty_max:
                    parts.append(f"**Vertical Overshoot**: Peak y in band ({y_peak:.2f} m) is above target y-max ({ty_max:.1f} m).")
                else:
                    parts.append(f"**Vertical Band**: Peak y in band is inside target y-range [{ty_min:.1f}, {ty_max:.1f}] m.")

    # --- Structure mass vs limit (dynamic threshold from metrics) ---
    mass = metrics.get("structure_mass")
    max_mass = metrics.get("max_structure_mass")
    if mass is not None and max_mass is not None and _is_finite(mass) and _is_finite(max_mass):
        parts.append(f"**Launcher Mass**: {mass:.2f} kg / {max_mass:.1f} kg")
        if max_mass > 0:
            pct = 100.0 * mass / max_mass
            parts.append(f"**Mass Budget Usage**: {pct:.1f}%")

    # --- Simulation phase ---
    if "step_count" in metrics and metrics.get("step_count") is not None:
        parts.append(f"**Steps Elapsed**: {metrics['step_count']}")

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
    Diagnostic, process-aware suggestions. No spoilers: diagnose physical mechanism
    and trade-offs, never dictate exact parameter values or code.
    Uses only dynamic thresholds from metrics (stage-mutation safe).
    """
    suggestions = []
    msg = (error or failure_reason or "").lower()

    # --- Physics engine limits (numerical instability) ---
    for key in ("projectile_x", "projectile_y", "projectile_vx", "projectile_vy", "projectile_speed"):
        val = metrics.get(key)
        if val is not None and not _is_finite(val):
            suggestions.append("- **Numerical Instability**: Simulation state contains non-finite values; consider whether time step, stiffness, or collision setup could cause instability.")
            break

    # --- Root-cause: design constraint violated first ---
    max_mass = metrics.get("max_structure_mass", float("inf"))
    mass = metrics.get("structure_mass")
    if mass is not None and max_mass != float("inf") and mass > max_mass:
        suggestions.append("- **Design Constraint (Root Cause)**: Structure mass exceeds the allowed budget. Optimize the strength-to-mass ratio of the launcher rather than adding more material.")

    if "build zone" in msg or "outside" in msg:
        suggestions.append("- **Design Constraint (Root Cause)**: At least one component lies outside the valid construction region. Ensure all beam centers and joint anchors lie within the specified build zone.")

    if "simulation bounds" in msg:
        suggestions.append("- **Trajectory Boundary**: The projectile left the valid simulation domain. The launch may be too violent or directed outward; consider how energy is transferred to the projectile.")

    # --- Multi-objective trade-off: mass OK but trajectory failed ---
    if failed and not success and mass is not None and max_mass != float("inf") and mass <= max_mass and "design constraint" not in msg.lower():
        suggestions.append("- **Multi-Objective**: Mass budget is satisfied but the trajectory did not meet the target. Consider whether launch energy delivery (impulse, timing) or trajectory shape is the limiting factor.")

    # --- Trajectory diagnostics (no spoilers: mechanism, not numbers) ---
    if failed or not success:
        px = metrics.get("projectile_x")
        tx_min = metrics.get("target_x_min")
        tx_max = metrics.get("target_x_max")
        y_peak = metrics.get("max_y_in_target_x")
        ty_min = metrics.get("target_y_min")
        ty_max = metrics.get("target_y_max")

        if px is not None and tx_min is not None and tx_max is not None and _is_finite(px):
            if px < tx_min:
                suggestions.append("- **Range Shortfall**: The projectile did not reach the target x-band. Consider whether launch impulse or energy loss (e.g. dissipation) is limiting range.")
            elif px > tx_max:
                suggestions.append("- **Range Overshoot**: The projectile passed beyond the target x-band. Consider whether excess launch energy or trajectory flatness is causing overshoot.")

        if y_peak is not None and ty_min is not None and ty_max is not None and _is_finite(y_peak):
            if y_peak > ty_max:
                suggestions.append("- **Altitude Overshoot in Band**: Peak altitude within the target x-band exceeds the vertical window. Trajectory curvature may be too steep for the allowed y-range.")
            elif y_peak < ty_min:
                suggestions.append("- **Altitude Shortfall in Band**: Peak altitude within the target x-band stays below the vertical window. Consider whether a steeper arc or higher launch speed is needed to enter the zone.")

    return suggestions
