"""
Task-specific feedback for C-04: The Escaper.
Purified version: strictly grounded in evaluator metrics.
"""
from typing import Dict, Any, List
import math

def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """Format high-resolution physical metrics for C-04."""
    metric_parts = []
    
    if "agent_x" in metrics and "agent_y" in metrics:
        metric_parts.append(f"**Agent Coordinates**: ({metrics['agent_x']:.2f}, {metrics['agent_y']:.2f})")
    
    metric_parts.append("\n**Tactile (Whisker) Feedback**")
    if "whisker_front" in metrics:
        metric_parts.append(f"- Front Proximity: {metrics['whisker_front']:.2f} m")
    if "whisker_left" in metrics:
        metric_parts.append(f"- Left Proximity: {metrics['whisker_left']:.2f} m")
    if "whisker_right" in metrics:
        metric_parts.append(f"- Right Proximity: {metrics['whisker_right']:.2f} m")
    
    metric_parts.append("\n**Escape Progress**")
    if "progress_x_pct" in metrics:
        metric_parts.append(f"- Linear Progression: {metrics['progress_x_pct']:.1f}%")
    if "reached_exit" in metrics:
        metric_parts.append(f"- Exit Occupancy: {metrics['reached_exit']}")
    if "consecutive_steps_in_exit" in metrics:
        metric_parts.append(f"- Final Hold Timer: {metrics['consecutive_steps_in_exit']}/60")
    if "distance_to_exit_x" in metrics:
        metric_parts.append(f"- Displacement to Goal: {metrics['distance_to_exit_x']:.2f} m")
    
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
    """Generate diagnostic suggestions based on navigational and interaction failure modes."""
    suggestions = []
    
    if error:
        return [f"System Error: {error}. Check API usage."]

    if not failed and not success:
        if not metrics.get("reached_exit", False):
            suggestions.append("Navigation through the final corridor was incomplete. Analyze whisker data for non-linear aerodynamic resistance or zero-friction surface anomalies.")
        else:
            suggestions.append("The exit zone was reached but the hold was not maintained. Stabilize position within the goal coordinates for the full duration.")

    if failed:
        x = metrics.get("agent_x", 0.0)
        exit_x = metrics.get("exit_x_min", 18.0)
        
        # 1. Behavioral Unlock (Grounded but non-spoiler)
        if x < exit_x and "timeout" in (failure_reason or "").lower():
            suggestions.append("Forward progress appears to be blocked by an impenetrable mechanical barrier. This mission requires a specific behavioral interaction within an activation zone to unlock.")
            suggestions.append("Observe the environment for regions where unconventional movement or force application triggers a system state change.")
            
        # 2. Dynamic Disturbances
        if x > exit_x / 3:
            suggestions.append("Localized physical disturbances (currents or shear flows) detected. If the robot stalls or is repelled, seek alternative altitudes or utilize surface bracing.")
            
        # 3. Perception Latency
        if "collision" in (failure_reason or "").lower() or "stuck" in (failure_reason or "").lower():
            suggestions.append("Collision detected. If the robot is unable to react to walls, compensate for potential signal latency in the proximity (whisker) sensors.")

        # 4. Final Accuracy
        if metrics.get("reached_exit") and metrics.get("consecutive_steps_in_exit", 0) < 60:
            suggestions.append("The escape protocol failed due to positional drift. Maintain steady control within the exit band to complete the mission.")

    return suggestions
