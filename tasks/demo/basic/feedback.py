"""
Task-specific feedback generation for basic task
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Format task-specific metrics for basic task
    Args:
        metrics: Evaluation metrics dictionary
    Returns:
        List of formatted metric strings
    """
    metric_parts = []
    
    if 'distance_traveled' in metrics:
        metric_parts.append(f"**Distance traveled**: {metrics['distance_traveled']:.2f}m")
        metric_parts.append(f"**Current position**: x={metrics.get('current_x', 0):.2f}m, y={metrics.get('current_y', 0):.2f}m")
        if 'target_x' in metrics:
            metric_parts.append(f"**Target position**: x={metrics['target_x']:.2f}m")
        if 'progress' in metrics:
            metric_parts.append(f"**Progress**: {metrics['progress']:.1f}%")
        if 'max_distance' in metrics:
            metric_parts.append(f"**Maximum distance reached**: {metrics['max_distance']:.2f}m")
        if 'step_count' in metrics:
            metric_parts.append(f"**Simulation steps**: {metrics['step_count']}")
        
        # Physical state information for fine-grained debugging
        metric_parts.append("\n**Physical State Information**:")
        if 'current_x' in metrics and 'current_y' in metrics:
            metric_parts.append(f"- Agent position: ({metrics['current_x']:.3f}, {metrics['current_y']:.3f})")
        if 'velocity' in metrics:
            metric_parts.append(f"- Agent velocity: {metrics['velocity']:.3f} m/s")
        if 'velocity_x' in metrics and 'velocity_y' in metrics:
            metric_parts.append(f"- Agent velocity components: vx={metrics['velocity_x']:.3f} m/s, vy={metrics['velocity_y']:.3f} m/s")
        if 'angular_velocity' in metrics:
            metric_parts.append(f"- Agent angular velocity: {metrics['angular_velocity']:.3f} rad/s")
        if 'angle' in metrics:
            metric_parts.append(f"- Agent angle: {metrics['angle']:.3f} rad ({metrics['angle'] * 180 / 3.14159:.1f}°)")
    
    # Add any additional metrics that might be present
    excluded_keys = ['distance_traveled', 'current_x', 'current_y', 'target_x', 'progress', 
                    'max_distance', 'step_count', 'success', 'failed', 'failure_reason',
                    'velocity', 'velocity_x', 'velocity_y', 'angular_velocity', 'angle']
    other_metrics = {k: v for k, v in metrics.items() if k not in excluded_keys}
    if other_metrics:
        metric_parts.append("\n**Additional Metrics**:")
        for key, value in other_metrics.items():
            if isinstance(value, (int, float)):
                metric_parts.append(f"- {key}: {value:.3f}" if isinstance(value, float) else f"- {key}: {value}")
            else:
                metric_parts.append(f"- {key}: {value}")
    
    return metric_parts


