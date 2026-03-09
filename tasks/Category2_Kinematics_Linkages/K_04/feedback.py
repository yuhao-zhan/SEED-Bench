"""
Task-specific feedback generation for K-04: The Pusher
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Expose high-resolution physical metrics for K-04: The Pusher.
    """
    metric_parts = []
    
    if 'object_x' in metrics:
        metric_parts.append(f"**Payload State**: Position at x={metrics['object_x']:.2f}m")
        if 'distance_pushed' in metrics:
            metric_parts.append(f"- Net Displacement: {metrics['distance_pushed']:.2f}m")
        if 'object_velocity_x' in metrics:
            metric_parts.append(f"- Current Velocity: {metrics['object_velocity_x']:.3f} m/s")

    if 'pusher_x' in metrics:
        metric_parts.append(f"**Actuator State**: Position at x={metrics['pusher_x']:.2f}m")
        if 'pusher_angle' in metrics:
            metric_parts.append(f"- Chassis Orientation: {metrics['pusher_angle']:.3f} rad (tilt)")
        if 'max_pusher_tilt' in metrics:
            metric_parts.append(f"- Peak Tilt Observed: {metrics['max_pusher_tilt']:.3f} rad")

    if 'structure_mass' in metrics:
        max_m = metrics.get('max_structure_mass', float('inf'))
        metric_parts.append(f"**Structural Profile**: Mass {metrics['structure_mass']:.2f}kg")
        if max_m != float('inf'):
            utilization = (metrics['structure_mass'] / max_m) * 100
            metric_parts.append(f"- Mass Budget Utilization: {utilization:.1f}%")

    return metric_parts


def get_improvement_suggestions(metrics: Dict[str, Any], score: float, success: bool, 
                                failed: bool, failure_reason: str = None, 
                                error: str = None) -> List[str]:
    """
    Generate diagnostic physical feedback for K-04: The Pusher.
    """
    suggestions = []
    
    if error or (failed and failure_reason and "design constraint" in failure_reason.lower()):
        if "mass" in (error or failure_reason).lower():
            max_m = metrics.get('max_structure_mass', 0.0)
            suggestions.append(f"DIAGNOSTIC: Pusher assembly mass ({metrics.get('structure_mass', 0):.2f}kg) exceeds the environmental threshold ({max_m:.1f}kg).")
            suggestions.append("ADVISORY: Excessive structural inertia may be overwhelming actuator output.")
        return suggestions

    if failed:
        if "tipped over" in failure_reason.lower() or metrics.get('pusher_tipped', False):
            suggestions.append("DIAGNOSTIC: Loss of rotational equilibrium. Destabilizing torque exceeded restoring torque.")
            suggestions.append("ADVISORY: Analyze the center of mass location relative to the support base.")
        
        elif "fell off" in failure_reason.lower():
            suggestions.append("DIAGNOSTIC: Loss of payload constraint. The object drifted beyond the operational boundaries.")
            suggestions.append("ADVISORY: Ensure the push vector remains aligned with the intended payload trajectory.")

    if not success and not failed:
        pusher_v = metrics.get('pusher_velocity_x', 0.0)
        object_v = metrics.get('object_velocity_x', 0.0)
        
        if pusher_v > 0.5 and object_v < 0.1:
            suggestions.append("DIAGNOSTIC: Mechanical slip or lack of effective engagement.")
            suggestions.append("ADVISORY: Investigate the contact geometry at the pusher-payload interface.")
        
        if failure_reason and "wheel spinning" in failure_reason.lower():
            suggestions.append("DIAGNOSTIC: Traction saturation. Motor torque is exceeding the frictional limit.")
        
        elif failure_reason and "wheels suspended" in failure_reason.lower():
            suggestions.append("DIAGNOSTIC: Suspension geometry failure. Drive links are not making contact with the ground.")

    return suggestions
