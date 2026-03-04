"""
Task-specific feedback generation for S-04: The Balancer
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """Format task-specific metrics"""
    metric_parts = []
    
    if 'load_caught' in metrics:
        metric_parts.append(f"**Load caught**: {metrics['load_caught']}")
    if 'beam_angle_deg' in metrics:
        metric_parts.append(f"**Beam angle**: {metrics['beam_angle_deg']:.1f}°")
    if 'max_angle_seen_deg' in metrics:
        metric_parts.append(f"**Max angle**: {metrics['max_angle_seen_deg']:.1f}°")
    if 'balance_duration' in metrics:
        metric_parts.append(f"**Balance duration**: {metrics['balance_duration']:.2f}s / {metrics.get('target_balance_time', 15):.1f}s")
    
    # Additional physics metrics (richer feedback similar to S_01)
    if 'structure_mass' in metrics:
        metric_parts.append(f"**Structure mass**: {metrics['structure_mass']:.2f}kg")
    if 'structure_com_x' in metrics and 'structure_com_y' in metrics:
        metric_parts.append(f"**Structure COM**: x={metrics['structure_com_x']:.3f}m, y={metrics['structure_com_y']:.3f}m (relative to pivot)")
    if 'net_torque_about_pivot' in metrics:
        metric_parts.append(f"**Net static torque about pivot**: {metrics['net_torque_about_pivot']:.1f} N·m (target ≈ 0)")
    if 'min_body_y' in metrics and metrics['min_body_y'] is not None:
        metric_parts.append(f"**Minimum body y**: {metrics['min_body_y']:.3f}m (failure if < -0.1m)")
    if metrics.get('load_mass') is not None and metrics.get('load_pos') is not None:
        lx, ly = metrics['load_pos']
        metric_parts.append(f"**Load**: m={metrics['load_mass']:.2f}kg at (x={lx:.3f}, y={ly:.3f})")
    
    return metric_parts


def get_improvement_suggestions(metrics: Dict[str, Any], score: float, success: bool, 
                                failed: bool, failure_reason: str = None, 
                                error: str = None) -> List[str]:
    """Generate improvement suggestions"""
    suggestions = []
    
    if error:
        error_lower = (error or "").lower()
        if "error building" in error_lower or "constraint" in error_lower:
            suggestions.append("- Beam limits for this task: width 0.1–7 m, height 0.1–2 m (enforced at build time)")
    
    if failed:
        if failure_reason and "ground" in failure_reason.lower():
            suggestions.append("- Structure is touching ground - ensure it only contacts the pivot")
            suggestions.append("- Adjust structure geometry to avoid ground contact")
            suggestions.append("- Consider raising the structure higher above the pivot to provide clearance")
        elif failure_reason and "catch" in failure_reason.lower():
            suggestions.append("- Structure must be present at (3,0) to catch the load")
            suggestions.append("- Extend structure to reach load position")
        elif failure_reason and "angle" in failure_reason.lower():
            suggestions.append("- Structure is not balanced - add counter-weight on opposite side")
            suggestions.append("- Use high-density beams for counter-weights")
            suggestions.append("- Adjust center of mass to balance the load")
            suggestions.append("- Consider adding damping (angular/linear) to reduce oscillations")
            suggestions.append("- If an obstacle is blocking your path, adjust the beam's `y` coordinate to build around it.")
            suggestions.append("- If wind is pushing the structure, the center of mass or aerodynamic profile needs to counteract the new torque.")
            suggestions.append("- If experiencing initial rotation, add active stabilization in agent_action()")
    
    # Torque/COM guided suggestions (works even when not 'failed' but not successful)
    if metrics:
        torque = metrics.get('net_torque_about_pivot')
        com_x = metrics.get('structure_com_x')
        max_angle = metrics.get('max_angle_seen_deg')
        balance_duration = metrics.get('balance_duration', 0.0)
        target_balance_time = metrics.get('target_balance_time', 15.0)
        
        if isinstance(torque, (int, float)):
            if abs(torque) > 500:
                if torque > 0:
                    suggestions.append("- Net torque is positive (clockwise heavy): move/add counterweight to negative x (left of pivot) or reduce mass on right")
                else:
                    suggestions.append("- Net torque is negative (counter-clockwise heavy): reduce left mass or shift counterweight closer to pivot")
        
        if isinstance(com_x, (int, float)):
            if abs(com_x) > 0.1:
                suggestions.append("- Try to align structure COM x closer to 0 to reduce steady tilt (target COM x ≈ 0)")
        
        # Suggestions for oscillation/instability issues
        if isinstance(max_angle, (int, float)) and max_angle > 5.0:
            suggestions.append("- Structure is oscillating - increase angular damping or add active stabilization")
            suggestions.append("- Consider using a rigid pivot connection instead of free rotation if allowed")
        
        # Suggestions for balance duration issues
        if balance_duration < target_balance_time * 0.5:
            suggestions.append(f"- Balance duration ({balance_duration:.1f}s) is below target ({target_balance_time:.1f}s)")
            suggestions.append("- Ensure structure maintains angle within limits for the full duration")
            suggestions.append("- Add damping or active control to prevent angle from drifting")
    
    return suggestions
