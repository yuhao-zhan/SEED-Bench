"""
S-04: The Balancer task curriculum stages (mutations).
"""

from __future__ import annotations

from typing import Any, Dict, List


UNIFORM_SUFFIX = """
Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables MIGHT have changed from the initial environment, NOT ALL of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
 - Fragile Anchor Points: The central pivot joint has a strict static torque capacity. Even slight imbalances will snap the structure.
 - Lateral Wind Currents: Invisible air currents exert a continuous horizontal force, creating a persistent overturning torque.
 - Dynamic Loading: The target mass is dropped from a height rather than being stationary, requiring robust impact absorption.
 - Kinetic Obstructions: Moving or static structural barriers exist in the environment, requiring precise spatial planning.
 - Variable Gravity: Local gravitational fluctuations increase the effective weight of all components.

Discovery via feedback: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode to infer the hidden constraints and adapt your design.
"""


def update_task_description_for_visible_changes(base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update description for visible changes."""
    description = base_description
    if target_terrain_config.get("obstacle_active"):
        if target_terrain_config.get("moving_obstacle"):
            description += "\n- **Moving Obstacle Detected**: A dynamic obstruction is oscillating in the environment."
        else:
            description += "\n- **Obstacle Detected**: A static structural barrier exists in the environment."
    if target_terrain_config.get("wind_active"):
        description += f"\n- **Wind Active**: Strong lateral wind detected."
    if target_terrain_config.get("drop_load"):
        description = description.replace(
            "It may automatically attach (weld) to your structure if any part of your design is built within 0.5m of (3,0), OR it may be DROPPED from above.",
            "The load will be DROPPED from above at x=3.0. You must catch and balance it without it touching the ground."
        )
    return description


def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update success criteria for visible changes."""
    criteria = base_success_criteria
    if target_terrain_config.get("drop_load"):
        criteria = criteria.replace(
            "Successfully catch or connect to the heavy load at x=3.0.",
            "Successfully catch the falling load and prevent it from touching the ground."
        )
    return criteria


def get_s04_curriculum_stages() -> List[Dict[str, Any]]:
    """Returns ordering stage configs."""
    return [
        {
            "stage_id": "Stage-1",
            "title": "Structural Fragility",
            "mutation_description": "The pivot joint is extremely brittle. Precise mathematical balance is required.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "force_pivot_joint": True,
                "fragile_joints": True,
                "max_joint_torque": 50.0,
                "load_mass": 200.0,
            },
            "physics_config": {
                "angular_damping": 2.0,
            },
        },
        {
            "stage_id": "Stage-2",
            "title": "Aerodynamic Overturning",
            "mutation_description": "A powerful lateral wind creates a constant overturning torque.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "force_pivot_joint": True,
                "wind_active": True,
                "wind_force_multiplier": 50.0,
                "load_mass": 200.0,
            },
            "physics_config": {
                "angular_damping": 2.0,
            },
        },
        {
            "stage_id": "Stage-3",
            "title": "The Labyrinth",
            "mutation_description": "A massive static obstacle blocks the standard horizontal path to the load.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "force_pivot_joint": True,
                "obstacle_active": True,
                "obstacles": [[0.5, 0.0, 2.5, 2.0]],
                "load_mass": 200.0,
            },
            "physics_config": {
                "angular_damping": 2.0,
            },
        },
        {
            "stage_id": "Stage-4",
            "title": "Planetary Kinetic Storm",
            "mutation_description": "High gravity, strong wind, moving obstacles, and a dropped load combine.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "force_pivot_joint": True,
                "obstacle_active": True,
                "moving_obstacle": True,
                "obstacle_rect": [-1.0, 1.0, 1.0, 2.0],
                "obstacle_amplitude": 1.5,
                "obstacle_frequency": 0.5,
                "wind_active": True,
                "wind_force_multiplier": 20.0,
                "drop_load": True,
                "load_mass": 300.0,
                "fragile_joints": True,
                "max_joint_torque": 500.0,
            },
            "physics_config": {
                "gravity": (0, -20.0),
                "angular_damping": 5.0,
            },
        },
    ]
