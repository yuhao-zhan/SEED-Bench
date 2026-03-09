"""
Task-specific feedback generation for Category 4: Granular/Fluid Interaction.
Provides process-aware, diagnostic feedback by analyzing physical mechanisms of failure.
"""
from typing import Dict, Any, List


def format_task_metrics(metrics: Dict[str, Any]) -> List[str]:
    """
    Format task-specific metrics for Granular/Fluid Interaction tasks.
    Groups metrics into Containment/Performance, Structural Integrity, and Process Dynamics.
    """
    metric_parts = []

    # 1. Containment & Task Performance
    metric_parts.append("### 1. Containment & Task Performance")
    # F-01/F-03/F-04 style (Particles)
    if "initial_particle_count" in metrics:
        init = metrics["initial_particle_count"]
        leaked = metrics.get("leaked_particle_count")
        in_hopper = metrics.get("particles_in_truck") or metrics.get("particles_in_hopper")
        
        if leaked is not None:
            metric_parts.append(f"- Particles Retained: {init - leaked:.0f} / {init} ({metrics.get('containment_percent', 0):.1f}%)")
            metric_parts.append(f"- Leakage Rate: {metrics.get('leakage_rate_percent', 0):.2f}% (Limit: {metrics.get('leakage_limit_percent', 'N/A')}%)")
        if in_hopper is not None:
            metric_parts.append(f"- Particles Relocated: {in_hopper} / {init} (Target: {metrics.get('min_particles_in_hopper', 'N/A')})")

    # F-02 style (Navigation)
    if "vehicle_front_x" in metrics:
        metric_parts.append(f"- Horizontal Progress: {metrics['vehicle_front_x']:.2f} m (Target: {metrics.get('target_x', 'N/A')} m)")
        if "progress" in metrics:
            metric_parts.append(f"- Completion: {metrics['progress']:.1f}%")
        if "vehicle_lowest_y" in metrics:
            metric_parts.append(f"- Lowest Elevation: {metrics['vehicle_lowest_y']:.2f} m (Sink Limit: -0.5 m)")

    # F-05 style (Boat/Cargo)
    if "cargo_retained" in metrics:
        metric_parts.append(f"- Cargo Secured: {metrics['cargo_retained']} / {metrics.get('initial_cargo_count', 'N/A')}")
        if "boat_angle_deg" in metrics:
            metric_parts.append(f"- Peak Tilt Angle: {metrics['boat_angle_deg']:.1f}° (Max: {metrics.get('boat_max_angle_deg', 'N/A')}°)")

    # 2. Structural Integrity & Design Constraints
    metric_parts.append("\n### 2. Structural Integrity & Design Constraints")
    if "structure_mass" in metrics:
        mass = metrics["structure_mass"]
        limit = metrics.get("max_structure_mass", float('inf'))
        metric_parts.append(f"- Total Structure Mass: {mass:.2f} kg / {limit:.2f} kg")
    if "structure_broken" in metrics:
        status = "CRITICAL FAILURE (Joints Snapped)" if metrics["structure_broken"] else "NOMINAL (Intact)"
        metric_parts.append(f"- Structural State: {status}")
    if "joint_count" in metrics:
        metric_parts.append(f"- Joint Complexity: {metrics['joint_count']} active connections")
    if "beam_count" in metrics:
        metric_parts.append(f"- Component Count: {metrics['beam_count']} beams")

    # 3. Process Kinematics & Environmental Interaction
    metric_parts.append("\n### 3. Process Kinematics & Environmental Interaction")
    if "velocity_x" in metrics or "speed" in metrics:
        vx = metrics.get("velocity_x", 0)
        vy = metrics.get("velocity_y", 0)
        speed = metrics.get("speed", (vx**2 + vy**2)**0.5)
        metric_parts.append(f"- Current Velocity: [{vx:.2f}, {vy:.2f}] m/s (Speed: {speed:.2f} m/s)")
    if "bucket_angle_deg" in metrics or "arm_joint_angle_deg" in metrics:
        metric_parts.append(f"- Actuator State: Bucket {metrics.get('bucket_angle_deg', 0):.1f}°, Arm {metrics.get('arm_joint_angle_deg', 0):.1f}°")
    if "step_count" in metrics:
        metric_parts.append(f"- Operational Duration: {metrics['step_count']} simulation steps")

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
    Generate actionable diagnostic warnings for Category 4 tasks.
    Focuses on identifying the physical root cause without dictating the engineering solution.
    """
    suggestions = []
    
    # 1. Design Constraint Violations (Fatal Errors)
    if error or (failure_reason and "design constraint" in failure_reason.lower()):
        reason = (error or failure_reason).lower()
        if "mass" in reason:
            limit = metrics.get("max_structure_mass", "the allowed")
            suggestions.append(f"Diagnostic: Structural mass exceeds the {limit} kg limit. Efficiency is low.")
            suggestions.append("- Analyze the strength-to-weight ratio; identify redundant components that contribute mass without supporting critical loads.")
        if "build zone" in reason:
            suggestions.append("Diagnostic: Geometric violation. Components are outside the permitted functional domain.")
            suggestions.append("- Ensure the spatial distribution of components aligns with defined build boundaries.")
        if "joint" in reason:
            suggestions.append("Diagnostic: Connectivity budget exceeded. The design is overly complex for the given joint limit.")
            suggestions.append("- Consider more efficient structural topologies that require fewer connections to maintain integrity.")
        if "anchor" in reason or "terrain" in reason:
            suggestions.append("Diagnostic: Illegal grounding. The environment forbids floor-based anchoring in this configuration.")
            suggestions.append("- Design for self-stability; the structure must rely on internal balance and weight distribution rather than external fixing.")
        if "dof" in reason or "revolute" in reason:
            suggestions.append("Diagnostic: Insufficient degrees of freedom. The mechanism lacks the required mobility for the task.")
            suggestions.append("- Verify the kinematics of the system; ensure enough articulated joints exist to perform complex trajectories.")

    # 2. Performance-Based Diagnostics (Physical Mechanisms)
    elif failed:
        reason = (failure_reason or "").lower()
        
        # A. Structural Failure (Dynamics/Statics)
        if metrics.get("structure_broken"):
            suggestions.append("Diagnostic: Structural integrity compromised under external load (Hydrostatic or Dynamic impact).")
            suggestions.append("- The structure failed due to local stress exceeding joint break thresholds. Analyze the load paths during surges or debris impact.")
            suggestions.append("- Consider the trade-off between structural rigidity and flexibility; stiff designs may snap where compliant ones survive.")

        # B. Containment Failure (Fluid/Granular)
        if "leakage" in reason or "deposited" in reason or "particles" in reason:
            leak_rate = metrics.get("leakage_rate_percent", 0)
            limit = metrics.get("leakage_limit_percent", 0)
            if leak_rate > limit:
                suggestions.append(f"Diagnostic: Containment failure. Material loss ({leak_rate:.2f}%) exceeds permissible threshold.")
                suggestions.append("- Analyze the 'seepage' points. Identify if gaps in the geometry or insufficient coverage allow granular flow.")
                suggestions.append("- Observe the interaction between material and boundaries; check if hydrostatic pressure is pushing particles over or under the structure.")
            else:
                suggestions.append("Diagnostic: Insufficient material relocation. The volume of transferred material is below mission requirements.")
                suggestions.append("- Evaluate the 'scoop' efficiency; check if material is spilling during transport due to gravity or momentum.")

        # C. Buoyancy & Stability (Fluids)
        if "sank" in reason or "lowest_y" in reason:
            suggestions.append("Diagnostic: Displacement failure. The vehicle's net buoyancy is insufficient to counter gravitational forces.")
            suggestions.append("- Analyze the relationship between displaced fluid volume and total mass. A more voluminous hull may be required to maintain elevation.")
        if "capsize" in reason or "angle" in reason:
            suggestions.append("Diagnostic: Stability failure. The center of mass (COM) and center of buoyancy (COB) are misaligned, causing a capsizing moment.")
            suggestions.append("- Consider lowering the center of gravity or widening the base of support to resist lateral environmental forces like wind or waves.")

        # D. Propulsion & Resistance (Fluids/Dynamics)
        if "reach" in reason or "progress" in reason:
            suggestions.append("Diagnostic: Propulsive deficit. Drag and opposing current forces exceed the system's thrust output.")
            suggestions.append("- Analyze the efficiency of propulsion strokes against the environmental resistance. Check if thrust timing or magnitude is suboptimal.")
            suggestions.append("- Observe obstacles in the environment; 'stalling' often occurs when kinetic energy is lost to collisions with pillars or terrain.")

    # 3. Sub-Optimal Success (Refinement)
    elif not success and score < 100:
        suggestions.append("Diagnostic: Operational efficiency is sub-optimal. The task was completed but near the failure margins.")
        if metrics.get("structure_mass", 0) > metrics.get("max_structure_mass", 0) * 0.9:
            suggestions.append("- Design is mass-heavy. Optimizing for a lighter structure may improve safety margins and mobility.")
        if metrics.get("leakage_rate_percent", 0) > 0:
            suggestions.append("- Trace residual seepage; minor geometric refinements could achieve 100% containment.")

    return suggestions
