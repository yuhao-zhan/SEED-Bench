"""
Task-specific feedback generation for K-03: The Gripper
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Expose high-resolution physical metrics for K-03: The Gripper.
    """
    metric_parts = []
    
    if 'object_grasped' in metrics:
        status = "SECURED" if metrics['object_grasped'] else "LOOSE/NONE"
        metric_parts.append(f"**Grasp State**: {status}")
        if 'object_contact_points' in metrics:
            metric_parts.append(f"- Interaction Complexity: {metrics['object_contact_points']} contact points detected")
        if 'gripper_bodies_touching_object' in metrics:
            metric_parts.append(f"- Contact Geometry: {metrics['gripper_bodies_touching_object']} gripper links in contact")

    if 'object_y' in metrics:
        metric_parts.append(f"**Payload Kinematics**: Current altitude y={metrics['object_y']:.2f}m")
        if 'height_gained' in metrics:
            metric_parts.append(f"- Elevation Δy: {metrics['height_gained']:.2f}m")
        if 'target_object_y' in metrics:
            metric_parts.append(f"- Mission Objective: altitude >= {metrics['target_object_y']:.2f}m")

    if 'structure_mass' in metrics:
        max_mass = metrics.get('max_structure_mass', float('inf'))
        metric_parts.append(f"**Structural Profile**: Mass {metrics['structure_mass']:.2f}kg")
        if max_mass != float('inf'):
            utilization = (metrics['structure_mass'] / max_mass) * 100
            metric_parts.append(f"- Mass Budget Utilization: {utilization:.1f}%")

    if 'steps_with_object_above_target' in metrics:
        req_steps = metrics.get('min_simulation_steps_required', 0)
        held_steps = metrics['steps_with_object_above_target']
        metric_parts.append(f"**Temporal Performance**: Objective sustained for {held_steps} steps")
        if req_steps > 0:
            stability_ratio = min(held_steps / req_steps, 1.0) * 100
            metric_parts.append(f"- Grip Stability Factor: {stability_ratio:.1f}% of requirement")

    return metric_parts


def get_improvement_suggestions(metrics: Dict[str, Any], score: float, success: bool, 
                                failed: bool, failure_reason: str = None, 
                                error: str = None) -> List[str]:
    """
    Generate diagnostic physical feedback for K-03: The Gripper.
    """
    suggestions = []
    
    if error or (failed and failure_reason and "design constraint" in failure_reason.lower()):
        if "mass" in (error or failure_reason).lower():
            max_m = metrics.get('max_structure_mass', 0.0)
            suggestions.append(f"DIAGNOSTIC: Gripper assembly mass ({metrics.get('structure_mass', 0):.2f}kg) violates environmental limits ({max_m:.1f}kg).")
            suggestions.append("ADVISORY: Optimize the arm and linkage density to improve actuator efficiency.")
        return suggestions

    if failed:
        if "object fell" in failure_reason.lower() or metrics.get('object_fell', False):
            suggestions.append("DIAGNOSTIC: Static equilibrium loss. The forces between the gripper and object were insufficient to counteract weight.")
            suggestions.append("ADVISORY: Analyze the contact geometry. Ensure the linkage generates sufficient friction or form-closure to secure the payload.")
        
        elif "not lifted" in failure_reason.lower() or metrics.get('height_gained', 0) < 0.1:
            suggestions.append("DIAGNOSTIC: Insufficient work output. The net lifting force is not overcoming the combined weight of the system and payload.")

    elif not success:
        target_y = metrics.get('target_object_y', 0.0)
        if metrics.get('max_object_y_reached', 0) >= target_y:
            suggestions.append("DIAGNOSTIC: Target altitude achieved but stability duration threshold not met.")
            suggestions.append("ADVISORY: The gripper is functional but exhibits dynamic instability over time.")
        
        elif metrics.get('object_grasped', False):
            suggestions.append("DIAGNOSTIC: Object secured but vertical displacement is insufficient to reach the target.")

    return suggestions
