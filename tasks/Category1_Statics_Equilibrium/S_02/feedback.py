"""
Task-specific feedback generation for S-02: The Skyscraper
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Format task-specific metrics for S-02: The Skyscraper.
    Exposes structural height and stability metrics.
    """
    metric_parts = []
    
    # 1. Height Metrics
    if 'initial_height' in metrics:
        ih = metrics['initial_height']
        th = metrics.get('target_height', 30.0)
        status = "✅" if ih >= th else "❌"
        metric_parts.append(f"{status} **Peak Structural Height**: {ih:.2f}m (Target: >{th:.1f}m)")

    if 'min_height_during_quake' in metrics and metrics['min_height_during_quake'] is not None:
        mh = metrics['min_height_during_quake']
        st = metrics.get('survival_threshold', 5.0)
        status = "✅" if mh >= st else "❌"
        metric_parts.append(f"{status} **Seismic Survival Height**: {mh:.2f}m (Limit: >{st:.1f}m)")

    # 2. Stability Metrics
    if 'rel_com_x' in metrics:
        rcx = metrics['rel_com_x']
        sz = metrics.get('stability_zone', 300.0)
        status = "✅" if abs(rcx) <= sz else "❌"
        metric_parts.append(f"{status} **Center of Mass Deviation**: {rcx:+.3f}m (Allowed: ±{sz:.1f}m)")

    if 'current_height' in metrics:
        metric_parts.append(f"**Final Structure State Height**: {metrics['current_height']:.2f}m")

    return metric_parts


def get_improvement_suggestions(metrics: Dict[str, Any], score: float, success: bool, 
                                failed: bool, failure_reason: str = None, 
                                error: str = None) -> List[str]:
    """
    Generate actionable diagnostic warnings for S-02.
    Diagnoses seismic and stability failures.
    """
    suggestions = []
    reason_lower = str(failure_reason).lower() if failure_reason else ""

    if error:
        suggestions.append(">> DIAGNOSTIC: Engineering validation failed.")
        return suggestions

    if failed:
        suggestions.append(f">> FAILURE MODE: {failure_reason}")
        
        if "height" in reason_lower:
            suggestions.append("-> Diagnostic: Vertical extension failure. The tower's highest vertical point is below the target threshold. Check for cumulative structural deflection or insufficient vertical density.")
        elif "collapsed" in reason_lower or "survival" in reason_lower:
            suggestions.append("-> Diagnostic: Seismic resonance or structural failure. The tower was unable to dissipate lateral energy during the earthquake phase, leading to a catastrophic loss of verticality.")
        elif "tipped" in reason_lower or "stability" in reason_lower:
            suggestions.append("-> Diagnostic: High Overturning Moment. The system's center of mass shifted beyond the stability boundary, causing the gravitational vector to fall outside the base of support.")
        elif "explosion" in reason_lower or "instability" in reason_lower:
            suggestions.append("-> Diagnostic: Numerical instability detected. This usually results from extreme beam density ratios or excessive joint overlapping causing the physics solver to diverge.")

    return suggestions
