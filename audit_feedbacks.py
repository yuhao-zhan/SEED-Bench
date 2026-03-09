import os

AUDITED_FEEDBACK_CODE = '''"""
Task-specific feedback generation for Category 4: Granular/Fluid Interaction.
Audit-Purified Version: Zero hallucinations, no hardcoded thresholds, strictly diagnostic.
Grounds all feedback in metrics provided by the environment evaluator.
"""
from typing import Dict, Any, List

def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Exposes physical metrics from the Evaluator metrics dictionary.
    """
    parts = []

    # 1. Structural Design & Constraints
    struct_keys = ["structure_mass", "max_structure_mass", "structure_broken", "joint_count", "beam_count", "terrain_joint_count"]
    if any(k in metrics for k in struct_keys):
        parts.append("### 1. Structural Design & Constraints")
        if "structure_mass" in metrics:
            limit = metrics.get("max_structure_mass")
            limit_str = f" / {limit:.2f} kg" if limit is not None else ""
            parts.append(f"- Total Structure Mass: {metrics['structure_mass']:.2f} kg{limit_str}")
        if "structure_broken" in metrics:
            parts.append(f"- Structural Integrity: {'FAILED (Joints Snapped)' if metrics['structure_broken'] else 'NOMINAL (Intact)'}")
        if "joint_count" in metrics:
            parts.append(f"- Joint Complexity: {metrics['joint_count']} active connections")
        if "beam_count" in metrics:
            parts.append(f"- Component Count: {metrics['beam_count']} beams")

    # 2. Task Performance & Efficiency
    perf_keys = ["leakage_rate_percent", "purity_percent", "delivery_ratio_percent", "cargo_retained", "progress", "particles_in_truck", "particles_in_target"]
    if any(k in metrics for k in perf_keys):
        parts.append("\\n### 2. Task Performance & Efficiency")
        if "leakage_rate_percent" in metrics:
            limit = metrics.get("leakage_limit_percent")
            limit_str = f" (Limit: {limit:.2f}%)" if limit is not None else ""
            parts.append(f"- Leakage Rate: {metrics['leakage_rate_percent']:.2f}%{limit_str}")
        if "purity_percent" in metrics:
            limit = metrics.get("min_purity_percent")
            limit_str = f" (Target: {limit:.1f}%)" if limit is not None else ""
            parts.append(f"- Sorting Purity: {metrics['purity_percent']:.1f}%{limit_str}")
        if "delivery_ratio_percent" in metrics:
            limit = metrics.get("min_delivery_ratio_percent")
            limit_str = f" (Target: {limit:.1f}%)" if limit is not None else ""
            parts.append(f"- Delivery Efficiency: {metrics['delivery_ratio_percent']:.1f}%{limit_str}")
        if "cargo_retained" in metrics:
            total = metrics.get("initial_cargo_count", "N/A")
            parts.append(f"- Cargo Secured: {metrics['cargo_retained']} / {total}")
        if "particles_in_truck" in metrics or "particles_in_target" in metrics:
            count = metrics.get("particles_in_truck") if metrics.get("particles_in_truck") is not None else metrics.get("particles_in_target")
            target = metrics.get("min_particles_in_hopper")
            target_str = f" (Target: {target})" if target is not None else ""
            parts.append(f"- Relocated Particles: {count}{target_str}")
        if "progress" in metrics and metrics["progress"] is not None:
            parts.append(f"- Completion Progress: {metrics['progress']:.1f}%")

    # 3. Physical Process & Kinematics
    kin_keys = ["velocity_x", "speed", "vehicle_lowest_y", "boat_angle_deg", "bucket_angle_deg", "arm_joint_angle_deg"]
    if any(k in metrics for k in kin_keys):
        parts.append("\\n### 3. Physical Process & Kinematics")
        vx, vy = metrics.get("velocity_x"), metrics.get("velocity_y")
        if vx is not None and vy is not None:
            parts.append(f"- Velocity State: [{vx:.2f}, {vy:.2f}] m/s")
        if "speed" in metrics and metrics["speed"] is not None:
            parts.append(f"- Absolute Speed: {metrics['speed']:.2f} m/s")
        if "vehicle_lowest_y" in metrics and metrics["vehicle_lowest_y"] is not None:
            parts.append(f"- Elevation (Lowest Point): {metrics['vehicle_lowest_y']:.2f} m")
        if "boat_angle_deg" in metrics and metrics["boat_angle_deg"] is not None:
            limit = metrics.get("boat_max_angle_deg")
            limit_str = f" (Limit: {limit:.1f}°)" if limit is not None else ""
            parts.append(f"- Tilt/Roll Angle: {metrics['boat_angle_deg']:.1f}°{limit_str}")
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
    Actionable diagnostic warnings without giving design spoilers.
    """
    suggestions = []
    reason = ((error or "") + " " + (failure_reason or "")).lower()

    if "design constraint" in reason or error:
        if "mass" in reason:
            suggestions.append("Diagnostic: Structural mass limit exceeded. Analyze component density and optimize for a higher strength-to-weight ratio.")
        if "build zone" in reason:
            suggestions.append("Diagnostic: Geometric boundary violation. Ensure the structural topology is contained within permitted spatial limits.")
        if "anchor" in reason or "terrain" in reason:
            suggestions.append("Diagnostic: Invalid boundary anchoring. The system relies on prohibited external grounding points.")
        if "joint" in reason:
            suggestions.append("Diagnostic: Topology limit exceeded. The design exceeds the maximum allowed connectivity complexity.")

    elif failed:
        if metrics.get("structure_broken"):
            suggestions.append("Diagnostic: Structural integrity failure. Stress concentrations at connections exceeded the joint break threshold under environmental load.")
        
        if "leakage" in reason:
            suggestions.append("Diagnostic: Containment failure. Evaluate geometric coverage and potential seepage paths caused by hydrostatic pressure.")
        
        if "delivery" in reason or "deposited" in reason or "particles" in reason:
            suggestions.append("Diagnostic: Insufficient momentum transfer. The kinematic sequence failed to relocate material to the target region efficiently.")
        
        if "purity" in reason:
            suggestions.append("Diagnostic: Sorting phase failure. Aperture dimensions or separator dynamics allowed particulate cross-contamination.")
            
        if "sank" in reason or "lowest_y" in reason:
            suggestions.append("Diagnostic: Buoyancy deficit. The displaced fluid volume is insufficient to support the system\\'s total gravitational load.")
        
        if "reach" in reason or "progress" in reason:
            suggestions.append("Diagnostic: Propulsive deficit. Net forward thrust is insufficient to overcome environmental drag and currents.")
        
        if "capsize" in reason or "angle" in reason:
            suggestions.append("Diagnostic: Stability failure. The center-of-gravity and center-of-buoyancy alignment resulted in a critical overturning moment.")

    return suggestions
'''

for i in range(1, 7):
    folder = f'tasks/Category4_Granular_FluidInteraction/F_0{i}'
    feedback_file = os.path.join(folder, 'feedback.py')
    if os.path.exists(feedback_file):
        with open(feedback_file, 'w') as f:
            f.write(AUDITED_FEEDBACK_CODE)
        print(f"Audited and updated {feedback_file}")

