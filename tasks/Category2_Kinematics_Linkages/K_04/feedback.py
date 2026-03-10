"""
Task-specific feedback generation for K-04: The Pusher.
Purified and audited for code-grounded truth and cross-stage compatibility.
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Expose high-resolution physical metrics for K-04: The Pusher.
    All strings and keys are grounded in evaluator.py metrics.
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
        if max_m != float('inf') and max_m > 0:
            utilization = (metrics['structure_mass'] / max_m) * 100
            metric_parts.append(f"- Mass Budget Utilization: {utilization:.1f}%")

    return metric_parts


def get_improvement_suggestions(metrics: Dict[str, Any], score: float, success: bool, 
                                failed: bool, failure_reason: str = None, 
                                error: str = None) -> List[str]:
    """
    Generate diagnostic physical feedback for K-04: The Pusher.
    Strictly follows the Hallucination, Hardcode, Over-fitting, and No-Spoilers audits.
    """
    suggestions = []
    reason_str = (failure_reason or "").lower()
    error_str = (error or "").lower()
    
    # Audit 1 & 2: Constraint Violation (Grounded in metrics.get)
    if error_str or (failed and "design constraint" in reason_str):
        if "mass" in error_str or "mass" in reason_str:
            max_m = metrics.get('max_structure_mass', 0.0)
            suggestions.append(f"DIAGNOSTIC: Pusher assembly mass ({metrics.get('structure_mass', 0):.2f}kg) exceeds the environmental threshold ({max_m:.1f}kg).")
            suggestions.append("ADVISORY: High structural inertia detected. Ensure actuator torque can overcome the mass of the constructed tool.")
        return suggestions

    # Audit 3: Failure Mode Diagnostics (Grounded in evaluator.py failure_reason)
    if failed:
        if "tipped over" in reason_str or metrics.get('pusher_tipped', False):
            suggestions.append("DIAGNOSTIC: Loss of rotational equilibrium. The chassis tilt angle exceeded the stability threshold.")
            suggestions.append("ADVISORY: Analyze the vertical and horizontal center of mass location relative to the ground contact points.")
        
        elif "fell off" in reason_str:
            suggestions.append("DIAGNOSTIC: Loss of payload constraint. The target object has departed from the support platform.")
            suggestions.append("ADVISORY: Investigate the alignment of the force vector applied to the object to ensure a stable trajectory.")

    # Audit 4: Performance Diagnostics (Grounded in system behaviors)
    if not success and not failed:
        # Check for engagement failure as defined by evaluator's "not pushed effectively" logic
        if "not pushed effectively" in reason_str:
            suggestions.append("DIAGNOSTIC: Mechanical slip or lack of effective engagement between actuator and payload.")
            suggestions.append("ADVISORY: Evaluate the contact geometry and friction at the pusher-payload interface.")
        
        # Check for traction/suspension issues identified by evaluator's wheel state checks
        if "wheel spinning" in reason_str:
            suggestions.append("DIAGNOSTIC: Traction saturation. Rotational energy is being lost at the ground interface.")
        
        elif "wheels suspended" in reason_str:
            suggestions.append("DIAGNOSTIC: Suspension geometry failure. The drive components have lost contact with the terrain.")

    return suggestions
