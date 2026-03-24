"""
Task-specific feedback for C-03: The Seeker.
Uses evaluator metrics when present; falls back to environment defaults for activation-zone hints only.
"""
from typing import Dict, Any, List
import importlib.util
import math
import os

# Loaded via importlib from evaluation pipeline (not a package); load env from same dir.
_fb_dir = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "c03_environment", os.path.join(_fb_dir, "environment.py")
)
_c03_env = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_c03_env)
ACTIVATION_ZONE_X_MIN = _c03_env.ACTIVATION_ZONE_X_MIN
ACTIVATION_ZONE_X_MAX = _c03_env.ACTIVATION_ZONE_X_MAX
ACTIVATION_REQUIRED_STEPS = _c03_env.ACTIVATION_REQUIRED_STEPS
_spec_ev = importlib.util.spec_from_file_location(
    "c03_evaluator", os.path.join(_fb_dir, "evaluator.py")
)
_c03_ev = importlib.util.module_from_spec(_spec_ev)
_spec_ev.loader.exec_module(_c03_ev)
HEADING_REFERENCE_MIN_TARGET_SPEED = _c03_ev.HEADING_REFERENCE_MIN_TARGET_SPEED

def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """Format high-resolution physical metrics for C-03."""
    metric_parts = []
    
    # Interception Proximity
    if "distance_to_target" in metrics:
        metric_parts.append(f"**Target Proximity**: Range {metrics['distance_to_target']:.2f} m, Relative Speed {metrics.get('relative_speed', 0.0):.2f} m/s")
    
    if "heading_error_deg" in metrics:
        metric_parts.append(f"**Alignment Status**: Heading Error {metrics['heading_error_deg']:.2f}°")
    
    # Mission Progress & Resource
    metric_parts.append("\n**Mission Progression**")
    if "rendezvous_count" in metrics:
        metric_parts.append(f"- Captured Rendezvous Events: {metrics['rendezvous_count']}/2")
    if "activation_achieved" in metrics:
        metric_parts.append(f"- Seeker System Activation: {metrics['activation_achieved']}")
    if "remaining_impulse_budget" in metrics:
        metric_parts.append(f"- Propellant Reserve: {metrics['remaining_impulse_budget']:.1f} N·s propellant remaining")
    
    # Dynamic Limits
    metric_parts.append("\n**Capture Constraints**")
    if "rendezvous_distance" in metrics:
        metric_parts.append(f"- Max Capture Range: {metrics['rendezvous_distance']:.2f} m")
    if "rendezvous_rel_speed" in metrics:
        metric_parts.append(
            f"- Relative speed capture limit (must be <): {metrics['rendezvous_rel_speed']:.2f} m/s"
        )
    
    if metrics.get("failed") and metrics.get("failure_reason"):
        metric_parts.append(f"\n**Primary System Failure**: {metrics['failure_reason']}")
        
    return metric_parts

def get_improvement_suggestions(
    metrics: Dict[str, Any],
    score: float,
    success: bool,
    failed: bool,
    failure_reason: str = None,
    error: str = None,
) -> List[str]:
    """Generate diagnostic suggestions based on grounded physical failure modes."""
    suggestions = []
    
    if error:
        return [f"System Error: {error}. Check intercept and propellant APIs."]

    # Dynamic Variables
    d = metrics.get("distance_to_target", float('inf'))
    dv = metrics.get("relative_speed", float('inf'))
    limit_d = metrics.get("rendezvous_distance", 0.0)
    limit_dv = metrics.get("rendezvous_rel_speed", 0.0)
    rendezvous_count = metrics.get("rendezvous_count", 0)
    activation = metrics.get("activation_achieved", False)
    out_of_fuel = metrics.get("out_of_fuel", False)
    
    if not failed and not success:
        if rendezvous_count < 1:
            if not activation:
                suggestions.append(
                    "Priority: achieve activation (consecutive dwell in the activation zone) so rendezvous can count; "
                    "then intercept inside a phase-1 slot before that window ends."
                )
            else:
                suggestions.append(
                    "Activation is satisfied; satisfy rendezvous geometry (range, relative speed, heading) inside an "
                    "upcoming phase-1 slot before the phase-1 window closes."
                )
        elif rendezvous_count < 2:
            suggestions.append(
                "Complete a phase-2 rendezvous in-slot before the phase-2 window ends; keep matching velocity and heading."
            )

    if failed:
        # 1. Activation Root-Cause
        if not activation and "activation" in (failure_reason or "").lower():
            az_min = metrics.get("activation_zone_x_min", ACTIVATION_ZONE_X_MIN)
            az_max = metrics.get("activation_zone_x_max", ACTIVATION_ZONE_X_MAX)
            areq = int(metrics.get("activation_required_steps", ACTIVATION_REQUIRED_STEPS))
            suggestions.append(
                f"Seeker system failed to activate. Hold seeker x in "
                f"[{az_min:g}, {az_max:g}] m for "
                f"{areq} consecutive simulation steps before rendezvous can count."
            )
            
        # 2. Interception Dynamics (Docking Failure)
        if "rendezvous" in (failure_reason or "").lower():
            if d > limit_d:
                suggestions.append(
                    "Intercept proximity was outside the capture envelope. Account for target evasive motion "
                    "and unmodeled environmental effects in the corridor."
                )
            if dv >= limit_dv:
                suggestions.append(
                    "Relative docking speed is at or above the capture limit (evaluator requires strict <). "
                    "Use proactive braking so relative speed stays below the threshold."
                )
            if not metrics.get("heading_aligned", False):
                hr = float(
                    metrics.get("heading_reference_min_target_speed", HEADING_REFERENCE_MIN_TARGET_SPEED)
                )
                suggestions.append(
                    f"Orientation misaligned during capture. Align heading with target velocity when "
                    f"target speed ≥ {hr:g} m/s, else with seeker-to-target "
                    f"direction (thrust follows heading)."
                )

        # 3. Dynamic Boundary Failure
        if metrics.get("corridor_violation"):
            suggestions.append("Breach of the time-varying lateral corridor. Controller response may be too slow for the dynamic environmental constraints.")
            
        # 4. Resource & Propellant Efficiency
        if out_of_fuel:
            suggestions.append(
                "Propellant exhaustion. Reduce wasted thrust (cooldown cycles, corridor corrections); "
                "environment-specific forces and damping can change impulse cost—infer effective dynamics from motion."
            )
        
        # 5. Stability/Tracking Loss
        if "target lost" in (failure_reason or "").lower():
            suggestions.append("Post-capture tracking failure. The distance exceeded the track limit. Adjust pursuit gains to prevent target breakout.")

    return suggestions
