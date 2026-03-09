"""
K-02: The Climber task curriculum stages (mutations).

All stage definitions live under tasks/Category2_Kinematics_Linkages/K_02 as requested.
The solver agent is NOT told the exact parameter changes; it must infer from feedback.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List
import re

def update_task_description_for_visible_changes(base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """
    Update task description to reflect visible physical changes.
    """
    description = base_description
    default_y_max = 25.0
    target_y_max = target_terrain_config.get("build_zone_y_max", default_y_max)
    base_y_max = base_terrain_config.get("build_zone_y_max", default_y_max)

    if target_y_max != base_y_max:
        # Update Build Zone description using regex
        # Matches: - **Build Zone**: x=[0, 5], y=[0, 25].
        # Matches: - **Build Zone**: All components must stay within x=[0, 5], y=[0, 25].
        build_zone_pattern = r"(y=\[0, )(\d+\.?\d*)(\])"
        if re.search(build_zone_pattern, description):
            description = re.sub(
                build_zone_pattern,
                f"\\g<1>{target_y_max:.1f}\\g<3> (originally y=[0, {base_y_max:.1f}] in the source environment)",
                description
            )
        
        # Also handle the second occurrence if it exists
        if re.search(build_zone_pattern, description):
             description = re.sub(
                build_zone_pattern,
                f"\\g<1>{target_y_max:.1f}\\g<3> (originally y=[0, {base_y_max:.1f}] in the source environment)",
                description
            )

    return description


def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """
    Update success criteria to reflect visible physical changes.
    """
    # Success criteria mentions "build zone", but not the specific value in K-02 base prompt.
    return base_success_criteria


def get_k02_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns ordered stage configs for K-02: The Climber task variants.
    """
    task_description_suffix = """
## Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables **MIGHT** have changed from the initial environment, **NOT ALL** of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
- **Atmospheric Shear (Wind)**: Lateral forces may push against your structure at different altitudes.
- **Surface Slickness (Suction Zones)**: The wall's adhesive properties may only be functional in certain bands.
- **Seismic Resonance (Oscillation)**: The wall may oscillate at specific frequencies, testing structural stability.
- **Structural Thresholds (Mass)**: The environment may impose minimum or maximum mass requirements for stability.
- **Geological Instability (Ground)**: The ground surface may become unstable or vanish over time.

**Discovery via feedback**: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode to infer the hidden constraints and adapt your design.
"""
    return [
        {
            "stage_id": "Stage-1",
            "title": "Gauntlet Phase",
            "mutation_description": "Build zone restricted to y < 5.0m. Ground surface vanishes after 5.0s. Forces mobile climbing.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {
                "build_zone_y_max": 5.0,
                "target_height": 20.0,
                "destroy_ground_time": 5.0
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-2",
            "title": "Reach Phase",
            "mutation_description": "2m suction gap at y=18m. Build zone y < 10.0m. Forces long-reach morphology.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {
                "build_zone_y_max": 10.0,
                "target_height": 20.0,
                "suction_zones": [(0, 18), (20, 32)]
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-3",
            "title": "Heavyweight Phase",
            "mutation_description": "10Hz seismic oscillation. Boulders falling every 5s. Min mass 20kg. Forces high-mass robust builds.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {
                "build_zone_y_max": 5.0,
                "target_height": 20.0,
                "wall_oscillation_amp": 0.2,
                "wall_oscillation_freq": 10.0,
                "boulder_interval": 5.0,
                "min_structure_mass": 20.0
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-4",
            "title": "Storm Cell Phase",
            "mutation_description": "Extremely tight build zone y < 2.0m. Vortex wind forces. Forces ultra-compact designs.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {
                "build_zone_y_max": 2.0,
                "target_height": 20.0,
                "wind_force": -5.0,
                "vortex_y": 10.0,
                "vortex_force_x": 10.0
            },
            "physics_config": {},
        },
    ]
