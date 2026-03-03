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
    
    # Structure reach (always show if available)
    if 'max_reach' in metrics:
        metric_parts.append(f"**Max reach**: {metrics['max_reach']:.2f}m")
        if 'target_reach' in metrics:
            metric_parts.append(f"**Target reach**: {metrics['target_reach']:.2f}m")
            reach_ratio = metrics['max_reach'] / metrics['target_reach'] if metrics['target_reach'] > 0 else 0
            metric_parts.append(f"**Reach progress**: {reach_ratio * 100:.1f}%")
    
    # Load information
    if 'load_attached' in metrics:
        metric_parts.append(f"**Tip load attached**: {metrics['load_attached']}")
    if 'load_hold_time' in metrics:
        required_hold_time = 10.0
        metric_parts.append(f"**Tip load hold time**: {metrics['load_hold_time']:.2f}s / {required_hold_time:.1f}s")
        if metrics.get('load_attached'):
            hold_progress = min(metrics['load_hold_time'] / required_hold_time * 100, 100)
            metric_parts.append(f"**Tip hold progress**: {hold_progress:.1f}%")
    if 'load2_attached' in metrics:
        metric_parts.append(f"**Mid-span load attached**: {metrics['load2_attached']}")
    if 'load2_hold_time' in metrics:
        required_hold_time = 10.0
        metric_parts.append(f"**Mid-span load hold time**: {metrics['load2_hold_time']:.2f}s / {required_hold_time:.1f}s")
        if metrics.get('load2_attached'):
            hold_progress = min(metrics['load2_hold_time'] / required_hold_time * 100, 100)
            metric_parts.append(f"**Mid-span hold progress**: {hold_progress:.1f}%")
    
    # Tip height (anti-sag)
    if 'min_tip_y' in metrics and metrics['min_tip_y'] is not None:
        metric_parts.append(f"**Min tip height (y)**: {metrics['min_tip_y']:.2f}m")
        if 'min_tip_height' in metrics:
            metric_parts.append(f"**Required min**: {metrics['min_tip_height']:.2f}m")
            if metrics.get('tip_sagged'):
                metric_parts.append(f"⚠️ **Tip sag**: FAILED (tip dropped below {metrics['min_tip_height']}m)")
    
    # Anchor status
    if 'anchor_broken' in metrics:
        metric_parts.append(f"**Anchor status**: {'BROKEN' if metrics['anchor_broken'] else 'INTACT'}")
    
    # Structure mass
    if 'structure_mass' in metrics:
        metric_parts.append(f"**Structure mass**: {metrics['structure_mass']:.2f}kg")
    
    # Anchor information
    if 'anchor_count' in metrics:
        metric_parts.append(f"**Wall anchors**: {metrics['anchor_count']}")
        if 'max_anchor_points' in metrics:
            metric_parts.append(f"**Max anchors allowed**: {metrics['max_anchor_points']}")
    
    # Torque information (if available)
    if 'max_anchor_torque' in metrics:
        metric_parts.append(f"**Max anchor torque**: {metrics['max_anchor_torque']:.2f} Nm")
        if 'max_anchor_torque_limit' in metrics:
            metric_parts.append(f"**Torque limit**: {metrics['max_anchor_torque_limit']:.2f} Nm")
            if metrics['max_anchor_torque'] > 0:
                torque_ratio = metrics['max_anchor_torque'] / metrics['max_anchor_torque_limit']
                metric_parts.append(f"**Torque usage**: {torque_ratio * 100:.1f}%")
    
    # Structure integrity
    if 'joint_count' in metrics:
        metric_parts.append(f"**Joint count**: {metrics['joint_count']}")
        if 'initial_joint_count' in metrics:
            if metrics['joint_count'] < metrics['initial_joint_count']:
                broken_joints = metrics['initial_joint_count'] - metrics['joint_count']
                metric_parts.append(f"**Broken joints**: {broken_joints}")
    
    # Simulation steps
    if 'step_count' in metrics:
        metric_parts.append(f"**Simulation steps**: {metrics['step_count']}")
    
    # Physical state information for fine-grained debugging
    if 'current_reach' in metrics or 'structure_mass' in metrics:
        metric_parts.append("\n**Physical State Information**:")
        if 'current_reach' in metrics:
            metric_parts.append(f"- Current structure reach: {metrics['current_reach']:.3f}m")
        if 'structure_mass' in metrics:
            metric_parts.append(f"- Total structure mass: {metrics['structure_mass']:.3f}kg")
        if 'anchor_count' in metrics:
            metric_parts.append(f"- Active wall anchors: {metrics['anchor_count']}")
        if 'load_attached' in metrics and metrics['load_attached']:
            if 'load_position_x' in metrics:
                metric_parts.append(f"- Load position: x={metrics['load_position_x']:.3f}m")
            if 'load_mass' in metrics:
                metric_parts.append(f"- Load mass: {metrics['load_mass']:.3f}kg")
    
    # Add any additional metrics
    excluded_keys = ['max_reach', 'target_reach', 'load_attached', 'load_hold_time', 'load2_attached', 'load2_hold_time',
                    'anchor_broken', 'tip_sagged', 'min_tip_y', 'min_tip_height', 'structure_mass', 'anchor_count',
                    'max_anchor_points', 'max_anchor_torque', 'max_anchor_torque_limit', 'joint_count', 'initial_joint_count',
                    'step_count', 'success', 'failed', 'failure_reason', 'current_reach', 'load_position_x', 'load_mass', 'load2_mass']
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
    Generate task-specific improvement suggestions for S-03: The Cantilever
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
        if "corrosive" in error_lower or "forbidden zone" in error_lower:
            suggestions.append("- Your anchor was placed in a corroded wall zone and failed immediately.")
            suggestions.append("- Change the y-coordinate of your wall anchors to avoid the unstable region.")
        elif "anchor" in error_lower and "maximum" in error_lower:
            suggestions.append("- Too many wall anchors: maximum 2 anchor points allowed")
            suggestions.append("- Reduce number of anchor points or redesign structure")
        elif "error building" in error_lower:
            suggestions.append("- Review the error message above to identify the specific constraint violation")
            suggestions.append("- Beam limits for this task: width 0.1–10 m, height 0.1–2 m (enforced at build time)")
    
    elif failed:
        if failure_reason and "sagged" in failure_reason.lower():
            min_tip_y = metrics.get('min_tip_y')
            min_h = metrics.get('min_tip_height', -4.0)
            suggestions.append(f"- Tip dropped to or below y={min_h}m (min_tip_y={min_tip_y:.2f}m); structure is too flexible")
            suggestions.append("- Add more diagonal bracing to reduce deflection under load")
            suggestions.append("- Use stiffer design: shorter beam segments, more triangulation from wall to tip")
            suggestions.append("- Ensure chord and diagonals form a rigid truss that limits vertical sag")
        elif failure_reason and "anchor" in failure_reason.lower() and "torque" in failure_reason.lower():
            suggestions.append("- Wall anchors are breaking due to excessive torque (>2600 Nm)")
            suggestions.append("- Use truss design with diagonal supports to distribute load")
            suggestions.append("- You have only 2 anchor points; optimize geometry to reduce moment on each")
            suggestions.append("- Ensure diagonal supports connect from wall to multiple points along structure")
        elif failure_reason and "reach" in failure_reason.lower():
            max_reach = metrics.get('max_reach', 0)
            target_reach = metrics.get('target_reach', 10.0)
            suggestions.append(f"- Structure reach ({max_reach:.2f}m) does not meet target ({target_reach:.2f}m)")
            suggestions.append("- Increase structure length or use longer beam segments")
            suggestions.append("- Ensure structure extends horizontally from wall")
        elif failure_reason and "tip load" in failure_reason.lower():
            hold_time = metrics.get('load_hold_time', 0)
            suggestions.append(f"- Structure cannot support tip load for required 10s (held {hold_time:.2f}s)")
            suggestions.append("- Strengthen structure with more diagonal supports and ensure a node near x=7.5m for mid-span load")
        elif failure_reason and "mid-span load" in failure_reason.lower():
            suggestions.append("- Mid-span load attaches at t=10s to the node closest to x=7.5m (x in [5,10])")
            suggestions.append("- Ensure your structure has a beam or joint node near x=7.5m so the second load can attach")
            suggestions.append("- Strengthen the mid-span region with diagonals")
        elif failure_reason and "load" in failure_reason.lower():
            hold_time = metrics.get('load_hold_time', 0)
            suggestions.append(f"- Structure cannot support loads for required 10s (tip held {hold_time:.2f}s)")
            suggestions.append("- Use truss design to distribute load; ensure node near x=7.5m for second load")
        elif failure_reason and "design constraint" in failure_reason.lower():
            suggestions.append("- Review design constraints: maximum 2 wall anchors allowed")
            suggestions.append("- Beam limits: width 0.1–10 m, height 0.1–2 m (enforced at build time)")
    
    elif not success:
        max_reach = metrics.get('max_reach', 0)
        target_reach = metrics.get('target_reach', 10.0)
        if max_reach < target_reach:
            suggestions.append(f"- Structure reach ({max_reach:.2f}m) is below target ({target_reach:.2f}m)")
            suggestions.append("- Extend structure further horizontally; ensure a node near x=7.5m for mid-span load")
        else:
            hold_time = metrics.get('load_hold_time', 0)
            load2_hold = metrics.get('load2_hold_time', 0)
            if hold_time < 10.0 or load2_hold < 10.0:
                suggestions.append(f"- Tip hold {hold_time:.2f}s, mid-span hold {load2_hold:.2f}s (need 10s each)")
                suggestions.append("- Ensure node near x=7.5m for second load; strengthen with diagonals")
                suggestions.append("- Check anchor torque levels - may be approaching 2600 Nm limit")
    
    return suggestions
