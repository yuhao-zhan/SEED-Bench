"""
Task-specific feedback generation for classify_balls task
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Format task-specific metrics for classify_balls task
    Args:
        metrics: Evaluation metrics dictionary
    Returns:
        List of formatted metric strings
    """
    metric_parts = []
    
    if 'accuracy' in metrics:
        metric_parts.append(f"**Classification accuracy**: {metrics['accuracy']:.1f}%")
        metric_parts.append(f"**Total balls**: {metrics.get('total_balls', 0)}")
        if 'red_balls_correct' in metrics:
            metric_parts.append(f"**Red balls correct**: {metrics['red_balls_correct']}/{metrics.get('total_red', 0)}")
            metric_parts.append(f"**Blue balls correct**: {metrics['blue_balls_correct']}/{metrics.get('total_blue', 0)}")
        if 'red_balls_wrong' in metrics:
            if metrics['red_balls_wrong'] > 0:
                metric_parts.append(f"**Red balls wrong**: {metrics['red_balls_wrong']}")
            if metrics['blue_balls_wrong'] > 0:
                metric_parts.append(f"**Blue balls wrong**: {metrics['blue_balls_wrong']}")
        
        # Physical state information
        metric_parts.append("\n**Physical State Information**:")
        if 'balls_on_conveyor' in metrics:
            metric_parts.append(f"- Balls on conveyor: {metrics['balls_on_conveyor']}")
        if 'balls_in_red_basket' in metrics:
            metric_parts.append(f"- Balls in red basket: {metrics['balls_in_red_basket']}")
        if 'balls_in_blue_basket' in metrics:
            metric_parts.append(f"- Balls in blue basket: {metrics['balls_in_blue_basket']}")
    
    # Add any additional metrics that might be present
    excluded_keys = ['accuracy', 'total_balls', 'red_balls_correct', 'blue_balls_correct',
                    'red_balls_wrong', 'blue_balls_wrong', 'balls_on_conveyor',
                    'balls_in_red_basket', 'balls_in_blue_basket', 'success', 'failed', 'failure_reason']
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
    Generate task-specific improvement suggestions for classify_balls task
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
        if "error building agent" in error_lower:
            suggestions.append("- Review the error message above to identify the specific constraint violation")
            suggestions.append("- Ensure all parameters are within allowed ranges")
    
    elif not success:
        if 'accuracy' in metrics:
            if metrics.get('accuracy', 0) < 50:
                suggestions.append("- Sensor may not be able to correctly detect ball colors")
                suggestions.append("- Check sensor position: should detect balls on conveyor before they fall")
                suggestions.append("- For blue balls: They should naturally fall into blue bin (x=0.5, range -1.25 to 2.25), no action needed")
                suggestions.append("- For red balls: Use piston to push right into red bin (x=4.0, range 2.5 to 5.5)")
                suggestions.append("- Check actuator position: Should intercept ball path for gentle deflection")
                suggestions.append("- Ensure delay timing matches ball trajectory - balls move at 2.0 m/s on conveyor")
            elif metrics.get('accuracy', 0) < 100:
                suggestions.append("- Good progress! Check timing: piston may activate too early or too late")
                suggestions.append("- Verify piston has enough force and extension length to push balls")
                suggestions.append("- Consider adjusting delay_seconds and output_duration parameters")
            else:
                suggestions.append("- High accuracy, check reasons for few misclassifications")
    
    return suggestions
