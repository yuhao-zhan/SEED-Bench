"""
Task-specific feedback generation for S-06: The Overhang
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Format task-specific metrics for S-06: The Overhang.
    Exposes cantilever overhang and static stability.
    """
    metric_parts = []
    
    # 1. Overhang Metrics
    if 'max_x_position' in metrics and 'target_overhang' in metrics:
        mx = metrics['max_x_position']
        to = metrics.get('target_overhang', 0.1)
        status = "✅" if mx >= to else "❌"
        metric_parts.append(f"{status} **Cantilever Overhang Distance**: {mx:.2f}m (Target: {to:.2f}m)")

    # 2. Stability Duration
    if 'stable_duration' in metrics and 'target_stability_time' in metrics:
        sd = metrics['stable_duration']
        ts = metrics.get('target_stability_time', 10.0)
        status = "✅" if sd >= ts else "❌"
        metric_parts.append(f"{status} **Static Stability Duration**: {sd:.2f}s / {ts:.2f}s")

    # 3. Micro-Kinematics
    if 'total_kinetic_energy' in metrics:
        metric_parts.append(f"**Total System Kinetic Energy**: {metrics['total_kinetic_energy']:.2e} J")
    if 'max_velocity' in metrics:
        metric_parts.append(f"**Peak Observed Velocity**: {metrics['max_velocity']:.3f} m/s")

    # 4. Budget Metrics
    if 'block_count' in metrics and 'max_block_count_limit' in metrics:
        bc = metrics['block_count']
        mbl = metrics.get('max_block_count_limit', 20)
        status = "✅" if bc <= mbl else "❌"
        metric_parts.append(f"{status} **Block Utilization**: {bc} / {mbl}")

    if 'structure_mass' in metrics:
        metric_parts.append(f"**Total Structural Mass**: {metrics['structure_mass']:.2f}kg")

    return metric_parts


def get_improvement_suggestions(metrics: Dict[str, Any], score: float, success: bool, 
                                failed: bool, failure_reason: str = None, 
                                error: str = None) -> List[str]:
    """
    Generate actionable diagnostic warnings for S-06.
    Diagnoses overhang tipping and stability failures.
    """
    suggestions = []
    reason_lower = str(failure_reason).lower() if failure_reason else ""

    if error:
        suggestions.append(">> DIAGNOSTIC: Boundary constraint violation.")
        return suggestions

    if failed:
        suggestions.append(f">> FAILURE MODE: {failure_reason}")
        
        if "fell off table" in reason_lower:
            suggestions.append("-> Diagnostic: Terminal Instability. The structure's center of mass has drifted beyond the support boundary, causing a catastrophic loss of equilibrium.")
        elif "ceiling" in reason_lower:
            suggestions.append("-> Diagnostic: Spatial Constraint Violation. The vertical stack height has breached the ceiling clearance limit.")
        elif "stable" in reason_lower:
            suggestions.append("-> Diagnostic: Static Equilibrium Failure. The system exhibits persistent kinetic energy and has failed to reach a steady-state configuration within the required timeframe.")
        elif "overhang" in reason_lower:
            suggestions.append("-> Diagnostic: Insufficient Longitudinal Extension. The horizontal projection of the stack is below the target threshold.")

    return suggestions
