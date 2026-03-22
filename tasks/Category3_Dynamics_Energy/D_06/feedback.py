"""
D-06: The Catch — evaluator-grounded diagnostic feedback only.
"""
from typing import Any, Dict, List
import math


def _is_finite(x: Any) -> bool:
    if x is None:
        return True
    try:
        return math.isfinite(float(x))
    except (TypeError, ValueError):
        return True


def _safe_float(x: Any) -> float:
    return float(x)


def _format_uncaptured_positions(metrics: Dict[str, Any], limit: int = 7) -> str:
    uncaptured = metrics.get("uncaptured_positions")
    if not isinstance(uncaptured, list) or not uncaptured:
        return ""
    parts: List[str] = []
    for item in uncaptured[:limit]:
        if not isinstance(item, (tuple, list)) or len(item) < 3:
            continue
        idx, x, y = item[0], item[1], item[2]
        if _is_finite(x) and _is_finite(y):
            parts.append(f"#{int(idx)} at ({_safe_float(x):.2f}, {_safe_float(y):.2f})")
    return ", ".join(parts)


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """High-resolution baseline output (no suggestions)."""
    if not metrics:
        return []

    out: List[str] = []

    # Phase A: progress and capture state
    caught = metrics.get("balls_caught_count")
    required = metrics.get("balls_required_count")
    if _is_finite(caught) and _is_finite(required):
        caught_i = int(caught)
        required_i = int(required)
        remaining = max(0, required_i - caught_i)
        out.append(
            f"**Phase A - Capture progress**: {caught_i}/{required_i} stabilized in target (remaining: {remaining})"
        )

    # Phase B: lead projectile state
    if _is_finite(metrics.get("ball_speed")):
        out.append(f"**Phase B - Lead projectile speed**: {_safe_float(metrics['ball_speed']):.3f} m/s")
    if _is_finite(metrics.get("ball_speed_vs_threshold")):
        out.append(
            f"**Phase B - Speed margin vs catch criterion**: {_safe_float(metrics['ball_speed_vs_threshold']):.3f} m/s (negative means below threshold)"
        )
    if metrics.get("ball_in_catch_zone") is not None:
        out.append(f"**Phase B - Lead projectile in target zone**: {bool(metrics.get('ball_in_catch_zone'))}")
    if metrics.get("ball_caught") is not None:
        out.append(f"**Phase B - All balls caught flag**: {bool(metrics.get('ball_caught'))}")

    # Phase C: structural/load envelope (dynamic limits from metrics)
    structure_mass = metrics.get("structure_mass")
    max_structure_mass = metrics.get("max_structure_mass")
    mass_budget_pct = metrics.get("mass_budget_used_pct")
    if _is_finite(structure_mass):
        msg = f"**Phase C - Structure mass**: {_safe_float(structure_mass):.2f} kg"
        if _is_finite(max_structure_mass):
            msg += f" / limit {_safe_float(max_structure_mass):.2f} kg"
            if _is_finite(mass_budget_pct):
                msg += f" ({_safe_float(mass_budget_pct):.1f}% of limit)"
            else:
                max_m = _safe_float(max_structure_mass)
                pct = (_safe_float(structure_mass) / max_m * 100.0) if max_m > 0 else 0.0
                msg += f" ({pct:.1f}% of limit)"
        out.append(msg)

    beam_count = metrics.get("beam_count")
    joint_count = metrics.get("joint_count")
    if beam_count is not None or joint_count is not None:
        out.append(
            f"**Phase C - Topology counts**: beams={int(beam_count) if beam_count is not None else 'n/a'}, joints={int(joint_count) if joint_count is not None else 'n/a'}"
        )

    if _is_finite(metrics.get("max_joint_force_limit")):
        out.append(
            f"**Phase C - Joint peak-failure limit**: {_safe_float(metrics['max_joint_force_limit']):.1f} N"
        )
    if _is_finite(metrics.get("joint_fatigue_threshold")):
        out.append(
            f"**Phase C - Joint sustained-load threshold**: {_safe_float(metrics['joint_fatigue_threshold']):.1f} N"
        )
    if metrics.get("structure_smashed") is not None:
        out.append(
            f"**Phase C - Structure integrity**: {'broken' if bool(metrics.get('structure_smashed')) else 'intact'}"
        )

    # Phase D: sequencing/containment flags
    if metrics.get("sequential_violation") is not None:
        out.append(f"**Phase D - Sequential violation flag**: {bool(metrics.get('sequential_violation'))}")
    if _is_finite(metrics.get("approach_x_m")):
        out.append(f"**Phase D - Approach line**: x < {_safe_float(metrics['approach_x_m']):.2f} m")
    if metrics.get("pit_failure") is not None:
        out.append(f"**Phase D - Pit failure flag**: {bool(metrics.get('pit_failure'))}")

    uncaptured_line = _format_uncaptured_positions(metrics)
    if uncaptured_line:
        out.append(f"**Phase D - Uncaptured positions (index, x, y)**: {uncaptured_line}")

    if _is_finite(metrics.get("step_count")):
        out.append(f"**Simulation step**: {int(metrics['step_count'])}")
    if metrics.get("failed") is not None:
        out.append(f"**Failed flag**: {bool(metrics.get('failed'))}")
    if metrics.get("success") is not None:
        out.append(f"**Success flag**: {bool(metrics.get('success'))}")
    if metrics.get("failure_reason"):
        out.append(f"**Failure reason**: {metrics.get('failure_reason')}")

    return out


