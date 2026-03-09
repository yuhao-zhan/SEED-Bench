"""
Task-specific feedback generation for S-05: The Shelter
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Format task-specific metrics for S-05: The Shelter.
    Exposes impact protection and structural stability.
    """
    metric_parts = []
    
    # 1. Protection Metrics
    if 'core_force' in metrics and 'max_core_force' in metrics:
        cf = metrics['core_force']
        mcf = metrics.get('max_core_force', 150.0)
        status = "✅" if cf <= mcf else "❌"
        metric_parts.append(f"{status} **Peak Protected Core Impact**: {cf:.2f} N (Threshold: {mcf:.2f} N)")

    # 2. Structural Metrics
    if 'structure_mass' in metrics and ('max_mass' in metrics or 'max_structure_mass' in metrics):
        sm = metrics['structure_mass']
        msm = metrics.get('max_mass') or metrics.get('max_structure_mass') or 300.0
        status = "✅" if sm <= msm else "❌"
        metric_parts.append(f"{status} **Structural Mass Budget**: {sm:.2f}kg / {msm:.0f}kg")

    if 'min_body_y' in metrics:
        metric_parts.append(f"**Structural Clearance Height**: {metrics['min_body_y']:.2f}m")
    
    if 'max_height_limit' in metrics:
        metric_parts.append(f"**Structural Height Limit**: {metrics['max_height_limit']:.2f}m")

    return metric_parts


def get_improvement_suggestions(metrics: Dict[str, Any], score: float, success: bool, 
                                failed: bool, failure_reason: str = None, 
                                error: str = None) -> List[str]:
    """
    Generate actionable diagnostic warnings for S-05.
    Diagnoses impact and collapse failures.
    """
    suggestions = []
    reason_lower = str(failure_reason).lower() if failure_reason else ""

    if error:
        suggestions.append(">> DIAGNOSTIC: Constraint violation.")
        return suggestions

    if failed:
        suggestions.append(f">> FAILURE MODE: {failure_reason}")
        
        if "core force" in reason_lower or "protection" in reason_lower or "force" in reason_lower:
            suggestions.append("-> Diagnostic: Insufficient kinetic energy isolation. The structural geometry failed to effectively shield the core zone from the impact impulse.")
        elif "collapse" in reason_lower or "below ground" in reason_lower:
            suggestions.append("-> Diagnostic: Structural failure. The load-path geometry collapsed under its own weight or failed to maintain vertical clearance after collision impacts.")
        elif "height" in reason_lower:
            suggestions.append("-> Diagnostic: Spatial constraint violation. The structure's vertical projection exceeds the maximum height limit for this zone.")

    return suggestions
