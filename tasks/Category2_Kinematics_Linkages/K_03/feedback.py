"""
Task-specific feedback generation for K-03: The Gripper.
Audited for code-grounded truth and physical diagnostics.
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Expose physical metrics returned by the K-03 evaluator.
    """
    metric_parts = []
    
    # Grasp Diagnostics
    if 'object_grasped' in metrics:
        status = "SECURED" if metrics['object_grasped'] else "NONE"
        metric_parts.append(f"**Grasp State**: {status}")
        if 'object_contact_points' in metrics:
            metric_parts.append(f"- Contact Points: {metrics['object_contact_points']}")
        if 'gripper_bodies_touching_object' in metrics:
            metric_parts.append(f"- Touching Bodies: {metrics['gripper_bodies_touching_object']}")

    # Kinematics
    if 'object_y' in metrics:
        metric_parts.append(f"**Payload Kinematics**: Altitude y={metrics['object_y']:.2f}m")
        if 'height_gained' in metrics:
            metric_parts.append(f"- Elevation Change: {metrics['height_gained']:.2f}m")
        if 'target_object_y' in metrics:
            metric_parts.append(f"- Target Threshold: y >= {metrics['target_object_y']:.2f}m")

    # Structural Budget
    if 'structure_mass' in metrics:
        max_mass = metrics.get('max_structure_mass', 0.0)
        metric_parts.append(f"**Structural Profile**: Mass {metrics['structure_mass']:.2f}kg")
        if max_mass > 0:
            utilization = (metrics['structure_mass'] / max_mass) * 100
            metric_parts.append(f"- Mass Budget Utilization: {utilization:.1f}%")

    # Temporal stability
    if 'steps_with_object_above_target' in metrics:
        req_steps = metrics.get('min_simulation_steps_required', 1)
        held_steps = metrics['steps_with_object_above_target']
        metric_parts.append(f"**Stability Duration**: {held_steps} steps at/above target")
        if req_steps > 0:
            stability_ratio = min(held_steps / req_steps, 1.0) * 100
            metric_parts.append(f"- Required Duration Progress: {stability_ratio:.1f}%")

    return metric_parts


def get_improvement_suggestions(metrics: Dict[str, Any], score: float, success: bool, 
                                failed: bool, failure_reason: str = None, 
                                error: str = None) -> List[str]:
    """
    Generate diagnostic feedback based on physical failure modes in K-03.
    """
    suggestions = []
    
    # 1. Constraint Violations
    if failed and failure_reason and "design constraint" in failure_reason.lower():
        if "mass" in failure_reason.lower():
            max_m = metrics.get('max_structure_mass', 0.0)
            suggestions.append(f"DIAGNOSTIC: System mass exceeds the environmental limit of {max_m:.1f}kg.")
            suggestions.append("ADVISORY: Re-evaluate material density and beam dimensions to optimize the payload-to-structure mass ratio.")
        elif "zone" in failure_reason.lower():
            suggestions.append("DIAGNOSTIC: Gripper components were detected outside the permitted build area.")
        return suggestions

    # 2. Dynamic Failures
    if failed:
        if metrics.get('object_fell', False) or (failure_reason and "fell" in failure_reason.lower()):
            suggestions.append("DIAGNOSTIC: Payload slip or drop detected. The gripper failed to maintain static equilibrium against gravity and damping.")
            suggestions.append("ADVISORY: Analyze the contact mechanics. Ensure the gripper geometry can sustain the object's mass and friction profile during acceleration.")
        
        elif failure_reason and "not lifted" in failure_reason.lower():
            suggestions.append("DIAGNOSTIC: Insufficient vertical work. The mechanism's lifting force did not significantly overcome the system weight.")
            suggestions.append("ADVISORY: Verify the actuator settings (motor force and speed) and the mechanical advantage of the lifting linkage.")

    # 3. Stability/Precision issues (Not fully failed, but not successful)
    elif not success:
        target_y = metrics.get('target_object_y', 0.0)
        max_y = metrics.get('max_object_y_reached', 0.0)
        
        if max_y >= target_y:
            suggestions.append("DIAGNOSTIC: Target altitude achieved, but temporal stability criteria were not satisfied.")
            suggestions.append("ADVISORY: The gripper is functional but exhibits dynamic instability over time. Improve the sustained grip performance.")
        
        elif metrics.get('object_grasped', False):
            suggestions.append("DIAGNOSTIC: Payload secured but vertical displacement is insufficient to reach the target threshold.")
            suggestions.append("ADVISORY: Ensure the lifting joint has sufficient range of motion and actuator force to reach the target altitude.")

    return suggestions
