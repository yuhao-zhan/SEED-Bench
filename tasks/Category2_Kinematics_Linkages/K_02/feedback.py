"""
Task-specific feedback generation for K-02: The Climber
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Expose high-resolution physical metrics for K-02: The Climber.
    """
    metric_parts = []
    
    if 'climber_y' in metrics:
        metric_parts.append(f"**Vertical Trajectory**: Current altitude y={metrics['climber_y']:.2f}m")
        if 'height_gained' in metrics:
            metric_parts.append(f"- Net Elevation Gain: {metrics['height_gained']:.2f}m")
        if 'max_height_reached' in metrics:
            metric_parts.append(f"- Apogee reached: {metrics['max_height_reached']:.2f}m")
        if 'target_y' in metrics:
            metric_parts.append(f"- Mission Objective: {metrics['target_y']:.1f}m target height")

    if 'climber_x' in metrics:
        metric_parts.append(f"**Contact Mechanics**: Horizontal position x={metrics['climber_x']:.2f}m")

    if 'structure_mass' in metrics:
        max_mass = metrics.get('max_structure_mass', float('inf'))
        metric_parts.append(f"**Structural Profile**: Mass {metrics['structure_mass']:.2f}kg")
        if max_mass != float('inf'):
            utilization = (metrics['structure_mass'] / max_mass) * 100
            metric_parts.append(f"- Payload Budget Utilization: {utilization:.1f}%")

    if 'step_count' in metrics:
        req_steps = metrics.get('min_simulation_steps_required', 0)
        metric_parts.append(f"**Temporal Analysis**: System active for {metrics['step_count']} steps")
        if req_steps > 0:
            survival = min(metrics['step_count'] / req_steps, 1.0) * 100
            metric_parts.append(f"- Duty Cycle: {survival:.1f}% of required operational time")

    return metric_parts


def get_improvement_suggestions(metrics: Dict[str, Any], score: float, success: bool, 
                                failed: bool, failure_reason: str = None, 
                                error: str = None) -> List[str]:
    """
    Generate diagnostic physical feedback for K-02: The Climber.
    """
    suggestions = []
    
    if error or (failed and failure_reason and "design constraint" in failure_reason.lower()):
        if "mass" in (error or failure_reason).lower():
            max_mass = metrics.get('max_structure_mass', 0.0)
            suggestions.append(f"DIAGNOSTIC: Structural mass ({metrics.get('structure_mass', 0):.2f}kg) exceeds the environmental budget ({max_mass:.1f}kg).")
            suggestions.append("ADVISORY: Actuator lifting capacity may be overwhelmed by the current system weight.")
        return suggestions

    if failed:
        if "lost wall contact" in failure_reason.lower():
            suggestions.append("DIAGNOSTIC: Loss of horizontal constraint. The system drifted beyond the effective interaction range of the vertical surface.")
            suggestions.append("ADVISORY: Analyze the net forces. Ensure the linkage maintains a normal force component toward the wall during the ascent.")
        
        elif "fell" in failure_reason.lower() or metrics.get('climber_fell', False):
            suggestions.append("DIAGNOSTIC: Gravitational collapse. The net vertical support force failed to counteract the system weight.")
            suggestions.append("ADVISORY: Review the adhesion cycle logic; ensure static contact is maintained while other links are in motion.")

    elif not success:
        progress = metrics.get('progress', 0.0)
        if progress > 0 and progress < 100:
            suggestions.append(f"DIAGNOSTIC: Functional climb detected but elevation gain is suboptimal ({progress:.1f}% of objective).")

    return suggestions
