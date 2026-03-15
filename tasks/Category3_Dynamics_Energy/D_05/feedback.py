"""
D-05: The Hammer — process-aware diagnostic feedback.
Dynamics/Energy domain: kinetic energy, impact force, trajectory, and obstacle timing.
All content is derived only from the metrics dict returned by evaluator.evaluate().
No hardcoded environmental thresholds; thresholds are read from metrics (stage-mutable).
"""
from typing import Dict, Any, List
import math


def _is_finite(x: Any) -> bool:
    """Return False if x is NaN, Inf, or not a number."""
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
    Phase-segregated; includes boundary/proximity margins where available.
    No suggestions; purely factual state and measurements.
    """
    parts = []

    # —— Phase: Outcome (always present from evaluator) ——
    if "success" in metrics:
        parts.append(f"**Outcome**: {'Success' if metrics['success'] else 'Failed'}")
    if "shell_broken" in metrics:
        parts.append(f"**Target Shell**: {'Broken' if metrics['shell_broken'] else 'Intact'}")
    if "step_count" in metrics:
        parts.append(f"**Simulation Steps**: {metrics['step_count']}")

    # —— Phase: Final state (hammer at termination; only when agent_body was provided) ——
    if "hammer_x" in metrics and "hammer_y" in metrics:
        parts.append(f"**Hammer Position (final)**: (x: {metrics['hammer_x']:.2f} m, y: {metrics['hammer_y']:.2f} m)")
    if "velocity_x" in metrics and "velocity_y" in metrics:
        parts.append(f"**Hammer Velocity (final)**: ({metrics['velocity_x']:.2f}, {metrics['velocity_y']:.2f}) m/s")
    if "speed" in metrics and _is_finite(metrics.get("speed")):
        parts.append(f"**Speed (magnitude)**: {metrics['speed']:.2f} m/s")
    if "angular_velocity" in metrics and _is_finite(metrics.get("angular_velocity")):
        parts.append(f"**Angular Velocity (final)**: {metrics['angular_velocity']:.2f} rad/s")
    if "kinetic_energy" in metrics and _is_finite(metrics.get("kinetic_energy")):
        parts.append(f"**Kinetic Energy (final)**: {metrics['kinetic_energy']:.2f} J")

    # —— Phase: Proximity & boundary margins (only from existing metrics) ——
    if all(k in metrics for k in ("hammer_x", "hammer_y", "shell_x", "shell_y")):
        dx = metrics["hammer_x"] - metrics["shell_x"]
        dy = metrics["hammer_y"] - metrics["shell_y"]
        if _is_finite(dx) and _is_finite(dy):
            dist = math.sqrt(dx * dx + dy * dy)
            parts.append(f"**Distance to Shell Center**: {dist:.2f} m")
    mass = metrics.get("structure_mass")
    max_mass = metrics.get("max_structure_mass")
    if mass is not None and max_mass is not None and _is_finite(mass) and _is_finite(max_mass) and max_mass > 0:
        margin = max_mass - mass
        parts.append(f"**Mass Budget Margin**: {margin:.2f} kg remaining (structure {mass:.2f} / limit {max_mass:.1f} kg)")

    # —— Phase: Collision / first failure (root-cause ordering matches evaluator) ——
    obs = []
    if metrics.get("hammer_hit_slot_bar"):
        obs.append("Slot Bar (oscillating)")
    if metrics.get("hammer_hit_slot_wall"):
        obs.append("Slot Barrier")
    if metrics.get("hammer_hit_pendulum"):
        obs.append("Pendulum")
    if metrics.get("hammer_hit_gate"):
        obs.append("Gate 1")
    if metrics.get("hammer_hit_gate2"):
        obs.append("Gate 2")
    if metrics.get("hammer_hit_wall"):
        obs.append("Central Wall")
    if obs:
        first = obs[0]
        parts.append(f"**First Obstacle Contact**: {first}" + (f" (also: {', '.join(obs[1:])})" if len(obs) > 1 else ""))

    # —— Phase: Design constraints (dynamic thresholds from metrics) ——
    if "structure_mass" in metrics:
        m = metrics["structure_mass"]
        limit = metrics.get("max_structure_mass")
        if limit is not None and _is_finite(limit):
            parts.append(f"**Structure Mass**: {m:.2f} kg / {limit:.1f} kg (limit)")
        else:
            parts.append(f"**Structure Mass**: {m:.2f} kg")

    # —— Phase: Environment / terrain (only if present in metrics) ——
    if "shell_x" in metrics and "shell_y" in metrics:
        parts.append(f"**Shell Position**: ({metrics['shell_x']:.1f}, {metrics['shell_y']:.1f}) m")
    if "shell_break_force" in metrics and _is_finite(metrics.get("shell_break_force")):
        parts.append(f"**Shell Break Threshold (environment)**: {metrics['shell_break_force']:.0f} N")
    if metrics.get("central_wall"):
        parts.append("**Central Wall**: Present (direct path to shell blocked)")
    if metrics.get("shield_has_window"):
        parts.append("**Shield**: Timed window present")
    if "pendulum_pivot" in metrics:
        parts.append(f"**Pendulum Pivot**: {metrics['pendulum_pivot']}")
    if "pendulum_rod_length" in metrics and _is_finite(metrics.get("pendulum_rod_length")):
        parts.append(f"**Pendulum Rod Length**: {metrics['pendulum_rod_length']:.1f} m")

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
    Diagnostic, process-aware suggestions. No spoilers: diagnose the physical
    mechanism of failure without dictating design or implementation.
    All thresholds are read from metrics (stage-mutation safe).
    """
    suggestions = []
    msg = (error or failure_reason or "").lower()

    # —— Non-finite state (only when evaluator provided these metrics) ——
    for key in ("speed", "kinetic_energy", "velocity_x", "velocity_y", "angular_velocity"):
        val = metrics.get(key)
        if val is not None and not _is_finite(val):
            suggestions.append(
                "- **Invalid simulation state**: Reported velocity or energy values are non-finite; trajectory or integration may be invalid."
            )
            break

    # —— Design constraint violations (threshold from metrics only) ——
    mass = metrics.get("structure_mass")
    max_mass = metrics.get("max_structure_mass")
    if (
        max_mass is not None
        and _is_finite(max_mass)
        and mass is not None
        and _is_finite(mass)
        and mass > max_mass
    ):
        suggestions.append(
            "- **Mass budget exceeded**: Total structure mass exceeds the allowed limit for this environment."
        )

    if "outside build zone" in msg or "build zone" in msg:
        suggestions.append(
            "- **Spatial constraint**: At least one component lies outside the permitted build zone. Anchor and beams must remain within the stated bounds."
        )

    # —— Root-cause chain: what broke first (evaluator order) ——
    if failed and failure_reason:
        if "oscillating bar" in msg or metrics.get("hammer_hit_slot_bar"):
            suggestions.append(
                "- **Timing vs. geometry**: The hammer contacted the moving bar inside the slot. The safe window for passage is time-dependent and coupled to the bar's oscillation."
            )
        elif "slot barrier" in msg or "narrow" in msg or "gap" in msg or metrics.get("hammer_hit_slot_wall"):
            suggestions.append(
                "- **Trajectory vs. gap**: The head contacted the slot barrier before reaching the shell. Clearance through the vertical gap depends on trajectory and geometry."
            )
        elif "pendulum" in msg or metrics.get("hammer_hit_pendulum"):
            suggestions.append(
                "- **Aperture–timing conflict**: The hammer hit a pendulum before reaching the shell. The path is clear only when the pendulum has cleared; timing is critical."
            )
        elif "gate" in msg or metrics.get("hammer_hit_gate") or metrics.get("hammer_hit_gate2"):
            suggestions.append(
                "- **Gate timing**: The hammer contacted a gate before reaching the shell. The gate open window is time-dependent; transit must occur when the gate is open."
            )
        elif "central wall" in msg or "over" in msg or metrics.get("hammer_hit_wall"):
            suggestions.append(
                "- **Path obstruction**: The hammer hit the central wall before reaching the shell. The direct path is blocked; the trajectory must clear the obstacle to reach the shell."
            )
        elif "shell not broken" in msg or (
            not metrics.get("shell_broken")
            and not any(
                [
                    metrics.get("hammer_hit_slot_bar"),
                    metrics.get("hammer_hit_slot_wall"),
                    metrics.get("hammer_hit_pendulum"),
                    metrics.get("hammer_hit_gate"),
                    metrics.get("hammer_hit_gate2"),
                    metrics.get("hammer_hit_wall"),
                ]
            )
        ):
            suggestions.append(
                "- **Impact deficit**: The shell was not broken by termination. Delivered kinetic energy and peak force depend on mass, velocity, and damping; the break threshold may vary by environment."
            )

    # —— Additional diagnostics (only states reachable per evaluator logic) ——
    no_obstacle = not any(
        [
            metrics.get("hammer_hit_pendulum"),
            metrics.get("hammer_hit_gate"),
            metrics.get("hammer_hit_gate2"),
            metrics.get("hammer_hit_wall"),
            metrics.get("hammer_hit_slot_wall"),
            metrics.get("hammer_hit_slot_bar"),
        ]
    )
    mass_ok = (
        max_mass is None
        or mass is None
        or not _is_finite(mass)
        or not _is_finite(max_mass)
        or mass <= max_mass
    )
    if not success and not mass_ok and no_obstacle:
        suggestions.append(
            "- **Mass vs. path**: No obstacle contact was recorded but structure mass exceeds the allowed limit for this environment."
        )

    return suggestions
