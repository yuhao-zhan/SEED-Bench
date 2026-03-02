"""
Task-specific feedback generation for S-05: The Shelter
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Format task-specific metrics for S-05: The Shelter
    Args:
        metrics: Evaluation metrics dictionary
    Returns:
        List of formatted metric strings
    """
    metric_parts = []
    
    # Core protection metrics (always show if available)
    if 'core_damage' in metrics:
        core_damage = metrics['core_damage']
        max_force = metrics.get('max_core_force', 50.0)
        damage_percent = (core_damage / max_force) * 100 if max_force > 0 else 0
        metric_parts.append(f"**Core damage**: {core_damage:.2f}N / {max_force:.1f}N ({damage_percent:.1f}%)")
        if core_damage >= max_force:
            metric_parts.append(f"⚠️ **Core status**: DAMAGED (exceeded {max_force}N limit)")
        elif core_damage > max_force * 0.8:
            metric_parts.append(f"⚠️ **Core status**: CRITICAL (near limit)")
        else:
            metric_parts.append(f"✅ **Core status**: PROTECTED")
    
    # Structure stability
    if 'structure_stable' in metrics:
        metric_parts.append(f"**Structure stability**: {'✅ STABLE' if metrics['structure_stable'] else '❌ COLLAPSED'}")
    
    # Structure mass
    if 'structure_mass' in metrics:
        structure_mass = metrics['structure_mass']
        max_mass = metrics.get('max_mass', 350.0)
        mass_percent = (structure_mass / max_mass) * 100 if max_mass > 0 else 0
        metric_parts.append(f"**Structure mass**: {structure_mass:.2f}kg / {max_mass:.0f}kg ({mass_percent:.1f}%)")
        if structure_mass > max_mass:
            metric_parts.append(f"⚠️ **Mass status**: EXCEEDS LIMIT")
    
    # Meteor impact information
    if 'meteor_count' in metrics:
        metric_parts.append(f"**Meteors spawned**: {metrics['meteor_count']}")
    if 'meteors_impacted' in metrics:
        metric_parts.append(f"**Meteors impacted**: {metrics['meteors_impacted']}")
    
    # Simulation steps
    if 'step_count' in metrics:
        metric_parts.append(f"**Simulation steps**: {metrics['step_count']}")
    
    # Physical state information for fine-grained debugging
    if 'structure_mass' in metrics or 'core_damage' in metrics:
        metric_parts.append("\n**Physical State Information**:")
        
        # Structure information
        if 'structure_mass' in metrics:
            metric_parts.append(f"- Structure mass: {metrics['structure_mass']:.3f} kg")
        if 'body_count' in metrics:
            metric_parts.append(f"- Number of beams: {metrics['body_count']}")
        if 'joint_count' in metrics:
            metric_parts.append(f"- Number of joints: {metrics['joint_count']}")
        
        # Core protection details
        if 'core_damage' in metrics:
            metric_parts.append(f"- Core damage level: {metrics['core_damage']:.3f} N")
            if 'max_impact_force' in metrics:
                metric_parts.append(f"- Maximum impact force recorded: {metrics['max_impact_force']:.3f} N")
        
        # Structure positions (if available)
        if 'min_body_y' in metrics:
            metric_parts.append(f"- Lowest structure point: y={metrics['min_body_y']:.3f} m")
        if 'max_body_y' in metrics:
            metric_parts.append(f"- Highest structure point: y={metrics['max_body_y']:.3f} m")
    
    # Add any additional metrics
    excluded_keys = ['core_damage', 'max_core_force', 'structure_stable', 'structure_mass', 
                    'max_mass', 'meteor_count', 'meteors_impacted', 'step_count', 'success', 
                    'failed', 'failure_reason', 'body_count', 'joint_count', 'min_body_y', 
                    'max_body_y', 'max_impact_force']
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
    Generate task-specific improvement suggestions for S-05: The Shelter
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
            max_mass = metrics.get('max_mass', 350.0)
            suggestions.append(f"- Reduce structure mass to be within {max_mass:.0f}kg limit")
            suggestions.append("- Use lighter materials (lower density) or optimize beam sizes")
            suggestions.append("- Consider using truss designs to reduce material while maintaining strength")
        elif "keep-out" in error_lower or "cannot build" in error_lower:
            suggestions.append("- Cannot build within 0.5m of core at (0,0)")
            suggestions.append("- Adjust beam positions to maintain minimum distance from core")
            suggestions.append("- Check that all beam centers are at least 0.5m away from origin")
        elif "error building" in error_lower:
            suggestions.append("- Review the error message above to identify the specific constraint violation")
            suggestions.append("- Ensure all parameters (beam sizes, positions) are within allowed ranges")
    
    elif failed:
        if failure_reason and "design constraint violated" in failure_reason.lower():
            failure_lower = failure_reason.lower()
            if "structure mass" in failure_lower:
                max_mass = metrics.get('max_mass', 350.0)
                suggestions.append(f"- Reduce structure mass to be within {max_mass:.0f}kg limit")
                suggestions.append("- Consider using truss designs to reduce material while maintaining strength")
                suggestions.append("- Optimize beam sizes and densities to minimize total mass")
            if "keep-out" in failure_lower:
                suggestions.append("- Cannot build within 0.5m of core")
                suggestions.append("- Adjust beam positions to maintain distance from core at (0,0)")
        elif failure_reason and ("core" in failure_reason.lower() and "force" in failure_reason.lower()):
            core_damage = metrics.get('core_damage', 0)
            suggestions.append(f"- Core received {core_damage:.2f}N force (exceeds 50N limit)")
            suggestions.append("- Meteors come from BOTH left and right; ensure roof deflects from both sides")
            suggestions.append("- Use low restitution materials (restitution < 0.2) to absorb impact energy")
            suggestions.append("- Ensure shelter covers core from both left (x in [-5,-2]) and right (x in [2,5]) impact directions")
            suggestions.append("- Increase roof height or add multiple deflection layers")
            suggestions.append("- Consider angled roof design to deflect meteors away from core")
        elif failure_reason and "collapsed" in failure_reason.lower():
            suggestions.append("- Shelter structure is not strong enough to support its own weight")
            suggestions.append("- Add more support columns or strengthen joints")
            suggestions.append("- Increase beam thickness or use higher density materials")
            suggestions.append("- Add cross-bracing for structural stability")
            suggestions.append("- Ensure all joints are properly connected")
    elif not success:
        core_damage = metrics.get('core_damage', 0)
        max_force = metrics.get('max_core_force', 50.0)
        if core_damage > max_force * 0.5:
            suggestions.append("- Core is receiving significant impact force")
            suggestions.append("- Improve roof coverage and deflection angles")
            suggestions.append("- Add additional protective layers")
        structure_mass = metrics.get('structure_mass', 0)
        max_mass = metrics.get('max_mass', 350.0)
        if structure_mass > max_mass * 0.9:
            suggestions.append(f"- Structure mass ({structure_mass:.2f}kg) is close to limit ({max_mass}kg)")
            suggestions.append("- Optimize design to reduce mass while maintaining protection")
    
    return suggestions
