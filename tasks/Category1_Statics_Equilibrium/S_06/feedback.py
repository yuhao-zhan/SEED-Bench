"""
Task-specific feedback generation for S-06: The Overhang.
Refactored for Code-Grounded Truth and strict logical consistency.
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Format task-specific metrics for S-06: The Overhang.
    Grounded exclusively in evaluator.py metrics.
    """
    metric_parts = []
    
    # 1. Overhang Reach
    if 'max_x_position' in metrics and 'target_overhang' in metrics:
        mx = metrics['max_x_position']
        to = metrics['target_overhang']
        status = "✅" if metrics.get('overhang_ok', False) else "❌"
        metric_parts.append(f"{status} **Maximum Horizontal Reach**: {mx:.2f}m (Target: {to:.2f}m)")

    # 2. Static Stability
    if 'stable_duration' in metrics and 'target_stability_time' in metrics:
        sd = metrics['stable_duration']
        ts = metrics['target_stability_time']
        status = "✅" if metrics.get('stability_ok', False) else "❌"
        metric_parts.append(f"{status} **Static Stability Duration**: {sd:.2f}s / {ts:.2f}s")

    # 3. Mass Budget
    if 'structure_mass' in metrics and 'max_total_mass_limit' in metrics:
        sm = metrics['structure_mass']
        mml = metrics['max_total_mass_limit']
        status = "✅" if sm <= mml else "❌"
        metric_parts.append(f"{status} **Total Mass Utilization**: {sm:.2f} / {mml:.2f} units")

    # 4. Block Count
    if 'block_count' in metrics and 'max_block_count_limit' in metrics:
        bc = metrics['block_count']
        mcl = metrics['max_block_count_limit']
        status = "✅" if bc <= mcl else "❌"
        metric_parts.append(f"{status} **Block Utilization**: {bc} / {mcl} blocks")

    # 5. System State (Read-Only Diagnostics)
    if 'total_kinetic_energy' in metrics:
        metric_parts.append(f"**System Kinetic Energy**: {metrics['total_kinetic_energy']:.2e} J")
    
    if 'center_of_mass_x' in metrics:
        com_x = metrics['center_of_mass_x']
        metric_parts.append(f"**Calculated Center of Mass (x)**: {com_x:.2f}m")

    return metric_parts


def get_improvement_suggestions(metrics: Dict[str, Any], score: float, success: bool, 
                                failed: bool, failure_reason: str = None, 
                                error: str = None) -> List[str]:
    """
    Generate diagnostic feedback for S-06.
    Ensures zero spoilers and strict alignment with evaluator.py failure modes.
    """
    suggestions = []
    reason_lower = str(failure_reason).lower() if failure_reason else ""

    if failed:
        suggestions.append(f">> FAILURE MODE DETECTED: {failure_reason}")
        
        if "fell off table" in reason_lower:
            suggestions.append("-> Diagnostic: Equilibrium Failure. The assembly's aggregate center of mass has likely moved beyond the support boundary.")
        elif "ceiling" in reason_lower:
            suggestions.append("-> Diagnostic: Vertical Clearance Breach. The structure's height has exceeded the specified environmental boundary.")
        elif "maximum mass" in reason_lower:
            suggestions.append("-> Diagnostic: Resource Limit Violation. The total mass of all components has exceeded the allocated budget.")
        elif "design constraint" in reason_lower:
            suggestions.append("-> Diagnostic: Dimensional or Spatial Violation. One or more blocks do not comply with the initialization rules (dimensions, count, or spawn zone).")
        elif not metrics.get('stability_ok', True):
            suggestions.append("-> Diagnostic: Dynamic Instability. The structure maintains residual kinetic energy and fails to satisfy the static equilibrium duration.")
        elif not metrics.get('overhang_ok', True):
            suggestions.append("-> Diagnostic: Insufficient Longitudinal Reach. The structure is stable but the horizontal extension is below the required target.")

    return suggestions
