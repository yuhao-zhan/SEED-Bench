"""
K-02: The Climber task curriculum stages (mutations).
Overhauled to introduce severe, physics-based challenges.
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
        build_zone_pattern = r"(y=\[0, )(\d+\.?\d*)(\])"
        if re.search(build_zone_pattern, description):
            description = re.sub(
                build_zone_pattern,
                f"\\g<1>{target_y_max:.1f}\\g<3> (originally y=[0, {base_y_max:.1f}] in the source environment)",
                description
            )

    default_min_mass = 0.0
    target_min_mass = target_terrain_config.get("min_structure_mass", default_min_mass)
    base_min_mass = base_terrain_config.get("min_structure_mass", default_min_mass)
    if target_min_mass != base_min_mass:
        # Update Mass Budget line: "at least 0 kg and less than 50 kg" -> new min with (originally ...)
        min_mass_pattern = r"(Total structure mass must be at least )(\d+\.?\d*)( kg and less than )(\d+\.?\d*)( kg\.)"
        if re.search(min_mass_pattern, description):
            description = re.sub(
                min_mass_pattern,
                f"\\g<1>{target_min_mass:.1f} kg (originally {base_min_mass:.1f} kg in the source environment) and less than \\g<4>\\g<5>",
                description
            )
        # Success criteria Design Constraints: "Minimum 0 kg, maximum < 50 kg"
        min_mass_criteria_pattern = r"(Minimum )(\d+\.?\d*)( kg, maximum)"
        if re.search(min_mass_criteria_pattern, description):
            description = re.sub(
                min_mass_criteria_pattern,
                f"\\g<1>{target_min_mass:.1f} kg (originally {base_min_mass:.1f} kg in the source environment), maximum",
                description
            )

    return description


def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    criteria = base_success_criteria
    default_min_mass = 0.0
    target_min_mass = target_terrain_config.get("min_structure_mass", default_min_mass)
    base_min_mass = base_terrain_config.get("min_structure_mass", default_min_mass)
    if target_min_mass != base_min_mass:
        min_mass_criteria_pattern = r"(Minimum )(\d+\.?\d*)( kg, maximum)"
        if re.search(min_mass_criteria_pattern, criteria):
            criteria = re.sub(
                min_mass_criteria_pattern,
                f"\\g<1>{target_min_mass:.1f} kg (originally {base_min_mass:.1f} kg in the source environment), maximum",
                criteria
            )
    return criteria


def get_k02_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns ordered stage configs for K-02: The Climber task variants.
    """
    
    # UNION of all physical variables modified across all stages
    # - max_joint_force: Structural load limit
    # - max_joint_torque: Actuator torque limit
    # - gravity: Base gravitational acceleration
    # - gravity_evolution: Time-dependent gravity shift
    # - suction_zones: Functional regions for adhesive pads
    # - wall_oscillation_amp/freq: Seismic wall movement
    # - boulder_interval: Periodic projectile interference
    # - min_structure_mass: Stability requirement
    # - wind_force: Constant lateral atmospheric pressure
    # - wind_oscillation: Pulsing atmospheric turbulence
    # - vortex_y/force: Height-triggered extreme weather phenomena
    # - build_zone_y_max: Vertical extent of the build zone
    
    task_description_suffix = """
## Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables MIGHT have changed from the initial environment, NOT ALL of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
 - **Build Zone (Vertical Extent)**: The allowed vertical range for placing and operating the structure may differ from the default.
 - **Structural Integrity Thresholds (Joint Force/Torque)**: Joints may snap if subjected to excessive reaction forces or if motors exert too much torque.
 - **Gravitational Instability (Gravity/Evolution)**: Gravitational acceleration or its variation over time may differ from the default; vertical loads may be significantly different.
 - **Surface Adhesion Gaps (Suction Zones)**: The wall's surface may be slick or non-adhesive in certain altitude bands, requiring long-reach transitions.
 - **Mass Displacement Constraints (Min Mass)**: Certain regions require a minimum structural inertia to remain stable against environmental forces.
 - **Atmospheric Turbulence (Wind/Vortex)**: Lateral wind forces and height-dependent vortices may attempt to push the climber away from the wall.

Discovery via feedback: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., where a joint breaks or how a body moves) to infer the hidden constraints and adapt your design.
"""

    return [
        {
            "stage_id": "Stage-1",
            "title": "Fragile Structural Integrity",
            "mutation_description": "Extremely strict joint strength limits and build zone restriction. Forces ultra-lightweight and smooth motion.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {
                "build_zone_y_max": 5.0,
            },
            "physics_config": {
                "max_joint_force": 100.0,
                "max_joint_torque": 200.0,
            },
        },
        {
            "stage_id": "Stage-2",
            "title": "Gravitational Flux & Void Zones",
            "mutation_description": "Stronger gravity that increases over time, combined with a 3m suction gap. Forces high-power, long-reach climbing.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {
                "build_zone_y_max": 8.0,
                "suction_zones": [(0, 16), (19, 35)],
            },
            "physics_config": {
                "gravity": (0, -12.0),
                "gravity_evolution": -0.1,
            },
        },
        {
            "stage_id": "Stage-3",
            "title": "Resonant Interference Phase",
            "mutation_description": "Minimum mass requirement in a restricted build zone. Forces robust, heavy-duty builds.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {
                "build_zone_y_max": 5.0,
                "min_structure_mass": 25.0,
            },
            "physics_config": {
                "max_joint_force": 3000.0,
            },
        },
        {
            "stage_id": "Stage-4",
            "title": "The Vortex Storm",
            "mutation_description": "Extreme wind, oscillating turbulence, and height-dependent vortex forces in a tiny build zone. Forces ultra-stable compact designs.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {
                "build_zone_y_max": 2.5,
                "wind_force": -30.0,
                "wind_oscillation": 5.0,
                "vortex_y": 5.0,
                "vortex_force_x": 50.0,
                "vortex_force_y": -20.0,
            },
            "physics_config": {
                "gravity": (0, -20.0),
            },
        },
    ]
