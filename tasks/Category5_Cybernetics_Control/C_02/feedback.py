"""
Task-specific feedback for C-02: The Lander.
Purified version: strictly grounded in evaluator metrics.
"""
from typing import Dict, Any, List
import math

def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """Format high-resolution physical metrics for C-02."""
    metric_parts = []
    
    if "lander_x" in metrics and "lander_y" in metrics:
        metric_parts.append(f"**Lander Position**: ({metrics['lander_x']:.2f}, {metrics['lander_y']:.2f})")
    if "lander_vx" in metrics and "lander_vy" in metrics:
        metric_parts.append(f"**Lander Velocity**: (vx: {metrics['lander_vx']:.2f}, vy: {metrics['lander_vy']:.2f}) m/s")
    if "lander_angle" in metrics:
        metric_parts.append(f"**Orientation**: {math.degrees(metrics['lander_angle']):.2f}° (0° = Upright)")
    if "remaining_fuel" in metrics and metrics["remaining_fuel"] is not None:
        metric_parts.append(f"**Propellant Status**: {metrics['remaining_fuel']:.1f} N·s remaining")
    
    metric_parts.append("\n**Touchdown Evaluation**")
    if "landed" in metrics:
        metric_parts.append(f"- Contact Reached: {metrics['landed']}")
    if "landing_vy" in metrics and metrics["landing_vy"] is not None:
        metric_parts.append(f"- Impact Vertical Speed: {abs(metrics['landing_vy']):.2f} m/s")
    if "landing_angle" in metrics and metrics["landing_angle"] is not None:
        metric_parts.append(f"- Final Attitude Deviation: {math.degrees(abs(metrics['landing_angle'])):.2f}°")
    
    metric_parts.append("\n**Environmental Bounds**")
    if "zone_x_min" in metrics and "zone_x_max" in metrics:
        metric_parts.append(f"- Active Landing Window (x): [{metrics['zone_x_min']:.2f}, {metrics['zone_x_max']:.2f}] m")
    if "max_safe_vertical_speed" in metrics:
        metric_parts.append(f"- Landing Speed Tolerance: {metrics['max_safe_vertical_speed']:.2f} m/s")
    if "height_above_ground" in metrics:
        metric_parts.append(f"- Surface Altitude: {metrics['height_above_ground']:.3f} m")
    
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
    """Generate diagnostic suggestions based on landing and atmospheric mechanics."""
    suggestions = []
    
    if error:
        return [f"System Error: {error}. Check API usage."]

    if not failed and not success:
        if not metrics.get("landed", False):
            suggestions.append("Touchdown was not achieved before the mission deadline. Verify the vertical throttle profile to ensure sufficient proximity to the target surface.")
        else:
            suggestions.append("The craft landed without critical failure, but mission success criteria were not fully satisfied. Analyze propellant efficiency and zone synchronization.")

    if failed:
        vy = abs(metrics.get("landing_vy", 0.0) if metrics.get("landing_vy") is not None else 0.0)
        limit_vy = metrics.get("max_safe_vertical_speed", 2.0)
        
        # 1. Structural/Impact
        if metrics.get("landed") and vy > limit_vy:
            suggestions.append("Structural failure due to high impact velocity. Adjust the descent throttle to account for potential gravity fluctuations or mass budget changes.")
            
        # 2. Stability
        angle_deg = math.degrees(abs(metrics.get("landing_angle", 0.0) if metrics.get("landing_angle") is not None else 0.0))
        limit_angle = math.degrees(metrics.get("max_landing_angle", 0.175))
        if metrics.get("landed") and angle_deg > limit_angle:
            suggestions.append("The craft capsized. Stabilize the attitude during the final approach phase to ensure an upright touchdown.")
            
        # 3. Dynamic Zone
        if metrics.get("landed") and "out of landing zone" in (failure_reason or "").lower():
            suggestions.append("Touchdown occurred outside the valid window. The landing platform is dynamic; coordinate the vertical descent with the platform's periodic movement.")
            
        # 4. Resource Depletion
        fuel = metrics.get("remaining_fuel", 0)
        min_fuel = metrics.get("min_fuel_remaining_at_landing", 450.0)
        if fuel <= 0 and not metrics.get("landed"):
            suggestions.append("Mission failure due to propellant exhaustion. Optimize the flight path to reduce high-thrust maneuvers against gravity.")
        elif metrics.get("landed") and fuel < min_fuel:
            suggestions.append("Mission efficiency requirement failed. A more energy-optimal descent profile is required to meet propellant margins.")

    return suggestions
