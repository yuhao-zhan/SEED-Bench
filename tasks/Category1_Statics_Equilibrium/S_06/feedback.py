"""
Task-specific feedback generation for S-06: The Overhang
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Format task-specific metrics for S-06: The Overhang
    Args:
        metrics: Evaluation metrics dictionary
    Returns:
        List of formatted metric strings
    """
    metric_parts = []
    
    # Primary metrics
    if 'max_x_position' in metrics:
        metric_parts.append(f"**Max x position**: {metrics['max_x_position']:.2f}m")
    if 'target_overhang' in metrics:
        metric_parts.append(f"**Target overhang**: {metrics['target_overhang']:.2f}m")
    if 'current_max_x' in metrics:
        metric_parts.append(f"**Current max x**: {metrics['current_max_x']:.2f}m")
    
    if 'stable_duration' in metrics:
        metric_parts.append(f"**Stable duration**: {metrics['stable_duration']:.2f}s / {metrics.get('target_stability_time', 10):.1f}s")
    if 'stability_ok' in metrics:
        metric_parts.append(f"**Stability**: {'OK' if metrics['stability_ok'] else 'UNSTABLE'}")
    if 'overhang_ok' in metrics:
        metric_parts.append(f"**Overhang**: {'OK' if metrics['overhang_ok'] else 'INSUFFICIENT'}")
    
    # Structure metrics
    if 'structure_mass' in metrics:
        metric_parts.append(f"**Structure mass**: {metrics['structure_mass']:.2f}kg")
    if 'block_count' in metrics:
        metric_parts.append(f"**Block count**: {metrics['block_count']}")
    
    # Physical state information
    if 'center_of_mass_x' in metrics or 'center_of_mass_y' in metrics:
        metric_parts.append("\n**Physical State Information**:")
        if 'center_of_mass_x' in metrics:
            metric_parts.append(f"- Center of mass X: {metrics['center_of_mass_x']:.3f}m")
            if 'target_overhang' in metrics:
                # Check if COM is on table (x < 0)
                if metrics['center_of_mass_x'] < 0:
                    metric_parts.append(f"  → COM is on table (stable)")
                else:
                    metric_parts.append(f"  → COM is over edge (unstable!)")
        if 'center_of_mass_y' in metrics:
            metric_parts.append(f"- Center of mass Y: {metrics['center_of_mass_y']:.3f}m")
        
        if 'min_y_position' in metrics and 'max_y_position' in metrics:
            metric_parts.append(f"- Structure height range: y=[{metrics['min_y_position']:.3f}, {metrics['max_y_position']:.3f}]m")
        
        if 'total_kinetic_energy' in metrics:
            metric_parts.append(f"- Total kinetic energy: {metrics['total_kinetic_energy']:.6f} J")
            if metrics['total_kinetic_energy'] < 0.001:
                metric_parts.append(f"  → Structure is nearly static")
            else:
                metric_parts.append(f"  → Structure is moving!")
        
        if 'max_velocity' in metrics:
            metric_parts.append(f"- Max block velocity: {metrics['max_velocity']:.4f} m/s")
            if metrics['max_velocity'] < 0.01:
                metric_parts.append(f"  → Blocks are nearly stationary")
            else:
                metric_parts.append(f"  → Blocks are moving (unstable)")
    
    # Simulation steps
    if 'step_count' in metrics:
        metric_parts.append(f"\n**Simulation steps**: {metrics['step_count']}")
    
    return metric_parts


def get_improvement_suggestions(metrics: Dict[str, Any], score: float, success: bool, 
                                failed: bool, failure_reason: str = None, 
                                error: str = None) -> List[str]:
    """
    Generate improvement suggestions for S-06: The Overhang
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
        if "spawn" in error_lower or "start zone" in error_lower:
            suggestions.append("- All blocks must spawn at x < 0 (on the table), but construction zone may be further restricted.")
        elif "width" in error_lower or "height" in error_lower or "dimension" in error_lower:
            suggestions.append("- Block dimensions must be: width <= 4.0m, height <= 0.4m")
        elif "too many blocks" in error_lower:
            suggestions.append("- Reduce number of blocks to be within 20 limit")
        elif "joint" in error_lower:
            suggestions.append("- Joints are disabled for this task - you can only use gravity and friction")
    
    elif failed:
        if failure_reason and "constraint" in failure_reason.lower():
            failure_lower = failure_reason.lower()
            if "too many blocks" in failure_lower:
                suggestions.append("- Reduce number of blocks to be within 20 limit")
            elif "spawn zone" in failure_lower or "start zone" in failure_lower:
                suggestions.append("- Your blocks are outside the permitted build access zone. Check the environmental feedback.")
            elif "width" in failure_lower or "height" in failure_lower:
                suggestions.append("- Block dimensions must be: width <= 4.0m, height <= 0.4m")
        elif failure_reason and "hit the ceiling" in failure_reason.lower():
            suggestions.append("- Vertical clearance is restricted. Keep your structure lower to the ground.")
        elif failure_reason and "fell" in failure_reason.lower():
            suggestions.append("- Structure is unstable and falling")
            com_x = metrics.get('center_of_mass_x', 0)
            if com_x >= 0:
                suggestions.append(f"- Center of mass is at x={com_x:.2f}m (over edge) - move it back onto table")
            suggestions.append("- Use counter-balancing: place heavier blocks further back on table")
            suggestions.append("- Ensure structure has sufficient base support to resist wind or tilt")
    
    elif not success:
        max_x = metrics.get('max_x_position', 0)
        target = metrics.get('target_overhang', 0.1)
        
        if max_x < target:
            suggestions.append(f"- Overhang is insufficient: {max_x:.2f}m < {target:.2f}m target")
            suggestions.append("- Use counter-balancing technique: extend blocks outward while placing counter-weights on table")
            suggestions.append("- Stack blocks in layers, gradually extending outward")
            com_x = metrics.get('center_of_mass_x', 0)
            if com_x >= 0:
                suggestions.append(f"- Center of mass is over edge (x={com_x:.2f}m) - add more blocks on table to balance")
            else:
                suggestions.append(f"- Center of mass is on table (x={com_x:.2f}m) - good, but need to extend further")
        
        elif not metrics.get('stability_ok', False):
            suggestions.append("- Structure is not stable for 10 seconds")
            stable_duration = metrics.get('stable_duration', 0)
            target_time = metrics.get('target_stability_time', 10)
            suggestions.append(f"- Only stable for {stable_duration:.2f}s, need {target_time:.1f}s")
            
            if metrics.get('max_velocity', 0) > 0.01:
                suggestions.append("- Structure is still moving - improve balance")
                suggestions.append("- Consider lateral forces like wind or tilt that might require heavier anchors")
    
    return suggestions
