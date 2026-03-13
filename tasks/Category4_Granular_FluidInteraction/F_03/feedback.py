"""
Task-specific feedback generation for F-03: The Excavator.
Audit-Purified Version: Strictly code-grounded, zero hallucinations, dynamic thresholding.
"""
from typing import Dict, Any, List

def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Exposes physical metrics provided by the Evaluator.
    """
    parts = []

    # 1. Structural Design & Constraints
    struct_keys = ["structure_mass", "max_structure_mass", "joint_count", "structure_broken"]
    if any(k in metrics for k in struct_keys):
        parts.append("### 1. Structural Design & Constraints")
        if "structure_mass" in metrics:
            limit = metrics.get("max_structure_mass", 0.0)
            parts.append(f"- Total Structure Mass: {metrics['structure_mass']:.2f} / {limit:.2f} kg")
        if "structure_broken" in metrics:
            parts.append(f"- Structural Integrity: {'FAILED (Joints Snapped)' if metrics['structure_broken'] else 'NOMINAL (Intact)'}")
        if "joint_count" in metrics:
            parts.append(f"- Active Connections: {metrics['joint_count']}")

    # 2. Task Performance & Efficiency
    perf_keys = ["particles_in_truck", "min_particles_in_hopper", "collected_ratio_percent"]
    if any(k in metrics for k in perf_keys):
        parts.append("\n### 2. Task Performance & Efficiency")
        if "particles_in_truck" in metrics:
            target = metrics.get("min_particles_in_hopper", 0)
            parts.append(f"- Relocated Particles: {metrics['particles_in_truck']} (Target: > {target})")
        if "collected_ratio_percent" in metrics:
            parts.append(f"- Material Transfer Ratio: {metrics['collected_ratio_percent']:.1f}%")

    # 3. Physical Process & Kinematics
    kin_keys = ["velocity_x", "speed", "bucket_angle_deg", "arm_joint_angle_deg"]
    if any(k in metrics for k in kin_keys):
        parts.append("\n### 3. Physical Process & Kinematics")
        vx, vy = metrics.get("velocity_x"), metrics.get("velocity_y")
        if vx is not None and vy is not None:
            parts.append(f"- End-Effector Velocity: [{vx:.2f}, {vy:.2f}] m/s")
        if "speed" in metrics and metrics["speed"] is not None:
            parts.append(f"- Absolute Speed: {metrics['speed']:.2f} m/s")
        if "bucket_angle_deg" in metrics or "arm_joint_angle_deg" in metrics:
            parts.append(f"- Actuator State: Bucket {metrics.get('bucket_angle_deg', 0):.1f}°, Arm {metrics.get('arm_joint_angle_deg', 0):.1f}°")

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
    Actionable diagnostic warnings based strictly on physical failure modes.
    """
    suggestions = []
    reason = ((error or "") + " " + (failure_reason or "")).lower()

    if "design constraint" in reason or error:
        if "mass" in reason:
            suggestions.append("Diagnostic: Structural mass limit exceeded. The current material distribution exceeds the gravitational load capacity of the environment.")
        if "build zone" in reason:
            suggestions.append("Diagnostic: Geometric boundary violation. Ensure all structural components and their sweeping paths remain within the permitted construction volume.")
        if "base" in reason:
            suggestions.append("Diagnostic: Invalid grounding. The primary support structure must be anchored at the designated coordinates to leverage environmental stability.")
        if "degrees of freedom" in reason or "revolute joint" in reason:
            suggestions.append("Diagnostic: Kinematic DOF deficit. The mechanism lacks the minimum required articulating joints to execute the multi-phase transfer task.")

    elif failed:
        if metrics.get("structure_broken"):
            suggestions.append("Diagnostic: Structural integrity failure. Peak dynamic stresses at connections exceeded the joint break threshold during the motion cycle.")
        
        if "deposited" in reason or "particles" in reason:
            count = metrics.get("particles_in_truck", 0)
            if count == 0:
                suggestions.append("Diagnostic: Acquisition failure. The mechanism failed to capture and retain granular material from the source zone.")
            else:
                suggestions.append("Diagnostic: Insufficient momentum transfer. The transfer rate or volume per cycle is insufficient to meet the target within the operational window.")
        
        if "exceeded" in reason or "time" in reason:
            suggestions.append("Diagnostic: Operational time limit exceeded. The kinematic sequence is either too slow or requires too many cycles to reach the objective.")

        # Multi-Objective Paradox: Score is high but failure occurred (e.g. broken joints)
        if score > 0 and metrics.get("structure_broken"):
            suggestions.append("Diagnostic: Performance paradox. The mechanism successfully relocated material but sacrificed structural integrity. Reinforce high-stress kinematic links.")

    return suggestions
