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
    
    # 1. Height Requirements
    if 'initial_height' in metrics:
        target = metrics.get('target_height', 30.0)
        status = "✅" if metrics['initial_height'] >= target else "❌"
        metric_parts.append(f"{status} **Initial Peak Height**: {metrics['initial_height']:.2f}m (Target: >{target:.1f}m)")

    # 2. Earthquake Survival
    if 'min_height_during_quake' in metrics and metrics['min_height_during_quake'] is not None:
        threshold = metrics.get('survival_threshold', 5.0)
        min_h = metrics['min_height_during_quake']
        status = "✅" if min_h >= threshold else "❌"
        metric_parts.append(f"{status} **Min Height during Quake**: {min_h:.2f}m (Threshold: >{threshold:.1f}m)")
    elif metrics.get('failed') and "Collapsed" in str(metrics.get('failure_reason')):
        metric_parts.append(f"❌ **Min Height during Quake**: <5.0m (Structure Collapsed)")

    # 3. Stability (Center of Mass)
    if 'rel_com_x' in metrics:
        zone = metrics.get('stability_zone', 300.0)
        com_x = metrics['rel_com_x']
        status = "✅" if abs(com_x) <= zone else "❌"
        metric_parts.append(f"{status} **Center of Mass X**: {com_x:.3f}m (Allowed Range: ±{zone:.1f}m)")

    # 4. Failure Reason (High Signal)
    if metrics.get('failed') and metrics.get('failure_reason'):
        metric_parts.append(f"\n⚠️ **FAILURE DETECTED**: {metrics['failure_reason']}")

    # 5. Current State
    if 'current_height' in metrics:
        metric_parts.append(f"\n**Current Height at simulation end**: {metrics['current_height']:.2f}m")
    
    return metric_parts


def get_improvement_suggestions(metrics: Dict[str, Any], score: float, success: bool, 
                                failed: bool, failure_reason: str = None, 
                                error: str = None) -> List[str]:
    """
    Generate task-specific improvement suggestions for S-02: The Skyscraper
    """
    suggestions = []
    
    if error:
        suggestions.append("- Fix the code execution error reported in the details.")
        return suggestions

    if failed:
        reason = str(failure_reason).lower()
        if "height" in reason:
            suggestions.append("- Your tower is not tall enough. Stack more beams or increase beam height (up to 10m).")
        if "collapsed" in reason or "survival" in reason:
            suggestions.append("- The structure failed under vibration. Use `add_spring` to create a Tuned Mass Damper (TMD) at the top.")
            suggestions.append("- Increase beam density at the bottom levels to lower the center of mass.")
            suggestions.append("- Ensure the structure is robust against seismic forces and joint breaking limits.")
        if "tipped" in reason or "stability" in reason:
            suggestions.append("- The tower is leaning too much. Ensure the structure is symmetrical or add counterweights.")
            suggestions.append("- Maximize the base width (up to 12m) while keeping foundation contact within x=[-2, 2].")
        if "width" in reason:
            suggestions.append("- The total structure width exceeds 12m. Use narrower beams for the upper levels.")
            
    return suggestions
