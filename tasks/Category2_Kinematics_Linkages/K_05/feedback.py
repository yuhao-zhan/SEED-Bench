"""
Task-specific feedback generation for K-05: The Lifter
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Expose high-resolution physical metrics for K-05: The Lifter.
    """
    metric_parts = []
    
    if 'object_y' in metrics:
        metric_parts.append(f"**Payload Kinematics**: Altitude y={metrics['object_y']:.2f}m")
        if 'height_gained' in metrics:
            metric_parts.append(f"- Net Vertical Displacement: {metrics['height_gained']:.2f}m")
        if 'object_velocity_y' in metrics:
            metric_parts.append(f"- Vertical Velocity: {metrics['object_velocity_y']:.3f} m/s")

    if 'joint_count' in metrics:
        status = "CRITICAL FAILURE" if metrics.get('structure_broken', False) else "NOMINAL"
        metric_parts.append(f"**Structural Health**: {status}")
        metric_parts.append(f"- Active Kinematic Constraints: {metrics['joint_count']} joints intact")

    if 'structure_mass' in metrics:
        max_m = metrics.get('max_structure_mass', float('inf'))
        metric_parts.append(f"**Structural Profile**: Integrated Mass {metrics['structure_mass']:.2f}kg")
        if max_m != float('inf'):
            utilization = (metrics['structure_mass'] / max_m) * 100
            metric_parts.append(f"- Mass Budget Utilization: {utilization:.1f}%")

    if 'steps_with_object_above_target' in metrics:
        req = metrics.get('min_simulation_steps_required', 1)
        metric_parts.append(f"- Sustain Duration: {metrics['steps_with_object_above_target']}/{req} steps at target altitude")

    return metric_parts


def get_improvement_suggestions(metrics: Dict[str, Any], score: float, success: bool, 
                                failed: bool, failure_reason: str = None, 
                                error: str = None) -> List[str]:
    """
    Generate diagnostic physical feedback for K-05: The Lifter.
    """
    suggestions = []
    
    if error or (failed and failure_reason and "design constraint" in failure_reason.lower()):
        if "mass" in (error or failure_reason).lower():
            max_m = metrics.get('max_structure_mass', 0.0)
            suggestions.append(f"DIAGNOSTIC: Structural mass ({metrics.get('structure_mass', 0):.2f}kg) exceeds the environmental threshold ({max_m:.1f}kg).")
        return suggestions

    if failed:
        if "integrity lost" in failure_reason.lower() or metrics.get('structure_broken', False):
            suggestions.append("DIAGNOSTIC: Structural yield detected. Internal reaction forces exceeded the failure threshold.")
            suggestions.append("ADVISORY: Analyze the mechanical advantage. High loads at the start of the stroke may cause extreme joint stress.")
        
        elif "not lifted" in failure_reason.lower() or metrics.get('height_gained', 0) < 0.1:
            suggestions.append("DIAGNOSTIC: Stalling detected. The input motor torque is not overcoming static load.")

    elif not success:
        progress = metrics.get('progress', 0.0)
        if 0 < progress < 100:
            suggestions.append(f"DIAGNOSTIC: Functional lift detected but capacity is limited ({progress:.1f}% of target).")
        
        if metrics.get('steps_with_object_above_target', 0) < metrics.get('min_simulation_steps_required', 0) and progress >= 100:
            suggestions.append("DIAGNOSTIC: Target altitude achieved but dynamic stability is insufficient to sustain the position.")

    return suggestions
