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
    base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]
) -> str:
    """Update task description when stage has visible changes."""
    description = base_description
    
    # Build zone changes
    target_bx = target_terrain_config.get("build_zone_x_max", 2.0)
    base_bx = base_terrain_config.get("build_zone_x_max", 2.0)
    target_by = target_terrain_config.get("build_zone_y_max", 5.0)
    base_by = base_terrain_config.get("build_zone_y_max", 5.0)
    
    if target_bx != base_bx or target_by != base_by:
        pattern = r"(- \*\*Build Zone\*\*: Mechanism must be built in x=\[)([^\]]+)(\], y=\[)([^\]]+)(\]\.)"
        replacement = f"\\g<1>-4.0, {target_bx}\\g<3>0.0, {target_by}\\g<5> (originally x=[-4.0, {base_bx}], y=[0.0, {base_by}] in the source environment)"
        description = re.sub(pattern, replacement, description)
        
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
        pattern = r"(1\. \*\*Material Transfer\*\*: At least )(\d+)( sand particles are deposited in the hopper \(x=-5.0, y=3.0\)\.)"
        criteria = re.sub(
            pattern,
            f"\\g<1>{target_count}\\g<3> (originally {base_count} particles in the source environment)",
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
- **Volumetric Capacity**: Hidden limits on how much material can be effectively retained and transported during each cycle of operation may be altered.
- **Build Zone**: The permitted construction volume (x and y bounds within which the mechanism must be built) may be adjusted.

**Discovery via feedback**: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., where a joint breaks or how a body moves) to infer the hidden constraints and adapt your design.
"""
    return [
        {
            "stage_id": "Stage-1",
            "title": "Slippery sand",
            "mutation_description": "Particle friction reduced significantly; sand slides off scoop almost immediately.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {
                "particles": {"friction": 0.05, "count": 200, "radius": 0.06, "density": 1500.0, "seed": 42},
                "min_particles_in_hopper": 75,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-2",
            "title": "Heavier world",
            "mutation_description": "Gravity increased; arm and scoop feel heavier, torque is insufficient to lift load.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {
                "min_particles_in_hopper": 17,
            },
            "physics_config": {"gravity": (0, -14.0)},
        },
        {
            "stage_id": "Stage-3",
            "title": "Dense atmosphere and slippery grains",
            "mutation_description": "Very high damping and near-zero friction; grains slide off quickly and mechanism is heavily sluggish.",
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
            "title": "Hostile excavation",
            "mutation_description": "Lower particle friction, stronger gravity, pit drift, higher target count, and limited scoop capacity per trip.",
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
