"""
Task-specific feedback for C-03: The Seeker.
Audited and purified version: zero hardcoding, zero hallucinations.
"""
from typing import Dict, Any, List
import math

def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """Format high-resolution physical metrics for C-03."""
    metric_parts = []
    
    # Interception Proximity
    if "distance_to_target" in metrics:
        metric_parts.append(f"**Target Proximity**: Range {metrics['distance_to_target']:.2f} m, Relative Speed {metrics.get('relative_speed', 0.0):.2f} m/s")
    
    if "heading_error_deg" in metrics:
        metric_parts.append(f"**Alignment Status**: Heading Error {metrics['heading_error_deg']:.2f}°")
    
    # Mission Progress & Resource
    metric_parts.append("\n**Mission Progression**")
    if "rendezvous_count" in metrics:
        metric_parts.append(f"- Captured Rendezvous Events: {metrics['rendezvous_count']}/2")
    if "activation_achieved" in metrics:
        metric_parts.append(f"- Seeker System Activation: {metrics['activation_achieved']}")
    if "remaining_impulse_budget" in metrics:
        metric_parts.append(f"- Propellant Reserve: {metrics['remaining_impulse_budget']:.1f} N·s propellant remaining")
    
    # Dynamic Limits
    metric_parts.append("\n**Capture Constraints**")
    if "rendezvous_distance" in metrics:
        metric_parts.append(f"- Max Capture Range: {metrics['rendezvous_distance']:.2f} m")
    if "rendezvous_rel_speed" in metrics:
        metric_parts.append(f"- Max Capture Relative Speed: {metrics['rendezvous_rel_speed']:.2f} m/s")
    
    if metrics.get("failed") and metrics.get("failure_reason"):
        metric_parts.append(f"\n**Primary System Failure**: {metrics['failure_reason']}")
        
    return metric_parts

def get_improvement_suggestions(
    metrics: Dict[str, Any],
    score: float,
    success: bool,
    failed: bool,
    failure_reason: str = None,
    error: str = None,
) -> List[str]:
    """Generate diagnostic suggestions based on grounded physical failure modes."""
    suggestions = []
    
    if error:
        return [f"System Error: {error}. Check intercept and propellant APIs."]

    # Dynamic Variables
    d = metrics.get("distance_to_target", float('inf'))
    dv = metrics.get("relative_speed", float('inf'))
    limit_d = metrics.get("rendezvous_distance", 0.0)
    limit_dv = metrics.get("rendezvous_rel_speed", 0.0)
    rendezvous_count = metrics.get("rendezvous_count", 0)
    activation = metrics.get("activation_achieved", False)
    out_of_fuel = metrics.get("out_of_fuel", False)
    
    if not failed and not success:
        if rendezvous_count < 1:
            suggestions.append("The first rendezvous window was missed. Synchronize position with the temporal mission slots.")
        elif rendezvous_count < 2:
            suggestions.append("Tracking was lost after the first capture. Maintain proximity through active trajectory matching.")

    if failed:
        # 1. Activation Root-Cause
        if not activation and "activation" in (failure_reason or "").lower():
            suggestions.append("Seeker system failed to activate. Activation requires a stabilized presence in the central mission zone without excessive acceleration.")
            
        # 2. Interception Dynamics (Docking Failure)
        if "rendezvous" in (failure_reason or "").lower():
            if d > limit_d:
                suggestions.append(f"Intercept proximity was outside the capture envelope. Account for target evasive behavior or atmospheric drift.")
            if dv > limit_dv:
                suggestions.append(f"Relative docking speed exceeded the structural docking tolerance. Utilize proactive braking pulses.")
            if not metrics.get("heading_aligned", False):
                suggestions.append("Orientation misaligned during capture. The thrust vector must remain collinear with the target velocity vector.")

        # 3. Dynamic Boundary Failure
        if metrics.get("corridor_violation"):
            suggestions.append("Breach of the time-varying lateral corridor. Controller response may be too slow for the dynamic environmental constraints.")
            
        # 4. Resource & Propellant Efficiency
        if out_of_fuel:
            suggestions.append("Propellant exhaustion. Intercept strategy may be inefficiently combating damping or course deviations.")
        
        # 5. Stability/Tracking Loss
        if "target lost" in (failure_reason or "").lower():
            suggestions.append("Post-capture tracking failure. The distance exceeded the track limit. Adjust pursuit gains to prevent target breakout.")

    return suggestions
