"""
Task-specific feedback for F-03: The Excavator.
Returns process and outcome metrics (bucket position/velocity, particles in hopper).
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    metric_parts = []

    # Primary outcome: collection
    if "initial_particle_count" in metrics:
        metric_parts.append(f"**Initial particles**: {metrics['initial_particle_count']}")
    if "particles_in_truck" in metrics:
        metric_parts.append(f"**Particles in hopper**: {metrics['particles_in_truck']}")
    if "min_particles_in_hopper" in metrics:
        metric_parts.append(f"**Target (min in hopper)**: {metrics['min_particles_in_hopper']}")
    if "collected_ratio_percent" in metrics:
        metric_parts.append(f"**Collected ratio**: {metrics['collected_ratio_percent']:.1f}%")
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

    # Physical state: bucket (agent) position and velocity
    if "agent_x" in metrics or "velocity_x" in metrics:
        metric_parts.append("\n**Bucket (agent) state**:")
        if "agent_x" in metrics and "agent_y" in metrics:
            metric_parts.append(f"- Position: x={metrics['agent_x']:.3f} m, y={metrics['agent_y']:.3f} m")
        if "velocity_x" in metrics and "velocity_y" in metrics:
            metric_parts.append(f"- Velocity: vx={metrics['velocity_x']:.3f} m/s, vy={metrics['velocity_y']:.3f} m/s")
        if "speed" in metrics:
            metric_parts.append(f"- Speed: {metrics['speed']:.3f} m/s")
        if "angular_velocity" in metrics:
            metric_parts.append(f"- Angular velocity: {metrics['angular_velocity']:.3f} rad/s")
        if "bucket_angle_rad" in metrics:
            metric_parts.append(f"- Bucket angle: {metrics['bucket_angle_rad']:.3f} rad ({metrics.get('bucket_angle_deg', 0):.1f}°)")
    # Arm and joint angles (process metrics)
    if "arm_joint_angle_rad" in metrics or "arm_x" in metrics:
        metric_parts.append("\n**Arm state**:")
        if "arm_joint_angle_rad" in metrics:
            metric_parts.append(f"- Arm joint angle: {metrics['arm_joint_angle_rad']:.3f} rad ({metrics.get('arm_joint_angle_deg', 0):.1f}°)")
        if "arm_x" in metrics and "arm_y" in metrics:
            metric_parts.append(f"- Arm position: x={metrics['arm_x']:.3f} m, y={metrics['arm_y']:.3f} m")
        if "arm_angle_rad" in metrics:
            metric_parts.append(f"- Arm body angle: {metrics['arm_angle_rad']:.3f} rad")

    excluded = {
        "initial_particle_count", "particles_in_truck", "collected_ratio", "collected_ratio_percent",
        "min_particles_in_hopper", "min_collected_ratio", "min_collected_ratio_percent",
        "structure_mass", "max_structure_mass", "structure_broken", "joint_count", "step_count",
        "success", "failed", "failure_reason",
        "agent_x", "agent_y", "velocity_x", "velocity_y", "speed", "angular_velocity",
        "bucket_angle_rad", "bucket_angle_deg", "arm_joint_angle_rad", "arm_joint_angle_deg",
        "arm_x", "arm_y", "arm_angle_rad",
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
            suggestions.append(f"- Reduce structure mass to be within {metrics.get('max_structure_mass', 800):.0f} kg")
        elif "build zone" in error_lower:
            suggestions.append("- Place all beams within build zone x=[-4, 2], y=[0, 5]")
    elif failed:
        if failure_reason and "design constraint" in failure_reason.lower():
            if "structure mass" in failure_reason.lower():
                suggestions.append(f"- Keep total mass below {metrics.get('max_structure_mass', 800):.0f} kg")
            if "build zone" in failure_reason.lower():
                suggestions.append("- Ensure all beams are inside the build zone between pit and truck")
        elif failure_reason and ("deposited" in failure_reason.lower() or "hopper" in failure_reason.lower()):
            suggestions.append("- Design bucket/scoop to hold material without spilling during rotation")
            suggestions.append("- Use at least 2 DOF (Arm + Bucket) with revolute joints; control motors to scoop at pit and dump at hopper (x=-5.0, y=3.0)")
        elif failure_reason and "structure integrity" in failure_reason.lower():
            suggestions.append("- Strengthen joints; scooping and dumping exert large forces")
    elif not success:
        if (metrics.get("particles_in_truck") or 0) < 15:
            suggestions.append("- Aim to deposit > 15 sand particles into the Hopper within 40 seconds")
    return suggestions
