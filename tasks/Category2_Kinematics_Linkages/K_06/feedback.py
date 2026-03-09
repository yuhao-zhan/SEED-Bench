"""
Task-specific feedback generation for K-06: The Wiper
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Expose high-resolution physical metrics for K-06: The Wiper.
    """
    metric_parts = []
    
    if 'cleaning_percentage' in metrics:
        metric_parts.append(f"**Cleaning Efficiency**: {metrics['cleaning_percentage']:.1f}% particles displaced")
        if 'particles_removed' in metrics:
            metric_parts.append(f"- Net Removal: {metrics['particles_removed']} units")
        if 'residual_percentage' in metrics:
            metric_parts.append(f"- Residual Payload: {metrics['residual_percentage']:.1f}% remaining")

    if 'wiper_x' in metrics:
        metric_parts.append(f"**Wiper State**: Current position at (x={metrics['wiper_x']:.2f}m, y={metrics['wiper_y']:.2f}m)")

    if 'structure_mass' in metrics:
        max_m = metrics.get('max_structure_mass', float('inf'))
        metric_parts.append(f"**Structural Profile**: Mass {metrics['structure_mass']:.2f}kg")
        if max_m != float('inf'):
            utilization = (metrics['structure_mass'] / max_m) * 100
            metric_parts.append(f"- Mass Budget Utilization: {utilization:.1f}%")

    if 'step_count' in metrics:
        req = metrics.get('min_simulation_steps_required', 1)
        metric_parts.append(f"**Operational Analysis**: {metrics['step_count']}/{req} steps completed")

    return metric_parts


def get_improvement_suggestions(metrics: Dict[str, Any], score: float, success: bool, 
                                failed: bool, failure_reason: str = None, 
                                error: str = None) -> List[str]:
    """
    Generate diagnostic physical feedback for K-06: The Wiper.
    """
    suggestions = []
    
    if error or (failed and failure_reason and "design constraint" in failure_reason.lower()):
        if "mass" in (error or failure_reason).lower():
            max_m = metrics.get('max_structure_mass', 0.0)
            suggestions.append(f"DIAGNOSTIC: Wiper assembly mass ({metrics.get('structure_mass', 0):.2f}kg) exceeds the environmental threshold ({max_m:.1f}kg).")
        return suggestions

    if failed:
        if "particles remaining" in failure_reason.lower():
            suggestions.append("DIAGNOSTIC: Insufficient clearing coverage. The swept area does not encompass the target particle field.")
            suggestions.append("ADVISORY: Analyze the range of motion (ROM) of the linkage. Motor amplitude or arm length may be insufficient.")
        
        elif metrics.get('step_count', 0) < metrics.get('min_simulation_steps_required', 0):
            suggestions.append("DIAGNOSTIC: Operational duration threshold not met. The system failed to sustain the wiping cycle.")

    elif not success:
        progress = metrics.get('progress', 0.0)
        if 0 < progress < 100:
            suggestions.append(f"DIAGNOSTIC: Functional wiping detected but efficiency is suboptimal ({progress:.1f}% of target).")
        
        max_res = metrics.get('max_residual_percent', 0.0)
        if metrics.get('residual_percentage', 0) > max_res:
            suggestions.append("DIAGNOSTIC: High residual payload remaining in the target field.")

    return suggestions
