"""
Task-specific feedback for C-06: The Governor.
Purified version: strictly grounded in evaluator metrics.
"""
from typing import Dict, Any, List

def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """Format high-resolution physical metrics for C-06."""
    metric_parts = []
    
    if "wheel_angular_velocity" in metrics:
        metric_parts.append(f"**Current Angular Velocity**: {metrics['wheel_angular_velocity']:.3f} rad/s")
    if "target_speed" in metrics:
        metric_parts.append(f"**Reference Target Speed**: {metrics['target_speed']:.3f} rad/s")
    if "mean_speed_error" in metrics:
        metric_parts.append(f"**Cumulative Regulation Error**: {metrics['mean_speed_error']:.4f} rad/s")
    
    metric_parts.append("\n**Operational Stability**")
    if "stall_count" in metrics:
        metric_parts.append(f"- Stall Protocol Counter: {metrics['stall_count']}/60 steps")
    if "stall_speed_threshold" in metrics:
        metric_parts.append(f"- Minimum Operational Speed: {metrics['stall_speed_threshold']:.1f} rad/s")
    
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
    """Generate diagnostic suggestions based on rotational mechanics and load rejection."""
    suggestions = []
    
    if error:
        return [f"System Error: {error}. Check rotational velocity and torque APIs."]

    if not failed and not success:
        # Regulation phase reached but failed final error checks
        if "regulation" in (failure_reason or "").lower() or metrics.get("mean_speed_error", 1.0) > 0.1:
            suggestions.append("The mean regulation quality failed the stability threshold. Analyze the system response to periodic load disturbances and nonlinear cogging effects.")
        else:
            suggestions.append("Regulation quality was near target, but mission completion was not confirmed. Verify the consistency of your control output across the full operational range.")

    if failed:
        # 1. Stall Mechanics
        if metrics.get("stall_count", 0) >= 60:
            suggestions.append("System failure due to wheel stall. Motor torque was insufficient to reject resistive loads. Observe if stall occurs at high speed (drag-limited) or low speed (stiction-limited).")
            
        # 2. Regulation Precision
        if "regulation" in (failure_reason or "").lower():
            suggestions.append("Regulation quality failed. This suggests the controller cannot reject periodic ripples or sudden step-load increments.")
            suggestions.append("Consider adjusting gains to improve disturbance rejection without inducing oscillatory instability.")
            
        # 3. Latency/Phase Lag
        if metrics.get("stall_count", 0) < 60 and "regulation" in (failure_reason or "").lower():
            suggestions.append("Unstable oscillations detected. This indicates significant phase lag in the feedback loop; ensure your control strategy accounts for sensing latency.")

    return suggestions
