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
    # We keep the description mostly base to follow the "Information Hiding" mandate.
    return base_description


def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    # We keep the success criteria mostly base to follow the "Information Hiding" mandate.
    return base_success_criteria

# DYNAMICALLY GENERATED UNIFORM_SUFFIX based on the union of all mutated variables in Stages 1-4
UNIFORM_SUFFIX = """
Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables MIGHT have changed from the initial environment, NOT ALL of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
 - **Gravity**: The downward acceleration may differ from standard, altering impact energy and structural load.
 - **Debris Density**: Falling boulders may have significantly higher mass, leading to massive accumulation of weight.
 - **Bombardment Intensity & Frequency**: More boulders may fall, and they may fall more frequently.
 - **Material Elasticity (Restitution)**: The elasticity of falling boulders may change, altering how they ricochet off surfaces.
 - **Atmospheric Turbulence (Wind)**: A lateral force may be acting on all structures and debris, potentially causing drift or collapse.
 - **Structural Integrity (Joint Strength)**: Anchors and connections may have limited load-bearing capacity and can snap under excessive force or torque.
 - **Core Fragility**: The central object may have an extremely low tolerance for impact forces, requiring near-perfect isolation.
 - **Resource Scarcity (Mass Budget)**: The total mass of materials allowed for construction may be significantly restricted.

Discovery via feedback: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., where a joint breaks or how a body moves) to infer the hidden constraints and adapt your design.
"""

def get_s05_curriculum_stages() -> List[Dict[str, Any]]:
    return [
        {
            "stage_id": "Stage-1",
            "title": "The Heavy Accumulation",
            "mutation_description": "Dense boulders (100.0) and high gravity (-30.0). Joint strength is limited (15000N). Requires a multi-pillar sloped design to shed weight and survive impacts.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "meteor_density": 100.0,
                "meteor_restitution": 0.0,
                "meteor_count": 20,
                "meteor_spawn_interval": 30,
                "max_joint_force": 15000.0,
                "max_core_force": 1000.0,
            },
            "physics_config": {
                "gravity": (0, -30.0),
            },
        },
        {
            "stage_id": "Stage-2",
            "title": "The Weightless Restraint",
            "mutation_description": "Extreme mass limitation (1.5kg) forces structural minimalism. The heavy standard concrete structures will be instantly rejected by the environment.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "max_structure_mass": 1.5,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-3",
            "title": "The Aerodynamic Fragility",
            "mutation_description": "Strong lateral wind (-50.0) combined with fragile joints (500N). Massive standard structures will snap their own anchors due to wind drag. Requires a minimalist, lightweight aerodynamic frame.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "wind_force": -50.0,
                "max_joint_force": 500.0,
                "max_joint_torque": 500.0,
                "meteor_count": 30,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-4",
            "title": "The Ultimate Gauntlet",
            "mutation_description": "Mass budget (100kg), wind (20.0), gravity (-30.0), bouncy debris, and fragile core (1.0N) with weak joints (10000N).",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "max_structure_mass": 100.0,
                "wind_force": 20.0,
                "meteor_density": 20.0,
                "meteor_restitution": 0.8,
                "max_core_force": 1.0,
                "max_joint_force": 10000.0,
                "meteor_count": 30,
            },
            "physics_config": {
                "gravity": (0, -30.0),
            },
        },
    ]
