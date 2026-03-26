"""
F-03: The Excavator — curriculum stages (mutations).

Mutated tasks vary physical parameters: particle friction, gravity, damping,
pit drift, target count, scoop capacity. Invisible changes are not revealed in
the prompt; the solver must infer from feedback. Visible changes (e.g. stricter
target count) are stated in task_description_suffix.
Stage-1/2: single parameter change each. Stage-3/4: multiple parameter changes.
Ordered by difficulty ascending.
"""
from __future__ import annotations

from typing import Any, Dict, List
import re


def update_task_description_for_visible_changes(
    base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any],
    target_physics_config: Dict[str, Any] = None, base_physics_config: Dict[str, Any] = None
) -> str:
    """Update task description when stage has visible changes."""
    description = base_description
    target_physics_config = target_physics_config or {}
    base_physics_config = base_physics_config or {}
    
    # Build zone changes
    target_bx = target_terrain_config.get("build_zone_x_max", 2.0)
    base_bx = base_terrain_config.get("build_zone_x_max", 2.0)
    target_by = target_terrain_config.get("build_zone_y_max", 5.0)
    base_by = base_terrain_config.get("build_zone_y_max", 5.0)
    
    # Defaults for mins
    target_xmin = target_terrain_config.get("build_zone_x_min", -4.0)
    base_xmin = base_terrain_config.get("build_zone_x_min", -4.0)
    target_ymin = target_terrain_config.get("build_zone_y_min", 0.0)
    base_ymin = base_terrain_config.get("build_zone_y_min", 0.0)

    if target_bx != base_bx or target_by != base_by or target_xmin != base_xmin or target_ymin != base_ymin:
        # Capture trailing base sentence so it is preserved (not deleted)
        pattern = r"(- \*\*Build Zone\*\*: Mechanism must be built in x=\[)([^\]]+)(\], y=\[)([^\]]+)(\]\. )(Base is anchored at x=.*?, y=.*? \(evaluator accepts any body within 0\.5 m of this position\)\.)"
        replacement = f"\\g<1>{target_xmin}, {target_bx}\\g<3>{target_ymin}, {target_by}] (originally x=[{base_xmin}, {base_bx}], y=[{base_ymin}, {base_by}] in the source environment). \\g<6>"
        description = re.sub(pattern, replacement, description)

    # Mass Budget (visible when mutated)
    target_mass = float(target_terrain_config.get("max_structure_mass", 800.0))
    base_mass = float(base_terrain_config.get("max_structure_mass", 800.0))
    if target_mass != base_mass:
        mass_pattern = r"(- \*\*Mass Budget\*\*: Total structure mass <= )([\d.]+)( kg\.)"
        if re.search(mass_pattern, description):
            description = re.sub(
                mass_pattern,
                f"\\g<1>{target_mass:.1f} kg (originally {base_mass:.1f} kg in the source environment).",
                description,
            )

    # Per-scoop capacity (visible when mutated)
    default_scoop_capacity = 999
    target_scoop = int(target_terrain_config.get("scoop_capacity", default_scoop_capacity))
    base_scoop = int(base_terrain_config.get("scoop_capacity", default_scoop_capacity))
    if target_scoop != base_scoop:
        scoop_pattern = r"(- \*\*Per-scoop capacity\*\*: Maximum particles carried per scoop per trip: )(\d+)(.*?in the source environment \(effectively unlimited\)\.)"
        if re.search(scoop_pattern, description):
            description = re.sub(
                scoop_pattern,
                f"\\g<1>{target_scoop} (originally {base_scoop} in the source environment).",
                description,
            )

    # Scoop Mechanics (visible when mutated)
    target_margin = float(target_terrain_config.get("carry_margin", 2.0))
    base_margin = float(base_terrain_config.get("carry_margin", 2.0))
    target_angle = float(target_terrain_config.get("dump_angle_threshold", 0.6))
    base_angle = float(base_terrain_config.get("dump_angle_threshold", 0.6))
    
    if target_margin != base_margin or target_angle != base_angle:
        # Match the Scoop Mechanics line and update values while preserving sentence structure
        mech_pattern = r"(- \*\*Scoop Mechanics\*\*:.*?capture and \"carry\" particles within a )([\d.]+) m( margin.*?not tilted beyond )([\d.]+) radians(?: \([~\d.]+[°deg]+\))?(\. Captured particles are released ONLY when the scoop is over the target hopper and its rotation angle exceeds )([\d.]+) (radians\.)"
        if re.search(mech_pattern, description):
            description = re.sub(
                mech_pattern,
                f"\\g<1>{target_margin} m (originally {base_margin} m in the source environment)\\g<3>{target_angle} radians (originally {base_angle} radians in the source environment)\\g<5>{target_angle} radians (originally {base_angle} radians in the source environment).",
                description
            )

    # Joint Strength (visible when mutated)
    target_force = target_physics_config.get("joint_max_force", float("inf"))
    target_joint_torque = target_physics_config.get("joint_max_torque", float("inf"))
    base_force = base_physics_config.get("joint_max_force", float("inf"))
    base_joint_torque = base_physics_config.get("joint_max_torque", float("inf"))

    if (target_force != base_force and target_force < float("inf")) or \
       (target_joint_torque != base_joint_torque and target_joint_torque < float("inf")):
        pattern = r"(- \*\*Joint Strength\*\*: Joints are )(unbreakable)(.*?in the source environment.*?infinite\)\.)"
        
        limit_parts = []
        if target_force < float("inf"):
            limit_parts.append(f"force exceeds {target_force:.1f}")
        if target_joint_torque < float("inf"):
            limit_parts.append(f"torque exceeds {target_joint_torque:.1f}")
        
        new_val = "subject to failure if " + " or ".join(limit_parts)
        replacement = f"\\g<1>{new_val} (originally unbreakable in the source environment)."
        if re.search(pattern, description):
            description = re.sub(pattern, replacement, description)

    # Time Limit (visible when mutated)
    target_time = float(target_terrain_config.get("max_time_seconds", 40.0))
    base_time = float(base_terrain_config.get("max_time_seconds", 40.0))
    if target_time != base_time:
        time_pattern = r"(- \*\*Time Limit\*\*: Complete the task within )(\d+)( seconds\.)"
        if re.search(time_pattern, description):
            description = re.sub(
                time_pattern,
                f"\\g<1>{target_time:.0f} (originally {base_time:.0f} in the source environment) seconds.",
                description,
            )

    # Motor Torque (visible when mutated)
    target_motor_torque = float(target_physics_config.get("max_motor_torque", 100.0))
    base_motor_torque = float(base_physics_config.get("max_motor_torque", 100.0))
    if target_motor_torque != base_motor_torque:
        torque_pattern = r"(- \*\*Motor Torque\*\*: Maximum motor torque for revolute joints is )([\d.]+)( N·m\.)"
        if re.search(torque_pattern, description):
            description = re.sub(
                torque_pattern,
                f"\\g<1>{target_motor_torque:.1f} N·m (originally {base_motor_torque:.1f} N·m in the source environment).",
                description,
            )

    # Obstacle (visible when removed)
    target_wall = target_terrain_config.get("central_wall", True)
    if not target_wall:
        wall_pattern = r"(- \*\*Obstacle\*\*:.*?)(A central wall at x=-1\.0 m.*?has_central_wall\(\).*?\.)"
        description = re.sub(wall_pattern, "- **Obstacle**: None (originally A central wall at x=-1.0 m (y=[0.5, 1.5] m, width=0.24 m) in the source environment).", description)

    # Material / Particle Count (visible when mutated)
    pit_config_target = target_terrain_config.get("particles", {})
    pit_config_base = base_terrain_config.get("particles", {})
    target_count = int(pit_config_target.get("count", 200))
    base_count = int(pit_config_base.get("count", 200))
    if target_count != base_count:
        count_pattern = r"(- \*\*Material\*\*: )(\d+)( sand particles in a pit)"
        if re.search(count_pattern, description):
            description = re.sub(
                count_pattern,
                f"\\g<1>{target_count} (originally {base_count} in the source environment)\\g<3>",
                description,
            )

    # Particle Properties (radius and density)
    target_radius = float(pit_config_target.get("radius", 0.06))
    base_radius = float(pit_config_base.get("radius", 0.06))
    if target_radius != base_radius:
        radius_pattern = r"(- \*\*Particle Properties\*\*: Each particle has a radius of )([\d.]+)( m)"
        if re.search(radius_pattern, description):
            description = re.sub(
                radius_pattern,
                f"\\g<1>{target_radius} (originally {base_radius} in the source environment) m",
                description,
            )

    target_density = float(pit_config_target.get("density", 1500.0))
    base_density = float(pit_config_base.get("density", 1500.0))
    if target_density != base_density:
        density_pattern = r"( and a material density of )([\d.]+)( kg/m³\.)"
        if re.search(density_pattern, description):
            description = re.sub(
                density_pattern,
                f"\\g<1>{target_density} (originally {base_density} in the source environment) kg/m³.",
                description,
            )

    # Pit Drift (INVISIBLE variable - NO VALUE REVEALED)
    # The presence of pit drift is already mentioned as a possibility in the task description
    # and its change is warned in the UNIFORM_SUFFIX. We do not reveal exact values here.

    # Target Hopper zone (visible when mutated)
    hvx_min = float(target_terrain_config.get("hopper_valid_x_min", -6.0))
    hvx_max = float(target_terrain_config.get("hopper_valid_x_max", -4.0))
    hvy_min = float(target_terrain_config.get("hopper_valid_y_min", 0.5))
    hvy_max = float(target_terrain_config.get("hopper_valid_y_max", 5.0))
    
    bvx_min = float(base_terrain_config.get("hopper_valid_x_min", -6.0))
    bvx_max = float(base_terrain_config.get("hopper_valid_x_max", -4.0))
    bvy_min = float(base_terrain_config.get("hopper_valid_y_min", 0.5))
    bvy_max = float(base_terrain_config.get("hopper_valid_y_max", 5.0))
    
    if (hvx_min != bvx_min or hvx_max != bvx_max or hvy_min != bvy_min or hvy_max != bvy_max):
        hopper_pattern = r"(Particles count as deposited.*?hopper zone x=\[)([^\]]+)(\] m, y=\[)([^\]]+)(\] m\.)"
        description = re.sub(
            hopper_pattern,
            f"\\g<1>{hvx_min}, {hvx_max}\\g<3>{hvy_min}, {hvy_max}] (originally x=[{bvx_min}, {bvx_max}], y=[{bvy_min}, {bvy_max}] in the source environment) m.",
            description
        )

    return description