def get_improvement_suggestions(metrics: Dict[str, Any], *args, **kwargs) -> List[str]:
    """
    Diagnostic, no-spoiler feedback describing failure mechanisms and trade-offs.
    Uses only evaluator-returned metrics and dynamic metric thresholds.
    """
    if not metrics:
        return []

    suggestions: List[str] = []
    failure_reason = str(metrics.get("failure_reason") or "")
    failed = bool(metrics.get("failed"))
    smashed = bool(metrics.get("structure_smashed"))
    pit = bool(metrics.get("pit_failure"))
    seq = bool(metrics.get("sequential_violation"))
    design_fail = "Design constraint violated" in failure_reason or "Design must be anchored" in failure_reason
    timeout_like = failed and "Not all balls caught" in failure_reason

    # Design constraint diagnostics via reason text + metric-backed budget
    if design_fail:
        if "anchor" in failure_reason.lower():
            suggestions.append(
                "- **Anchoring failure**: The initial design is treated as invalid without a rigid connection to static ground, so runtime behavior is never the limiting mechanism."
            )
        if "outside build zone" in failure_reason:
            suggestions.append(
                "- **Build footprint violation**: At least one beam center is outside the legal construction region for this stage."
            )
        if "FORBIDDEN ZONE" in failure_reason:
            suggestions.append(
                "- **Forbidden x-band violation**: Beam placement intersects a protected vertical corridor that is reserved for projectile transit."
            )
        if "SWEEPER BAND" in failure_reason or "SWEEPER" in failure_reason:
            suggestions.append(
                "- **Sweeper-band violation**: Beam placement intersects a restricted y-band that must remain clear."
            )
        if "Beam count" in failure_reason and "exceeds" in failure_reason:
            suggestions.append(
                "- **Component-limit violation**: Beam count exceeds the stage's allowed structural complexity."
            )

    structure_mass = metrics.get("structure_mass")
    max_structure_mass = metrics.get("max_structure_mass")
    if (
        _is_finite(structure_mass)
        and _is_finite(max_structure_mass)
        and _safe_float(max_structure_mass) > 0.0
        and _safe_float(structure_mass) >= _safe_float(max_structure_mass)
    ):
        suggestions.append(
            "- **Mass-budget violation**: Structural mass reaches or exceeds the current stage limit, so the design is invalid before dynamic performance can matter."
        )

    # Runtime mechanism diagnostics
    if smashed:
        suggestions.append(
            "- **Load-path failure**: A joint failed under peak or sustained reaction loading, indicating impact/load transmission exceeded the current structural tolerance envelope."
        )
    if pit:
        suggestions.append(
            "- **Containment-energy failure**: An uncaught projectile entered the pit region with excessive speed, indicating insufficient energy dissipation before low-altitude transit."
        )
    if seq:
        approach_x = metrics.get("approach_x_m")
        if _is_finite(approach_x):
            suggestions.append(
                f"- **Temporal ordering failure**: A higher-index projectile crossed the approach line (x < {_safe_float(approach_x):.2f} m) before all lower-index projectiles were already stabilized."
            )
        else:
            suggestions.append(
                "- **Temporal ordering failure**: A higher-index projectile entered the approach region before lower-index projectiles were stabilized."
            )

    caught = metrics.get("balls_caught_count")
    required = metrics.get("balls_required_count")
    if (
        failed
        and _is_finite(caught)
        and _is_finite(required)
        and int(caught) < int(required)
        and not (smashed or pit or seq or design_fail)
    ):
        suggestions.append(
            "- **Incomplete capture before stop**: The run ended before all balls were stabilized in the target region."
        )

    # Speed/catch margin diagnostics from available scalar metrics
    speed_margin = metrics.get("ball_speed_vs_threshold")
    if _is_finite(speed_margin) and _safe_float(speed_margin) > 0:
        suggestions.append(
            "- **Residual kinetic state**: At least the lead projectile remains above catch-speed criterion, so dissipation in the final target region is insufficient."
        )

    return suggestions
