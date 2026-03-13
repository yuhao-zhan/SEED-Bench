"""
D-06: The Catch — process-aware, diagnostic feedback.

Exposes only metrics provided by evaluator._make_metrics(). Uses dynamic thresholds
from metrics (max_structure_mass, max_joint_force_limit) so feedback adapts to
stage mutations. Diagnoses physical mechanism of failure without prescribing code.
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


def _has_numerical_instability(metrics: Dict[str, Any]) -> bool:
    """True if any numeric metric in the evaluator output is non-finite."""
    numeric_keys = (
        "ball_x", "ball_y", "ball_vx", "ball_vy", "ball_speed",
        "structure_mass", "mass_budget_used_pct", "ball_speed_vs_threshold",
        "step_count", "max_joint_force_limit", "max_structure_mass",
        "balls_caught_count", "balls_required_count", "beam_count", "joint_count",
    )
    for k in numeric_keys:
        v = metrics.get(k)
        if v is not None and not _is_finite(v):
            return True
    up = metrics.get("uncaptured_positions")
    if isinstance(up, list):
        for item in up:
            if isinstance(item, (tuple, list)) and len(item) >= 3:
                if not _is_finite(item[1]) or not _is_finite(item[2]):
                    return True
    return False


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Expose high-resolution physical metrics from evaluator output only.
    No suggestions; baseline state and margins. All thresholds from metrics.
    """
    if not metrics:
        return []

    out: List[str] = []

    # --- Numerical stability (only if present in metrics)
    if _has_numerical_instability(metrics):
        out.append("**Numerical instability**: One or more physical quantities are non-finite (NaN or infinite). Simulation state may be invalid.")

    # --- Phase: capture progress (exactly what evaluator provides)
    caught = metrics.get("balls_caught_count")
    required = metrics.get("balls_required_count")
    if required is not None:
        caught = caught if caught is not None else 0
        remaining = max(0, required - caught)
        out.append(f"**Capture progress**: {caught}/{required} projectiles stabilized (pending: {remaining})")

    # --- Structure: mass and complexity (dynamic limits from metrics)
    structure_mass = metrics.get("structure_mass")
    max_mass = metrics.get("max_structure_mass")
    if structure_mass is not None:
        mass_str = f"**Structure mass**: {float(structure_mass):.2f} kg"
        if max_mass is not None and _is_finite(max_mass):
            pct = (float(structure_mass) / float(max_mass) * 100) if float(max_mass) > 0 else 0
            mass_str += f" ({pct:.1f}% of current environment mass budget)"
        out.append(mass_str)

    beam_count = metrics.get("beam_count")
    joint_count = metrics.get("joint_count")
    if beam_count is not None:
        out.append(f"**Component count**: {int(beam_count)} beams, {int(joint_count) if joint_count is not None else 0} joints")

    # --- Structural limit (environment threshold; from metrics)
    max_force = metrics.get("max_joint_force_limit")
    if max_force is not None and _is_finite(max_force):
        out.append(f"**Joint force limit (environment)**: {float(max_force):.1f} N (peak or sustained excess causes joint failure)")

    # --- Primary ball / lead projectile state (backward-compat keys)
    ball_speed = metrics.get("ball_speed")
    ball_speed_vs = metrics.get("ball_speed_vs_threshold")
    if ball_speed is not None and _is_finite(ball_speed):
        out.append(f"**Lead projectile speed**: {float(ball_speed):.3f} m/s")
    if ball_speed_vs is not None and _is_finite(ball_speed_vs):
        out.append(f"**Speed vs catch threshold**: {float(ball_speed_vs):.3f} m/s (negative = below threshold)")

    in_zone = metrics.get("ball_in_catch_zone")
    if in_zone is not None:
        out.append(f"**Lead projectile in target zone**: {bool(in_zone)}")

    # --- Uncaptured positions (phase-specific: which projectiles not yet caught)
    uncaptured = metrics.get("uncaptured_positions")
    if uncaptured and isinstance(uncaptured, list) and len(uncaptured) > 0:
        parts = [f"#{idx} at ({x:.2f}, {y:.2f})" for (idx, x, y) in uncaptured[:7]]
        out.append(f"**Uncaptured (index, x, y)**: {', '.join(parts)}")

    # --- Integrity and step
    structure_smashed = metrics.get("structure_smashed")
    if structure_smashed is not None:
        out.append(f"**Structure integrity**: {'broken (joint failure)' if structure_smashed else 'intact'}")

    step_count = metrics.get("step_count")
    if step_count is not None and _is_finite(step_count):
        out.append(f"**Simulation steps**: {int(step_count)}")

    return out


