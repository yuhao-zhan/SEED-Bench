"""
Task-specific feedback generation for S-01: The Bridge
This module provides diagnostic feedback based on physical metrics to help the agent 
understand the root cause of failures in structural equilibrium and dynamic loading.
"""
from typing import Dict, Any, List
import math


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Format high-resolution physical metrics for S-01: The Bridge.
    Exposes raw physical states extracted from the evaluator.
    """
    metric_parts = []
    
    # 1. Kinematic & Spatial Progress
    if 'vehicle_x' in metrics and 'target_x' in metrics:
        vx = metrics['vehicle_x']
        tx = metrics['target_x']
        start_x = metrics.get('vehicle_start_x', 0.0)
        total_dist = tx - start_x
        progress = min(max(0, vx - start_x) / total_dist, 1.0) * 100.0 if total_dist > 0 else 0.0
        metric_parts.append(f"**Spatial State**: x={vx:.2f}m / Target: {tx:.2f}m ({progress:.1f}% Complete)")

    # 2. Structural Integrity & Resource Allocation
    if 'structure_mass' in metrics and 'max_structure_mass' in metrics:
        sm = metrics['structure_mass']
        msm = metrics['max_structure_mass']
        status = "✅" if sm <= msm else "❌"
        metric_parts.append(f"**Mass Budget**: {sm:.2f}kg / {msm:.0f}kg {status}")

    if 'joint_count' in metrics and 'initial_joint_count' in metrics:
        jc = metrics['joint_count']
        ijc = metrics['initial_joint_count']
        if ijc > 0:
            status = "✅" if jc == ijc else "⚠️"
            metric_parts.append(f"**Active Joints**: {jc} / {ijc} {status}")

    # 3. Dynamic Stress & Stability Indicators
    if 'max_vertical_accel' in metrics:
        mva = metrics['max_vertical_accel']
        limit = metrics.get('max_vertical_acceleration_limit', float('inf'))
        status = "✅" if mva <= limit else "❌"
        metric_parts.append(f"**Peak Vertical Acceleration**: {mva:.2f} m/s² (Limit: {limit:.2f}) {status}")

    if 'normalized_angle' in metrics:
        angle_deg = math.degrees(metrics['normalized_angle'])
        metric_parts.append(f"**Vehicle Attitude**: {angle_deg:.1f}°")

    if 'airborne_rotation_accumulated' in metrics and metrics.get('is_airborne', False):
        rot_deg = math.degrees(metrics['airborne_rotation_accumulated'])
        metric_parts.append(f"**Airborne Rotation**: {rot_deg:.1f}°")

    return metric_parts


def get_improvement_suggestions(metrics: Dict[str, Any], score: float, success: bool, 
                                failed: bool, failure_reason: str = None, 
                                error: str = None) -> List[str]:
    """
    Generate actionable diagnostic warnings for S-01.
    Strictly diagnostic without dictating mechanical design or API parameters.
    """
    suggestions = []
    reason_lower = str(failure_reason).lower() if failure_reason else ""
    
    if error:
        return [">> SYSTEM ERROR: Initialization failed. Check design constraints and mass budget."]

    if failed:
        suggestions.append(f">> FAILURE MODE: {failure_reason}")
        
        # 1. Structural vs Manifold Diagnostics
        if "integrity" in reason_lower or "joints broke" in reason_lower:
            suggestions.append("-> Diagnostic: Ultimate yield strength exceeded. The structure reached a critical stress state that its connections could not withstand under the current load path.")
        
        if "fell into water" in reason_lower:
            if not metrics.get('structure_broken', False):
                suggestions.append("-> Diagnostic: Support manifold discontinuity. The vehicle maintained structural support but exited the boundaries of the established path.")
            else:
                suggestions.append("-> Diagnostic: Support manifold collapse. The structural failure removed the vertical reaction force required to maintain elevation.")

        # 2. Dynamic Interaction Diagnostics
        if "vertical acceleration" in reason_lower:
            suggestions.append("-> Diagnostic: Impulsive shock loading. Severe vertical energy transfer indicates lack of surface continuity or high-gradient transitions on the deck.")
        
        if "rotated" in reason_lower or "flipped" in reason_lower or "unstable" in reason_lower:
            suggestions.append("-> Diagnostic: Rotational instability. The vehicle has acquired excess angular momentum or lost a level support plane, leading to uncontrolled pitch.")

        # 3. Constraint-Specific Diagnostics
        if "mass" in reason_lower:
            suggestions.append("-> Diagnostic: Gravitational overload. The current configuration exceeds the environmental mass threshold. Material distribution must be optimized.")

    elif not success and not failed:
        # Stall diagnostic using the specific metric provided by the evaluator
        stall_x = metrics.get('stall_threshold_x', 0.0)
        vx = metrics.get('vehicle_x', 0.0)
        if vx < stall_x and stall_x > 0:
            suggestions.append("-> Diagnostic: Traversal stall. Forward progress stopped before reaching the gap. Verify the continuity and friction of the starting support surface.")

    return suggestions