def update_success_criteria_for_visible_changes(
    base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]
) -> str:
    """Update success criteria when stage has visible changes."""
    criteria = base_success_criteria
    
    # Target particle count
    target_count = target_terrain_config.get("min_particles_in_hopper", 15) # Default 15
    base_count = base_terrain_config.get("min_particles_in_hopper", 15)
    
    if target_count != base_count:
        pattern = r"(1\. \*\*Material Transfer\*\*: At least )(\d+)( sand particles are deposited in the hopper zone \(x=\[.*?\] m, y=\[.*?\] m; center at x=.*?, y=.*?\)\.)"
        criteria = re.sub(
            pattern,
            f"\\g<1>{target_count} (originally {base_count} in the source environment)\\g<3>",
            criteria
        )
    
    # Hopper zone bounds in success criteria
    hvx_min = float(target_terrain_config.get("hopper_valid_x_min", -6.0))
    hvx_max = float(target_terrain_config.get("hopper_valid_x_max", -4.0))
    hvy_min = float(target_terrain_config.get("hopper_valid_y_min", 0.5))
    hvy_max = float(target_terrain_config.get("hopper_valid_y_max", 5.0))
    
    bvx_min = float(base_terrain_config.get("hopper_valid_x_min", -6.0))
    bvx_max = float(base_terrain_config.get("hopper_valid_x_max", -4.0))
    bvy_min = float(base_terrain_config.get("hopper_valid_y_min", 0.5))
    bvy_max = float(base_terrain_config.get("hopper_valid_y_max", 5.0))
    
    if (hvx_min != bvx_min or hvx_max != bvx_max or hvy_min != bvy_min or hvy_max != bvy_max):
        # Update both the x and y ranges in the success criteria string
        pattern = r"(deposited in the hopper zone \(x=\[)([^\]]+)(\] m, y=\[)([^\]]+)(\] m; center at x=.*?, y=.*?\)\.)"
        criteria = re.sub(
            pattern,
            f"\\g<1>{hvx_min}, {hvx_max}\\g<3>{hvy_min}, {hvy_max}] (originally x=[{bvx_min}, {bvx_max}], y=[{bvy_min}, {bvy_max}] in the source environment) m; center at x=-5.0, y=3.0).",
            criteria
        )
        
    return criteria


