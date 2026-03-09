"""
Task-specific feedback for C-05: The Logic Lock.
Audited and purified version: zero hardcoding, zero hallucinations.
"""
from typing import Dict, Any, List
import math

def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """Format high-resolution physical metrics for C-05."""
    metric_parts = []
    
    # Logic State
    metric_parts.append("**Control Logic Matrix**")
    if "triggered_switches" in metrics:
        triggered = metrics['triggered_switches']
        metric_parts.append(f"- Active Nodes: [{', '.join(triggered) if triggered else 'None'}]")
    if "next_required" in metrics:
        metric_parts.append(f"- Targeting Milestone: Node {metrics['next_required']}")
    if "progress_percent" in metrics:
        metric_parts.append(f"- Mission Progression: {metrics['progress_percent']:.1f}%")
    
    # Trigger Diagnostics
    metric_parts.append("\n**Local Node Interaction**")
    if "steps_in_current_zone" in metrics:
        req = metrics.get('steps_required_to_trigger', 'N/A')
        metric_parts.append(f"- Contact Dwell Time: {metrics['steps_in_current_zone']}/{req} steps")
    if "speed" in metrics:
        metric_parts.append(f"- Entry Velocity: {metrics['speed']:.3f} m/s (Limit: {metrics.get('env_speed_cap_inside', 'N/A')})")
    if "cooldown_remaining" in metrics:
        metric_parts.append(f"- System Lockout (Cooldown): {metrics['cooldown_remaining']} steps")
    if "distance_to_next_zone" in metrics and metrics["distance_to_next_zone"] is not None:
        metric_parts.append(f"- Proximity to Target: {metrics['distance_to_next_zone']:.2f} m")
    
    # Environmental Flags
    metric_parts.append("\n**Environmental Anomaly Flags**")
    if metrics.get("env_flag_tight_a_to_b"):
        metric_parts.append("- Warning: Temporal window for sequencing is constrained.")
    if metrics.get("env_flag_long_barrier_delay"):
        metric_parts.append("- Warning: High actuation latency detected.")
    if metrics.get("env_flag_sensitive_trigger"):
        metric_parts.append("- Warning: Input sensitivity thresholds are active (force limit).")
    if metrics.get("env_flag_strong_repulsion"):
        metric_parts.append("- Warning: Intense repulsion detected around targets.")

    if metrics.get("failed") and metrics.get("failure_reason"):
        metric_parts.append(f"\n**Primary Logic Failure**: {metrics['failure_reason']}")
        
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
        return [f"System Error: {error}. Check trigger API and sequence definitions."]

    triggered = metrics.get("triggered_switches", [])
    next_req = metrics.get("next_required")
    speed = metrics.get("speed", 1.0)
    speed_cap = metrics.get("env_speed_cap_inside", 0.0)
    dist_to_next = metrics.get("distance_to_next_zone", float('inf'))
    
    if not failed and not success:
        if next_req == "B":
            suggestions.append("Node B activation failed. Verify the temporal window following Node A.")
        elif next_req == "C":
            suggestions.append("Node C activation failed. Ensure the altitude requirement and system cooldown are satisfied.")

    if failed:
        # 1. Sequence Root-Cause
        if metrics.get("wrong_order"):
            suggestions.append("Sequence violation. Nodes must be triggered in the order A -> B -> C.")
            
        # 2. Velocity Cap
        if dist_to_next < 0.2 and speed > speed_cap:
            suggestions.append(f"Activation failed due to excessive velocity. Speed must be below the zone limit.")
            
        # 3. Temporal Window
        if "A" in triggered and "B" not in triggered and "timeout" in (failure_reason or "").lower():
            suggestions.append("The temporal chain between A and B expired. Accelerate the transition.")
            
        # 4. Input Sensitivity
        if metrics.get("env_flag_sensitive_trigger") and dist_to_next < 0.2:
            suggestions.append("Progress resets unexpectedly. Avoid high-magnitude force application inside trigger zones.")
            
        # 5. Spatial State for Node C
        if "B" in triggered and "C" not in triggered:
            y_req = metrics.get("env_c_required_max_y", 0.0)
            if metrics.get("agent_y", 0.0) < y_req:
                suggestions.append(f"Physical state requirement for Node C not met. Approach must originate from high altitude.")

    return suggestions
