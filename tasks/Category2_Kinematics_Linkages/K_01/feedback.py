"""
Task-specific feedback generation for K-01: The Walker
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Expose high-resolution physical metrics for K-01: The Walker.
    """
    metric_parts = []
    
    if 'walker_x' in metrics and 'walker_y' in metrics:
        metric_parts.append(f"**Kinematic State**: Current position at (x={metrics['walker_x']:.2f}m, y={metrics['walker_y']:.2f}m)")
        if 'distance_traveled' in metrics:
            metric_parts.append(f"- Horizontal Displacement: {metrics['distance_traveled']:.2f}m")
        if 'max_x_reached' in metrics:
            metric_parts.append(f"- Peak Forward Reach: {metrics['max_x_reached']:.2f}m")
        if 'progress' in metrics:
            metric_parts.append(f"- Mission Completion: {metrics['progress']:.1f}%")

    if 'structure_mass' in metrics:
        max_mass = metrics.get('max_structure_mass', float('inf'))
        mass_status = "EXCEEDED" if metrics['structure_mass'] > max_mass else "WITHIN LIMIT"
        metric_parts.append(f"**Structural Profile**: Total Mass {metrics['structure_mass']:.2f}kg ({mass_status})")

    if 'min_torso_y' in metrics:
        metric_parts.append(f"**Stability Metrics**: Minimum observed torso height {metrics['min_torso_y']:.2f}m")

    if 'step_count' in metrics:
        req_steps = metrics.get('min_simulation_steps_required', 0)
        metric_parts.append(f"**Temporal Analysis**: Simulation active for {metrics['step_count']} steps")
        if req_steps > 0:
            survival_ratio = min(metrics['step_count'] / req_steps, 1.0) * 100
            metric_parts.append(f"- Duty Cycle Completion: {survival_ratio:.1f}% of required survival time")
    
    return metric_parts


def get_improvement_suggestions(metrics: Dict[str, Any], score: float, success: bool, 
                                failed: bool, failure_reason: str = None, 
                                error: str = None) -> List[str]:
    """
    Generate diagnostic physical feedback for K-01: The Walker.
    """
    suggestions = []
    
    if error or (failed and failure_reason and "design constraint" in failure_reason.lower()):
        if "mass" in (error or failure_reason).lower():
            curr_mass = metrics.get('structure_mass', 0.0)
            max_mass = metrics.get('max_structure_mass', 0.0)
            suggestions.append(f"DIAGNOSTIC: Structural mass ({curr_mass:.2f}kg) exceeds the environmental threshold ({max_mass:.1f}kg).")
            suggestions.append("ADVISORY: Actuator torque may be insufficient to propel the current structural inertia.")
        return suggestions

    if failed:
        if "collapsed" in failure_reason.lower() or "torso touched" in failure_reason.lower():
            suggestions.append("DIAGNOSTIC: Critical loss of vertical support. The center of mass height fell below the survival threshold.")
            suggestions.append("ADVISORY: Analyze the linkage phase coordination; ensure the support polygon remains stable throughout the gait cycle.")
        
        elif "did not move" in failure_reason.lower() or metrics.get('distance_traveled', 0) < 0.1:
            suggestions.append("DIAGNOSTIC: Insufficient traction or momentum transfer. The gait cycle is not generating effective horizontal displacement.")
            suggestions.append("ADVISORY: Investigate the contact mechanics between the terminal links and the ground surface.")

    elif not success:
        if metrics.get('step_count', 0) < metrics.get('min_simulation_steps_required', 0):
            suggestions.append("DIAGNOSTIC: Premature termination of simulation. The structure failed to maintain its physical integrity or height for the full required duration.")

    return suggestions