def get_improvement_suggestions(metrics: Dict[str, Any], score: float, success: bool, 
                                failed: bool, failure_reason: str = None, 
                                error: str = None) -> List[str]:
    """
    Generate task-specific improvement suggestions for basic task
    Args:
        metrics: Evaluation metrics dictionary
        score: Score (0-100)
        success: Whether successful
        failed: Whether failed
        failure_reason: Failure reason
        error: Error message if code execution failed
    Returns:
        List of improvement suggestion strings
    """
    suggestions = []
    
    if error:
        # Suggestions based on error type
        error_lower = error.lower()
        if "chassis height" in error_lower and "exceeds" in error_lower:
            suggestions.append("- Reduce chassis height to be within 1.0m limit")
            suggestions.append("- Check that you are not creating obstacles as part of the agent (obstacles are part of the environment, not the agent)")
        elif "wheel" in error_lower and ("too many" in error_lower or "exceeds" in error_lower or "maximum" in error_lower):
            suggestions.append("- Vehicle must have at most 2 wheels")
            suggestions.append("- Reduce the number of wheels to 2 or fewer")
            suggestions.append("- A standard vehicle design uses 2 wheels (front and rear)")
        elif "error building agent" in error_lower:
            suggestions.append("- Review the error message above to identify the specific constraint violation")
            suggestions.append("- Ensure all parameters (wheel radius, chassis height, etc.) are within allowed ranges")
            suggestions.append("- Check that wheels are positioned to contact the ground (y - radius ≈ 1.0)")
            suggestions.append("- Ensure the design has at most 2 wheels")
    
    elif failed:
        if failure_reason and "design constraint violated" in failure_reason.lower():
            # Handle design constraint violations from evaluator
            failure_lower = failure_reason.lower()
            if "wheel" in failure_lower and ("too many" in failure_lower or "maximum" in failure_lower):
                suggestions.append("- Vehicle must have at most 2 wheels")
                suggestions.append("- Reduce the number of wheels to 2 or fewer")
                suggestions.append("- A standard vehicle design uses 2 wheels (front and rear)")
            if "chassis height" in failure_lower and "exceeds" in failure_lower:
                suggestions.append("- Reduce chassis height to be within 1.0m limit")
            if "wheel radius" in failure_lower:
                if "below minimum" in failure_lower:
                    suggestions.append("- Increase wheel radius to be at least 0.3m")
                elif "exceeds maximum" in failure_lower:
                    suggestions.append("- Reduce wheel radius to be at most 2.0m")
            if "does not contact ground" in failure_lower or "contact ground" in failure_lower:
                suggestions.append("- **Initial design issue**: Wheel does not contact ground at start position")
                suggestions.append("- Adjust wheel position or wheel radius so that wheel bottom contacts ground initially (y - radius ≈ 1.0)")
                suggestions.append("- Note: Wheels can lift during obstacle climbing (this is allowed), but initial position must be correct")
            if "connection point too far" in failure_lower:
                suggestions.append("- Reduce connection distance to be within 5.0m from each body")
            if "motor speed" in failure_lower and "exceeds" in failure_lower:
                suggestions.append("- Reduce motor speed to be within [-50, 50] rad/s range")
            if "motor torque" in failure_lower and "exceeds" in failure_lower:
                suggestions.append("- Reduce motor torque to be within [0, 2000] N·m range")
            # General suggestion if no specific match
            if not suggestions:
                suggestions.append("- Review the constraint violations listed above and adjust your design accordingly")
                suggestions.append("- Ensure all design parameters meet the constraints specified in the task description")
        elif failure_reason == "Fell off map":
            suggestions.append("- Agent design may be unstable, consider lowering center of gravity or adding support")
            suggestions.append("- Check wheel positions and connection methods, ensure structural stability")
        elif failure_reason == "Moved backward too much":
            suggestions.append("- Check motor direction and speed settings")
            suggestions.append("- Ensure sufficient friction between wheels and ground")
        elif failure_reason and "unstable" in failure_reason.lower() and "rotation" in failure_reason.lower():
            suggestions.append("- Vehicle is rotating excessively, indicating unstable design or hacking behavior")
            suggestions.append("- Reduce motor torque or speed to prevent excessive angular momentum")
            suggestions.append("- Ensure wheels maintain contact with ground (avoid designs that cause vehicle to spin in air)")
            suggestions.append("- Consider using fewer wheels or adjusting wheel positions for better stability")
            suggestions.append("- Check that motor speeds are reasonable (not at maximum limits)")
        elif failure_reason and "flying" in failure_reason.lower() and "altitude" in failure_reason.lower():
            suggestions.append("- Vehicle is flying at excessive altitude, indicating hacking behavior")
            suggestions.append("- Design must move on terrain, not fly over obstacles")
            suggestions.append("- Reduce motor power to prevent vehicle from launching into air")
            suggestions.append("- Ensure wheels maintain ground contact throughout the journey")
            suggestions.append("- Consider lowering center of gravity or reducing wheel size")
    elif not success:
        if 'distance_traveled' in metrics:
            if metrics.get('distance_traveled', 0) < 1:
                suggestions.append("- Agent may not have enough power, consider increasing motor torque or speed")
                suggestions.append("- Check if wheels are in proper contact with ground")
            elif metrics.get('progress', 0) < 50:
                suggestions.append("- Agent may not be able to overcome obstacles, consider increasing wheel radius or adjusting center of gravity")
                suggestions.append("- Try increasing motor power or adjusting wheel positions")
                suggestions.append("- Note: Vehicle must have at most 2 wheels - focus on optimizing the 2-wheel design")
            else:
                suggestions.append("- Close to target, check the design of the final path segment")
    
    return suggestions
