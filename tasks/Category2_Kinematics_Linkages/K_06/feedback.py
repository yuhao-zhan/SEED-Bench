"""
Task-specific feedback generation for K-06: The Wiper
Returns process and result physical metrics for solver feedback (reference S_01 style).
"""
from typing import Dict, Any, List

# TIME_STEP for simulation time (seconds)
try:
    import sys
    import os
    _scripts = os.path.join(os.path.dirname(__file__), '../../..')
    if _scripts not in sys.path:
        sys.path.insert(0, _scripts)
    from common.simulator import TIME_STEP
except Exception:
    TIME_STEP = 1.0 / 60.0


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Format task-specific metrics for K-06: The Wiper.
    Returns process and result physical metrics (cleaning, mass, simulation time, etc.).
    """
    metric_parts = []

    # --- Process and result summary ---
    metric_parts.append("**Process and Result Metrics**:")
    if 'step_count' in metrics:
        sim_time_s = metrics['step_count'] * TIME_STEP
        metric_parts.append(f"- Simulation steps: {metrics['step_count']} (time: {sim_time_s:.2f}s)")
    if 'min_simulation_steps_required' in metrics:
        req_time_s = metrics['min_simulation_steps_required'] * TIME_STEP
        metric_parts.append(f"- Required minimum run: {metrics['min_simulation_steps_required']} steps ({req_time_s:.1f}s)")

    # Wiper position
    if 'wiper_x' in metrics:
        wiper_y = metrics.get('wiper_y', 0)
        metric_parts.append(f"- Wiper (base) position: x={metrics['wiper_x']:.2f}m, y={wiper_y:.2f}m")

    # Particle cleaning (process + result)
    if 'initial_particle_count' in metrics:
        metric_parts.append(f"- Initial particles on glass: {metrics['initial_particle_count']}")
    if 'current_particle_count' in metrics:
        metric_parts.append(f"- Remaining particles (central zone): {metrics['current_particle_count']}")
    if 'particles_removed' in metrics:
        metric_parts.append(f"- Particles removed (pushed to edges): {metrics['particles_removed']}")
    if 'cleaning_percentage' in metrics:
        metric_parts.append(f"- Cleaning percentage: {metrics['cleaning_percentage']:.1f}%")
    if 'residual_percentage' in metrics:
        metric_parts.append(f"- Residual percentage: {metrics['residual_percentage']:.1f}%")
        if 'max_residual_percent' in metrics:
            metric_parts.append(f"- Target: residual <= {metrics['max_residual_percent']:.0f}%")
    if 'progress' in metrics:
        metric_parts.append(f"- Progress: {metrics['progress']:.1f}%")

    # Structure mass (design constraint)
    if 'structure_mass' in metrics:
        metric_parts.append(f"- Structure mass: {metrics['structure_mass']:.2f}kg")
        if 'max_structure_mass' in metrics:
            metric_parts.append(f"- Mass limit: {metrics['max_structure_mass']:.0f}kg")

    # Motion / removal events (steps where particle count decreased)
    if 'steps_with_motion' in metrics:
        metric_parts.append(f"- Steps with particle removal events: {metrics['steps_with_motion']}")

    # Success / failure
    if 'success' in metrics:
        metric_parts.append(f"- Task success: {metrics['success']}")
    if metrics.get('failed') and metrics.get('failure_reason'):
        metric_parts.append(f"- Failure reason: {metrics['failure_reason']}")

    # Any extra metrics
    excluded_keys = [
        'wiper_x', 'wiper_y', 'initial_particle_count', 'current_particle_count', 'particles_removed',
        'cleaning_percentage', 'residual_percentage', 'max_residual_percent', 'progress', 'structure_mass',
        'max_structure_mass', 'steps_with_motion', 'min_simulation_steps_required', 'step_count',
        'success', 'failed', 'failure_reason'
    ]
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
    Generate task-specific improvement suggestions for K-06: The Wiper
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
            max_mass = metrics.get('max_structure_mass', 15.0)
            suggestions.append(f"- Reduce structure mass to be within {max_mass:.0f}kg limit")
            suggestions.append("- Use lighter materials (lower density) or optimize beam sizes")
            suggestions.append("- Consider using fewer or smaller components")
        elif "build zone" in error_lower:
            suggestions.append("- Ensure all beams are placed within the build zone")
            suggestions.append("- Check that wiper components are within x=[0, 12], y=[2, 10]")
        elif "error building" in error_lower:
            suggestions.append("- Review the error message above to identify the specific constraint violation")
            suggestions.append("- Ensure all parameters (beam sizes, positions) are within allowed ranges")
    
    elif failed:
        if failure_reason and "design constraint violated" in failure_reason.lower():
            failure_lower = failure_reason.lower()
            if "structure mass" in failure_lower:
                max_mass = metrics.get('max_structure_mass', 15.0)
                suggestions.append(f"- Reduce structure mass to be within {max_mass:.0f}kg limit")
                suggestions.append("- Optimize beam sizes and densities to minimize total mass")
            if "build zone" in failure_lower:
                suggestions.append("- Ensure all beams are placed within the build zone")
        elif failure_reason and "too many particles" in failure_reason.lower():
            suggestions.append("- Wiper is not covering the entire glass surface effectively")
            suggestions.append("- Improve four-bar linkage mechanism to increase coverage area")
            suggestions.append("- Adjust motor speeds and phase coordination for better sweeping motion")
            suggestions.append("- Ensure wiper blade makes contact with glass surface to push particles")
            suggestions.append("- Consider optimizing linkage geometry for maximum coverage")
            suggestions.append("- Increase wiper blade size or use multiple passes")
    elif not success:
        if 'cleaning_percentage' in metrics:
            if metrics.get('cleaning_percentage', 0) < 50.0:
                suggestions.append("- Wiper is not effectively cleaning particles")
                suggestions.append("- Improve four-bar linkage mechanism for better coverage")
                suggestions.append("- Adjust motor speeds and coordination")
                suggestions.append("- Ensure wiper blade contacts the glass surface")
            elif metrics.get('cleaning_percentage', 0) < 80.0:
                suggestions.append("- Wiper is making progress but needs to clean more particles")
                suggestions.append("- Improve coverage area or increase sweeping speed")
                suggestions.append("- Check that wiper reaches all areas of the glass surface")
        
        if 'step_count' in metrics and 'min_simulation_steps_required' in metrics:
            if metrics.get('step_count', 0) < metrics.get('min_simulation_steps_required', 0):
                suggestions.append("- Simulation did not run for at least 8 seconds (required for success)")
                suggestions.append("- Ensure the wiper runs long enough to sweep and push particles to the edges")
    
    return suggestions
