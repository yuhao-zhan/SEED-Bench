"""
Task-specific feedback generation for S-02: The Skyscraper
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Format task-specific metrics for S-02: The Skyscraper
    Args:
        metrics: Evaluation metrics dictionary
    Returns:
        List of formatted metric strings
    """
    metric_parts = []
    
    # Height metrics (always show if available)
    if 'initial_height' in metrics:
        metric_parts.append(f"**Initial height**: {metrics['initial_height']:.2f}m")
        if 'target_height' in metrics:
            height_ratio = metrics['initial_height'] / metrics['target_height']
            metric_parts.append(f"**Height ratio**: {height_ratio:.2f} (target: >1.0)")
    if 'current_height' in metrics:
        metric_parts.append(f"**Current height**: {metrics['current_height']:.2f}m")
    if 'target_height' in metrics:
        metric_parts.append(f"**Target height**: {metrics['target_height']:.2f}m")
    
    # Earthquake survival metrics
    if 'min_height_during_quake' in metrics and metrics['min_height_during_quake'] is not None:
        min_height = metrics['min_height_during_quake']
        survival_height = metrics.get('survival_height', 25.0)
        metric_parts.append(f"**Min height during quake**: {min_height:.2f}m (survival threshold: {survival_height:.2f}m)")
        if min_height < survival_height:
            height_deficit = survival_height - min_height
            metric_parts.append(f"**Height deficit**: {height_deficit:.2f}m below survival threshold")
    
    # Stability metrics
    if 'center_of_mass_x_range' in metrics:
        cm_range = metrics['center_of_mass_x_range']
        stability_min = metrics.get('stability_x_min', -4.0)
        stability_max = metrics.get('stability_x_max', 4.0)
        metric_parts.append(f"**Center of mass x range**: [{cm_range[0]:.2f}, {cm_range[1]:.2f}]m")
        metric_parts.append(f"**Stability bounds**: x=[{stability_min:.2f}, {stability_max:.2f}]m")
        
        # Check if out of bounds
        if cm_range[0] < stability_min or cm_range[1] > stability_max:
            if cm_range[0] < stability_min:
                overshoot = stability_min - cm_range[0]
                metric_parts.append(f"**Left overshoot**: {overshoot:.2f}m beyond stability bound")
            if cm_range[1] > stability_max:
                overshoot = cm_range[1] - stability_max
                metric_parts.append(f"**Right overshoot**: {overshoot:.2f}m beyond stability bound")
    
    # Structure properties
    if 'structure_mass' in metrics:
        metric_parts.append(f"**Structure mass**: {metrics['structure_mass']:.2f}kg")
    if 'structure_width' in metrics:
        metric_parts.append(f"**Structure width**: {metrics['structure_width']:.2f}m")
    if 'num_beams' in metrics:
        metric_parts.append(f"**Number of beams**: {metrics['num_beams']}")
    if 'num_joints' in metrics:
        initial_joints = metrics.get('initial_joint_count', metrics['num_joints'])
        metric_parts.append(f"**Number of joints**: {metrics['num_joints']} (initial: {initial_joints})")
        if metrics['num_joints'] < initial_joints:
            metric_parts.append(f"⚠️ **Joints broken**: {initial_joints - metrics['num_joints']} joints failed")
    if 'num_springs' in metrics:
        metric_parts.append(f"**Number of springs**: {metrics['num_springs']}")
    if 'structure_broken' in metrics:
        metric_parts.append(f"**Structure integrity**: {'BROKEN' if metrics['structure_broken'] else 'INTACT'}")
    
    # Height loss analysis
    if 'height_loss' in metrics and metrics.get('is_during_quake', False):
        height_loss = metrics['height_loss']
        if height_loss > 0:
            metric_parts.append(f"**Height loss during quake**: {height_loss:.2f}m")
            if 'initial_height' in metrics:
                collapse_ratio = height_loss / metrics['initial_height']
                metric_parts.append(f"**Collapse ratio**: {collapse_ratio:.2%}")
    
    # Physical state information
    if 'max_velocity_x' in metrics or 'max_velocity_y' in metrics or 'max_angular_velocity' in metrics:
        metric_parts.append("\n**Physical State Information**:")
        if 'max_velocity_x' in metrics:
            metric_parts.append(f"- Max horizontal velocity: {metrics['max_velocity_x']:.3f} m/s")
        if 'max_velocity_y' in metrics:
            metric_parts.append(f"- Max vertical velocity: {metrics['max_velocity_y']:.3f} m/s")
        if 'max_angular_velocity' in metrics:
            metric_parts.append(f"- Max angular velocity: {metrics['max_angular_velocity']:.3f} rad/s")
        if 'center_of_mass_x' in metrics and 'center_of_mass_y' in metrics:
            metric_parts.append(f"- Current center of mass: ({metrics['center_of_mass_x']:.3f}, {metrics['center_of_mass_y']:.3f})")
        if 'center_of_mass_displacement' in metrics:
            metric_parts.append(f"- Max center of mass displacement: {metrics['center_of_mass_displacement']:.3f}m")
    
    # Simulation progress
    if 'step_count' in metrics:
        step_count = metrics['step_count']
        time_seconds = step_count / 60.0  # Assuming 60fps
        metric_parts.append(f"\n**Simulation time**: {time_seconds:.2f}s ({step_count} steps)")
        
        # Earthquake timing
        quake_start_time = 2.0  # Earthquake starts at t=2s
        if time_seconds >= quake_start_time:
            quake_duration = time_seconds - quake_start_time
            metric_parts.append(f"**Earthquake duration**: {quake_duration:.2f}s")
        else:
            metric_parts.append(f"**Time until earthquake**: {quake_start_time - time_seconds:.2f}s")
    
    # Height history (if available)
    if 'height_history' in metrics and len(metrics['height_history']) > 1:
        metric_parts.append("\n**Height History** (last 5 samples):")
        for step, height in metrics['height_history'][-5:]:
            time_s = step / 60.0
            metric_parts.append(f"- t={time_s:.1f}s: {height:.2f}m")
    
    # Center of mass history (if available)
    if 'center_of_mass_history' in metrics and len(metrics['center_of_mass_history']) > 1:
        metric_parts.append("\n**Center of Mass History** (last 5 samples):")
        for step, cm_x, cm_y in metrics['center_of_mass_history'][-5:]:
            time_s = step / 60.0
            metric_parts.append(f"- t={time_s:.1f}s: x={cm_x:.2f}m, y={cm_y:.2f}m")
    
    # Additional metrics (already covered above, so skip)
    excluded_keys = ['initial_height', 'current_height', 'target_height', 'min_height_during_quake',
                    'center_of_mass_x_range', 'stability_x_min', 'stability_x_max', 'survival_height',
                    'structure_mass', 'structure_width', 'num_beams', 'num_joints', 'num_springs',
                    'initial_joint_count', 'initial_spring_count', 'structure_broken',
                    'height_loss', 'center_of_mass_x', 'center_of_mass_y', 'center_of_mass_displacement',
                    'max_velocity_x', 'max_velocity_y', 'max_angular_velocity',
                    'height_history', 'center_of_mass_history',
                    'step_count', 'quake_start_step', 'is_during_quake',
                    'success', 'failed', 'failure_reason', 'survival_tolerance']
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
    Generate task-specific improvement suggestions for S-02: The Skyscraper
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
        if "design constraint" in error_lower:
            suggestions.append("- Review the error message above to identify the specific constraint violation")
            suggestions.append("- Ensure all parameters (beam sizes, positions) are within allowed ranges")
            if "width" in error_lower:
                suggestions.append("- Reduce structure width to be within 8m limit")
            if "foundation" in error_lower:
                suggestions.append("- Ensure foundation contact is within x=[-2, 2]")
    
    elif failed:
        if failure_reason and "height" in failure_reason.lower():
            initial_height = metrics.get('initial_height', 0)
            target_height = metrics.get('target_height', 30.0)
            if initial_height < target_height:
                height_deficit = target_height - initial_height
                suggestions.append(f"- Increase structure height by at least {height_deficit:.2f}m to exceed {target_height}m")
                suggestions.append("- Consider using taller beams or stacking more levels")
                suggestions.append("- Check that all beams are properly connected vertically")
        
        elif failure_reason and "survival" in failure_reason.lower():
            min_height = metrics.get('min_height_during_quake', 0)
            survival_height = metrics.get('survival_height', 25.0)
            height_loss = metrics.get('height_loss', 0)
            collapse_ratio = metrics.get('height_loss', 0) / metrics.get('initial_height', 1) if metrics.get('initial_height', 0) > 0 else 0
            
            suggestions.append(f"- Structure collapsed during earthquake (lost {height_loss:.2f}m, {collapse_ratio:.1%} of initial height)")
            
            # Analyze collapse pattern
            if collapse_ratio > 0.5:
                suggestions.append("- CRITICAL: Structure lost more than 50% of height - fundamental design issue")
                suggestions.append("- Structure is too flexible or connections are too weak")
                suggestions.append("- Consider completely redesigning with stronger base and connections")
            elif collapse_ratio > 0.3:
                suggestions.append("- MAJOR: Structure lost 30-50% of height - significant structural weakness")
                suggestions.append("- Strengthen all connections between beams (use 7-11 joints per connection)")
                suggestions.append("- Increase beam density significantly (especially in lower sections)")
            else:
                suggestions.append("- Structure partially collapsed - connections need strengthening")
                suggestions.append("- Strengthen connections between beams (use multiple joints per connection)")
            
            # Check structure integrity
            if metrics.get('structure_broken', False):
                broken_joints = metrics.get('initial_joint_count', 0) - metrics.get('num_joints', 0)
                suggestions.append(f"- ⚠️ Structure integrity lost: {broken_joints} joints broke during quake")
                suggestions.append("- Joints are too weak - need stronger connections or more joints")
            
            # Physical state analysis
            max_vel_x = metrics.get('max_velocity_x', 0)
            max_vel_y = metrics.get('max_velocity_y', 0)
            max_ang_vel = metrics.get('max_angular_velocity', 0)
            if max_vel_x > 5.0 or max_vel_y > 5.0:
                suggestions.append(f"- High velocities detected (vx={max_vel_x:.2f}m/s, vy={max_vel_y:.2f}m/s) - structure is unstable")
            if max_ang_vel > 2.0:
                suggestions.append(f"- High angular velocity ({max_ang_vel:.2f} rad/s) - structure is rotating/tilting excessively")
            
            # Design suggestions
            suggestions.append("- Consider adding tuned mass dampers using add_spring() to reduce vibrations")
            suggestions.append("- Increase beam density for better structural integrity (especially bottom 20m)")
            suggestions.append("- Use wider base and stronger foundation connections (multiple anchor points)")
            suggestions.append("- Consider adding cross-bracing or diagonal supports")
            suggestions.append("- Lower center of mass by making bottom section much heavier")
        
        elif failure_reason and "stability" in failure_reason.lower():
            cm_range = metrics.get('center_of_mass_x_range', [0, 0])
            stability_min = metrics.get('stability_x_min', -4.0)
            stability_max = metrics.get('stability_x_max', 4.0)
            
            if cm_range[0] < stability_min:
                overshoot = stability_min - cm_range[0]
                suggestions.append(f"- Structure tipping to the left ({overshoot:.2f}m beyond bound)")
            if cm_range[1] > stability_max:
                overshoot = cm_range[1] - stability_max
                suggestions.append(f"- Structure tipping to the right ({overshoot:.2f}m beyond bound)")
            
            suggestions.append("- Lower center of mass by making base heavier or wider")
            suggestions.append("- Ensure foundation contact is within x=[-2, 2]")
            suggestions.append("- Strengthen foundation connections to prevent tipping")
            suggestions.append("- Consider adding counterweights or wider base")
        
        elif failure_reason and "width" in failure_reason.lower():
            current_width = metrics.get('width', 0)
            max_width = metrics.get('max_width', 8.0)
            suggestions.append(f"- Reduce structure width from {current_width:.2f}m to within {max_width}m limit")
            suggestions.append("- Use narrower beams or reduce horizontal spacing")
    
    elif not success:
        # Partial success - provide guidance
        initial_height = metrics.get('initial_height', 0)
        target_height = metrics.get('target_height', 30.0)
        if initial_height < target_height:
            suggestions.append(f"- Increase structure height to exceed {target_height}m (current: {initial_height:.2f}m)")
        
        min_height = metrics.get('min_height_during_quake', 0)
        if min_height > 0:
            survival_height = metrics.get('survival_height', 25.0)
            if min_height < survival_height:
                suggestions.append(f"- Improve earthquake resistance (min height: {min_height:.2f}m, need: {survival_height:.2f}m)")
        
        cm_range = metrics.get('center_of_mass_x_range', [0, 0])
        if cm_range[0] < -3.5 or cm_range[1] > 3.5:
            suggestions.append("- Improve stability by widening base or lowering center of mass")
    
    return suggestions
