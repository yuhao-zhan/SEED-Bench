import os

UNIFIED_FEEDBACK_CODE = '''"""
Task-specific feedback generation for Category 4: Granular/Fluid Interaction.
Provides process-aware, diagnostic feedback by analyzing physical mechanisms of failure.
Dynamic thresholds map to stages.py mutations.
"""
from typing import Dict, Any, List
import math


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Format task-specific metrics for Granular/Fluid Interaction tasks.
    Exposes high-resolution physical metrics without giving suggestions.
    """
    metric_parts = []

    # 1. Structural Integrity & System Constraints
    metric_parts.append("### 1. Structural Integrity & System Constraints")
    if "structure_mass" in metrics:
        mass = metrics["structure_mass"]
        limit = metrics.get("max_structure_mass", float('inf'))
        metric_parts.append(f"- Total Structure Mass: {mass:.2f} kg / Limit: {limit:.2f} kg")
    if "structure_broken" in metrics:
        status = "CRITICAL FAILURE (Joints Snapped)" if metrics["structure_broken"] else "NOMINAL (Intact)"
        metric_parts.append(f"- Structural State: {status}")
    if "joint_count" in metrics:
        metric_parts.append(f"- Joint Complexity: {metrics['joint_count']} active connections")
    if "beam_count" in metrics:
        metric_parts.append(f"- Component Count: {metrics['beam_count']} beams")

    # 2. Containment, Delivery & Task Performance
    metric_parts.append("\\n### 2. Containment, Delivery & Task Performance")
    # Particles/Fluids (F-01, F-03, F-04, F-06)
    if "initial_particle_count" in metrics:
        init = metrics["initial_particle_count"]
        leaked = metrics.get("leaked_particle_count")
        retained = metrics.get("retained_particle_count")
        in_target = metrics.get("particles_in_target") or metrics.get("particles_in_truck") or metrics.get("particles_in_hopper")
        
        if leaked is not None and retained is not None:
            metric_parts.append(f"- Particles Retained: {retained:.0f} / {init} ({metrics.get('containment_percent', 0):.1f}%)")
            metric_parts.append(f"- Leakage Rate: {metrics.get('leakage_rate_percent', 0):.2f}% (Limit: {metrics.get('leakage_limit_percent', 'N/A')}%)")
        if in_target is not None:
            metric_parts.append(f"- Particles Relocated/Delivered: {in_target} / {init} (Target: {metrics.get('min_particles_in_hopper', metrics.get('min_delivery_ratio_percent', 'N/A'))})")
    
    # Separation/Filter (F-04)
    if "purity_percent" in metrics:
        metric_parts.append(f"- Phase-Specific Segregation Purity: {metrics['purity_percent']:.1f}% (Limit: {metrics.get('min_purity_percent', 'N/A')}%)")
        correct = metrics.get('small_in_small_zone', 0) + metrics.get('medium_in_medium_zone', 0) + metrics.get('large_in_large_zone', 0)
        metric_parts.append(f"- Correctly Sorted Particles: {correct}")

    # Navigation/Progress (F-02)
    if "vehicle_front_x" in metrics:
        metric_parts.append(f"- Horizontal Progress: {metrics['vehicle_front_x']:.2f} m (Target: {metrics.get('target_x', 'N/A')} m)")
        if "progress" in metrics:
            metric_parts.append(f"- Completion: {metrics['progress']:.1f}%")

    # Cargo/Buoyancy (F-05)
    if "cargo_retained" in metrics:
        metric_parts.append(f"- Cargo Secured: {metrics['cargo_retained']} / {metrics.get('initial_cargo_count', 'N/A')}")
        if "boat_angle_deg" in metrics:
            metric_parts.append(f"- Peak Tilt Angle: {metrics['boat_angle_deg']:.1f}° (Limit: {metrics.get('boat_max_angle_deg', 'N/A')}°)")

    # 3. Process Kinematics, Dynamics & Environmental Interaction
    metric_parts.append("\\n### 3. Process Kinematics, Dynamics & Environmental Interaction")
    # Velocities
    vx = metrics.get("velocity_x")
    vy = metrics.get("velocity_y")
    speed = metrics.get("speed")
    if vx is not None and vy is not None:
        if speed is None:
            speed = (vx**2 + vy**2)**0.5
        metric_parts.append(f"- Kinematic State (Velocity): [{vx:.2f}, {vy:.2f}] m/s (Speed: {speed:.2f} m/s)")
    elif speed is not None:
        metric_parts.append(f"- Kinematic State (Speed): {speed:.2f} m/s")
    
    # Boundary Proximity / Elevation
    if "vehicle_lowest_y" in metrics:
        metric_parts.append(f"- Lowest Boundary Proximity: {metrics['vehicle_lowest_y']:.2f} m")
    if "particle_mean_y" in metrics:
        metric_parts.append(f"- Particle Mass Centroid Elevation: {metrics['particle_mean_y']:.2f} m")
    
    # Actuators
    if "bucket_angle_deg" in metrics or "arm_joint_angle_deg" in metrics:
        metric_parts.append(f"- Actuator State: Bucket {metrics.get('bucket_angle_deg', 0):.1f}°, Arm {metrics.get('arm_joint_angle_deg', 0):.1f}°")
    
    if "step_count" in metrics:
        metric_parts.append(f"- Operational Duration: {metrics['step_count']} simulation steps")

    # Collect any other unformatted metrics that might be uniquely added
    known_keys = {"structure_mass", "max_structure_mass", "structure_broken", "joint_count", "beam_count",
                  "initial_particle_count", "leaked_particle_count", "retained_particle_count", "particles_in_target",
                  "particles_in_truck", "particles_in_hopper", "containment_percent", "leakage_rate_percent",
                  "leakage_limit_percent", "min_particles_in_hopper", "min_delivery_ratio_percent", "purity_percent",
                  "min_purity_percent", "small_in_small_zone", "medium_in_medium_zone", "large_in_large_zone",
                  "vehicle_front_x", "target_x", "progress", "cargo_retained", "initial_cargo_count", "boat_angle_deg",
                  "boat_max_angle_deg", "velocity_x", "velocity_y", "speed", "vehicle_lowest_y", "particle_mean_y",
                  "bucket_angle_deg", "arm_joint_angle_deg", "step_count", "success", "failed", "failure_reason",
                  "particle_mean_x", "particle_active_count", "delivery_ratio_percent"}
    other = {k: v for k, v in metrics.items() if k not in known_keys}
    if other:
        metric_parts.append("\\n### 4. Advanced Domain Metrics")
        for k, v in other.items():
            if isinstance(v, float):
                metric_parts.append(f"- {k}: {v:.3f}")
            else:
                metric_parts.append(f"- {k}: {v}")

    return metric_parts


def get_improvement_suggestions(
    metrics: Dict[str, Any],
    score: float,
    success: bool,
    failed: bool,
    failure_reason: str = None,
    error: str = None,
) -> List[str]:
    """
    Generate actionable diagnostic warnings without dictating the answer.
    Checks for Root-Cause Chains, Multi-Objective Paradoxes, and Numerical Instability.
    Dynamic thresholds are used to ensure adaptability across mutated stages.
    """
    suggestions = []
    
    reason = ((error or "") + " " + (failure_reason or "")).lower()

    # 0. Physics Engine Limits & Numerical Instability
    vx = metrics.get("velocity_x", 0)
    vy = metrics.get("velocity_y", 0)
    speed = metrics.get("speed", 0)
    if speed == 0 and (vx != 0 or vy != 0):
        speed = (vx**2 + vy**2)**0.5
    
    if math.isnan(speed) or speed > 1000:
        suggestions.append("Diagnostic: Numerical instability detected. The physics engine produced impossible velocity spikes (NaN or >1000 m/s).")
        suggestions.append("- Root Cause: Likely caused by inter-penetrating bodies, extreme spring constants, or an over-constrained mechanism.")
        return suggestions  # Immediate return on engine explosion

    # 1. Multi-Objective Trade-off Paradox
    mass = metrics.get("structure_mass", 0)
    max_mass = metrics.get("max_structure_mass", float('inf'))
    
    # E.g., great performance but violated mass limit
    if mass > max_mass:
        if (metrics.get("containment_percent", 0) == 100 or 
            metrics.get("purity_percent", 0) > 90 or 
            metrics.get("progress", 0) > 90 or
            metrics.get("cargo_retained", -1) == metrics.get("initial_cargo_count", 0)):
            suggestions.append(f"Diagnostic (Multi-Objective Paradox): The system achieved its primary physical goal, but violated the systemic mass budget ({mass:.2f} > {max_mass:.2f} kg).")
            suggestions.append("- The structure is over-engineered. Optimize the strength-to-weight ratio to maintain functionality while shedding redundant dead-weight.")
        else:
            suggestions.append(f"Diagnostic: Structural mass exceeds the permitted dynamic boundary ({max_mass:.2f} kg limit).")
            suggestions.append("- Analyze load distribution and eliminate unnecessary components that do not contribute to the critical load path.")

    # 2. Root-Cause Chain Identification
    if metrics.get("structure_broken"):
        if speed > 15:
            suggestions.append("Diagnostic (Root-Cause Chain): Structural integrity compromised due to high-velocity dynamic impact.")
            suggestions.append("- A joint snapped upon collision. The kinetic energy exceeded the elastic limit of the connections.")
        elif mass > max_mass * 0.8:
            suggestions.append("Diagnostic (Root-Cause Chain): Structural integrity compromised likely due to excessive self-weight (dead-load) or severe hydrostatic pressure.")
            suggestions.append("- Internal forces from gravity or static fluid pressure exceeded the yield strength of the joints. Re-evaluate support pillars and span lengths.")
        else:
            suggestions.append("Diagnostic: Structural integrity compromised under environmental load.")
            suggestions.append("- The mechanism failed due to local stress concentrations. Analyze stress distribution during peak loads.")

    # 3. Domain-Specific Physical Mechanisms
    if "leakage" in reason or "deposited" in reason or "particles" in reason or "delivery" in reason:
        leak_rate = metrics.get("leakage_rate_percent", 0)
        limit = metrics.get("leakage_limit_percent", 0)
        
        if "delivery" in reason or metrics.get("delivery_ratio_percent") is not None:
            target_pct = metrics.get("min_delivery_ratio_percent", 90.0)
            if metrics.get("delivery_ratio_percent", 0) < target_pct:
                suggestions.append(f"Diagnostic: Fluid/Granular momentum transfer insufficient. Delivery efficiency is below the required threshold ({target_pct}%).")
                suggestions.append("- Analyze the kinetic flow path. Identify points where momentum is lost to friction, gravity wells, or adverse aerodynamic forces (headwinds).")
        
        elif leak_rate > limit:
            suggestions.append(f"Diagnostic: Hydrostatic/Granular containment failure. Material loss ({leak_rate:.2f}%) exceeds the dynamic permissible limit.")
            suggestions.append("- Observe the fluid-structure interaction. Check if hydrostatic pressure causes deformation that opens seepage paths, or if geometric coverage is incomplete.")
        else:
            suggestions.append("Diagnostic: Insufficient material relocation or segregation.")
            suggestions.append("- Evaluate the kinematic efficiency of the scooping or sorting mechanism. Momentum transfer to the granular medium is suboptimal.")

    if "purity" in reason or "contaminated" in reason:
        suggestions.append("Diagnostic: Phase-specific segregation failure. Particulate cross-contamination detected.")
        suggestions.append("- Analyze the spatial filtration apertures. The geometric sieve dimensions do not correspond to the target phase dimensions.")

    if "sank" in reason or "lowest_y" in reason or "water" in reason:
        if metrics.get("cargo_in_water", 0) > 0:
            suggestions.append("Diagnostic: Displacement or retention failure. Cargo lost to the fluid environment.")
            suggestions.append("- Check if high acceleration or extreme tilt angles caused the cargo to slide off. Consider friction and boundary constraints.")
        else:
            suggestions.append("Diagnostic: Displacement deficit. The net buoyant force is insufficient to counteract the gravitational vector of the system.")
            suggestions.append("- Re-calculate Archimedes\' principle for the current hull volume versus total mass. A larger displacement volume is necessary.")

    if "capsize" in reason or "angle" in reason:
        max_angle = metrics.get("boat_max_angle_deg", 18)
        suggestions.append(f"Diagnostic: Stability failure. Roll angle exceeded the critical threshold ({max_angle}°).")
        suggestions.append("- The center of mass (COM) and center of buoyancy (COB) are misaligned under load, creating a destructive capsizing moment. Lower the COM.")

    if "reach" in reason or "progress" in reason:
        suggestions.append("Diagnostic: Kinematic/Propulsive deficit. The net forward thrust is overcome by fluid drag and adverse environmental currents.")
        suggestions.append("- Analyze the propulsive strokes. Ensure that cyclic force application synchronizes with momentum conservation to overcome drag.")
        suggestions.append("- Investigate potential geometric collisions with environmental obstacles that sap kinetic energy.")

    # 4. General Design Constraints
    if "build zone" in reason:
        suggestions.append("Diagnostic: Geometric violation. The structural topology extends beyond the active dynamic boundaries.")
        suggestions.append("- Restrict component placement to the valid coordinate envelope to maintain physical consistency.")
    if "anchor" in reason or "terrain" in reason:
        suggestions.append("Diagnostic: Invalid boundary conditions. The structure relies on disallowed external fixed supports.")
        suggestions.append("- The design must be self-stabilizing through internal force equilibrium rather than external grounding.")
    if "joint" in reason or "dof" in reason:
        suggestions.append("Diagnostic: Topology constraint violation. The system either lacks required mobility (DOF) or exceeds the allowed topological complexity.")
        suggestions.append("- Optimize the linkage network to achieve the desired kinematics with the minimum required revolute/fixed connections.")

    return suggestions
'''

for i in range(1, 7):
    folder = f'tasks/Category4_Granular_FluidInteraction/F_0{i}'
    feedback_file = os.path.join(folder, 'feedback.py')
    if os.path.exists(feedback_file):
        with open(feedback_file, 'w') as f:
            f.write(UNIFIED_FEEDBACK_CODE)
        print(f"Updated {feedback_file}")

