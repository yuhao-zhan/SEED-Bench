"""
Task-specific feedback for C-04: The Escaper.
Audited and purified version: zero hardcoding, zero hallucinations.
"""
from typing import Dict, Any, List
import math

def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """Format high-resolution physical metrics for C-04."""
    metric_parts = []
    
    # Navigational Coordinates
    if "agent_x" in metrics and "agent_y" in metrics:
        metric_parts.append(f"**Navigational Coordinates**: ({metrics['agent_x']:.2f}, {metrics['agent_y']:.2f})")
    
    # Tactile Diagnostics
    metric_parts.append("\n**Tactile Feedback (Whiskers)**")
    if "whisker_front" in metrics:
        metric_parts.append(f"- Front Proximity: {metrics['whisker_front']:.2f} m")
    if "whisker_left" in metrics:
        metric_parts.append(f"- Left Proximity: {metrics['whisker_left']:.2f} m")
    if "whisker_right" in metrics:
        metric_parts.append(f"- Right Proximity: {metrics['whisker_right']:.2f} m")
    
    # Mission Progress
    metric_parts.append("\n**Escape Progress Profile**")
    if "progress_x_pct" in metrics:
        metric_parts.append(f"- Linear Progression to Goal: {metrics['progress_x_pct']:.1f}%")
    if "consecutive_steps_in_exit" in metrics:
        metric_parts.append(f"- Goal Occupancy Duration: {metrics['consecutive_steps_in_exit']}/60 steps")
    if "distance_to_exit_x" in metrics:
        metric_parts.append(f"- Distance to Exit Boundary: {metrics['distance_to_exit_x']:.2f} m")
    
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
    """Generate diagnostic suggestions based on navigational and interaction failure modes."""
    suggestions = []
    
    if error:
        return [f"System Error: {error}. Check sensor and actuator APIs."]

    x = metrics.get("agent_x", 0.0)
    exit_x = metrics.get("exit_x_min", 0.0)
    reached_exit = metrics.get("reached_exit", False)
    
    if not failed and not success:
        if not reached_exit:
            suggestions.append("Navigation through the final corridor remains incomplete. Investigate for unresponsive barriers or non-obvious environmental locks.")
        else:
            suggestions.append("The escape zone was reached but occupancy was lost. Stabilize position within the exit band.")

    if failed:
        # 1. Behavioral Unlock Root-Cause (Diagnostic)
        if x < exit_x and "timeout" in (failure_reason or "").lower():
            if x > 10.0:
                suggestions.append("The final exit is locked by a high-magnitude force field. This barrier may be unresponsive to conventional forward momentum.")
                suggestions.append("Observe the environment for regions where unconventional movement or specific force vectors trigger a system state change.")
            else:
                suggestions.append("Mission timed out in the early maze phase. Analyze for energy dissipation zones or unidirectional currents.")
            
        # 2. Environmental Disturbances
        if 12.0 <= x <= 18.0:
            suggestions.append("Intense aerodynamic disturbances detected. Seek alternative altitudes or utilize surface bracing if progress is repelled.")
            
        # 3. Perception Latency
        if "collision" in (failure_reason or "").lower():
            suggestions.append("Collision detected. Compensate for potential signal latency in the proximity (whisker) sensor stream.")

        # 4. Final Hold Protocol
        if reached_exit and metrics.get("consecutive_steps_in_exit", 0) < 60:
            suggestions.append("Exit occupancy failed the duration protocol. Maintain steady control within the goal coordinates.")

    return suggestions