def get_improvement_suggestions(metrics: Dict[str, Any], *args, **kwargs) -> List[str]:
    """
    Diagnostic suggestions from physical failure modes only. Uses dynamic
    thresholds from metrics (stage-mutation safe). No spoilers: no code or
    explicit parameter values.
    """
    if not metrics:
        return []

    suggestions: List[str] = []
    failure_reason = (metrics.get("failure_reason") or "")

    # --- Physics engine / numerical
    if _has_numerical_instability(metrics):
        suggestions.append("- **Numerical instability**: Simulation produced non-finite values. Consider whether initial conditions or geometry could cause singularities or extreme forces.")

    # --- Design constraints (root cause: invalid setup; check first)
    if "Design constraint violated" in failure_reason or "Design must be anchored" in failure_reason:
        if "anchored" in failure_reason.lower() or "anchor" in failure_reason.lower():
            suggestions.append("- **Invalid setup**: The structure is not correctly anchored to the ground. At least one beam must be rigidly connected to the static environment.")
        if "outside build zone" in failure_reason:
            suggestions.append("- **Build zone**: One or more components lie outside the permitted construction region. All beam centers must lie within the task build zone.")
        if "FORBIDDEN ZONE" in failure_reason:
            suggestions.append("- **Spatial constraint**: A component center lies in a forbidden vertical band. Projectile paths must remain unobstructed; relocate beam centers to allowed x-ranges.")
        if "SWEEPER" in failure_reason:
            suggestions.append("- **Sweeper bands**: A component center lies in a forbidden horizontal band. These bands are reserved for projectile transit; adjust vertical placement.")

    max_mass = metrics.get("max_structure_mass")
    structure_mass = metrics.get("structure_mass")
    if structure_mass is not None and max_mass is not None and _is_finite(max_mass) and _is_finite(structure_mass):
        if float(structure_mass) > float(max_mass):
            suggestions.append("- **Mass budget**: Total structure mass exceeds the current environment limit. Consider improving strength-to-weight ratio so the catcher stays within the allowed mass.")

    if "Beam count" in failure_reason and "exceeds" in failure_reason:
        suggestions.append("- **Complexity limit**: The number of beam components exceeds the environment limit. The design must achieve capture with fewer structural elements.")

    # --- Structural failure (joint broke: peak or sustained load)
    if metrics.get("structure_smashed"):
        suggestions.append("- **Structural failure**: At least one joint failed under load (peak force or sustained load exceeded the environment limit). Impact energy is being concentrated; consider how to distribute or dissipate it without prescribing a specific mechanism.")

    # --- Sequential / ordering (ball arrived before previous caught)
    if metrics.get("sequential_violation"):
        suggestions.append("- **Arrival order**: A projectile entered the catch zone before a previous one was fully stabilized. The physical system requires sequential absorption; concurrent arrivals or pile-ups can eject projectiles and violate the order constraint.")

    # --- Pit failure (containment / energy dissipation)
    if metrics.get("pit_failure"):
        suggestions.append("- **Containment**: A projectile reached the lower region at high speed before being caught. The design must prevent fast escape through the floor—consider how energy is dissipated or how the lower boundary is physically defined.")

    # --- Multi-objective trade-off: structure failed while over mass
    if metrics.get("structure_smashed") and structure_mass is not None and max_mass is not None and _is_finite(max_mass) and _is_finite(structure_mass):
        if float(structure_mass) > float(max_mass):
            suggestions.append("- **Trade-off**: The structure failed under load and also exceeded the mass budget. Optimizing for both structural capacity and mass limit may be necessary.")

    # --- Timeout / not all caught (no structural or pit cause)
    if not metrics.get("structure_smashed") and not metrics.get("pit_failure") and not metrics.get("sequential_violation"):
        if metrics.get("failed") and "Not all balls caught" in failure_reason:
            caught = metrics.get("balls_caught_count", 0)
            required = metrics.get("balls_required_count", 7)
            if required and caught is not None and caught < required:
                suggestions.append("- **Incomplete capture**: Not all projectiles were stabilized within the target zone before the end of the run. Consider arrival timing, deflector cooperation, and energy absorption so every projectile is brought to rest in the allowed region.")

    return suggestions
