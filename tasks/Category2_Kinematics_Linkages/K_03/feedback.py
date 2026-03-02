"""
Task-specific feedback generation for K-03: The Gripper
"""
import math
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Format task-specific metrics for K-03: The Gripper
    Args:
        metrics: Evaluation metrics dictionary
    Returns:
        List of formatted metric strings
    """
    metric_parts = []
    
    # Gripper and object position (always show if available)
    if 'gripper_x' in metrics:
        gripper_y = metrics.get('gripper_y', 0)
        metric_parts.append(f"**Gripper position**: x={metrics['gripper_x']:.2f}m, y={gripper_y:.2f}m")
    if 'object_x' in metrics:
        object_y = metrics.get('object_y', 0)
        metric_parts.append(f"**Object position**: x={metrics['object_x']:.2f}m, y={object_y:.2f}m")
        if 'target_object_y' in metrics:
            metric_parts.append(f"**Target height**: y={metrics['target_object_y']:.2f}m")
        if 'height_gained' in metrics:
            metric_parts.append(f"**Height gained**: {metrics['height_gained']:.2f}m")
        if 'max_object_y_reached' in metrics:
            metric_parts.append(f"**Max height reached**: {metrics['max_object_y_reached']:.2f}m")
        if 'progress' in metrics:
            metric_parts.append(f"**Progress**: {metrics['progress']:.1f}%")
    elif 'target_object_y' in metrics:
        # At least show target if object position not available
        metric_parts.append(f"**Target height**: y={metrics['target_object_y']:.2f}m")
    
    # Structure mass
    if 'structure_mass' in metrics:
        metric_parts.append(f"**Structure mass**: {metrics['structure_mass']:.2f}kg")
        if 'max_structure_mass' in metrics:
            metric_parts.append(f"**Mass limit**: {metrics['max_structure_mass']:.0f}kg")
    
    # Object status and contact (physical grasp)
    if 'gripper_bodies_touching_object' in metrics:
        metric_parts.append(f"**Gripper bodies touching object**: {metrics['gripper_bodies_touching_object']}")
        if 'object_contact_points' in metrics:
            metric_parts.append(f"**Object contact points**: {metrics['object_contact_points']}")
    if 'min_object_y_seen' in metrics:
        metric_parts.append(f"**Minimum object height**: {metrics['min_object_y_seen']:.2f}m")
        if 'object_fell' in metrics:
            status = "FELL" if metrics['object_fell'] else "HELD"
            metric_parts.append(f"**Object status**: {status}")
        if 'object_grasped' in metrics:
            grasped = "YES" if metrics['object_grasped'] else "NO"
            metric_parts.append(f"**Object grasped**: {grasped}")
    
    # Grip tracking
    if 'steps_with_object_above_target' in metrics:
        metric_parts.append(f"**Steps with object above target**: {metrics['steps_with_object_above_target']}")
        if 'min_simulation_steps_required' in metrics:
            metric_parts.append(f"**Required steps**: {metrics['min_simulation_steps_required']}")
    
    # Simulation steps
    if 'step_count' in metrics:
        metric_parts.append(f"**Simulation steps**: {metrics['step_count']}")
    
    # Physical state information for fine-grained debugging (like S_01)
    if 'gripper_x' in metrics and 'object_x' in metrics:
        metric_parts.append("\n**Physical State Information**:")
        metric_parts.append(f"- Gripper position: ({metrics.get('gripper_x', 0):.3f}, {metrics.get('gripper_y', 0):.3f}) m")
        metric_parts.append(f"- Object position: ({metrics.get('object_x', 0):.3f}, {metrics.get('object_y', 0):.3f}) m")
        dx = metrics.get('object_x', 0) - metrics.get('gripper_x', 0)
        dy = metrics.get('object_y', 0) - metrics.get('gripper_y', 0)
        dist = math.sqrt(dx*dx + dy*dy)
        metric_parts.append(f"- Object–gripper distance: {dist:.3f} m")
        if 'height_gained' in metrics:
            metric_parts.append(f"- Height gained (object): {metrics['height_gained']:.3f} m")
        if 'max_object_y_reached' in metrics:
            metric_parts.append(f"- Max object height reached: {metrics['max_object_y_reached']:.3f} m")
        if 'min_object_y_seen' in metrics:
            metric_parts.append(f"- Min object height seen: {metrics['min_object_y_seen']:.3f} m")
        if 'progress' in metrics:
            metric_parts.append(f"- Progress toward target: {metrics['progress']:.1f}%")
    
    # Add any additional metrics (exclude physical state keys)
    excluded_keys = ['gripper_x', 'gripper_y', 'object_x', 'object_y', 'target_object_y', 'height_gained', 'max_object_y_reached', 'progress', 'structure_mass',
                    'max_structure_mass', 'min_object_y_seen', 'object_fell', 'object_grasped', 'object_contact_points', 'gripper_bodies_touching_object',
                    'steps_with_object_above_target', 'min_simulation_steps_required', 'step_count', 'success', 'failed', 'failure_reason']
    other_metrics = {k: v for k, v in metrics.items() if k not in excluded_keys}
    if other_metrics:
        metric_parts.append("\n**Additional Metrics**:")
        for key, value in other_metrics.items():
            if isinstance(value, (int, float)):
                metric_parts.append(f"- {key}: {value:.3f}" if isinstance(value, float) else f"- {key}: {value}")
            else:
                metric_parts.append(f"- {key}: {value}")
    
    return metric_parts


def get_improvement_suggestions(metrics: Dict[str, Any], score: float, success: bool, 
                                failed: bool, failure_reason: str = None, 
                                error: str = None) -> List[str]:
    """
    Generate task-specific improvement suggestions for K-03: The Gripper
    Args:
        metrics: Evaluation metrics dictionary
        score: Score (0-100)
        success: Whether successful
        failed: Whether failed
        failure_reason: Failure reason
        error: Error message if code execution failed
    Returns:
        List of improvement suggestion strings
    """
    suggestions = []
    
    if error:
        error_lower = error.lower()
        if "structure mass" in error_lower and "exceeds" in error_lower:
            max_mass = metrics.get('max_structure_mass', 30.0)
            suggestions.append(f"- Reduce structure mass to be within {max_mass:.0f}kg limit")
            suggestions.append("- Use lighter materials (lower density) or optimize beam sizes")
            suggestions.append("- Consider using fewer or smaller components")
        elif "build zone" in error_lower:
            suggestions.append("- Ensure all beams are placed within the build zone")
            suggestions.append("- Check that gripper components are within x=[0, 10], y=[5, 15]")
        elif "error building" in error_lower:
            suggestions.append("- Review the error message above to identify the specific constraint violation")
            suggestions.append("- Ensure all parameters (beam sizes, positions) are within allowed ranges")
    
    elif failed:
        if failure_reason and "design constraint violated" in failure_reason.lower():
            failure_lower = failure_reason.lower()
            if "structure mass" in failure_lower:
                max_mass = metrics.get('max_structure_mass', 30.0)
                suggestions.append(f"- Reduce structure mass to be within {max_mass:.0f}kg limit")
                suggestions.append("- Optimize beam sizes and densities to minimize total mass")
            if "build zone" in failure_lower:
                suggestions.append("- Ensure all beams are placed within the build zone")
        elif failure_reason and "fell" in failure_reason.lower():
            suggestions.append("- Object is slipping from gripper - increase friction of gripper components")
            suggestions.append("- Improve gripping mechanism to maintain better contact with object")
            suggestions.append("- Adjust motor coordination to maintain compression force on object")
            suggestions.append("- Consider using multiple contact points for better grip")
            suggestions.append("- Ensure gripper fingers/arms maintain contact with object during lifting")
        elif failure_reason and "not lifted" in failure_reason.lower():
            suggestions.append("- Gripper may not be making proper contact with object")
            suggestions.append("- Adjust gripper position and finger/arm angles to grasp object")
            suggestions.append("- Motor speeds may be too low or not properly coordinated")
            suggestions.append("- Check that gripper can reach the object (x=5.0m, y=2.0m)")
            suggestions.append("- Verify that linkage mechanisms create proper gripping motion")
    elif not success:
        if 'height_gained' in metrics:
            if metrics.get('height_gained', 0) < 2.0:
                suggestions.append("- Object is not being lifted effectively")
                suggestions.append("- Adjust motor speeds and phase coordination")
                suggestions.append("- Ensure gripper maintains contact with object")
            elif metrics.get('height_gained', 0) < 5.0:
                suggestions.append("- Object is being lifted but needs to reach higher")
                suggestions.append("- Increase motor speeds or improve lifting efficiency")
                suggestions.append("- Check that gripper maintains upward force")
        
        if 'object_fell' in metrics and metrics.get('object_fell', False):
            suggestions.append("- Object is falling - improve grip and friction")
        
        if 'object_grasped' in metrics and not metrics.get('object_grasped', False):
            suggestions.append("- Gripper is not making contact with object")
            suggestions.append("- Adjust gripper position and finger configuration")
        
        if 'steps_with_object_above_target' in metrics and 'min_simulation_steps_required' in metrics:
            if metrics.get('steps_with_object_above_target', 0) < metrics.get('min_simulation_steps_required', 0):
                suggestions.append("- Object grip is not sustained long enough")
                suggestions.append("- Improve stability and continuous grip")
    
    return suggestions
