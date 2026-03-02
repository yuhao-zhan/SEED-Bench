"""
Task-specific feedback for D-06: The Catch
Returns process and outcome physical metrics for debugging and improvement (ref S_01).
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    parts = []
    # Primary outcome
    if "ball_x" in metrics:
        parts.append(f"**Ball position**: x={metrics['ball_x']:.2f} m, y={metrics['ball_y']:.2f} m")
    if "ball_speed" in metrics:
        parts.append(f"**Ball speed**: {metrics['ball_speed']:.2f} m/s (caught if < 0.4 m/s)")
    if "ball_caught" in metrics:
        parts.append(f"**Ball caught**: {'Yes' if metrics['ball_caught'] else 'No'}")
    if "structure_smashed" in metrics:
        parts.append(f"**Structure smashed**: {'Yes' if metrics['structure_smashed'] else 'No'}")
    # Structure
    if "structure_mass" in metrics:
        parts.append(f"**Catcher mass**: {metrics['structure_mass']:.2f} kg")
        if "max_structure_mass" in metrics:
            parts.append(f"**Mass limit**: {metrics['max_structure_mass']:.0f} kg")
        if "mass_budget_used_pct" in metrics:
            parts.append(f"**Mass budget used**: {metrics['mass_budget_used_pct']:.1f}%")
    if "joint_count" in metrics:
        parts.append(f"**Joints remaining**: {metrics['joint_count']}")
    if "max_joint_force_limit" in metrics:
        parts.append(f"**Joint force limit**: {metrics['max_joint_force_limit']:.0f} N")
    if "step_count" in metrics:
        parts.append(f"**Simulation steps**: {metrics['step_count']}")

    # Physical state (process/result indicators)
    if "ball_vx" in metrics or "ball_speed_vs_threshold" in metrics:
        parts.append("\n**Physical state / process**")
        if "ball_vx" in metrics and "ball_vy" in metrics:
            parts.append(f"- Ball velocity: vx={metrics['ball_vx']:.3f} m/s, vy={metrics['ball_vy']:.3f} m/s")
        if "ball_speed_vs_threshold" in metrics:
            diff = metrics["ball_speed_vs_threshold"]
            parts.append(f"- Ball speed vs catch threshold (0.4 m/s): {diff:+.3f} m/s (negative = caught)")

    if metrics.get("uncaptured_positions"):
        parts.append("\n**Uncaptured balls (add coverage in these regions)**")
        for idx, ux, uy in metrics["uncaptured_positions"]:
            parts.append(f"- Ball {idx} landed at x≈{ux:.1f}, y≈{uy:.1f}")
    excluded = {"ball_x", "ball_y", "ball_vx", "ball_vy", "ball_speed", "success", "failed", "failure_reason",
                "step_count", "structure_mass", "max_structure_mass", "structure_smashed", "ball_caught",
                "joint_count", "max_joint_force_limit", "mass_budget_used_pct", "ball_speed_vs_threshold",
                "uncaptured_positions"}
    other = {k: v for k, v in metrics.items() if k not in excluded}
    if other:
        parts.append("\n**Other metrics**")
        for k, v in other.items():
            parts.append(f"- {k}: {v:.3f}" if isinstance(v, float) else f"- {k}: {v}")
    return parts


def get_improvement_suggestions(metrics: Dict[str, Any], score: float, success: bool, failed: bool,
                                failure_reason: str = None, error: str = None) -> List[str]:
    suggestions = []
    if error:
        if "structure mass" in error.lower() and "exceeds" in error.lower():
            suggestions.append("- Reduce catcher mass to stay within 10 kg")
        if "build zone" in error.lower() or "outside" in error.lower():
            suggestions.append("- Place all beam centers inside build zone x=[7, 11], y=[0.5, 5.5]; max 7 beams")
    elif failed:
        if failure_reason and "design constraint" in (failure_reason or "").lower():
            if "anchored" in (failure_reason or "").lower() or "unanchored" in (failure_reason or "").lower():
                suggestions.append("- Anchor at least one beam to ground: add_joint(body, None, (x, 0.5), 'rigid') — unanchored beams are invalid")
            if "mass" in (failure_reason or "").lower():
                suggestions.append("- Reduce total mass below 10 kg")
            if "build zone" in (failure_reason or "").lower() or "beam count" in (failure_reason or "").lower():
                suggestions.append("- Keep all parts inside build zone; max 9 beams; avoid forbidden zones and sweeper bands")
        elif failure_reason and "structure smashed" in (failure_reason or "").lower():
            suggestions.append("- Reduce peak and sustained force on joints: add buffering (low restitution, many joints)")
            suggestions.append("- Spread impact over many joints; sustained high load can also cause failure — use softer materials (density ~0.04)")
        elif failure_reason and "sequential" in (failure_reason or "").lower():
            suggestions.append("- Use lower restitution (e.g. 0.01) so balls absorb quickly; each must be caught before the next arrives")
            suggestions.append("- Ball-ball collisions can eject balls if they pile up; design for sequential absorption")
        elif failure_reason and ("ball not caught" in (failure_reason or "").lower() or "not all" in (failure_reason or "").lower()):
            suggestions.append("- Three focal regions required: left, middle-right, far-right — use uncaptured ball positions in feedback to add missing coverage")
            suggestions.append("- Use set_material_properties(body, restitution=0.1) to absorb impact")
    elif not success:
        if metrics.get("structure_smashed", False):
            suggestions.append("- Structure was damaged; increase buffering to keep joint forces below limit")
        elif not metrics.get("ball_caught", False):
            if metrics.get("uncaptured_positions"):
                suggestions.append("- Add catcher coverage where uncaptured balls landed (see feedback); you need all three regions: left, middle-right, far-right")
            else:
                suggestions.append("- Ball was not stopped; improve catcher placement or absorption")
    return suggestions
