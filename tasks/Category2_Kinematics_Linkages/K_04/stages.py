"""
K-04: The Pusher task curriculum stages (mutations).

All stage definitions live under tasks/Category2_Kinematics_Linkages/K_04 as requested.
The solver agent is NOT told the exact parameter changes; it must infer from feedback.
"""

from __future__ import annotations

from typing import Any, Dict, List
import re

def update_task_description_for_visible_changes(base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """
    Update task description to reflect visible physical changes.
    """
    description = base_description
    
    # Update Target x position (visible)
    target_dist = target_terrain_config.get("target_distance", 10.0)
    base_dist = base_terrain_config.get("target_distance", 10.0)
    if target_dist != base_dist:
        # Match "- **Target**: Push the object to at least x=18.0m"
        target_pattern = r"(- \*\*Target\*\*: Push the object to at least x=)(\d+\.?\d*)(m)"
        if re.search(target_pattern, description):
            description = re.sub(
                target_pattern,
                f"\\g<1>{8.0 + target_dist:.1f}\\g<3> (originally x={8.0 + base_dist:.1f}m in the source environment)",
                description
            )
            
    # Update Build Zone (if changed)
    target_bz = target_terrain_config.get("build_zone", {})
    base_bz = base_terrain_config.get("build_zone", {})
    target_x = target_bz.get("x", [0.0, 15.0])
    target_y = target_bz.get("y", [1.5, 8.0])
    base_x = base_bz.get("x", [0.0, 15.0])
    base_y = base_bz.get("y", [1.5, 8.0])
    if (target_x != base_x or target_y != base_y) and isinstance(target_x, (list, tuple)) and isinstance(target_y, (list, tuple)):
        x_min_t, x_max_t = float(target_x[0]), float(target_x[1])
        y_min_t, y_max_t = float(target_y[0]), float(target_y[1])
        x_min_b, x_max_b = float(base_x[0]), float(base_x[1])
        y_min_b, y_max_b = float(base_y[0]), float(base_y[1])
        bz_desc_pattern = r"(- \*\*Build Zone\*\*: x=\[)(\d+\.?\d*),\s*(\d+\.?\d*)(\], y=\[)(\d+\.?\d*),\s*(\d+\.?\d*)(\].)"
        if re.search(bz_desc_pattern, description):
            description = re.sub(
                bz_desc_pattern,
                lambda m: (
                    f"{m.group(1)}{x_min_t:.1f}, {x_max_t:.1f}{m.group(4)}{y_min_t:.1f}, {y_max_t:.1f}{m.group(8)} "
                    f"(originally x=[{x_min_b:.1f}, {x_max_b:.1f}], y=[{y_min_b:.1f}, {y_max_b:.1f}] in the source environment)."
                ),
                description
            )
        bz_constraint_pattern = r"(All components must stay within x=\[)(\d+\.?\d*),\s*(\d+\.?\d*)(\], y=\[)(\d+\.?\d*),\s*(\d+\.?\d*)(\].)"
        if re.search(bz_constraint_pattern, description):
            description = re.sub(
                bz_constraint_pattern,
                f"\\g<1>{x_min_t:.1f}, {x_max_t:.1f}\\g<4>{y_min_t:.1f}, {y_max_t:.1f}\\g<8> (originally x=[{x_min_b:.1f}, {x_max_b:.1f}], y=[{y_min_b:.1f}, {y_max_b:.1f}] in the source environment).",
                description
            )

    # Update Mass Budget (if changed)
    target_mass = target_terrain_config.get("max_structure_mass", 40.0)
    base_mass = base_terrain_config.get("max_structure_mass", 40.0)
    if target_mass != base_mass:
        mass_pattern = r"(- \*\*Mass Budget\*\*: Total structure mass must be less than )(\d+\.?\d*)( kg\.)"
        if re.search(mass_pattern, description):
            description = re.sub(
                mass_pattern,
                f"\\g<1>{target_mass:.0f} kg (originally {base_mass:.0f} kg in the source environment).",
                description
            )
            
    return description

def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """
    Update success criteria to reflect visible physical changes.
    """
    criteria = base_success_criteria
    
    # Target distance
    target_dist = target_terrain_config.get("target_distance", 10.0)
    base_dist = base_terrain_config.get("target_distance", 10.0)
    if target_dist != base_dist:
        # Match "1. **Movement**: Object reaches x >= 18.0m."
        dist_pattern = r"(\*\*Movement\*\*: Object reaches x >= )(\d+\.?\d*)(m\.)"
        if re.search(dist_pattern, criteria):
            criteria = re.sub(
                dist_pattern,
                f"\\g<1>{8.0 + target_dist:.1f}\\g<3> (originally x >= {8.0 + base_dist:.1f}\\g<3> in the source environment).",
                criteria
            )
            
    # Mass budget
    target_mass = target_terrain_config.get("max_structure_mass", 40.0)
    base_mass = base_terrain_config.get("max_structure_mass", 40.0)
    if target_mass != base_mass:
        # Match "**Mass Budget**: < 40 kg."
        mass_pattern = r"(\*\*Mass Budget\*\*: < )(\d+\.?\d*)( kg\.)"
        if re.search(mass_pattern, criteria):
            criteria = re.sub(
                mass_pattern,
                f"\\g<1>{target_mass:.0f}\\g<3> (originally {base_mass:.0f}\\g<3> in the source environment).",
                criteria
            )
            
    return criteria

def get_k04_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns ordered stage configs for K-04: The Pusher task variants.
    """
    task_description_suffix = """
## Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables **MIGHT** have changed from the initial environment, **NOT ALL** of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
- **Ground Friction**: The traction and slipperiness of the pushing surface may be altered.
- **Center of Mass Offset**: The internal mass distribution and balance of the pushed object may have changed.
- **Object Mass**: The weight of the payload block may be higher or lower than initial specifications.
- **Object Friction**: The friction between the payload and the ground (or pusher) may be altered.
- **Gravity**: The magnitude and direction of the gravitational force may differ from standard.
- **Damping**: The rate at which the object's momentum and motion are dissipated may vary.

**Discovery via feedback**: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., where a joint breaks or how a body moves) to infer the hidden constraints and adapt your design.
"""
    return [
        {
            "stage_id": "Stage-1",
            "title": "High Tipping Hazard",
            "mutation_description": "Object has a high center of mass and tips backward easily if pushed from below.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {
                "object": {"center_of_mass_offset": [0.1, 0.2]}
            },
            "physics_config": {"do_sleep": False},
        },
        {
            "stage_id": "Stage-2",
            "title": "Sticky Terrain",
            "mutation_description": "Ground friction is huge (1.5) and object is heavy (60.0). Requires massive continuous pushing force.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {
                "ground_friction": 1.5,
                "object": {"mass": 60.0}
            },
            "physics_config": {"do_sleep": False},
        },
        {
            "stage_id": "Stage-3",
            "title": "Slippery Ground",
            "mutation_description": "Object and ground have almost zero friction (0.1).",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {
                "ground_friction": 0.1,
                "object": {"friction": 0.1}
            },
            "physics_config": {"do_sleep": False},
        },
        {
            "stage_id": "Stage-4",
            "title": "Extreme Challenge: Low Gravity",
            "mutation_description": "Gravity is very weak (-2.0) and ground friction is low. Object floats away if struck upwards.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {
                "ground_friction": 0.05
            },
            "physics_config": {"gravity": [0, -2.0], "do_sleep": False},
        },
    ]
