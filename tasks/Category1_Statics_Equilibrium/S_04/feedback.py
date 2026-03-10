"""
Task-specific feedback generation for S-04: The Balancer
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Format task-specific metrics for S-04: The Balancer.
    Exposes angular equilibrium and torque state.
    """
    metric_parts = []
    
    # 1. Equilibrium Duration
    if 'balance_duration' in metrics and 'target_balance_time' in metrics:
        bd = metrics['balance_duration']
        tb = metrics.get('target_balance_time', 15.0)
        status = "✅" if bd >= tb else "❌"
        metric_parts.append(f"{status} **Balance Duration**: {bd:.2f}s / {tb:.2f}s")

    # 2. Angular State
    if 'beam_angle_deg' in metrics:
        metric_parts.append(f"**Current Beam Angle**: {metrics['beam_angle_deg']:+.2f}°")
    if 'max_angle_seen_deg' in metrics:
        mad = metrics.get('max_angle_deviation_deg', 10.0)
        metric_parts.append(f"**Max Angle Recorded**: {metrics['max_angle_seen_deg']:.2f}° (Tolerance: ±{mad:.1f}°)")

    # 3. Torque Calculation
    if 'net_torque_about_pivot' in metrics:
        metric_parts.append(f"**Net Torque About Pivot**: {metrics['net_torque_about_pivot']:+.2f} N·m")

    # 4. Status Flags
    if 'load_caught' in metrics:
        status = "✅ ATTACHED" if metrics['load_caught'] else "❌ NOT CAUGHT"
        metric_parts.append(f"**Payload Status**: {status}")

    if 'structure_mass' in metrics:
        metric_parts.append(f"**Total Design Mass**: {metrics['structure_mass']:.2f} kg")

    return metric_parts


def get_improvement_suggestions(metrics: Dict[str, Any], score: float, success: bool, 
                                failed: bool, failure_reason: str = None, 
                                error: str = None) -> List[str]:
    """
    Generate actionable diagnostic warnings for S-04.
    Diagnoses torque imbalances and stability failures.
    """
    suggestions = []
    reason_lower = str(failure_reason).lower() if failure_reason else ""

    if error:
        suggestions.append(">> DIAGNOSTIC: Design constraint violation. Review build zone and primitive limits.")
        return suggestions

    if failed:
        suggestions.append(f">> FAILURE MODE: {failure_reason}")
        
        # Angle / Stability Diagnosis
        if "angle" in reason_lower or "tilt" in reason_lower:
            suggestions.append("-> Diagnostic: Static moment imbalance detected. The distribution of mass across the pivot is generating a net torque that overcomes the allowed angular tolerance.")
        
        # Ground / Fall Diagnosis
        elif "ground" in reason_lower or "fell" in reason_lower:
            suggestions.append("-> Diagnostic: Excessive rotation or structural failure caused a component to breach the lower boundary. Ensure the counterweight precisely offsets the payload's overturning moment.")
            
        # Catching Diagnosis
        elif "catch" in reason_lower:
            suggestions.append("-> Diagnostic: Payload engagement failure. The structure did not maintain proximity to the target coordinate (x=3.0) during the capture phase.")

    return suggestions
