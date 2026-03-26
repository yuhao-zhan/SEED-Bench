"""
Task-specific feedback generation for F-01: The Dam (extreme).

Design goals:
- Process-aware diagnostics instead of binary-only judgments.
- No hallucination: only reason from keys present in evaluator metrics.
- No spoilers: diagnose mechanism, avoid explicit design/code prescriptions.
- Dynamic thresholds: derive limits from metrics, never hardcode stage values.
"""
from typing import Any, Dict, List
import math


def _safe_float(value: Any, default: float = None) -> float:
    if value is None:
        return default
    try:
        num = float(value)
    except (TypeError, ValueError):
        return default
    return num if math.isfinite(num) else default


def _signed_margin_str(observed: float, limit: float, unit: str) -> str:
    margin = limit - observed
    relation = "within" if margin >= 0 else "over"
    return f"{abs(margin):.2f}{unit} {relation} limit"


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Baseline metric rendering with phase-aware organization.
    Reports only values that exist in `metrics`.
    """
    lines: List[str] = []
    if not metrics:
        return lines

    if "constraint_violations" in metrics:
        violations = metrics.get("constraint_violations") or []
        lines.append("### 1. Design Validation Phase")
        lines.append("- Validation Outcome: FAILED")
        lines.append(f"- Violation Count: {len(violations)}")
        for idx, violation in enumerate(violations[:12], 1):
            lines.append(f"  {idx}. {violation}")
        if len(violations) > 12:
            lines.append(f"  ... and {len(violations) - 12} more.")
        if metrics.get("failure_reason"):
            lines.append(f"- Failure Reason: {metrics['failure_reason']}")
        if "step_count" in metrics:
            lines.append(f"- Evaluation Step: {metrics['step_count']}")
        return lines

    lines.append("### 1. Structural State")
    if "structure_mass" in metrics:
        mass = _safe_float(metrics.get("structure_mass"))
        max_mass = _safe_float(metrics.get("max_structure_mass"))
        if mass is not None:
            if max_mass is not None:
                lines.append(
                    f"- Structure Mass: {mass:.2f} kg / {max_mass:.2f} kg "
                    f"({_signed_margin_str(mass, max_mass, ' kg')})"
                )
            else:
                lines.append(f"- Structure Mass: {mass:.2f} kg")
    elif "max_structure_mass" in metrics:
        lines.append(f"- Max Structure Mass: {metrics['max_structure_mass']}")

    if "beam_count" in metrics:
        if "max_beam_count" in metrics:
            lines.append(f"- Beam Count: {metrics['beam_count']} / {metrics['max_beam_count']}")
        else:
            lines.append(f"- Beam Count: {metrics['beam_count']}")

    if "joint_count" in metrics:
        if "terrain_joint_count" in metrics:
            try:
                beam_to_beam = int(metrics["joint_count"]) - int(metrics["terrain_joint_count"])
                lines.append(
                    f"- Joints: total={metrics['joint_count']}, terrain={metrics['terrain_joint_count']}, "
                    f"beam-to-beam={beam_to_beam}"
                )
            except (TypeError, ValueError):
                lines.append(f"- Joint Count: {metrics['joint_count']}")
                lines.append(f"- Terrain Joint Count: {metrics['terrain_joint_count']}")
        else:
            lines.append(f"- Joint Count: {metrics['joint_count']}")
    elif "terrain_joint_count" in metrics:
        lines.append(f"- Terrain Joint Count: {metrics['terrain_joint_count']}")

    if "structure_broken" in metrics:
        integrity = "BROKEN" if metrics["structure_broken"] else "INTACT"
        lines.append(f"- Structural Integrity Flag: {integrity}")
        if metrics["structure_broken"] and metrics.get("first_joint_break_step"):
            lines.append(f"- First Joint Failure Step: {metrics['first_joint_break_step']}")

    lines.append("\n### 2. Containment State")
    if "initial_particle_count" in metrics:
        lines.append(f"- Initial Particles: {metrics['initial_particle_count']}")
    if "leaked_particle_count" in metrics:
        lines.append(f"- Leaked Particles (scored): {metrics['leaked_particle_count']}")
    if "retained_particle_count" in metrics:
        lines.append(f"- Retained Particles: {metrics['retained_particle_count']}")
    if "current_particle_count" in metrics:
        lines.append(f"- Active Particles in Simulation: {metrics['current_particle_count']}")

    leak_pct = _safe_float(metrics.get("leakage_rate_percent"))
    limit_pct = _safe_float(metrics.get("leakage_limit_percent"))
    if leak_pct is not None:
        if limit_pct is not None:
            lines.append(
                f"- Leakage Rate: {leak_pct:.2f}% / {limit_pct:.2f}% "
                f"({_signed_margin_str(leak_pct, limit_pct, ' pp')})"
            )
        else:
            lines.append(f"- Leakage Rate: {leak_pct:.2f}%")

    if "containment_percent" in metrics:
        cp = _safe_float(metrics.get("containment_percent"))
        if cp is not None:
            lines.append(f"- Containment Percent: {cp:.2f}%")

    lines.append("\n### 3. Evaluation Outcome")
    if "step_count" in metrics:
        lines.append(f"- Step Count: {metrics['step_count']}")
    if "success" in metrics:
        lines.append(f"- Success Flag: {metrics['success']}")
    if "failed" in metrics:
        lines.append(f"- Failed Flag: {metrics['failed']}")
    if metrics.get("failure_reason"):
        lines.append(f"- Failure Reason: {metrics['failure_reason']}")

    return lines


def get_improvement_suggestions(
    metrics: Dict[str, Any],
    score: float,
    success: bool,
    failed: bool,
    failure_reason: str = None,
    error: str = None,
) -> List[str]:
    """
    Process-aware diagnostics:
    - identifies mechanism and trade-offs from available metrics
    - avoids implementation spoilers
    - uses dynamic limits from metrics only
    """
    del score  # Score is binary for this task; diagnostics use physical metrics.

    tips: List[str] = []
    reason = f"{error or ''} {failure_reason or ''}".lower()

    if "constraint_violations" in metrics:
        violations = metrics.get("constraint_violations") or []
        text = " ".join(str(v).lower() for v in violations)
        tips.append(
            "Root-cause chain: failure occurred during design validation, so runtime disturbance handling "
            "was never reached."
        )
        if "mass" in text and ("exceeds" in text or "maximum" in text):
            tips.append(
                "Mass-limited regime: the design violates mass budget, so static loading allowance is already "
                "exhausted before dynamic loads are applied."
            )
        if "beam count" in text:
            tips.append(
                "Topology cardinality mismatch: beam count is outside allowed bounds, preventing valid "
                "structural evaluation."
            )
        if "joint count" in text or ("joint" in text and "exceeds" in text):
            tips.append(
                "Connection-density limit reached: the weld network complexity exceeds the allowed joint budget."
            )
        if "outside build zones" in text or "build zone" in text:
            tips.append(
                "Boundary proximity issue: at least one beam violates strip/y placement constraints."
            )
        if "underflow" in text or "below y=" in text:
            tips.append(
                "Underflow-gap violation: geometry intersects the mandatory low-clearance exclusion region."
            )
        if "middle strip" in text or "right strip" in text or "left strip" in text:
            tips.append(
                "Strip-occupancy mismatch: required strip occupancy constraints are not simultaneously satisfied."
            )
        if "span" in text:
            tips.append(
                "Gate-span condition unmet: the structure does not provide required left-to-right strip presence."
            )
        if "connected structure" in text or "connected component" in text or "isolated" in text:
            tips.append(
                "Connectivity failure: the dam is not a single beam-to-beam connected component."
            )
        if "vertical band" in text or "band y=" in text:
            tips.append(
                "Vertical distribution imbalance: at least one required height band has insufficient beam centers."
            )
        if "height" in text or "width" in text:
            tips.append(
                "Member-dimension limit exceeded: at least one beam violates geometric size bounds."
            )
        return tips

    leak_pct = _safe_float(metrics.get("leakage_rate_percent"))
    leak_limit_pct = _safe_float(metrics.get("leakage_limit_percent"))
    structure_broken = bool(metrics.get("structure_broken", False))

    leakage_exceeded = (
        leak_pct is not None
        and leak_limit_pct is not None
        and leak_pct > leak_limit_pct
    )

    if failed:
        if structure_broken and leakage_exceeded:
            tips.append(
                "Failure pattern: both integrity loss and leakage-limit exceedance are present."
            )
        elif structure_broken:
            tips.append(
                "Primary failure mode: structural integrity loss (beam-to-beam joint reduction observed)."
            )
        elif leakage_exceeded:
            tips.append(
                "Primary failure mode: containment deficit (leakage rate exceeds current stage limit)."
            )
        else:
            tips.append(
                "Failure reported without a direct metric exceedance signature; inspect failure reason text and "
                "full metric trace for hidden ordering effects."
            )

    if failed and "joints broke" in reason and not structure_broken:
        tips.append(
            "Consistency check: failure reason references broken joints, but structural break flag is not set; "
            "verify step-wise metric reporting consistency."
        )
    if failed and "leakage rate" in reason and (leak_pct is None or leak_limit_pct is None):
        tips.append(
            "Observability gap: failure reason references leakage, but leakage metrics are incomplete in this record."
        )

    if success and not tips:
        tips.append(
            "Run succeeded under current criteria. Use metric margins (mass/leakage buffers) to evaluate robustness "
            "against stage mutations."
        )

    return tips
