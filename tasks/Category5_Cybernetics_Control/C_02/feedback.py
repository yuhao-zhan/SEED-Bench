"""
Task-specific feedback for C-02: The Lander.
Audited and purified version: zero hardcoding, zero hallucinations.
"""
from typing import Dict, Any, List
import math

def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """Format high-resolution physical metrics for C-02."""
    metric_parts = []
    
    # Core State Variables
    if "lander_x" in metrics and "lander_y" in metrics:
        metric_parts.append(f"**Flight State**: Position ({metrics['lander_x']:.2f}, {metrics['lander_y']:.2f}), Vertical Speed {metrics.get('lander_vy', 0.0):.2f} m/s")
    
    if "lander_angle" in metrics:
        metric_parts.append(f"**Attitude**: {math.degrees(metrics['lander_angle']):.2f}° (0° = Upright), Angular Rate {metrics.get('lander_angular_velocity', 0.0):.3f} rad/s")
    
    if "remaining_fuel" in metrics and metrics["remaining_fuel"] is not None:
        metric_parts.append(f"**Resource Reserve**: {metrics['remaining_fuel']:.1f} N·s propellant remaining")
    
    # Touchdown Specifics
    metric_parts.append("\n**Final Phase Diagnostics**")
    if metrics.get("landed", False):
        if "landing_vy" in metrics and metrics["landing_vy"] is not None:
            metric_parts.append(f"- Impact Magnitude (vy): {abs(metrics['landing_vy']):.3f} m/s")
        if "landing_angle" in metrics and metrics["landing_angle"] is not None:
            metric_parts.append(f"- Attitude Deviation: {math.degrees(abs(metrics['landing_angle'])):.2f}°")
    else:
        metric_parts.append(f"- Current Altitude: {metrics.get('height_above_ground', 0.0):.3f} m")

    # Environmental Limits
    metric_parts.append("\n**Environmental Constraints**")
    if "zone_x_min" in metrics and "zone_x_max" in metrics:
        metric_parts.append(f"- Active Landing Zone (x): [{metrics['zone_x_min']:.2f}, {metrics['zone_x_max']:.2f}] m")
    if "max_safe_vertical_speed" in metrics:
        metric_parts.append(f"- Structural Limit (Impact): {metrics['max_safe_vertical_speed']:.2f} m/s")
    
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

    # Dynamic Limits
    vy = abs(metrics.get("landing_vy", 0.0) if metrics.get("landing_vy") is not None else 0.0)
    limit_vy = metrics.get("max_safe_vertical_speed", float('inf'))
    fuel = metrics.get("remaining_fuel", 0.0)
    min_fuel = metrics.get("min_fuel_remaining_at_landing", 0.0)
    landed = metrics.get("landed", False)
    limit_angle = metrics.get("max_landing_angle", float('inf'))
    angle = abs(metrics.get("landing_angle", 0.0) if metrics.get("landing_angle") is not None else 0.0)
    
    if not failed and not success:
        if not landed:
            suggestions.append("The mission timed out before contact was achieved. Adjust the vertical throttle to ensure proximity within the timeframe.")
        else:
            suggestions.append("Touchdown was achieved but mission efficiency protocols were not met. Analyze propellant management.")

    if failed:
        # 1. Kinetic Stress Root-Cause
        if landed and vy > limit_vy:
            suggestions.append("Structural failure due to high impact velocity. Descent momentum must be neutralized more effectively before touchdown.")
            
        # 2. Attitude Loss
        if landed and angle > limit_angle:
            suggestions.append("The craft capsized. High rotational inertia or sensing lag may be destabilizing the attitude during the high-thrust final approach.")
            
        # 3. Dynamic Window Synchronization
        if landed and "out of landing zone" in (failure_reason or "").lower():
            suggestions.append("The landing occurred outside the valid horizontal window. Coordinate the descent with the platform's periodic movement.")
            
        # 4. Propellant Depletion
        if fuel <= 0 and not landed:
            suggestions.append("Mission failure due to propellant exhaustion. The flight path may be inefficiently managing course corrections against environmental disturbances.")
        elif landed and fuel < min_fuel:
            suggestions.append("Propellant margins were insufficient for the mission requirements. A more energy-efficient descent profile is needed.")

        # 5. Collision (No-fly corridor)
        if "forbidden zone" in (failure_reason or "").lower():
            suggestions.append("Flight path breached corridor constraints. Verify vertical altitude limits and maintain stabilization within the safe passage zone.")

    return suggestions
