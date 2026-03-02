"""
Task-specific feedback generation for K-01: The Walker
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Format task-specific metrics for K-01: The Walker
    Args:
        metrics: Evaluation metrics dictionary
    Returns:
        List of formatted metric strings
    """
    metric_parts = []
    
    # Walker position and progress (always show if available)
    if 'walker_x' in metrics:
        walker_y = metrics.get('walker_y', 0)
        metric_parts.append(f"**Walker position**: x={metrics['walker_x']:.2f}m, y={walker_y:.2f}m")
        if 'target_x' in metrics:
            metric_parts.append(f"**Target position**: x={metrics['target_x']:.2f}m")
        if 'distance_traveled' in metrics:
            metric_parts.append(f"**Distance traveled**: {metrics['distance_traveled']:.2f}m")
        if 'progress' in metrics:
            metric_parts.append(f"**Progress**: {metrics['progress']:.1f}%")
    elif 'target_x' in metrics:
        # At least show target if walker position not available
        metric_parts.append(f"**Target position**: x={metrics['target_x']:.2f}m")
    
    # Structure mass
    if 'structure_mass' in metrics:
        metric_parts.append(f"**Structure mass**: {metrics['structure_mass']:.2f}kg")
        if 'max_structure_mass' in metrics:
            metric_parts.append(f"**Mass limit**: {metrics['max_structure_mass']:.0f}kg")
    
    # Torso height tracking
    if 'min_torso_y' in metrics:
        metric_parts.append(f"**Minimum torso height**: {metrics['min_torso_y']:.2f}m")
        if 'torso_touched_ground' in metrics:
            status = "TOUCHED GROUND" if metrics['torso_touched_ground'] else "ABOVE GROUND"
            metric_parts.append(f"**Torso status**: {status}")
    
    # Motion tracking
    if 'steps_with_motion' in metrics:
        metric_parts.append(f"**Steps with motion**: {metrics['steps_with_motion']}")
        if 'min_simulation_steps_required' in metrics:
            metric_parts.append(f"**Required steps**: {metrics['min_simulation_steps_required']}")
    
    # Velocity information
    if 'velocity_x' in metrics or 'speed' in metrics:
        metric_parts.append("\n**Physical State Information**:")
        if 'velocity_x' in metrics and 'velocity_y' in metrics:
            metric_parts.append(f"- Walker velocity: vx={metrics['velocity_x']:.3f} m/s, vy={metrics['velocity_y']:.3f} m/s")
        if 'speed' in metrics:
            metric_parts.append(f"- Walker speed: {metrics['speed']:.3f} m/s")
        if 'angular_velocity' in metrics:
            metric_parts.append(f"- Walker angular velocity: {metrics['angular_velocity']:.3f} rad/s")
    
    # Simulation steps
    if 'step_count' in metrics:
        metric_parts.append(f"**Simulation steps**: {metrics['step_count']}")
    
    # Add any additional metrics
    excluded_keys = ['walker_x', 'walker_y', 'target_x', 'distance_traveled', 'progress', 'structure_mass',
                    'max_structure_mass', 'min_torso_y', 'torso_touched_ground', 'steps_with_motion',
                    'min_simulation_steps_required', 'step_count', 'success', 'failed', 'failure_reason']
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
    Generate task-specific improvement suggestions for K-01: The Walker
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
        error_lower = error.lower()
        if "structure mass" in error_lower and "exceeds" in error_lower:
            max_mass = metrics.get('max_structure_mass', 100.0)
            suggestions.append(f"- Reduce structure mass to be within {max_mass:.0f}kg limit")
            suggestions.append("- Use lighter materials (lower density) or optimize beam sizes")
            suggestions.append("- Consider using fewer or smaller components")
        elif "build zone" in error_lower:
            suggestions.append("- Ensure all beams are placed within the build zone")
            suggestions.append("- Check that walker components are above ground (y >= 2.0m)")
        elif "error building" in error_lower:
            suggestions.append("- Review the error message above to identify the specific constraint violation")
            suggestions.append("- Ensure all parameters (beam sizes, positions) are within allowed ranges")
    
    elif failed:
        if failure_reason and "design constraint violated" in failure_reason.lower():
            failure_lower = failure_reason.lower()
            if "structure mass" in failure_lower:
                max_mass = metrics.get('max_structure_mass', 100.0)
                suggestions.append(f"- Reduce structure mass to be within {max_mass:.0f}kg limit")
                suggestions.append("- Optimize beam sizes and densities to minimize total mass")
            if "build zone" in failure_lower:
                suggestions.append("- Ensure all beams are placed within the build zone")
        elif failure_reason and "torso touched ground" in failure_reason.lower():
            suggestions.append("- Walker legs are too short or not properly coordinated")
            suggestions.append("- Increase leg length or adjust leg angles to keep torso elevated")
            suggestions.append("- Improve phase coordination between legs to maintain stability")
            suggestions.append("- Consider using a quadrupedal design for better stability")
        elif failure_reason and "did not move forward" in failure_reason.lower():
            suggestions.append("- Motor speeds may be too low or not properly coordinated")
            suggestions.append("- Check that motors are driving joints in the correct direction")
            suggestions.append("- Ensure leg-ground contact provides sufficient friction for forward motion")
            suggestions.append("- Consider adjusting motor phase relationships for better gait")
            suggestions.append("- Verify that linkage mechanisms create proper walking motion")
    elif not success:
        if 'distance_traveled' in metrics:
            if metrics.get('distance_traveled', 0) < 5.0:
                suggestions.append("- Walker is not moving forward effectively")
                suggestions.append("- Adjust motor speeds and phase coordination")
                suggestions.append("- Ensure legs make proper contact with ground")
            elif metrics.get('distance_traveled', 0) < 10.0:
                suggestions.append("- Walker is making progress but needs to travel further")
                suggestions.append("- Increase motor speeds or improve gait efficiency")
                suggestions.append("- Check that walker maintains forward momentum")
        
        if 'torso_touched_ground' in metrics and metrics.get('torso_touched_ground', False):
            suggestions.append("- Torso is too close to ground - increase leg length or adjust design")
        
        if 'steps_with_motion' in metrics and 'min_simulation_steps_required' in metrics:
            if metrics.get('steps_with_motion', 0) < metrics.get('min_simulation_steps_required', 0):
                suggestions.append("- Walker motion is not sustained long enough")
                suggestions.append("- Improve stability and continuous forward motion")
    
    return suggestions
