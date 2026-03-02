"""
Task-specific feedback generation for K-05: The Lifter.

Height thresholds are derived from task design (align with evaluator.py).
"""
from typing import Dict, Any, List

# Use task design constants for suggestion thresholds (single source: evaluator)
from .evaluator import OBJECT_START_Y, TARGET_OBJECT_Y

REQUIRED_HEIGHT_GAIN = TARGET_OBJECT_Y - OBJECT_START_Y  # e.g. 7.2m
NOT_LIFTED_THRESHOLD = REQUIRED_HEIGHT_GAIN * 0.5        # below this: "not lifted effectively"
REACH_HIGHER_THRESHOLD = REQUIRED_HEIGHT_GAIN            # below this: "needs to reach higher"


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Format task-specific metrics for K-05: The Lifter
    Args:
        metrics: Evaluation metrics dictionary
    Returns:
        List of formatted metric strings
    """
    metric_parts = []
    
    # Lifter and object position (always show if available)
    if 'lifter_x' in metrics:
        lifter_y = metrics.get('lifter_y', 0)
        metric_parts.append(f"**Lifter position**: x={metrics['lifter_x']:.2f}m, y={lifter_y:.2f}m")
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
    
    # Structure integrity tracking
    if 'structure_broken' in metrics:
        status = "BROKEN" if metrics['structure_broken'] else "INTACT"
        metric_parts.append(f"**Structure integrity**: {status}")
        if 'joint_count' in metrics:
            metric_parts.append(f"**Joint count**: {metrics['joint_count']}")
    
    # Height maintenance tracking
    if 'steps_with_object_above_target' in metrics:
        metric_parts.append(f"**Steps with object above target**: {metrics['steps_with_object_above_target']}")
        if 'min_simulation_steps_required' in metrics:
            metric_parts.append(f"**Required steps**: {metrics['min_simulation_steps_required']}")
    
    # Simulation steps
    if 'step_count' in metrics:
        metric_parts.append(f"**Simulation steps**: {metrics['step_count']}")
    
    # Add any additional metrics
    excluded_keys = ['lifter_x', 'lifter_y', 'object_x', 'object_y', 'target_object_y', 'height_gained', 'max_object_y_reached', 'progress', 'structure_mass',
                    'max_structure_mass', 'structure_broken', 'joint_count', 'steps_with_object_above_target',
                    'min_simulation_steps_required', 'step_count', 'success', 'failed', 'failure_reason']
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
    Generate task-specific improvement suggestions for K-05: The Lifter
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
            max_mass = metrics.get('max_structure_mass', 60.0)
            suggestions.append(f"- Reduce structure mass to be within {max_mass:.0f}kg limit")
            suggestions.append("- Use lighter materials (lower density) or optimize beam sizes")
            suggestions.append("- Consider using fewer or smaller components")
        elif "build zone" in error_lower:
            suggestions.append("- Ensure all beams are placed within the build zone")
            suggestions.append("- Check that lifter components are within x=[0, 8], y=[1, 12]")
        elif "error building" in error_lower:
            suggestions.append("- Review the error message above to identify the specific constraint violation")
            suggestions.append("- Ensure all parameters (beam sizes, positions) are within allowed ranges")
    
    elif failed:
        if failure_reason and "design constraint violated" in failure_reason.lower():
            failure_lower = failure_reason.lower()
            if "structure mass" in failure_lower:
                max_mass = metrics.get('max_structure_mass', 60.0)
                suggestions.append(f"- Reduce structure mass to be within {max_mass:.0f}kg limit")
                suggestions.append("- Optimize beam sizes and densities to minimize total mass")
            if "build zone" in failure_lower:
                suggestions.append("- Ensure all beams are placed within the build zone")
        elif failure_reason and "structure integrity" in failure_reason.lower():
            suggestions.append("- Scissor links are breaking under load - joints are too weak")
            suggestions.append("- Consider using more joints or stronger connections")
            suggestions.append("- Distribute load more evenly across the scissor structure")
            suggestions.append("- Reduce motor torque to prevent overloading joints")
            suggestions.append("- Design scissor mechanism with better mechanical advantage to reduce joint forces")
        elif failure_reason and "not lifted" in failure_reason.lower():
            suggestions.append("- Lifter may not be generating enough force to lift the object")
            suggestions.append("- Motor speeds may be too low or not properly coordinated")
            suggestions.append("- Check that scissor mechanism is properly actuated")
            suggestions.append("- Ensure platform makes proper contact with object")
            suggestions.append("- Verify that scissor linkage creates proper lifting motion")
    elif not success:
        if 'height_gained' in metrics:
            height_gained = metrics.get('height_gained', 0)
            if height_gained < NOT_LIFTED_THRESHOLD:
                suggestions.append("- Object is not being lifted effectively")
                suggestions.append("- Adjust motor speeds and scissor mechanism coordination")
                suggestions.append("- Ensure scissor mechanism is properly designed for lifting")
            elif height_gained < REACH_HIGHER_THRESHOLD:
                suggestions.append("- Object is being lifted but needs to reach higher")
                suggestions.append("- Increase scissor mechanism extension or improve design")
                suggestions.append("- Check that scissor mechanism can achieve required height")
        
        if 'structure_broken' in metrics and metrics.get('structure_broken', False):
            suggestions.append("- Structure is breaking - improve joint strength or reduce load")
        
        if 'steps_with_object_above_target' in metrics and 'min_simulation_steps_required' in metrics:
            if metrics.get('steps_with_object_above_target', 0) < metrics.get('min_simulation_steps_required', 0):
                suggestions.append("- Object height is not sustained long enough")
                suggestions.append("- Improve stability and continuous lifting motion")
    
    return suggestions
