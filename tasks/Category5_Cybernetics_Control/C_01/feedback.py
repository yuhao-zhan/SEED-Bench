"""
Task-specific feedback for C-01: Cart-Pole Swing-up then Balance.
Audited and purified version: zero hardcoding, zero hallucinations.
"""
from typing import Dict, Any, List
import math

def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """Format high-resolution physical metrics for C-01."""
    metric_parts = []
    
    # Core State Variables
    if "pole_angle_deg" in metrics:
        metric_parts.append(f"**Pole State**: Angle {metrics['pole_angle_deg']:.2f}° (Vertical = 0°), Angular Velocity {metrics.get('pole_angular_velocity', 0.0):.3f} rad/s")
    
    if "cart_x" in metrics:
        metric_parts.append(f"**Cart State**: Position {metrics['cart_x']:.3f} m, Velocity {metrics.get('cart_velocity_x', 0.0):.3f} m/s")
    
    # Phase Diagnostics
    if "balance_achieved" in metrics:
        phase = "Balancing/Stability" if metrics["balance_achieved"] else "Energy Injection/Swing-up"
        metric_parts.append(f"- Active Control Objective: {phase}")
    
    # Boundary Proximity
    if "dist_from_center" in metrics and "safe_half_range" in metrics:
        metric_parts.append(f"- Track Displacement: {metrics['dist_from_center']:.3f} m (Safety limit: ±{metrics['safe_half_range']:.1f}m)")
    
    if "step_count" in metrics:
        metric_parts.append(f"- Mission Duration: {metrics['step_count']} steps")
    
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
        return [f"System Error: {error}. Check API usage."]

    safe_range = metrics.get('safe_half_range', float('inf'))
    dist_from_center = metrics.get('dist_from_center', 0.0)
    balance_achieved = metrics.get("balance_achieved", False)

    if not failed and not success:
        if not balance_achieved:
            suggestions.append("Energy injection is insufficient to reach the vertical equilibrium zone. Analyze the impulse-momentum transfer between the cart and the pendulum.")
        else:
            suggestions.append("Long-term stability was not maintained. This indicates a potential mismatch between the controller's response frequency and the system's natural oscillations.")

    if failed:
        # 1. Boundary vs Stability Root-Cause
        if dist_from_center > safe_range:
            if not balance_achieved:
                suggestions.append("The swing-up maneuver exceeded the spatial displacement budget. High-magnitude impulses are causing excessive cart translation before the pole can reach the balance zone.")
            else:
                suggestions.append("The stabilization phase is inducing horizontal drift. Ensure the balancing loop accounts for the cart's displacement from the track center.")
            
        # 2. Stability Failure
        if balance_achieved and "upright" in (failure_reason or "").lower():
            suggestions.append("The pole reached the balance zone but was lost due to excessive entry momentum or uncompensated disturbances. Analyze the phase feedback for potential sensing latency.")
            
        # 3. Energy Dissipation
        if not balance_achieved and dist_from_center <= safe_range:
            suggestions.append("The system is failing to build sufficient potential energy for swing-up. Check for environmental factors like high damping or altered gravity that may be dissipating input work.")

    return suggestions
