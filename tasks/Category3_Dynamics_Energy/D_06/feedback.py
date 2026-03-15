"""
D-06: The Catch — process-aware, diagnostic feedback.

Exposes only metrics provided by evaluator._make_metrics(). Uses dynamic thresholds
from metrics (max_structure_mass, max_joint_force_limit)
so feedback adapts to stage mutations. Diagnoses physical mechanism of failure
without prescribing code or parameter values.
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
    No suggestions; baseline state and margins. All thresholds from metrics
    (max_structure_mass, max_joint_force_limit, etc.) for stage-mutation safety.
    """
    if not metrics:
        return []

    out: List[str] = []

    # --- Numerical stability (only if present in metrics)
    if _has_numerical_instability(metrics):
        out.append(
            "**Numerical instability**: One or more physical quantities are non-finite (NaN or infinite). "
            "Simulation state may be invalid."
        )

    # --- Phase: capture progress (exactly what evaluator provides)
    caught = metrics.get("balls_caught_count")
    required = metrics.get("balls_required_count")
    if required is not None:
        caught = caught if caught is not None else 0
        remaining = max(0, int(required) - int(caught))
        out.append(
            f"**Capture progress**: {int(caught)}/{int(required)} projectiles stabilized (pending: {remaining})"
        )

    # --- Mass: use metrics only (dynamic limits)
    structure_mass = metrics.get("structure_mass")
    max_mass = metrics.get("max_structure_mass")
    mass_budget_pct = metrics.get("mass_budget_used_pct")
    if structure_mass is not None and _is_finite(structure_mass):
        mass_str = f"**Structure mass**: {float(structure_mass):.2f} kg"
        if max_mass is not None and _is_finite(max_mass):
            max_mass_f = float(max_mass)
            if mass_budget_pct is not None and _is_finite(mass_budget_pct):
                mass_str += f" ({float(mass_budget_pct):.1f}% of current environment mass budget)"
            else:
                pct = (float(structure_mass) / max_mass_f * 100) if max_mass_f > 0 else 0
                mass_str += f" ({pct:.1f}% of current environment mass budget)"
        out.append(mass_str)

    # --- Component counts (beam/joint; from metrics only)
    beam_count = metrics.get("beam_count")
    joint_count = metrics.get("joint_count")
    if beam_count is not None:
        out.append(
            f"**Component count**: {int(beam_count)} beams, "
            f"{int(joint_count) if joint_count is not None else 0} joints"
        )

    # --- Joint force limit (environment threshold; from metrics only)
    max_force = metrics.get("max_joint_force_limit")
    if max_force is not None and _is_finite(max_force):
        out.append(
            f"**Joint force limit (environment)**: {float(max_force):.1f} N "
            "(peak or sustained excess causes joint failure)"
        )

    # --- Lead projectile state (primary ball; backward-compat keys)
    ball_speed = metrics.get("ball_speed")
    ball_speed_vs = metrics.get("ball_speed_vs_threshold")
    if ball_speed is not None and _is_finite(ball_speed):
        out.append(f"**Lead projectile speed**: {float(ball_speed):.3f} m/s")
    if ball_speed_vs is not None and _is_finite(ball_speed_vs):
        out.append(
            f"**Speed vs catch threshold**: {float(ball_speed_vs):.3f} m/s "
            "(negative = below threshold)"
        )

    in_zone = metrics.get("ball_in_catch_zone")
    if in_zone is not None:
        out.append(f"**Lead projectile in target zone**: {bool(in_zone)}")

    # --- Phase-specific: uncaptured projectiles (index, x, y)
    uncaptured = metrics.get("uncaptured_positions")
    if uncaptured and isinstance(uncaptured, list) and len(uncaptured) > 0:
        parts = [f"#{int(idx)} at ({float(x):.2f}, {float(y):.2f})" for (idx, x, y) in uncaptured[:7]]
        out.append(f"**Uncaptured (index, x, y)**: {', '.join(parts)}")

    # --- Integrity and step
    structure_smashed = metrics.get("structure_smashed")
    if structure_smashed is not None:
        out.append(
            f"**Structure integrity**: {'broken (joint failure)' if structure_smashed else 'intact'}"
        )

    step_count = metrics.get("step_count")
    if step_count is not None and _is_finite(step_count):
        out.append(f"**Simulation steps**: {int(step_count)}")

    return out


