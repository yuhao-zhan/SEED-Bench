"""
Task-specific feedback generation for S-01: The Bridge
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Format task-specific metrics for S-01: The Bridge
    Args:
        metrics: Evaluation metrics dictionary
    Returns:
        List of formatted metric strings
    """
    metric_parts = []
    
    # Vehicle position and progress (always show if available)
    if 'vehicle_x' in metrics:
        vehicle_y = metrics.get('vehicle_y', 0)
        metric_parts.append(f"**Vehicle position**: x={metrics['vehicle_x']:.2f}m, y={vehicle_y:.2f}m")
        if 'target_x' in metrics:
            metric_parts.append(f"**Target position**: x={metrics['target_x']:.2f}m")
        
        progress = metrics.get('progress')
        if progress is None and 'target_x' in metrics:
            start_x = 5.0
            max_dist = metrics['target_x'] - start_x
            progress = min(max(0, metrics['vehicle_x'] - start_x) / max_dist, 1.0) * 100.0 if max_dist > 0 else 0.0
        
        if progress is not None:
            metric_parts.append(f"**Progress**: {progress:.1f}%")
    elif 'target_x' in metrics:
        # At least show target if vehicle position not available
        metric_parts.append(f"**Target position**: x={metrics['target_x']:.2f}m")
    
    # Structure mass
    if 'structure_mass' in metrics:
        metric_parts.append(f"**Structure mass**: {metrics['structure_mass']:.2f}kg")
        if 'max_structure_mass' in metrics:
            metric_parts.append(f"**Mass limit**: {metrics['max_structure_mass']:.0f}kg")
    
    # Vertical acceleration
    if 'max_vertical_accel' in metrics:
        metric_parts.append(f"**Max vertical acceleration**: {metrics['max_vertical_accel']:.2f} m/s² (limit: 19.6 m/s² = 2g)")
    
    # Structure integrity
    if 'structure_broken' in metrics:
        metric_parts.append(f"**Structure integrity**: {'BROKEN' if metrics['structure_broken'] else 'INTACT'}")
        if 'joint_count' in metrics:
            joint_str = f"**Joint count**: {metrics['joint_count']}"
            if 'initial_joint_count' in metrics:
                joint_str += f" / {metrics['initial_joint_count']}"
            metric_parts.append(joint_str)
    
    # Simulation steps
    if 'step_count' in metrics:
        metric_parts.append(f"**Simulation steps**: {metrics['step_count']}")
    
    # Physical state information for fine-grained debugging (similar to basic task)
    if 'vehicle_x' in metrics or 'angular_velocity' in metrics or 'angle' in metrics:
        metric_parts.append("\n**Physical State Information**:")
        if 'vehicle_x' in metrics and 'vehicle_y' in metrics:
            metric_parts.append(f"- Vehicle position: ({metrics['vehicle_x']:.3f}, {metrics['vehicle_y']:.3f})")
        # Get vehicle velocity if available (from evaluator metrics)
        if 'velocity_x' in metrics and 'velocity_y' in metrics:
            velocity = (metrics['velocity_x']**2 + metrics['velocity_y']**2)**0.5
            metric_parts.append(f"- Vehicle velocity: {velocity:.3f} m/s")
            metric_parts.append(f"- Vehicle velocity components: vx={metrics['velocity_x']:.3f} m/s, vy={metrics['velocity_y']:.3f} m/s")
        if 'angular_velocity' in metrics:
            metric_parts.append(f"- Vehicle angular velocity: {metrics['angular_velocity']:.3f} rad/s")
        if 'angle' in metrics:
            angle_deg = metrics['angle'] * 180 / 3.14159
            metric_parts.append(f"- Vehicle angle: {metrics['angle']:.3f} rad ({angle_deg:.1f}°)")
        if 'normalized_angle' in metrics:
            normalized_angle_deg = metrics['normalized_angle'] * 180 / 3.14159
            metric_parts.append(f"- Vehicle normalized angle: {metrics['normalized_angle']:.3f} rad ({normalized_angle_deg:.1f}°)")
    
    # Add any additional metrics
    excluded_keys = ['vehicle_x', 'vehicle_y', 'target_x', 'progress', 'structure_mass',
                    'max_structure_mass', 'max_vertical_accel', 'structure_broken', 'joint_count', 'step_count',
                    'success', 'failed', 'failure_reason', 'velocity_x', 'velocity_y', 'angular_velocity', 
                    'angle', 'normalized_angle', 'high_angular_velocity_count', 'is_airborne', 
                    'airborne_rotation_accumulated']
    other_metrics = {k: v for k, v in metrics.items() if k not in excluded_keys}
    if other_metrics:
        metric_parts.append("\n**Additional Metrics**:")
        for key, value in other_metrics.items():
            if isinstance(value, (int, float)):
                metric_parts.append(f"- {key}: {value:.3f}" if isinstance(value, float) else f"- {key}: {value}")
            else:
                metric_parts.append(f"- {key}: {value}")
    
    # Add stability metrics if available
    if 'is_airborne' in metrics or 'airborne_rotation_accumulated' in metrics:
        metric_parts.append("\n**Stability Metrics**:")
        if 'is_airborne' in metrics:
            metric_parts.append(f"- Vehicle is airborne: {metrics['is_airborne']}")
        if 'airborne_rotation_accumulated' in metrics:
            rotation_deg = metrics['airborne_rotation_accumulated'] * 180 / 3.14159
            metric_parts.append(f"- Airborne rotation accumulated: {metrics['airborne_rotation_accumulated']:.3f} rad ({rotation_deg:.1f}°)")
        if 'high_angular_velocity_count' in metrics:
            metric_parts.append(f"- High angular velocity count: {metrics['high_angular_velocity_count']}")
    
    return metric_parts


