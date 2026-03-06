"""
Task-specific feedback generation for K-04: The Pusher
"""
from typing import Dict, Any, List
import math


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Format task-specific metrics for K-04: The Pusher
    Args:
        metrics: Evaluation metrics dictionary
    Returns:
        List of formatted metric strings
    """
    metric_parts = []
    
    # Pusher and object position (always show if available)
    if 'pusher_x' in metrics:
        pusher_y = metrics.get('pusher_y', 0)
        metric_parts.append(f"**Pusher position**: x={metrics['pusher_x']:.2f}m, y={pusher_y:.2f}m")
        if 'pusher_angle' in metrics:
            angle_deg = metrics['pusher_angle'] * 180 / math.pi
            metric_parts.append(f"**Pusher angle**: {metrics['pusher_angle']:.3f} rad ({angle_deg:.1f}°)")
    if 'object_x' in metrics:
        object_y = metrics.get('object_y', 0)
        metric_parts.append(f"**Object position**: x={metrics['object_x']:.2f}m, y={object_y:.2f}m")
        if 'target_object_x' in metrics:
            metric_parts.append(f"**Target position**: x={metrics['target_object_x']:.2f}m")
        if 'distance_pushed' in metrics:
            metric_parts.append(f"**Distance pushed**: {metrics['distance_pushed']:.2f}m")
        if 'max_distance_pushed' in metrics:
            metric_parts.append(f"**Max distance pushed**: {metrics['max_distance_pushed']:.2f}m")
        if 'progress' in metrics:
            metric_parts.append(f"**Progress**: {metrics['progress']:.1f}%")
    elif 'target_object_x' in metrics:
        # At least show target if object position not available
        metric_parts.append(f"**Target position**: x={metrics['target_object_x']:.2f}m")
    
    # Structure mass
    if 'structure_mass' in metrics:
        metric_parts.append(f"**Structure mass**: {metrics['structure_mass']:.2f}kg")
        if 'max_structure_mass' in metrics:
            metric_parts.append(f"**Mass limit**: {metrics['max_structure_mass']:.0f}kg")
    
    # Stability tracking
    if 'max_pusher_tilt' in metrics:
        tilt_deg = metrics['max_pusher_tilt'] * 180 / math.pi
        metric_parts.append(f"**Maximum pusher tilt**: {metrics['max_pusher_tilt']:.3f} rad ({tilt_deg:.1f}°)")
        if 'pusher_tipped' in metrics:
            status = "TIPPED" if metrics['pusher_tipped'] else "STABLE"
            metric_parts.append(f"**Pusher status**: {status}")
    
    # Motion tracking
    if 'steps_with_motion' in metrics:
        metric_parts.append(f"**Steps with motion**: {metrics['steps_with_motion']}")
        if 'min_simulation_steps_required' in metrics:
            metric_parts.append(f"**Required steps**: {metrics['min_simulation_steps_required']}")
    
    # Simulation steps
    if 'step_count' in metrics:
        metric_parts.append(f"**Simulation steps**: {metrics['step_count']}")
    
    # Physical state information for debugging (like S_01 - rich metrics for feedback)
    if 'pusher_velocity_x' in metrics or 'object_velocity_x' in metrics:
        metric_parts.append("\n**Physical State Information**:")
        if 'pusher_velocity_x' in metrics and 'pusher_velocity_y' in metrics:
            v = (metrics['pusher_velocity_x']**2 + metrics['pusher_velocity_y']**2)**0.5
            metric_parts.append(f"- Pusher velocity: {v:.3f} m/s (vx={metrics['pusher_velocity_x']:.3f}, vy={metrics['pusher_velocity_y']:.3f})")
        if 'pusher_angular_velocity' in metrics:
            omega_deg = metrics['pusher_angular_velocity'] * 180 / math.pi
            metric_parts.append(f"- Pusher angular velocity: {metrics['pusher_angular_velocity']:.3f} rad/s ({omega_deg:.1f}°/s)")
        if 'pusher_angle' in metrics:
            angle_deg = metrics['pusher_angle'] * 180 / math.pi
            metric_parts.append(f"- Pusher tilt angle: {metrics['pusher_angle']:.3f} rad ({angle_deg:.1f}°)")
        if 'object_velocity_x' in metrics and 'object_velocity_y' in metrics:
            v = (metrics['object_velocity_x']**2 + metrics['object_velocity_y']**2)**0.5
            metric_parts.append(f"- Object velocity: {v:.3f} m/s (vx={metrics['object_velocity_x']:.3f}, vy={metrics['object_velocity_y']:.3f})")
        if 'object_angular_velocity' in metrics:
            metric_parts.append(f"- Object angular velocity: {metrics['object_angular_velocity']:.3f} rad/s")
        if 'object_y' in metrics:
            ground_y = 1.0
            metric_parts.append(f"- Object height (center y): {metrics['object_y']:.3f} m (ground at y={ground_y})")
        if 'distance_pushed' in metrics and 'target_object_x' in metrics:
            remaining = metrics.get('target_object_x', 16.0) - metrics.get('object_x', 8.0)
            if remaining > 0:
                metric_parts.append(f"- Distance remaining to target: {remaining:.2f} m")
    
    # Add any additional metrics
    excluded_keys = ['pusher_x', 'pusher_y', 'pusher_angle', 'object_x', 'object_y', 'target_object_x', 'distance_pushed', 'max_distance_pushed', 'progress', 'structure_mass',
                    'max_structure_mass', 'max_pusher_tilt', 'pusher_tipped', 'steps_with_motion',
                    'min_simulation_steps_required', 'step_count', 'success', 'failed', 'failure_reason',
                    'pusher_velocity_x', 'pusher_velocity_y', 'pusher_angular_velocity',
                    'object_velocity_x', 'object_velocity_y', 'object_angular_velocity']
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
    Generate task-specific improvement suggestions for K-04: The Pusher
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
            max_mass = metrics.get('max_structure_mass', 40.0)
            suggestions.append(f"- Reduce structure mass to be within {max_mass:.0f}kg limit")
            suggestions.append("- Use lighter materials (lower density) or optimize beam sizes")
            suggestions.append("- Consider using fewer or smaller components")
        elif "build zone" in error_lower:
            suggestions.append("- Ensure all beams are placed within the build zone")
            suggestions.append("- Check that pusher components are within x=[0, 15], y=[1.5, 8]")
        elif "error building" in error_lower:
            suggestions.append("- Review the error message above to identify the specific constraint violation")
            suggestions.append("- Ensure all parameters (beam sizes, positions) are within allowed ranges")
    
    elif failed:
        if failure_reason and "design constraint violated" in failure_reason.lower():
            failure_lower = failure_reason.lower()
            if "structure mass" in failure_lower:
                max_mass = metrics.get('max_structure_mass', 40.0)
                suggestions.append(f"- Reduce structure mass to be within {max_mass:.0f}kg limit")
                suggestions.append("- Optimize beam sizes and densities to minimize total mass")
            if "build zone" in failure_lower:
                suggestions.append("- Ensure all beams are placed within the build zone")
        elif failure_reason and "tipped over" in failure_reason.lower():
            suggestions.append("- Pusher is unstable - lower center of mass or widen wheelbase")
            suggestions.append("- Reduce pusher height or increase base width for better stability")
            suggestions.append("- Adjust motor speeds to prevent sudden accelerations that cause tipping")
            suggestions.append("- Consider using multiple wheels/tracks for better stability")
            suggestions.append("- Ensure pusher maintains contact with ground during pushing")
        elif failure_reason and "wheels suspended" in failure_reason.lower():
            suggestions.append("- Wheels are off ground (rear lifted - wheelie effect)")
            suggestions.append("- Move center of mass backward or reduce forward extension")
            suggestions.append("- Reduce initial velocity / motor torque to prevent lifting")
            suggestions.append("- Ensure wheels stay in contact with ground during push")
        elif failure_reason and "wheel spinning" in failure_reason.lower():
            suggestions.append("- Wheels are spinning but no forward motion (loss of traction)")
            suggestions.append("- Increase wheel-ground friction or reduce motor torque to prevent slipping")
            suggestions.append("- Ensure wheels make solid contact with ground (check wheel radius and chassis height)")
            suggestions.append("- Consider heavier pusher for better traction")
        elif failure_reason and "not pushed" in failure_reason.lower():
            suggestions.append("- Pusher may not be generating enough force to overcome object resistance")
            suggestions.append("- Motor speeds may be too low or not properly coordinated")
            suggestions.append("- Check that wheels/tracks maintain good contact with high-friction ground")
            suggestions.append("- Consider increasing wheel friction or using tracks instead of wheels")
            suggestions.append("- Ensure pusher makes proper contact with object to transfer force")
            suggestions.append("- High ground friction can cause wheel slipping - adjust motor torque")
    elif not success:
        if 'distance_pushed' in metrics:
            if metrics.get('distance_pushed', 0) < 3.0:
                suggestions.append("- Object is not being pushed effectively")
                suggestions.append("- Adjust motor speeds and phase coordination")
                suggestions.append("- Ensure pusher maintains contact with object and ground")
            elif metrics.get('distance_pushed', 0) < 8.0:
                suggestions.append("- Object is being pushed but needs to travel further")
                suggestions.append("- Increase motor speeds or improve pushing efficiency")
                suggestions.append("- Check that pusher maintains forward momentum")
        
        if 'pusher_tipped' in metrics and metrics.get('pusher_tipped', False):
            suggestions.append("- Pusher is tipping - improve stability design")
        
        if 'steps_with_motion' in metrics and 'min_simulation_steps_required' in metrics:
            if metrics.get('steps_with_motion', 0) < metrics.get('min_simulation_steps_required', 0):
                suggestions.append("- Pusher motion is not sustained long enough")
                suggestions.append("- Improve stability and continuous forward motion")
    
    return suggestions
