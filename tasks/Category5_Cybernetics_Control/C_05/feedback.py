"""
Task-specific feedback for C-05: The Logic Lock.
Purified version: strictly grounded in evaluator metrics.
"""
from typing import Dict, Any, List

def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """Format high-resolution physical metrics for C-05."""
    metric_parts = []
    
    metric_parts.append("**Switch Matrix State**")
    if "triggered_switches" in metrics:
        metric_parts.append(f"- Active Switches: {', '.join(metrics['triggered_switches']) if metrics['triggered_switches'] else 'None'}")
    if "next_required" in metrics:
        metric_parts.append(f"- Targeting Milestone: Switch {metrics['next_required']}")
    if "progress_percent" in metrics:
        metric_parts.append(f"- Mission Progression: {metrics['progress_percent']:.1f}%")
    
    metric_parts.append("\n**Trigger Diagnostics**")
    if "steps_in_current_zone" in metrics:
        metric_parts.append(f"- Contact Dwell Time: {metrics['steps_in_current_zone']}/{metrics.get('steps_required_to_trigger', 'N/A')} steps")
    if "speed" in metrics:
        metric_parts.append(f"- Local Velocity: {metrics['speed']:.3f} m/s")
    if "cooldown_remaining" in metrics:
        metric_parts.append(f"- System Cooldown: {metrics['cooldown_remaining']} steps")
    if "distance_to_next_zone" in metrics and metrics["distance_to_next_zone"] is not None:
        metric_parts.append(f"- Proximity to Target: {metrics['distance_to_next_zone']:.2f} m")
    
    metric_parts.append("\n**Environmental Markers**")
    if metrics.get("env_flag_tight_a_to_b"):
        metric_parts.append("- Warning: Temporal window for sequencing is constrained.")
    if metrics.get("env_flag_long_barrier_delay"):
        metric_parts.append("- Warning: Barrier actuation latency detected.")
    if metrics.get("env_flag_sensitive_trigger"):
        metric_parts.append("- Warning: Input sensitivity thresholds are active (force limit).")

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
    """Generate diagnostic suggestions based on sequencing and interaction mechanics."""
    suggestions = []
    
    if error:
        return [f"System Error: {error}. Check trigger API implementations."]

    if not failed and not success:
        next_req = metrics.get("next_required")
        if next_req == "B":
            suggestions.append("Switch B activation failed. Verify the temporal window and maintain a low entry velocity within the zone.")
        elif next_req == "C":
            suggestions.append("Switch C activation failed. Ensure the approach satisfies the required altitude profile and the system cooldown has elapsed.")

    if failed:
        triggered = metrics.get("triggered_switches", [])
        
        # 1. Sequence Order
        if metrics.get("wrong_order"):
            suggestions.append("Sequence violation detected. Activation must follow the strict order A -> B -> C.")
            
        # 2. Velocity Cap
        speed = metrics.get("speed", 1.0)
        speed_cap = metrics.get("env_speed_cap_inside", 0.5)
        if metrics.get("distance_to_next_zone", 1.0) < 0.2 and speed > speed_cap:
            suggestions.append(f"Activation failed due to excessive velocity. Reduce speed below {speed_cap:.2f} m/s to trigger the sensor.")
            
        # 3. Temporal Window
        if "A" in triggered and "B" not in triggered and "timeout" in (failure_reason or "").lower():
            suggestions.append("The temporal window between A and B expired. Accelerate the transition between these nodes.")
            
        # 4. Input Sensitivity
        if metrics.get("env_flag_sensitive_trigger") and metrics.get("steps_in_current_zone", 0) < 5:
            suggestions.append("Signal noise detected within the zone. Avoid applying excessive force while triggering the mechanism.")
            
        # 5. Spatial Requirement for C
        if "B" in triggered and "C" not in triggered:
            y_req = metrics.get("env_c_required_max_y", 2.9)
            if metrics.get("agent_y", 0.0) < y_req:
                suggestions.append(f"Spatial requirement for Switch C not met. Approach must originate from a higher altitude (min: {y_req:.1f} m).")

    return suggestions
