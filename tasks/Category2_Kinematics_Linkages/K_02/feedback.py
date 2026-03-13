"""
Task-specific feedback generation for K-02: The Climber.
Process-aware, diagnostic feedback grounded only in evaluator metrics.
No spoilers; all thresholds from metrics (stage-mutation adaptable).
"""
from typing import Dict, Any, List
import math

# Wall-contact band (evaluator logic); used only to compute margin from metrics.
_WALL_X_LO = 3.5
_WALL_X_HI = 7.5


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
    Expose high-resolution physical metrics from evaluator output only.
    No suggestions. Includes boundary-margin proximity where derivable from metrics.
    """
    parts: List[str] = []
    if not metrics:
        return parts

    # Numerical sanity: if any key numeric is non-finite, surface it
    numeric_keys = [
        'climber_x', 'climber_y', 'height_gained', 'max_height_reached', 'min_height_seen',
        'target_y', 'progress', 'step_count', 'structure_mass', 'max_structure_mass', 'min_structure_mass',
        'min_simulation_steps_required'
    ]
    non_finite = [k for k in numeric_keys if k in metrics and not _is_finite(metrics[k])]
    if non_finite:
        parts.append("**Numerical State**: Non-finite values detected in: " + ", ".join(non_finite) + ". Simulation may be numerically unstable.")

    # 1. Vertical trajectory (only if present)
    if 'climber_y' in metrics and _is_finite(metrics['climber_y']):
        y = float(metrics['climber_y'])
        target_y = metrics.get('target_y')
        if target_y is not None and _is_finite(target_y):
            target_y = float(target_y)
            margin_to_target = y - target_y
            parts.append(f"**Vertical Trajectory**: altitude y={y:.2f}m")
            parts.append(f"- Elevation to target: {margin_to_target:+.2f}m (target y={target_y:.1f}m)")
        else:
            parts.append(f"**Vertical Trajectory**: altitude y={y:.2f}m")
        if 'height_gained' in metrics and _is_finite(metrics['height_gained']):
            parts.append(f"- Height gained from start: {float(metrics['height_gained']):.2f}m")
        if 'max_height_reached' in metrics and _is_finite(metrics['max_height_reached']):
            parts.append(f"- Peak altitude reached: {float(metrics['max_height_reached']):.2f}m")
        if 'min_height_seen' in metrics and _is_finite(metrics['min_height_seen']):
            parts.append(f"- Minimum altitude during run: {float(metrics['min_height_seen']):.2f}m")

    # 2. Horizontal (wall-contact) margin
    if 'climber_x' in metrics and _is_finite(metrics['climber_x']):
        x = float(metrics['climber_x'])
        margin_lo = x - _WALL_X_LO
        margin_hi = _WALL_X_HI - x
        parts.append(f"**Horizontal (Wall Contact)**: x={x:.2f}m")
        parts.append(f"- Margin to lower bound (x={_WALL_X_LO}m): {margin_lo:+.2f}m")
        parts.append(f"- Margin to upper bound (x={_WALL_X_HI}m): {margin_hi:+.2f}m")

    # 3. Structural profile (mass vs limits from metrics)
    if 'structure_mass' in metrics and _is_finite(metrics['structure_mass']):
        mass = float(metrics['structure_mass'])
        max_m = metrics.get('max_structure_mass')
        min_m = metrics.get('min_structure_mass')
        max_m = float(max_m) if max_m is not None and _is_finite(max_m) else None
        min_m = float(min_m) if min_m is not None and _is_finite(min_m) else None
        parts.append(f"**Structural Profile**: Mass={mass:.2f}kg")
        if max_m is not None:
            parts.append(f"- Margin to mass ceiling: {max_m - mass:.2f}kg (max={max_m:.1f}kg)")
        if min_m is not None and min_m > 0:
            parts.append(f"- Margin to mass floor: {mass - min_m:.2f}kg (min={min_m:.1f}kg)")

    # 4. Temporal / phase
    if 'step_count' in metrics and _is_finite(metrics['step_count']):
        steps = int(metrics['step_count'])
        req = metrics.get('min_simulation_steps_required')
        req = int(req) if req is not None and _is_finite(req) else None
        parts.append(f"**Operational Duration**: {steps} steps completed")
        if req is not None and req > 0:
            ratio = min(steps / req, 1.0)
            parts.append(f"- Fraction of required time: {ratio * 100:.1f}% (required steps={req})")

    # 5. Progress (height progress %)
    if 'progress' in metrics and _is_finite(metrics['progress']):
        parts.append(f"**Altitude Progress**: {float(metrics['progress']):.1f}% of target band")

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
    Diagnostic system feedback: physical mechanism and root-cause framing.
    No implementation spoilers; thresholds taken from metrics (stage-adaptive).
    """
    suggestions: List[str] = []
    reason = (failure_reason or "").lower()
    err = (error or "").lower()

    # Dynamic thresholds from metrics only
    max_mass = metrics.get("max_structure_mass")
    min_mass = metrics.get("min_structure_mass")
    target_y = metrics.get("target_y")
    req_steps = metrics.get("min_simulation_steps_required")
    current_mass = metrics.get("structure_mass")
    climber_y = metrics.get("climber_y")
    climber_x = metrics.get("climber_x")
    step_count = metrics.get("step_count")
    max_height_reached = metrics.get("max_height_reached")
    progress = metrics.get("progress", 0.0)

    # Physics-engine / numerical instability
    if not metrics:
        return suggestions
    numeric_vals = [metrics.get(k) for k in (
        "climber_x", "climber_y", "structure_mass", "progress", "step_count"
    )]
    if any(v is not None and not _is_finite(v) for v in numeric_vals):
        suggestions.append("DIAGNOSTIC: One or more state quantities are non-finite (NaN or infinite). This may indicate numerical instability in the simulation or invalid design parameters.")

    # Root-cause: design-time vs runtime
    if "design constraint" in reason:
        # Design-time failure (step 0): constraint violated before dynamics
        if "mass" in reason:
            if max_mass is not None and _is_finite(max_mass) and current_mass is not None and _is_finite(current_mass):
                if current_mass > max_mass:
                    suggestions.append("DIAGNOSTIC: Failure at design check. Total structure mass exceeds the current environment mass budget; the system rejected the design before simulation.")
                    suggestions.append("DIAGNOSTIC: The constraint is a hard ceiling—vertical performance cannot be traded for mass in this environment. Consider the strength-to-weight trade-off of the linkage.")
                else:
                    suggestions.append("DIAGNOSTIC: Total mass is below the environment minimum requirement. The current stage may enforce a minimum structural inertia for stability.")
            else:
                suggestions.append("DIAGNOSTIC: A mass-related design constraint was violated. Check whether total mass is within the environment bounds (min and max) for this stage.")
        elif "build zone" in reason:
            suggestions.append("DIAGNOSTIC: A component lies outside the allowed build zone at initialization. The failure is geometric/placement, not runtime dynamics.")
            if climber_x is not None and _is_finite(climber_x):
                suggestions.append(f"DIAGNOSTIC: Reported position x={float(climber_x):.2f}m; wall-contact band is x in [3.5, 7.5]m; build zone x is [0, 5]m. Placement must satisfy both.")

    # Runtime failures
    elif failed:
        if "lost wall contact" in reason:
            suggestions.append("DIAGNOSTIC: Runtime failure: horizontal position left the wall-contact band. Lateral forces or kinematics pushed the climber away from the vertical surface.")
            suggestions.append("DIAGNOSTIC: The root cause is lateral dynamics (e.g., reaction forces, wind, or oscillation). Improving vertical grip alone may not fix this without addressing lateral stability.")
        elif "fell" in reason or metrics.get("climber_fell", False):
            suggestions.append("DIAGNOSTIC: Runtime failure: vertical collapse. Net vertical support (adhesion and reaction forces) became insufficient to sustain the climber against gravity and any vertical disturbances.")
            suggestions.append("DIAGNOSTIC: Consider whether support was lost due to timing (e.g., releasing adhesion before load transfer) or due to external/environmental load exceeding capacity.")

    # Multi-objective: no hard failure but objectives not all met
    if not failed and not success:
        if progress is not None and _is_finite(progress) and float(progress) > 0:
            suggestions.append(f"DIAGNOSTIC: No catastrophic failure, but mission not complete. Altitude progress is {float(progress):.1f}% of target; time or height criterion was not satisfied.")
            suggestions.append("DIAGNOSTIC: The climber operated but did not reach the required height or duration. Consider the trade-off between ascent rate and stability under the current environment.")

    # Paradox: e.g. high altitude but failed on another criterion (if evaluator ever reports such)
    if failed and max_height_reached is not None and _is_finite(max_height_reached) and target_y is not None and _is_finite(target_y):
        if float(max_height_reached) >= float(target_y):
            suggestions.append("DIAGNOSTIC: Peak altitude met or exceeded the target, but the run was still marked failed. The primary failure is likely not height—check wall contact, mass constraints, or duration.")

    return suggestions
