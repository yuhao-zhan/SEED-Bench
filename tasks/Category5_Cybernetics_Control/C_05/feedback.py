"""
Task-specific feedback for C-05: The Logic Lock.
Metrics and suggestions are grounded in evaluator outputs (no invented physics).
"""
from typing import Dict, Any, List

# Proximity hint when suggesting speed/force issues (order of zone half-width ~0.5 m).
NEAR_TARGET_ZONE_M = 0.2
# When env_flag_loose_a_to_b_recency is True (recency window wider than source), skip
# "A→B window expired" hints (curriculum uses 5000).

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
        in_zone = metrics.get("inside_next_required_zone")
        zone_note = (
            " Agent center is inside the **next required** switch zone; this |v| is what the simulator "
            "compares to the zone speed cap."
            if in_zone
            else ""
        )
        metric_parts.append(
            f"- Speed |v|: {metrics['speed']:.3f} m/s.{zone_note} "
            "(The cap applies only while inside a trigger zone; see task description.)"
        )
    if "cooldown_remaining" in metrics:
        metric_parts.append(f"- System Lockout (Cooldown): {metrics['cooldown_remaining']} steps")
    if "distance_to_next_zone" in metrics and metrics["distance_to_next_zone"] is not None:
        metric_parts.append(
            f"- Proximity to Target: {metrics['distance_to_next_zone']:.2f} m "
            "(shortest distance to the **switch zone rectangle** for the next required node)"
        )
    
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

    if metrics.get("timed_out"):
        metric_parts.append("\n**Episode limit**: Step budget exhausted before A→B→C completion.")
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
    speed_cap = metrics.get("env_speed_cap_inside")
    # Evaluator sets distance_to_next_zone to None when next_required is missing; treat as "far"
    # so comparisons below never raise TypeError on failure paths (e.g. wrong_order).
    _raw_dist = metrics.get("distance_to_next_zone")
    dist_to_next = float("inf") if _raw_dist is None else _raw_dist
    
    max_steps = metrics.get("max_steps") or 0
    step_count = metrics.get("step_count", 0)

    if not failed and not success:
        if next_req == "B":
            suggestions.append("Node B activation failed. Verify the temporal window following Node A.")
        elif next_req == "C":
            suggestions.append(
                "Node C activation failed. Verify **temporal window B→C** (you were in B recently enough), "
                "**C altitude / recent max y** over the lookback, **cooldown** after the previous trigger, "
                "and that **speed** and **in-zone controller force magnitude** stay within the stated limits so dwell accumulates."
            )
        if max_steps > 0 and step_count >= max_steps - 1:
            suggestions.append(
                "Episode step budget is almost exhausted; shorten path and timing where possible while "
                "keeping |v| and in-zone controller force within the stated caps so dwell still accumulates."
            )
        loose_ab = metrics.get("env_flag_loose_a_to_b_recency", False)
        if (
            "A" in triggered
            and "B" not in triggered
            and step_count >= max_steps - 5
            and not loose_ab
        ):
            suggestions.append(
                "If B never triggered, the A→B recency window may have expired—tighten the transition after A."
            )

    if failed:
        if metrics.get("timed_out"):
            suggestions.append(
                "Episode ended before the full A→B→C sequence; optimize timing and dwell under zone limits."
            )
        # 1. Sequence Root-Cause
        if metrics.get("wrong_order"):
            suggestions.append("Sequence violation. Nodes must be triggered in the order A -> B -> C.")
            
        # 2. Zone speed cap (|v| while inside the next-required zone is what the environment checks)
        inside = metrics.get("inside_next_required_zone")
        if (
            speed_cap is not None
            and speed > speed_cap
            and (inside or dist_to_next < NEAR_TARGET_ZONE_M)
        ):
            suggestions.append(
                "Speed magnitude exceeds the in-zone cap while at or inside the next required switch zone; "
                "dwell progress resets when |v| is above the cap—hold lower speed for consecutive steps inside the zone."
            )
            
        # 4. Input Sensitivity
        if metrics.get("env_flag_sensitive_trigger") and dist_to_next < NEAR_TARGET_ZONE_M:
            suggestions.append("Progress resets unexpectedly. Avoid high-magnitude force application inside trigger zones.")
            
        # 5. Spatial State for Node C (rule: recent max y over lookback must meet threshold; do not use current agent_y as proxy)
        if "B" in triggered and "C" not in triggered:
            suggestions.append("Physical state requirement for Node C may not be met. Ensure approach originates from an elevated path (recent max y over the lookback window must meet the threshold).")

    return suggestions
