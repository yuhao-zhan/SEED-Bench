"""
K-06: The Wiper task curriculum stages (mutations).

All stage definitions live under tasks/Category2_Kinematics_Linkages/K_06 as requested.
The solver agent is NOT told the exact parameter changes; it must infer from feedback.
"""

from __future__ import annotations

from typing import Any, Dict, List
import re


def update_task_description_for_visible_changes(base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update task description to reflect visible physical changes."""
    description = base_description
    
    # Particle count
    target_count = target_terrain_config.get("particles", {}).get("count", 45)
    base_count = base_terrain_config.get("particles", {}).get("count", 45)
    
    if target_count != base_count:
        pattern = r"(- \*\*Particles\*\*: )(\d+)( small particles)"
        description = re.sub(pattern, f"\\g<1>{target_count} small particles (originally {base_count} small particles in the source environment)", description)

    # Mass limit
    target_mass = target_terrain_config.get("max_structure_mass", 15.0)
    base_mass = base_terrain_config.get("max_structure_mass", 15.0)
    
    if target_mass != base_mass:
        pattern = r"(Total structure mass must be less than )(\d+\.?\d*)( kg)"
        description = re.sub(pattern, f"\\g<1>{target_mass:.2f} kg (originally {base_mass:.2f} kg in the source environment)", description)
        
    return description


def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update success criteria to reflect visible physical changes."""
    criteria = base_success_criteria
    
    # Mass limit
    target_mass = target_terrain_config.get("max_structure_mass", 15.0)
    base_mass = base_terrain_config.get("max_structure_mass", 15.0)
    
    if target_mass != base_mass:
        pattern = r"(\*\*Mass Budget\*\*: < )(\d+\.?\d*)( kg)"
        criteria = re.sub(pattern, f"\\g<1>{target_mass:.2f} kg (originally < {base_mass:.2f} kg in the source environment)", criteria)
        
    return criteria


def get_k06_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns ordered stage configs for K-06: The Wiper task variants.
    """
    task_description_suffix = """
## Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables **MIGHT** have changed from the initial environment, **NOT ALL** of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
- **Particle Count**: The total number of particles requiring removal may be adjusted.
- **Particle Distribution**: The initial layout and seeding of particles on the surface may have changed.
- **Particle Friction**: The adhesion and resistance of particles to being moved may be altered.
- **Particle Mass**: The mass and inertia of the individual particles may differ from standard.
- **Mass Budget**: The maximum total mass allowed for the wiper structure may be adjusted.

**Discovery via feedback**: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., where a joint breaks or how a body moves) to infer the hidden constraints and adapt your design.
"""
    return [
        {
            "stage_id": "Stage-1",
            "title": "More Particles and Difficult Layout",
            "mutation_description": "Particle count 80, layout seed changed.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {
                "particles": {"count": 80, "seed": 0, "friction": 0.45, "mass": 0.15},
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-2",
            "title": "Stickier Particles",
            "mutation_description": "Particle friction 0.70.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {
                "particles": {"count": 45, "seed": 42, "friction": 0.70, "mass": 0.15},
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-3",
            "title": "Strict Mass Limit",
            "mutation_description": "Mass limit reduced to 0.25 kg.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {
                "max_structure_mass": 0.25,
                "particles": {"count": 45, "seed": 42, "friction": 0.35, "mass": 0.15},
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-4",
            "title": "Combined Challenge",
            "mutation_description": "55 particles, friction 0.55, seed 5.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {
                "particles": {"count": 55, "seed": 5, "friction": 0.55, "mass": 0.15},
            },
            "physics_config": {},
        },
    ]
