"""
Task-specific feedback generation for S-03: The Cantilever
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Format task-specific metrics for S-03: The Cantilever
    Args:
        metrics: Evaluation metrics dictionary
    Returns:
        List of formatted metric strings
    """
    metric_parts = []
    
    # Structure reach
    if 'max_reach' in metrics:
        metric_parts.append(f"**Max reach**: {metrics['max_reach']:.2f}m")
        if 'target_reach' in metrics:
            metric_parts.append(f"**Target reach**: {metrics['target_reach']:.2f}m")
            reach_ratio = metrics['max_reach'] / metrics['target_reach'] if metrics['target_reach'] > 0 else 0
            metric_parts.append(f"**Reach progress**: {reach_ratio * 100:.1f}%")
    
    # Load information
    if 'load_attached' in metrics:
        metric_parts.append(f"**Primary payload attached**: {metrics['load_attached']}")
    if 'load_hold_time' in metrics:
        required_hold_time = 10.0
        metric_parts.append(f"**Primary payload hold time**: {metrics['load_hold_time']:.2f}s / {required_hold_time:.1f}s")
    if 'load2_attached' in metrics:
        metric_parts.append(f"**Secondary payload attached**: {metrics['load2_attached']}")
    if 'load2_hold_time' in metrics:
        required_hold_time = 10.0
        metric_parts.append(f"**Secondary payload hold time**: {metrics['load2_hold_time']:.2f}s / {required_hold_time:.1f}s")
    
    # Tip height (anti-sag)
    if 'min_tip_y' in metrics:
        metric_parts.append(f"**Min structure height (y)**: {metrics['min_tip_y']:.2f}m")
        if 'min_tip_height' in metrics:
            metric_parts.append(f"**Min height limit**: {metrics['min_tip_height']:.2f}m")
            if metrics.get('tip_sagged'):
                metric_parts.append(f"⚠️ **Structural Sag**: FAILED (dropped below {metrics['min_tip_height']}m)")
    
    # Anchor status
    if 'anchor_broken' in metrics:
        metric_parts.append(f"**Anchor status**: {'BROKEN' if metrics['anchor_broken'] else 'INTACT'}")
    
    # Structure mass
    if 'structure_mass' in metrics:
        limit = metrics.get('max_structure_mass', 10000.0)
        metric_parts.append(f"**Structure mass**: {metrics['structure_mass']:.2f}kg / {limit:.2f}kg")
    
    # Anchor information
    if 'anchor_count' in metrics:
        metric_parts.append(f"**Wall anchors**: {metrics['anchor_count']} / 2 max")
    
    # Torque information
    if 'max_anchor_torque' in metrics:
        metric_parts.append(f"**Max anchor torque**: {metrics['max_anchor_torque']:.2f} Nm")
        if 'max_anchor_torque_limit' in metrics:
            metric_parts.append(f"**Torque limit**: {metrics['max_anchor_torque_limit']:.2f} Nm")
            if metrics['max_anchor_torque_limit'] > 0:
                torque_ratio = metrics['max_anchor_torque'] / metrics['max_anchor_torque_limit']
                metric_parts.append(f"**Torque usage**: {torque_ratio * 100:.1f}%")
    
    # Structure integrity
    if 'joint_count' in metrics:
        if 'initial_joint_count' in metrics:
            if metrics['joint_count'] < metrics['initial_joint_count']:
                broken_joints = metrics['initial_joint_count'] - metrics['joint_count']
                metric_parts.append(f"**Broken joints**: {broken_joints}")
    
    return metric_parts


def get_improvement_suggestions(metrics: Dict[str, Any], score: float, success: bool, 
                                failed: bool, failure_reason: str = None, 
                                error: str = None) -> List[str]:
    """
    Generate task-specific improvement suggestions for S-03: The Cantilever
    """
    suggestions = []
    
    if error:
        suggestions.append("- Review the error message for specific constraint violations.")
        suggestions.append("- Ensure wall anchors are within allowed build zones and not in forbidden regions.")
    
    elif failed:
        if "sagged" in failure_reason.lower() or "reach" in failure_reason.lower():
            suggestions.append("- Structure is too flexible or failing to hold its shape under high gravity.")
            suggestions.append("- Use **pre-cambering**: angle your beams slightly upward during construction to counteract gravity-induced sag.")
            suggestions.append("- Increase triangulation density and beam thickness, especially near the wall anchors.")
            
        if "torque" in failure_reason.lower() or "integrity" in failure_reason.lower() or "anchor" in failure_reason.lower():
            usage = metrics.get('max_anchor_torque', 0) / metrics.get('max_anchor_torque_limit', 1) * 100
            suggestions.append(f"- Anchor torque reached {usage:.1f}% of limit. Use a wider vertical base for your wall anchors.")
            suggestions.append("- Connect diagonal supports from the wall to multiple points along the span to distribute moment forces.")
            
        if "hold" in failure_reason.lower() or "load" in failure_reason.lower():
            suggestions.append("- Dynamic impacts require a stiffer, more robust truss. Redundant bracing can absorb impact energy.")
            suggestions.append("- Ensure the structure remains horizontal enough for the payload to stay attached during the test duration.")

    return suggestions
