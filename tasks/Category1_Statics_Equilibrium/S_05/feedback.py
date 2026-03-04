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
    
    # Core protection metrics
    if 'core_force' in metrics:
        core_force = metrics['core_force']
        max_force = metrics.get('max_core_force', 150.0)
        force_percent = (core_force / max_force) * 100 if max_force > 0 else 0
        metric_parts.append(f"**Max Core Force**: {core_force:.2f}N / {max_force:.1f}N ({force_percent:.1f}%)")
        if core_force >= max_force:
            metric_parts.append(f"⚠️ **Core status**: DAMAGED (exceeded {max_force}N limit)")
        elif core_force > max_force * 0.8:
            metric_parts.append(f"⚠️ **Core status**: CRITICAL (near limit)")
        else:
            metric_parts.append(f"✅ **Core status**: PROTECTED")
    
    # Structure mass
    if 'structure_mass' in metrics:
        structure_mass = metrics['structure_mass']
        max_mass = metrics.get('max_mass', 300.0)
        mass_percent = (structure_mass / max_mass) * 100 if max_mass > 0 else 0
        metric_parts.append(f"**Structure mass**: {structure_mass:.2f}kg / {max_mass:.0f}kg ({mass_percent:.1f}%)")
        if structure_mass > max_mass:
            metric_parts.append(f"⚠️ **Mass status**: EXCEEDS LIMIT")
    
    # Physical state information
    if 'min_body_y' in metrics:
        metric_parts.append(f"- Lowest structure point: y={metrics['min_body_y']:.3f} m")
    
    return metric_parts


def get_improvement_suggestions(metrics: Dict[str, Any], score: float, success: bool, 
                                failed: bool, failure_reason: str = None, 
                                error: str = None) -> List[str]:
    """
    Generate task-specific improvement suggestions for S-05: The Shelter
    """
    suggestions = []
    
    if error:
        suggestions.append("- Ensure your code follows the provided API and constraints.")
        return suggestions

    if failed:
        if "mass" in failure_reason.lower():
            max_mass = metrics.get('max_mass', 300.0)
            suggestions.append(f"- Reduce total structure mass below the {max_mass}kg budget.")
            suggestions.append("- Use thinner beams or lower densities for non-critical components.")
        elif "core" in failure_reason.lower():
            suggestions.append("- The core is receiving excessive impact force. Improve your roof's energy absorption or deflection.")
            suggestions.append("- Consider an angled (A-shape) roof to deflect boulders to the sides.")
            suggestions.append("- Add a secondary 'safety' roof layer closer to the core to catch small debris.")
            suggestions.append("- If wind is present, ensure your roof covers a wider horizontal span to account for lateral meteor movement.")
        elif "collapsed" in failure_reason.lower():
            suggestions.append("- The structure is unstable or collapsed. Strengthen joints or add cross-bracing.")
            suggestions.append("- If ground friction is low, use wider bases or slanted pillars (triangulation) to prevent sliding.")
            suggestions.append("- Ensure all pillars are firmly anchored to the ground.")
        elif "height" in failure_reason.lower():
            suggestions.append("- Some components exceed the 7.5m height limit. Lower your roof or use flatter beams.")

    elif not success:
        suggestions.append("- Your shelter survived but the test period hasn't finished, or the core is still at risk.")
        suggestions.append("- Observe the failure mode: does the roof break, or does it simply fail to deflect enough energy?")

    return suggestions
