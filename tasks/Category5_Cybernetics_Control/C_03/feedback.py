"""
Task-specific feedback for C-03: The Seeker.
Purified version: strictly grounded in evaluator metrics.
"""
from typing import Dict, Any, List
import math

def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """Format high-resolution physical metrics for C-03."""
    metric_parts = []
    
    if "distance_to_target" in metrics:
        metric_parts.append(f"**Target Proximity**: {metrics['distance_to_target']:.2f} m")
    if "relative_speed" in metrics:
        metric_parts.append(f"**Relative Velocity Magnitude**: {metrics['relative_speed']:.2f} m/s")
    if "heading_error_deg" in metrics:
        metric_parts.append(f"**Orientation Alignment Error**: {metrics['heading_error_deg']:.2f}°")
    
    metric_parts.append("\n**Mission Milestones**")
    if "rendezvous_count" in metrics:
        metric_parts.append(f"- Rendezvous Completions: {metrics['rendezvous_count']}/2")
    if "activation_achieved" in metrics:
        metric_parts.append(f"- Seeker Activation Status: {metrics['activation_achieved']}")
    if "remaining_impulse_budget" in metrics:
        metric_parts.append(f"- Propellant Reserve: {metrics['remaining_impulse_budget']:.1f} N·s")
    
    metric_parts.append("\n**Capture Requirements**")
    if "rendezvous_distance" in metrics:
        metric_parts.append(f"- Max Capture Distance: < {metrics['rendezvous_distance']:.1f} m")
    if "rendezvous_rel_speed" in metrics:
        metric_parts.append(f"- Matching Velocity Tolerance: < {metrics['rendezvous_rel_speed']:.2f} m/s")
    
    if metrics.get("failed") and metrics.get("failure_reason"):
        metric_parts.append(f"\n**Failure Diagnosis**: {metrics['failure_reason']}")
        
    return metric_parts

def get_improvement_suggestions(
    metrics: Dict[str, Any],
    score: float,
    success: bool,
    failed: bool,
    failure_reason: str = None,
    error: str = None,
) -> List[str]:
    """Generate diagnostic suggestions based on rendezvous and intercept physics."""
    suggestions = []
    
    if error:
        return [f"System Error: {error}. Check API usage."]

    if not failed and not success:
        if metrics.get("rendezvous_count", 0) < 1:
            suggestions.append("The first rendezvous window was missed. Synchronize the intercept trajectory with the mission's temporal slots.")
        elif metrics.get("rendezvous_count", 0) < 2:
            suggestions.append("The second milestone was missed. Analyze the tracking stability after the first successful rendezvous.")

    if failed:
        # 1. Activation
        if not metrics.get("activation_achieved", False) and "activation" in (failure_reason or "").lower():
            suggestions.append("Rendezvous failed: the system was not activated. Maintain a steady presence in the central region for a sustained duration before attempting capture.")
            
        # 2. Physics Compliance
        d = metrics.get("distance_to_target", 999)
        dv = metrics.get("relative_speed", 999)
        limit_d = metrics.get("rendezvous_distance", 6.0)
        limit_dv = metrics.get("rendezvous_rel_speed", 1.8)
        
        if "rendezvous" in (failure_reason or "").lower():
            if d > limit_d:
                suggestions.append(f"Approach distance (min {d:.2f} m) failed the capture threshold ({limit_d:.1f} m). Check for target evasive behavior.")
            if dv > limit_dv:
                suggestions.append(f"Relative speed ({dv:.2f} m/s) exceeded the docking tolerance ({limit_dv:.1f} m/s). Use braking thrust to match the target's vector.")
            if not metrics.get("heading_aligned", False):
                suggestions.append("Heading alignment failed. The seeker's thrust vector must align with the target's trajectory during the rendezvous phase.")

        # 3. Corridor Constraints
        if metrics.get("corridor_violation"):
            suggestions.append("Departure from the time-varying horizontal corridor detected. Stabilize the craft's lateral position within the dynamic boundaries.")
            
        # 4. Resource Depletion
        if metrics.get("out_of_fuel"):
            suggestions.append("Mission failure due to propellant exhaustion. Develop a more energy-efficient intercept path with fewer course corrections.")

    return suggestions