def get_f03_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns ordered stage configs for F-03: The Excavator (difficulty ascending).
    Each stage: stage_id, title, mutation_description, task_description_suffix,
    terrain_config, physics_config. Original reference solution should fail in all mutated stages.
    """
    task_description_suffix = """
## Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables **MIGHT** have changed from the initial environment, **NOT ALL** of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
- **Particle Friction**: The surface traction between individual grains may be altered, affecting how easily material slides or piles within the scoop.
- **Gravity**: The acceleration due to the local gravitational field may vary, influencing the weight of the mechanism and the stability of the granular load.
- **Ambient Damping**: The rate at which mechanical motion and material flow are resisted by the environment may have changed.
- **Transfer Requirement**: The minimum quantity of material that must be successfully relocated to the target zone for mission success may be adjusted.
- **Internal Pit Drift**: Persistent lateral forces acting within the excavation zone may vary, potentially shifting material or resisting scoop entry.
- **Volumetric Capacity**: Limits on how much material can be effectively retained and transported during each cycle of operation may be altered.
- **Build Zone**: The permitted construction volume (x and y bounds within which the mechanism must be built) may be adjusted.

**Discovery via feedback**: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., where a joint breaks or how a body moves) to infer the hidden constraints and adapt your design.
"""
    return [
        {
            "stage_id": "Stage-1",
            "title": "Frictional Anomaly",
            "mutation_description": "Particle friction altered; sand behavior changed. Transfer requirement increased (75 particles).",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {
                "particles": {"friction": 0.05, "count": 200, "radius": 0.06, "density": 1500.0, "seed": 42},
                "min_particles_in_hopper": 75,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-2",
            "title": "Gravitational Anomaly",
            "mutation_description": "Gravity altered; load handling affected. Transfer requirement slightly increased (17 particles).",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {
                "min_particles_in_hopper": 17,
            },
            "physics_config": {"gravity": (0, -14.0)},
        },
        {
            "stage_id": "Stage-3",
            "title": "Multi-variable Physical Anomaly",
            "mutation_description": "Physical damping and friction anomalies; mechanism response and grain stability changed. Transfer requirement increased (20 particles) and build zone expanded (x_max=5.0).",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {
                "particles": {"friction": 0.002, "count": 200, "radius": 0.06, "density": 1500.0, "seed": 42},
                "min_particles_in_hopper": 20,
                "build_zone_x_max": 5.0,
            },
            "physics_config": {
                "linear_damping": 0.72,
                "angular_damping": 0.72,
            },
        },
        {
            "stage_id": "Stage-4",
            "title": "Hostile Excavation",
            "mutation_description": "Composite physical anomaly (friction, gravity, drift) with capacity constraints. Transfer requirement lowered (4 particles) but build zone expanded (x_max=6.0, y_max=6.0).",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {
                "particles": {"friction": 0.1, "count": 200, "radius": 0.06, "density": 1500.0, "seed": 42},
                "min_particles_in_hopper": 4,
                "pit_drift_force": 0.5,
                "scoop_capacity": 28,
                "build_zone_x_max": 6.0,
                "build_zone_y_max": 6.0,
            },
            "physics_config": {
                "gravity": (0, -15.0),
            },
        },
    ]