def get_improvement_suggestions(metrics: Dict[str, Any], score: float, success: bool, 
                                failed: bool, failure_reason: str = None, 
                                error: str = None) -> List[str]:
    """
    Generate task-specific improvement suggestions for S-01: The Bridge
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
            max_mass = metrics.get('max_structure_mass', 2000.0)
            suggestions.append(f"- Reduce structure mass to be within {max_mass:.0f}kg limit")
            suggestions.append("- Use lighter materials (lower density) or optimize beam sizes")
            suggestions.append("- Consider using truss designs to reduce material while maintaining strength")
        elif "build zone" in error_lower:
            # Build zone is dynamic based on gap width
            suggestions.append("- Ensure all beams are placed within the build zone")
            suggestions.append("- Check that beam positions are between the two cliffs")
        elif "error building" in error_lower:
            suggestions.append("- Review the error message above to identify the specific constraint violation")
            suggestions.append("- Ensure all parameters (beam sizes, positions) are within allowed ranges")
    
    elif failed:
        if failure_reason and "design constraint violated" in failure_reason.lower():
            failure_lower = failure_reason.lower()
            if "structure mass" in failure_lower:
                max_mass = metrics.get('max_structure_mass', 2000.0)
                suggestions.append(f"- Reduce structure mass to be within {max_mass:.0f}kg limit")
                suggestions.append("- Consider using truss designs to reduce material while maintaining strength")
                suggestions.append("- Optimize beam sizes and densities to minimize total mass")
            if "build zone" in failure_lower:
                suggestions.append("- Ensure all beams are placed within the build zone")
                suggestions.append("- Check that beam positions span from left cliff to right cliff")
        elif failure_reason == "Vehicle fell into water":
            suggestions.append("- Bridge structure is not strong enough or not properly connected")
            suggestions.append("- Ensure bridge deck is continuous and properly supported")
            suggestions.append("- Check that joints are properly anchored to cliff walls")
        elif failure_reason and "structure integrity" in failure_reason.lower():
            suggestions.append("- Structure is breaking under load - joints are too weak")
            suggestions.append("- Consider using more joints or stronger connections")
            suggestions.append("- Distribute load more evenly across the structure")
        elif failure_reason and "vertical acceleration" in failure_reason.lower():
            suggestions.append("- Bridge deck is too bumpy - vehicle is experiencing excessive vertical acceleration")
            suggestions.append("- Ensure deck surface is smooth and continuous")
            suggestions.append("- Consider adding more support beams to reduce deflection")
            suggestions.append("- Check that deck beams have sufficient friction (> 0.5)")
    elif not success:
        if 'vehicle_x' in metrics:
            if metrics.get('vehicle_x', 0) < 15:
                suggestions.append("- Bridge may not be properly connected to cliffs")
                suggestions.append("- Ensure structure is anchored to both cliff walls using joints")
            elif metrics.get('vehicle_x', 0) < metrics.get('target_x', 30):
                suggestions.append("- Bridge may not be strong enough to support vehicle weight")
                suggestions.append("- Consider adding more support beams or using truss design")
                max_mass = metrics.get('max_structure_mass', 2000.0)
                suggestions.append(f"- Check that structure mass is within budget ({max_mass:.0f}kg)")
                suggestions.append("- Ensure bridge spans the full gap width and is properly anchored")
            else:
                suggestions.append("- Close to target, check the final segment of the bridge")
    
    return suggestions
