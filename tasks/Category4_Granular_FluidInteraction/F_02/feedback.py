"""
Task-specific feedback for F-02: The Amphibian
Returns rich physical metrics (position, velocity, progress, integrity) for process and result.
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    metric_parts = []
    # Position and target
    if "vehicle_front_x" in metrics and metrics["vehicle_front_x"] is not None:
        metric_parts.append(f"**Vehicle front x**: {metrics['vehicle_front_x']:.2f}m")
    if "target_x" in metrics:
        metric_parts.append(f"**Target x**: {metrics['target_x']:.2f}m")
    if "progress" in metrics and metrics["progress"] is not None:
        metric_parts.append(f"**Progress toward shore**: {metrics['progress']:.1f}%")
    if "vehicle_lowest_y" in metrics and metrics["vehicle_lowest_y"] is not None:
        metric_parts.append(f"**Vehicle lowest y**: {metrics['vehicle_lowest_y']:.2f}m (sink if < -0.5)")
    # Velocity (process metric)
    if "velocity_x" in metrics and metrics["velocity_x"] is not None:
        metric_parts.append(f"**Front velocity x**: {metrics['velocity_x']:.2f} m/s")
    if "velocity_y" in metrics and metrics["velocity_y"] is not None:
        metric_parts.append(f"**Front velocity y**: {metrics['velocity_y']:.2f} m/s")
    if "velocity_x" in metrics and "velocity_y" in metrics and metrics.get("velocity_x") is not None and metrics.get("velocity_y") is not None:
        v = (metrics["velocity_x"]**2 + metrics["velocity_y"]**2)**0.5
        metric_parts.append(f"**Speed**: {v:.2f} m/s")
    # Mass and integrity
    if "structure_mass" in metrics:
        metric_parts.append(f"**Structure mass**: {metrics['structure_mass']:.2f} kg")
        if "max_structure_mass" in metrics:
            metric_parts.append(f"**Mass limit**: {metrics['max_structure_mass']:.0f} kg")
    if "structure_broken" in metrics:
        metric_parts.append(f"**Structure integrity**: {'BROKEN' if metrics['structure_broken'] else 'INTACT'}")
    if "joint_count" in metrics:
        metric_parts.append(f"**Joint count**: {metrics['joint_count']}")
    if "step_count" in metrics:
        metric_parts.append(f"**Simulation steps**: {metrics['step_count']}")
    # Outcome
    if "success" in metrics:
        metric_parts.append(f"**Success**: {metrics['success']}")
    if "failed" in metrics and metrics.get("failed"):
        metric_parts.append(f"**Failure reason**: {metrics.get('failure_reason', 'N/A')}")
    excluded = {
        "vehicle_front_x", "vehicle_lowest_y", "target_x", "progress", "velocity_x", "velocity_y",
        "structure_mass", "max_structure_mass", "structure_broken", "joint_count", "step_count",
        "success", "failed", "failure_reason",
    }
    other = {k: v for k, v in metrics.items() if k not in excluded}
    if other:
        metric_parts.append("\n**Additional metrics**:")
        for k, v in other.items():
            metric_parts.append(f"- {k}: {v:.3f}" if isinstance(v, float) else f"- {k}: {v}")
    return metric_parts


def get_improvement_suggestions(
    metrics: Dict[str, Any], score: float, success: bool, failed: bool,
    failure_reason: str = None, error: str = None,
) -> List[str]:
    suggestions = []
    if error:
        error_lower = error.lower()
        if "structure mass" in error_lower and "exceeds" in error_lower:
            suggestions.append(f"- Reduce vehicle mass to be within {metrics.get('max_structure_mass', 600):.0f} kg")
        elif "build zone" in error_lower:
            suggestions.append("- Place all beams within build zone x=[2, 8], y=[0, 4]")
    elif failed:
        if failure_reason and "design constraint" in failure_reason.lower():
            if "structure mass" in failure_reason.lower():
                suggestions.append(f"- Keep total mass below {metrics.get('max_structure_mass', 600):.0f} kg")
            if "build zone" in failure_reason.lower():
                suggestions.append("- Ensure all beams are inside build zone on the left bank")
        elif failure_reason and "sank" in failure_reason.lower():
            suggestions.append("- Improve buoyancy: use a wider or longer hull so the vehicle floats")
            suggestions.append("- Avoid heavy concentrated mass that pulls the vehicle under")
        elif failure_reason and ("reach right bank" in failure_reason.lower() or "reach shore" in failure_reason.lower()):
            suggestions.append("- Water has strong current, quadratic drag, and a **headwind burst** (x≈15–19). Each body has a **3-step cooldown** (can only thrust every 3 steps): use **9 paddles** (9 bodies) so 3 thrust each step. Pass step_count: apply_force(body, fx, fy, step_count=step_count).")
            suggestions.append("- **Three pillars** in the water block the path (x≈14, 17, 20). Apply **lift** (positive fy) when front_x is in [11.5–16] and [16–22] to rise over them; otherwise you collide and get stuck.")
            suggestions.append("- Keep total mass under 600 kg; lighter vehicles need less thrust. Balance with stability in wind (wide, low hull).")
        elif failure_reason and "structure integrity" in failure_reason.lower():
            suggestions.append("- Strengthen joints; water and motion can stress the structure")
    elif not success:
        if metrics.get("vehicle_front_x") is not None and metrics.get("vehicle_front_x", 0) < metrics.get("target_x", 26):
            suggestions.append("- Use apply_force to paddle and reach x >= 26m")
            if metrics.get("velocity_x") is not None and metrics.get("velocity_x", 0) < 0.5:
                suggestions.append("- Increase paddling force or apply force every step to gain speed")
    return suggestions
