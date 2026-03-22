"""
Task-specific feedback for C-04: The Escaper.
Audited and purified version: zero hardcoding, zero hallucinations.
"""
from typing import Dict, Any, List
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))
from tasks.Category5_Cybernetics_Control.C_04.environment import (
    ACTIVATION_X_MAX,
    ACTIVATION_X_MIN,
    LOCK_GATE_X_MAX,
    LOCK_GATE_X_MIN,
    ONEWAY_X,
)

# Fallbacks when metrics omit zone keys (e.g. direct unit tests calling feedback only).
def _m(
    metrics: Dict[str, Any],
    key: str,
    default: float,
) -> float:
    v = metrics.get(key, default)
    try:
        return float(v)
    except (TypeError, ValueError):
        return float(default)
from tasks.Category5_Cybernetics_Control.C_04.evaluator import CONSECUTIVE_EXIT_STEPS_REQUIRED

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
    if "whisker_up" in metrics:
        metric_parts.append(f"- Upward Proximity: {metrics['whisker_up']:.2f} m")
    if "whisker_down" in metrics:
        metric_parts.append(f"- Downward Proximity: {metrics['whisker_down']:.2f} m")
    
    # Mission Progress
    metric_parts.append("\n**Escape Progress Profile**")
    if "progress_x_pct" in metrics:
        metric_parts.append(f"- Linear Progression to Goal: {metrics['progress_x_pct']:.1f}%")
    if "consecutive_steps_in_exit" in metrics:
        metric_parts.append(f"- Goal Occupancy Duration: {metrics['consecutive_steps_in_exit']}/{CONSECUTIVE_EXIT_STEPS_REQUIRED} steps")
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

    x = float(metrics.get("agent_x", 0.0))
    exit_x = float(metrics.get("exit_x_min", 0.0))
    reached_exit = metrics.get("reached_exit", False)
    oneway_x = _m(metrics, "oneway_x_threshold", ONEWAY_X)
    lock_lo = _m(metrics, "lock_gate_x_min", LOCK_GATE_X_MIN)
    lock_hi = _m(metrics, "lock_gate_x_max", LOCK_GATE_X_MAX)
    act_lo = _m(metrics, "activation_x_min", ACTIVATION_X_MIN)
    act_hi = _m(metrics, "activation_x_max", ACTIVATION_X_MAX)
    
    if not failed and not success:
        if not reached_exit:
            suggestions.append("Navigation through the final corridor remains incomplete. Investigate for unresponsive barriers or non-obvious environmental locks.")
        else:
            suggestions.append("The escape zone was reached but occupancy was lost. Stabilize position within the exit band.")

    if failed:
        # 1. Behavioral Unlock Root-Cause (Diagnostic)
        if x < exit_x and "timeout" in (failure_reason or "").lower():
            if x > oneway_x:
                suggestions.append("A unidirectional rightward bias applies in this region. If progress feels restricted further ahead, investigate for non-obvious environmental locks.")
            else:
                suggestions.append("Mission timed out in the early maze phase. Analyze for energy dissipation zones or unmodeled horizontal forcing.")

        if lock_lo <= x <= lock_hi and not metrics.get("unlocked"):
            suggestions.append(
                "A repelling force field blocks the corridor here until **behavioral unlock** is completed. "
                f"Complete the unlock protocol in the activation zone (x in [{act_lo:g}, {act_hi:g}] m), then retry."
            )
            
        # 3. Collision / Structural Failure
        fr = (failure_reason or "").lower()
        if "structural" in fr or "impulse" in fr:
            suggestions.append(
                "Structural impulse limit exceeded: reduce impact speed and avoid hard wall contacts; check current structural k in the task description."
            )
        elif "collision" in fr:
            suggestions.append(
                "Collision detected. Compensate for potential signal latency in the proximity (whisker) sensor stream or adjust your navigation strategy."
            )

        # 4. Final Hold Protocol
        if reached_exit and metrics.get("consecutive_steps_in_exit", 0) < CONSECUTIVE_EXIT_STEPS_REQUIRED:
            suggestions.append("Exit occupancy failed the duration protocol. Maintain steady control within the goal coordinates for the required consecutive steps.")

    return suggestions
