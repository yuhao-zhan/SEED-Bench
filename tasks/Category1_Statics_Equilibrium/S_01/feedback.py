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
    Exposes raw physical states to allow the agent to deduce environmental constraints.
    """
    metric_parts = []
    
    # 1. Kinematic & Spatial Progress
    if 'vehicle_x' in metrics and 'target_x' in metrics:
        vx = metrics['vehicle_x']
        tx = metrics['target_x']
        start_x = metrics.get('vehicle_start_x', 5.0)
        total_dist = tx - start_x
        progress = min(max(0, vx - start_x) / total_dist, 1.0) * 100.0 if total_dist > 0 else 0.0
        
        # Determine current phase based on vehicle position relative to the left cliff edge (x=10)
        phase = "PRE-GAP" if vx <= 10.0 else "TRANSIT"
        metric_parts.append(f"**Spatial State**: x={vx:.2f}m / {tx:.2f}m ({progress:.1f}% Complete, Phase: {phase})")

    # 2. Structural Integrity & Resource Allocation
    if 'structure_mass' in metrics and 'max_structure_mass' in metrics:
        sm = metrics['structure_mass']
        msm = metrics['max_structure_mass']
        mass_efficiency = (sm / msm) * 100.0 if msm > 0 else 0.0
        status = "✅" if sm <= msm else "❌ EXCEEDED"
        metric_parts.append(f"**Mass Budget**: {sm:.2f}kg / {msm:.0f}kg ({mass_efficiency:.1f}% utilized) {status}")

    if 'joint_count' in metrics and 'initial_joint_count' in metrics:
        jc = metrics['joint_count']
        ijc = metrics['initial_joint_count']
        if ijc > 0:
            integrity = (jc / ijc) * 100.0
            status = "✅" if jc == ijc else "⚠️ DEGRADED" if jc > 0 else "❌ COLLAPSED"
            metric_parts.append(f"**Structural Cohesion**: {jc}/{ijc} joints active ({integrity:.1f}%) {status}")

    # 3. Dynamic Stress & Stability Indicators
    if 'max_vertical_accel' in metrics:
        mva = metrics['max_vertical_accel']
        limit = metrics.get('max_vertical_acceleration_limit', 19.6)
        status = "✅" if mva <= limit else "❌ EXCESSIVE"
        metric_parts.append(f"**Peak Vertical Impulse**: {mva:.2f} m/s² (Threshold: {limit:.2f} m/s²) {status}")

    if 'angle' in metrics:
        # Use normalized angle if available for more accurate attitude reporting
        angle_rad = metrics.get('normalized_angle', metrics['angle'])
        angle_deg = math.degrees(angle_rad)
        metric_parts.append(f"**Vehicle Pitch**: {angle_deg:.1f}°")

    if 'airborne_rotation_accumulated' in metrics and metrics.get('is_airborne', False):
        rot_deg = math.degrees(metrics['airborne_rotation_accumulated'])
        metric_parts.append(f"**Airborne Angular Displacement**: {rot_deg:.1f}°")

    return metric_parts


def get_improvement_suggestions(metrics: Dict[str, Any], score: float, success: bool, 
                                failed: bool, failure_reason: str = None, 
                                error: str = None) -> List[str]:
    """
    Generate actionable diagnostic warnings for S-01.
    Analyzes the 'Root-Cause Chain' to distinguish between static and dynamic failure modes.
    """
    suggestions = []
    reason_lower = str(failure_reason).lower() if failure_reason else ""
    
    if error:
        suggestions.append(">> SYSTEM ERROR: Initialization failed.")
        if "mass" in str(error).lower():
            suggestions.append("-> Diagnostic: Structural mass exceeds the environmental threshold. Physics engine refused to instantiate.")
        return suggestions

    if failed:
        suggestions.append(f">> FAILURE MODE DETECTED: {failure_reason}")
        
        # 1. Phase-Based Root Cause Analysis
        vx = metrics.get('vehicle_x', 0.0)
        step_count = metrics.get('step_count', 0)
        
        # Static vs Dynamic failure
        if vx <= 10.0 and ("integrity" in reason_lower or "joints broke" in reason_lower):
            suggestions.append("-> Diagnostic: Static Equilibrium Failure. The structure failed under its own dead-load before the vehicle applied dynamic stress. This suggests insufficient joint resilience or an unstable geometric configuration.")
        elif vx > 10.0 and ("integrity" in reason_lower or "joints broke" in reason_lower):
            suggestions.append("-> Diagnostic: Dynamic Load Failure. The structure supported its own weight but reached ultimate yield strength under the combined mass of the vehicle. Load paths may be concentrating stress at critical nodes.")

        # 2. Specific Physical Violations
        if "vertical acceleration" in reason_lower:
            suggestions.append("-> Diagnostic: Impulsive Shock Loading. High-frequency vertical energy transfer suggests a lack of deck continuity or 'bumpy' transitions, leading to high-g impacts.")
        
        if "fell into water" in reason_lower:
            if not metrics.get('structure_broken', False):
                suggestions.append("-> Diagnostic: Manifold Discontinuity. The vehicle maintained elevation but exited the supporting geometry. Check for gaps or insufficient deck length.")
            else:
                suggestions.append("-> Diagnostic: Support Manifold Collapse. Catastrophic structural failure removed the vertical reaction force.")

        if "rotated" in reason_lower or "flipped" in reason_lower or "unstable" in reason_lower:
            suggestions.append("-> Diagnostic: Rotational Instability. The structure is imparting torque to the vehicle or lacks a level support plane, leading to uncontrolled angular momentum.")

        # 3. Resource/Mass Trade-off Paradox
        mass = metrics.get('structure_mass', 0)
        max_mass = metrics.get('max_structure_mass', float('inf'))
        if mass > max_mass:
            suggestions.append(f"-> Diagnostic: Mass Budget Violation. The current design ({mass:.1f}kg) exceeds the environmental limit ({max_mass:.1f}kg). Optimize material distribution.")
        elif mass < max_mass * 0.3 and ("integrity" in reason_lower or "joints broke" in reason_lower):
            suggestions.append("-> Diagnostic: Under-engineered load path. High mass margin remains; consider reinforcing critical stress zones to increase load capacity.")

    elif not success and not failed:
        # Stall diagnostic
        if metrics.get('velocity_x', 0) < 0.1:
            suggestions.append("-> Diagnostic: Traversal Stall. The vehicle has lost forward momentum. This often indicates a friction deficit or a 'step' in the deck geometry that the wheels cannot overcome.")

    return suggestions
