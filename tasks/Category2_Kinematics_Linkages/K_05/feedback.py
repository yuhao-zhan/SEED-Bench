"""
Task-specific feedback generation for K-05: The Lifter
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Expose high-resolution physical metrics for K-05: The Lifter.
    """
    metric_parts = []
    
    # Altitude and Displacement
    if 'object_y' in metrics:
        metric_parts.append(f"**Payload State**: Altitude y={metrics['object_y']:.2f}m")
        if 'height_gained' in metrics:
            metric_parts.append(f"- Vertical Displacement: {metrics['height_gained']:.2f}m")
        if 'object_velocity_y' in metrics:
            metric_parts.append(f"- Vertical Velocity: {metrics['object_velocity_y']:.3f} m/s")

    # Structural Integrity
    if 'joint_count' in metrics:
        broken = metrics.get('structure_broken', False)
        status = "CRITICAL FAILURE" if broken else "INTACT"
        metric_parts.append(f"**Structural Status**: {status}")
        metric_parts.append(f"- Active Connections: {metrics['joint_count']} joints")

    # Mass Budget
    if 'structure_mass' in metrics:
        max_m = metrics.get('max_structure_mass', 0.0)
        curr_m = metrics['structure_mass']
        metric_parts.append(f"**Mass Budget**: {curr_m:.2f}kg / {max_m:.1f}kg")

    # Stability and Duration
    if 'steps_with_object_above_target' in metrics:
        req_steps = metrics.get('min_simulation_steps_required', 0)
        curr_steps = metrics['steps_with_object_above_target']
        metric_parts.append(f"**Stability Duration**: {curr_steps} steps held (Target: {req_steps})")

    return metric_parts


def get_improvement_suggestions(metrics: Dict[str, Any], score: float, success: bool, 
                                failed: bool, failure_reason: str = None, 
                                error: str = None) -> List[str]:
    """
    Generate diagnostic physical feedback for K-05: The Lifter.
    """
    suggestions = []
    
    # 1. Handle design constraint violations (Build Zone, Mass Budget)
    if failed and failure_reason and "design constraint" in failure_reason.lower():
        if "mass" in failure_reason.lower():
            max_m = metrics.get('max_structure_mass', 0.0)
            curr_m = metrics.get('structure_mass', 0.0)
            suggestions.append(f"DIAGNOSTIC: Structural mass ({curr_m:.2f}kg) exceeds the environment's current threshold of {max_m:.1f}kg.")
        elif "build zone" in failure_reason.lower():
            suggestions.append("DIAGNOSTIC: Build zone violation. All structural components must be contained within the specified x and y boundaries.")
        return suggestions

    # 2. Handle structural failures
    if metrics.get('structure_broken', False):
        suggestions.append("DIAGNOSTIC: Joint failure detected. The internal reaction forces exceeded the mechanical tolerance of the connectors.")

    # 3. Handle kinematic failures (stalling or insufficient height)
    height_gained = metrics.get('height_gained', 0.0)
    if failed and ("not lifted" in (failure_reason or "").lower() or height_gained < 0.1):
        suggestions.append("DIAGNOSTIC: Stalling. The mechanism failed to generate enough vertical lift to significantly displace the object.")
    
    # 4. Handle stability failures (reached height but fell/slid)
    elif not success and not failed:
        progress = metrics.get('progress', 0.0)
        if 0 < progress < 100:
            suggestions.append(f"DIAGNOSTIC: Insufficient lift height. Target altitude reached {progress:.1f}% of the required displacement.")
        
        steps_held = metrics.get('steps_with_object_above_target', 0)
        req_steps = metrics.get('min_simulation_steps_required', 0)
        if progress >= 100 and steps_held < req_steps:
            suggestions.append("DIAGNOSTIC: Target altitude reached, but the system failed the stability requirement. The object was not sustained at the target height.")

    return suggestions
