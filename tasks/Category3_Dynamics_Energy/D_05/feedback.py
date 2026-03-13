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
    No suggestions; purely factual state and measurements.
    """
    parts = []

    # —— Outcome (always present from evaluator) ——
    if "shell_broken" in metrics:
        parts.append(f"**Target Shell**: {'Broken' if metrics['shell_broken'] else 'Intact'}")
    if "success" in metrics:
        parts.append(f"**Outcome**: {'Success' if metrics['success'] else 'Failed'}")
    if "step_count" in metrics:
        parts.append(f"**Simulation Steps**: {metrics['step_count']}")

    # —— Hammer state at termination (when agent_body was provided) ——
    if "hammer_x" in metrics and "hammer_y" in metrics:
        parts.append(f"**Hammer Position (final)**: (x: {metrics['hammer_x']:.2f} m, y: {metrics['hammer_y']:.2f} m)")
    if "velocity_x" in metrics and "velocity_y" in metrics:
        parts.append(f"**Hammer Velocity (final)**: ({metrics['velocity_x']:.2f}, {metrics['velocity_y']:.2f}) m/s")
    if "speed" in metrics:
        parts.append(f"**Speed (magnitude)**: {metrics['speed']:.2f} m/s")
    if "angular_velocity" in metrics:
        parts.append(f"**Angular Velocity (final)**: {metrics['angular_velocity']:.2f} rad/s")
    if "kinetic_energy" in metrics:
        parts.append(f"**Kinetic Energy (final)**: {metrics['kinetic_energy']:.2f} J")

    # —— Boundary / proximity (only from existing metrics) ——
    if all(k in metrics for k in ("hammer_x", "hammer_y", "shell_x", "shell_y")):
        dx = metrics["hammer_x"] - metrics["shell_x"]
        dy = metrics["hammer_y"] - metrics["shell_y"]
        if _is_finite(dx) and _is_finite(dy):
            dist = math.sqrt(dx * dx + dy * dy)
            parts.append(f"**Distance to Shell Center**: {dist:.2f} m")

    # —— Obstacle / collision (root-cause ordering matches evaluator) ——
    obs = []
    if metrics.get("hammer_hit_slot_bar"): obs.append("Slot Bar (oscillating)")
    if metrics.get("hammer_hit_slot_wall"): obs.append("Slot Barrier")
    if metrics.get("hammer_hit_pendulum"): obs.append("Pendulum")
    if metrics.get("hammer_hit_gate"): obs.append("Gate 1")
    if metrics.get("hammer_hit_gate2"): obs.append("Gate 2")
    if metrics.get("hammer_hit_wall"): obs.append("Central Wall")
    if obs:
        parts.append(f"**Collision (first obstacle hit)**: {obs[0]}" if len(obs) == 1 else f"**Collisions**: {', '.join(obs)}")

    # —— Design constraints (dynamic thresholds from metrics) ——
    if "structure_mass" in metrics:
        mass = metrics["structure_mass"]
        limit = metrics.get("max_structure_mass")
        if limit is not None and _is_finite(limit):
            parts.append(f"**Structure Mass**: {mass:.2f} kg / {limit:.1f} kg (limit)")
        else:
            parts.append(f"**Structure Mass**: {mass:.2f} kg")

    # —— Environment / terrain (only if present in metrics) ——
    if "shell_x" in metrics and "shell_y" in metrics:
        parts.append(f"**Shell Position**: ({metrics['shell_x']:.1f}, {metrics['shell_y']:.1f}) m")
    if "shell_break_force" in metrics and _is_finite(metrics.get("shell_break_force")):
        parts.append(f"**Shell Break Threshold (environment)**: {metrics['shell_break_force']:.0f} N")
    if metrics.get("central_wall"):
        parts.append("**Central Wall**: Present (path blocked; high arc required)")

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

    # —— Numerical instability (physics engine limits) ——
    for key in ("speed", "kinetic_energy", "velocity_x", "velocity_y", "angular_velocity"):
        val = metrics.get(key)
        if val is not None and not _is_finite(val):
            suggestions.append("- **Numerical instability**: Simulation state contains non-finite values; trajectory or integration may be invalid.")
            break

    # —— Design constraint violations (dynamic threshold) ——
    mass = metrics.get("structure_mass")
    max_mass = metrics.get("max_structure_mass")
    if max_mass is not None and _is_finite(max_mass) and mass is not None and _is_finite(mass) and mass > max_mass:
        suggestions.append("- **Mass budget exceeded**: Total structure mass exceeds the allowed limit for this environment. Consider a better strength-to-weight trade-off.")

    if "outside build zone" in msg or "build zone" in msg:
        suggestions.append("- **Spatial constraint**: At least one component lies outside the permitted build zone. Anchor and beams must remain within the stated bounds.")

    # —— Root-cause chain: first failure mode (evaluator order) ——
    if failed and failure_reason:
        if "oscillating bar" in msg or metrics.get("hammer_hit_slot_bar"):
            suggestions.append("- **Timing vs. geometry**: The hammer contacted the moving bar inside the slot. The release phase and the bar's oscillation period are coupled; infer the safe window from trial rather than a fixed step.")
        elif "slot barrier" in msg or "narrow" in msg or metrics.get("hammer_hit_slot_wall"):
            suggestions.append("- **Trajectory vs. gap**: The head did not pass through the vertical gap. Trajectory shape (arc height and width) and head dimensions determine clearance.")
        elif "pendulum" in msg or metrics.get("hammer_hit_pendulum"):
            suggestions.append("- **Aperture–timing conflict**: The hammer hit a pendulum before reaching the shell. Swing timing and pendulum period determine when the path is clear.")
        elif "gate" in msg or metrics.get("hammer_hit_gate") or metrics.get("hammer_hit_gate2"):
            suggestions.append("- **Gate timing**: Transit occurred when a gate was closed. The open window is time-dependent; align launch or swing phase with that window.")
        elif "central wall" in msg or "over" in msg or metrics.get("hammer_hit_wall"):
            suggestions.append("- **Path obstruction**: The direct line to the shell is blocked. A higher arc or different pivot height may be required to clear the obstacle.")
        elif "shell not broken" in msg or (not metrics.get("shell_broken") and not any([
            metrics.get("hammer_hit_slot_bar"), metrics.get("hammer_hit_slot_wall"),
            metrics.get("hammer_hit_pendulum"), metrics.get("hammer_hit_gate"),
            metrics.get("hammer_hit_gate2"), metrics.get("hammer_hit_wall")
        ])):
            # Failure was timeout / insufficient impact (no obstacle hit)
            suggestions.append("- **Impact deficit**: The shell was not broken by termination. Delivered kinetic energy and peak force depend on head mass, swing speed, and damping; the break threshold may vary by environment.")

    # —— Multi-objective trade-off ——
    if success and failed is False:
        pass  # No suggestion needed for success.
    elif not success and metrics.get("shell_broken") and (
        metrics.get("hammer_hit_pendulum") or metrics.get("hammer_hit_gate") or
        metrics.get("hammer_hit_gate2") or metrics.get("hammer_hit_wall") or
        metrics.get("hammer_hit_slot_wall") or metrics.get("hammer_hit_slot_bar")
    ):
        suggestions.append("- **Constraint ordering**: The shell was broken but an obstacle was hit first. Success requires both breakage and no prior collision; trajectory must satisfy all constraints.")

    mass_ok = (max_mass is None or mass is None or not _is_finite(mass) or not _is_finite(max_mass) or mass <= max_mass)
    if not success and mass_ok and "shell not broken" in msg:
        suggestions.append("- **Energy delivery**: Mass budget is satisfied but impact was insufficient. Consider how moment of inertia and swing kinematics affect the energy transferred to the shell.")

    return suggestions
