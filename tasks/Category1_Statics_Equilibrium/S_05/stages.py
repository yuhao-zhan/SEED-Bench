"""
S-05: The Shelter task curriculum stages (mutations).
"""

from __future__ import annotations

from typing import Any, Dict, List

# Base task defaults (must match environment.py and prompt.py)
DEFAULT_METEOR_COUNT = 12
DEFAULT_CORE_MAX_FORCE = 150.0
DEFAULT_MAX_MASS = 300.0
DEFAULT_METEOR_SPAWN_INTERVAL = 30
DEFAULT_WIND_FORCE = 0.0
DEFAULT_METEOR_RESTITUTION = 0.2
DEFAULT_FLOOR_FRICTION = 0.5


def update_task_description_for_visible_changes(base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    # Information Hiding: We no longer update the prompt with specific mutated values.
    # The agent must discover these via the UNIFORM_SUFFIX and environmental feedback.
    return base_description


def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    # Information Hiding: We no longer update the success criteria with specific mutated values.
    return base_success_criteria

UNIFORM_SUFFIX = """
Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables MIGHT have changed from the initial environment, NOT ALL of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
 - **Gravity**: The downward acceleration may be significantly higher than standard, increasing impact energy.
 - **Atmospheric Turbulence (Wind)**: A constant lateral force may be acting on all structures and debris.
 - **Surface Friction**: The ground may be exceptionally slippery, making unanchored structures unstable.
 - **Material Elasticity (Restitution)**: Falling boulders may be highly bouncy, transferring more momentum upon impact.
 - **Core Fragility**: The central object may have a much lower tolerance for impact forces than usual.
 - **Resource Scarcity (Mass Budget)**: The total mass of materials allowed for construction may be severely limited.

Discovery via feedback: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., where a joint breaks or how a body moves) to infer the hidden constraints and adapt your design.
"""

def get_s05_curriculum_stages() -> List[Dict[str, Any]]:
    return [
        {
            "stage_id": "Stage-1",
            "title": "Extreme Gravity",
            "mutation_description": "Gravity increased to -60.0 m/s². The structural integrity of the shelter will be tested under extreme impact loads.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {},
            "physics_config": {
                "gravity": (0, -60.0),
            },
        },
        {
            "stage_id": "Stage-2",
            "title": "The Slippery Gale",
            "mutation_description": "Constant lateral wind force (15.0 N/kg) and low ground friction (0.1).",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "wind_force": 15.0,
                "floor_friction": 0.1,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-3",
            "title": "Kinetic Overload",
            "mutation_description": "High restitution meteors (0.8) and extremely fragile core (5.0N).",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "meteor_restitution": 0.8,
                "max_core_force": 5.0,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-4",
            "title": "The Ultimate Gauntlet",
            "mutation_description": "High gravity (-40), low mass (120kg), bouncy debris (0.8), wind (5.0), and fragile core (15N).",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "max_structure_mass": 120.0,
                "meteor_restitution": 0.8,
                "max_core_force": 15.0,
                "wind_force": 5.0,
            },
            "physics_config": {
                "gravity": (0, -40.0),
            },
        },
    ]
