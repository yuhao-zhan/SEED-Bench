"""
S-05: The Shelter task curriculum stages (mutations).
"""

from __future__ import annotations

from typing import Any, Dict, List
import re

# Base task defaults (must match environment.py and prompt.py)
DEFAULT_METEOR_COUNT = 12
DEFAULT_CORE_MAX_FORCE = 150.0
DEFAULT_MAX_MASS = 300.0
DEFAULT_METEOR_SPAWN_INTERVAL = 30
DEFAULT_WIND_FORCE = 0.0
DEFAULT_METEOR_RESTITUTION = 0.2
DEFAULT_METEOR_DENSITY = 5.0
DEFAULT_FLOOR_FRICTION = 0.5


def update_task_description_for_visible_changes(base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    description = base_description
    target_max_mass = target_terrain_config.get("max_structure_mass", DEFAULT_MAX_MASS)
    base_max_mass = base_terrain_config.get("max_structure_mass", DEFAULT_MAX_MASS)

    if target_max_mass != base_max_mass:
        # Update Mass Budget in constraints
        mass_desc_pattern = r"(- \*\*Mass Budget\*\*: Total structure mass must be less than )(\d+\.?\d*) kg\."
        if re.search(mass_desc_pattern, description):
            description = re.sub(
                mass_desc_pattern,
                f"\\g<1>{target_max_mass:.1f} kg (originally < {base_max_mass:.1f} kg in the source environment).",
                description
            )
    return description


def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    criteria = base_success_criteria
    target_max_mass = target_terrain_config.get("max_structure_mass", DEFAULT_MAX_MASS)
    base_max_mass = base_terrain_config.get("max_structure_mass", DEFAULT_MAX_MASS)

    if target_max_mass != base_max_mass:
        mass_pattern = r"(- \*\*Mass Budget\*\*: < )(\d+\.?\d*) kg\."
        if re.search(mass_pattern, criteria):
            criteria = re.sub(
                mass_pattern,
                f"\\g<1>{target_max_mass:.1f} kg (originally < {base_max_mass:.1f} kg in the source environment).",
                criteria
            )
    return criteria

# DYNAMICALLY GENERATED UNIFORM_SUFFIX based on the union of all mutated variables in Stages 1-4
UNIFORM_SUFFIX = """
Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables MIGHT have changed from the initial environment, NOT ALL of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
 - **Atmospheric Turbulence (Wind)**: Constant lateral forces may be acting on all objects, potentially blowing away unanchored or high-drag structures.
 - **Joint Shear Strength**: Connections may have limited linear load-bearing capacity and can fail under high-speed impacts or extreme lateral forces.
 - **Meteor Elasticity (Restitution)**: Falling debris may be highly elastic, causing unpredictable ricochets that can bypass standard overhead cover.
 - **Bombardment Intensity**: The total number of falling boulders may be significantly higher, increasing the duration and cumulative load of the storm.
 - **Core Fragility**: The central object may be exceptionally sensitive to even minor impacts, requiring near-perfect isolation.
 - **Mass Budget Scarcity**: The total allowed mass for construction may be severely restricted, forcing the use of ultra-lightweight materials.
 - **Joint Torque Tolerance**: Anchors and connections may have limited resistance to twisting forces, causing collapse under asymmetrical loads.
 - **Gravitational Constant**: The downward acceleration may be significantly higher, increasing structural stress and impact energy.

Discovery via feedback: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., where a joint breaks or how a body moves) to infer the hidden constraints and adapt your design.
"""

def get_s05_curriculum_stages() -> List[Dict[str, Any]]:
    return [
        {
            "stage_id": "Stage-1",
            "title": "The Gale Force",
            "mutation_description": "Strong lateral wind (-100.0) combined with limited joint strength (1000N). Massive structures will experience enormous drag and snap their own anchors.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "wind_force": -100.0,
                "max_joint_force": 1000.0,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-2",
            "title": "The Kinetic Ricochet",
            "mutation_description": "Perfect elasticity of meteors (restitution: 1.0) and extreme core sensitivity. Boulders will bounce off the floor and roof indefinitely.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "meteor_restitution": 1.0,
                "meteor_count": 100,
                "max_core_force": 5.0,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-3",
            "title": "The Gravitational Constraint",
            "mutation_description": "High gravity (-60.0) combined with a strict mass limit (2.0kg) and fragile joints (500N). The structure must be incredibly light yet robust enough to handle its own weight and high-energy impacts.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "max_structure_mass": 2.0,
                "max_joint_force": 500.0,
                "max_joint_torque": 500.0,
            },
            "physics_config": {
                "gravity": (0, -60.0),
            },
        },
        {
            "stage_id": "Stage-4",
            "title": "The Celestial Infernal",
            "mutation_description": "Extreme lateral wind (50.0), a hyper-fragile core (0.5N), high gravity (-40.0), and low mass budget (5.0kg). Multiple conflicting constraints require a perfect aerodynamic and structural balance.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "wind_force": 50.0,
                "max_core_force": 0.5,
                "meteor_restitution": 0.9,
                "max_structure_mass": 5.0,
                "max_joint_force": 10000.0,
                "max_joint_torque": 10000.0,
            },
            "physics_config": {
                "gravity": (0, -40.0),
            },
        },
    ]
