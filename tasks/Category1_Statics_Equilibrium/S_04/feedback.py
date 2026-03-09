"""
Task-specific feedback generation for S-04: The Balance
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Format task-specific metrics for S-04: The Balance.
    Exposes angular equilibrium and torque balance.
    """
    metric_parts = []
    
    # 1. Equilibrium Duration
    if 'balance_duration' in metrics and 'target_balance_time' in metrics:
        bd = metrics['balance_duration']
        tb = metrics.get('target_balance_time', 15.0)
        status = "✅" if bd >= tb else "❌"
        metric_parts.append(f"{status} **Equilibrium Stability Duration**: {bd:.2f}s / {tb:.2f}s")

    # 2. Angular State
    if 'beam_angle_deg' in metrics:
        metric_parts.append(f"**Current System Angle**: {metrics['beam_angle_deg']:+.2f}°")
    if 'max_angle_seen_deg' in metrics:
        mad = metrics.get('max_angle_deviation_deg', 10.0)
        metric_parts.append(f"**Peak Angular Deviation**: {metrics['max_angle_seen_deg']:.2f}° (Limit: ±{mad:.1f}°)")

    # 3. Force & Torque
    if 'net_torque_about_pivot' in metrics:
        metric_parts.append(f"**Net Torque about Fulcrum**: {metrics['net_torque_about_pivot']:+.2f} N·m")

    # 4. Status Flags
    if 'load_caught' in metrics:
        status = "✅ ENGAGED" if metrics['load_caught'] else "❌ MISSED"
        metric_parts.append(f"**Payload Capture Status**: {status}")

    if 'structure_mass' in metrics:
        metric_parts.append(f"**Structure Mass**: {metrics['structure_mass']:.2f}kg")

    return metric_parts


def get_improvement_suggestions(metrics: Dict[str, Any], score: float, success: bool, 
                                failed: bool, failure_reason: str = None, 
                                error: str = None) -> List[str]:
    """
    Generate actionable diagnostic warnings for S-04.
    Diagnoses torque imbalances.
    """
    suggestions = []
    reason_lower = str(failure_reason).lower() if failure_reason else ""

    if error:
        suggestions.append(">> DIAGNOSTIC: Constraint violation.")
        return suggestions

    if failed:
        suggestions.append(f">> FAILURE MODE: {failure_reason}")
        
        if "angle" in reason_lower or "flipped" in reason_lower or "tipped" in reason_lower:
            suggestions.append("-> Diagnostic: Unbalanced moment detected. The clockwise and counter-clockwise torques around the pivot are not equalizing, causing the lever arm to rotate past its stability boundary.")
        elif "ground" in reason_lower or "fell to the ground" in reason_lower:
            suggestions.append("-> Diagnostic: Excessive angular excursion. The distal end of the lever arm breached the floor boundary due to unmitigated rotation.")

    return suggestions
