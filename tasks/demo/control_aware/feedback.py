"""
Task-specific feedback generation for control-aware task (speed-controlled slider)
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Format task-specific metrics for slider control task
    """
    metric_parts = []
    
    if 'distance_traveled' in metrics:
        metric_parts.append(f"**Distance traveled**: {metrics['distance_traveled']:.2f}m")
        metric_parts.append(f"**Current position**: x={metrics.get('current_x', 0):.2f}m")
        if 'target_x' in metrics:
            metric_parts.append(f"**Target position**: x={metrics['target_x']:.2f}m")
        if 'progress' in metrics:
            metric_parts.append(f"**Progress**: {metrics['progress']:.1f}%")
        if 'max_distance' in metrics:
            metric_parts.append(f"**Maximum distance reached**: {metrics['max_distance']:.2f}m")
        
        # Speed limit information (CRITICAL for this task)
        if 'current_zone' in metrics:
            metric_parts.append(f"\n**Speed Zone Information**:")
            metric_parts.append(f"- Current zone: {metrics['current_zone']}")
            if 'speed_limit' in metrics:
                metric_parts.append(f"- Speed limit: {metrics['speed_limit']:.2f} m/s")
            if 'velocity_x' in metrics:
                metric_parts.append(f"- Current speed: {metrics['velocity_x']:.2f} m/s")
            if 'speed_violated' in metrics and metrics['speed_violated']:
                metric_parts.append(f"- ⚠️ **SPEED LIMIT VIOLATED**")
            if 'speed_violation_count' in metrics:
                metric_parts.append(f"- Total speed violations: {metrics['speed_violation_count']}")
    
    return metric_parts


def get_improvement_suggestions(metrics: Dict[str, Any], score: float, success: bool, 
                                failed: bool, failure_reason: str = None, 
                                error: str = None) -> List[str]:
    """
    Generate task-specific improvement suggestions for slider control task
    """
    suggestions = []
    
    if error:
        suggestions.append("- Review the error message above to identify the specific issue")
        suggestions.append("- Ensure slider is created correctly with add_slider()")
    
    elif failed:
        if failure_reason and "speed limit violated" in failure_reason.lower():
            suggestions.append("- **CRITICAL**: Speed limit violation detected")
            suggestions.append("- You MUST implement dynamic speed control in `agent_action()` function")
            suggestions.append("- Get current slider position using `sandbox.get_slider_state(slider)`")
            suggestions.append("- Determine which speed zone you are in:")
            suggestions.append("  - Zone 1 (0-10m): Speed limit 1.5 m/s")
            suggestions.append("  - Zone 2 (10-20m): Speed limit 3.0 m/s")
            suggestions.append("  - Zone 3 (20-30m): Speed limit 2.0 m/s")
            suggestions.append("- Adjust slider velocity dynamically based on current zone")
            suggestions.append("- Use `sandbox.set_slider_velocity(slider, velocity)` to update speed")
            suggestions.append("- Set velocity to 95% of limit to ensure safety margin")
            if 'current_zone' in metrics and 'speed_limit' in metrics and 'velocity_x' in metrics:
                current_zone = metrics.get('current_zone', 'Unknown')
                speed_limit = metrics.get('speed_limit', 0)
                current_speed = metrics.get('velocity_x', 0)
                suggestions.append(f"- Current status: In {current_zone}, speed limit is {speed_limit:.2f} m/s, but slider speed is {current_speed:.2f} m/s")
        elif failure_reason and "fell off track" in failure_reason.lower():
            suggestions.append("- Slider fell off track - check slider y position")
            suggestions.append("- Ensure slider stays on track (y ≈ 3.0m)")
        elif failure_reason and "moved backward" in failure_reason.lower():
            suggestions.append("- Slider moved backward - ensure velocity is always non-negative")
            suggestions.append("- Check that slider velocity is set to positive values only")
        elif failure_reason and "timeout" in failure_reason.lower():
            suggestions.append("- Did not reach target within time limit")
            suggestions.append("- Increase slider speed (but stay within zone limits)")
            suggestions.append("- Ensure speed control is working correctly in all zones")
    
    elif not success:
        if 'distance_traveled' in metrics:
            if metrics.get('distance_traveled', 0) < 5:
                suggestions.append("- Slider is moving too slowly")
                suggestions.append("- Increase speed in Zone 1 (but stay under 1.5 m/s limit)")
                suggestions.append("- **IMPORTANT**: Ensure you implement `agent_action()` function")
            elif metrics.get('progress', 0) < 50:
                suggestions.append("- Slider is making progress but needs to reach target")
                suggestions.append("- **CRITICAL**: Ensure speed control is working correctly")
                suggestions.append("- Check that `agent_action()` adjusts speed based on position")
                if 'speed_violation_count' in metrics and metrics['speed_violation_count'] > 0:
                    suggestions.append(f"- ⚠️ Speed violations detected: {metrics['speed_violation_count']} - reduce speed in appropriate zones")
            else:
                suggestions.append("- Close to target, check speed control in Zone 3")
                suggestions.append("- Zone 3 (20-30m) has speed limit 2.0 m/s")
    
    return suggestions
