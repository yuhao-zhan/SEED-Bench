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
    return base_description


def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """
    Update success criteria to reflect visible physical changes.
    """
    criteria = base_success_criteria
    
    # Target distance
    target_dist = target_terrain_config.get("target_distance", 10.0)
    base_dist = base_terrain_config.get("target_distance", 10.0)
    if target_dist != base_dist:
        # Match "Object reaches x >= 18.0m." or similar
        dist_pattern = r"(Object reaches x >= )(\d+\.?\d*)(m\.)"
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
                f"\\g<1>{target_mass:.0f}\\g<3> (originally < {base_mass:.0f}\\g<3> in the source environment).",
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
- **Gravity**: The magnitude and direction of the gravitational force may differ from standard.
- **Damping**: The rate at which the object's momentum and motion are dissipated may vary.

**Discovery via feedback**: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., where a joint breaks or how a body moves) to infer the hidden constraints and adapt your design.
"""
    return [
        {
            "stage_id": "Stage-1",
            "title": "Low Ground Friction",
            "mutation_description": "Ground friction reduced from 1.2 to 0.18.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {"ground_friction": 0.18},
            "physics_config": {"do_sleep": False},
        },
        {
            "stage_id": "Stage-2",
            "title": "Object Center of Mass Offset",
            "mutation_description": "Object center of mass offset (0.25, 0.15).",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {"object": {"center_of_mass_offset": (0.25, 0.15)}},
            "physics_config": {"do_sleep": False},
        },
        {
            "stage_id": "Stage-3",
            "title": "Low Friction + Heavy World",
            "mutation_description": "Ground friction 0.22, gravity -14 m/s\u00b2.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {"ground_friction": 0.22},
            "physics_config": {"gravity": (0, -14.0), "do_sleep": False},
        },
        {
            "stage_id": "Stage-4",
            "title": "Extreme Challenge",
            "mutation_description": "Ground friction 0.16, gravity -15, damping 0.4, CoM offset (0.2, 0.12).",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {
                "ground_friction": 0.16,
                "object": {
                    "linear_damping": 0.4,
                    "angular_damping": 0.4,
                    "center_of_mass_offset": (0.2, 0.12),
                },
            },
            "physics_config": {"gravity": (0, -15.0), "do_sleep": False},
        },
    ]