def get_improvement_suggestions(metrics: Dict[str, Any], *args, **kwargs) -> List[str]:
    """
    Diagnostic suggestions from physical failure modes only. Uses only
    metrics returned by the evaluator; thresholds from metrics (stage-mutation safe).
    No spoilers: describes failure mechanism, not design or parameters.
    """
    if not metrics:
        return []

    suggestions: List[str] = []
    failure_reason = (metrics.get("failure_reason") or "")

    # --- Numerical non-finite values (derived from metrics the evaluator returns)
    if _has_numerical_instability(metrics):
        suggestions.append(
            "- **Non-finite state**: One or more returned physical quantities are non-finite (NaN or infinite). "
            "Simulation state may be invalid."
        )

    # --- Root-cause chain: help agent infer what broke first (design → pit/sequential/structure → timeout)
    design_fail = "Design constraint violated" in failure_reason or "Design must be anchored" in failure_reason
    pit = bool(metrics.get("pit_failure"))
    seq = bool(metrics.get("sequential_violation"))
    smashed = bool(metrics.get("structure_smashed"))
    timeout_like = bool(metrics.get("failed")) and "Not all balls caught" in failure_reason
    multiple = sum([design_fail, pit, seq, smashed, timeout_like]) >= 2
    if multiple and failure_reason:
        suggestions.append(
            "- **Root-cause order**: Several failure modes are present. Design violations are checked at start; "
            "then pit, arrival order, or structural failure during the run; then timeout if the run ended before full capture."
        )

    # --- Design constraints (root cause: invalid setup)
    if design_fail:
        if "anchored" in failure_reason.lower() or "anchor" in failure_reason.lower():
            suggestions.append(
                "- **Invalid setup**: The structure is not correctly anchored to the ground. "
                "At least one beam must be rigidly connected to the static environment."
            )
        if "outside build zone" in failure_reason:
            suggestions.append(
                "- **Build zone**: One or more components lie outside the permitted construction region. "
                "All beam centers must lie within the task build zone."
            )
        if "FORBIDDEN ZONE" in failure_reason:
            suggestions.append(
                "- **Spatial constraint**: A component center lies in a forbidden vertical band. "
                "Projectile paths must remain unobstructed."
            )
        if "SWEEPER" in failure_reason:
            suggestions.append(
                "- **Sweeper bands**: A component center lies in a forbidden horizontal band. "
                "These bands are reserved for projectile transit."
            )

    # --- Mass budget (dynamic: from metrics only)
    max_mass = metrics.get("max_structure_mass")
    structure_mass = metrics.get("structure_mass")
    if (
        structure_mass is not None
        and max_mass is not None
        and _is_finite(max_mass)
        and _is_finite(structure_mass)
        and float(structure_mass) > float(max_mass)
    ):
        suggestions.append(
            "- **Mass budget**: Total structure mass exceeds the current environment limit. "
            "Strength-to-weight ratio may need to stay within the allowed mass."
        )

    # --- Beam count (only from failure_reason; evaluator does not expose max_beam_count in metrics)
    if "Beam count" in failure_reason and "exceeds" in failure_reason:
        suggestions.append(
            "- **Complexity limit**: The number of beam components exceeds the environment limit."
        )

    # --- Structural failure (joint broke: peak or sustained load)
    if smashed:
        suggestions.append(
            "- **Structural failure**: At least one joint failed under load (peak or sustained force "
            "exceeded the environment limit). Impact stress exceeded joint capacity."
        )

    # --- Sequential / arrival order
    if seq:
        suggestions.append(
            "- **Arrival order**: A projectile entered the catch zone before a previous one was fully stabilized. "
            "Sequential absorption is required; concurrent arrivals or pile-ups can violate the order constraint."
        )

    # --- Pit failure (containment)
    if pit:
        suggestions.append(
            "- **Containment**: A projectile reached the lower region at high speed before being caught. "
            "Energy was not sufficiently dissipated before reaching the lower boundary."
        )

    # --- Structure failed before full capture (smashed + incomplete; evaluator allows this)
    caught = metrics.get("balls_caught_count")
    required = metrics.get("balls_required_count")
    if (
        smashed
        and required is not None
        and caught is not None
        and _is_finite(required)
        and _is_finite(caught)
        and int(caught) > 0
        and int(caught) < int(required)
    ):
        suggestions.append(
            "- **Load vs capture**: The structure failed before all projectiles were caught. "
            "Joint load capacity may be the limiting factor rather than capture geometry."
        )

    # --- Incomplete capture (timeout / not all caught; no structural or pit cause)
    if not smashed and not pit and not seq:
        if metrics.get("failed") and "Not all balls caught" in failure_reason:
            if required and caught is not None and int(caught) < int(required):
                suggestions.append(
                    "- **Incomplete capture**: Not all projectiles were stabilized within the target zone "
                    "before the end of the run."
                )

    return suggestions
