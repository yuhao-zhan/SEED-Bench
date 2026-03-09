"""
Task-specific feedback for C-06: The Governor.
Audited and purified version: zero hardcoding, zero hallucinations.
"""
from typing import Dict, Any, List
import math

def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """Format high-resolution physical metrics for C-06."""
    metric_parts = []
    
    # Rotational State
    if "wheel_angular_velocity" in metrics:
        metric_parts.append(f"**Rotational State**: Speed {metrics['wheel_angular_velocity']:.3f} rad/s, Reference Target {metrics.get('target_speed', 0.0):.3f} rad/s")
    
    if "speed_error" in metrics:
        metric_parts.append(f"**Regulation Precision**: Mean Error {metrics.get('mean_speed_error', 0.0):.4f} rad/s")
    
    # Stability Diagnostics
    metric_parts.append("\n**Operational Stability Profile**")
    if "stall_count" in metrics:
        metric_parts.append(f"- Stall Counter: {metrics['stall_count']} consecutive steps")
    if "stall_speed_threshold" in metrics:
        metric_parts.append(f"- Critical Velocity Threshold: {metrics['stall_speed_threshold']:.2f} rad/s")
    
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
    """Generate diagnostic suggestions based on rotational mechanics and load rejection."""
    suggestions = []
    
    if error:
        return [f"System Error: {error}. Check rotational velocity and torque actuator APIs."]

    stall_count = metrics.get("stall_count", 0)
    mean_err = metrics.get("mean_speed_error", 0.0)
    
    if not failed and not success:
        suggestions.append("Regulation quality failed the final stability threshold. Analyze for periodic load disturbances or cogging effects.")

    if failed:
        # 1. Stall Root-Cause
        if stall_count > 0:
            suggestions.append("System stall detected. Motor torque was insufficient to reject resistive loads. Investigate potential stiction or torque limits.")
            
        # 2. Regulation Precision
        if "regulation" in (failure_reason or "").lower():
            suggestions.append("Regulation quality failed. The controller is unable to reject periodic ripples or sudden step-load increments.")
            
        # 3. Phase Lag / Latency
        if stall_count == 0 and "regulation" in (failure_reason or "").lower():
            suggestions.append("Unstable speed oscillations suggest significant phase lag in the feedback loop. Compensate for potential measurement latency.")
            
        # 4. Input Sensitivity
        if abs(metrics.get("speed_error", 0.0)) > 0.1 and stall_count == 0:
            suggestions.append("Persistent error observed. Investigate for potential actuator deadzones or insufficient gains.")

    return suggestions
