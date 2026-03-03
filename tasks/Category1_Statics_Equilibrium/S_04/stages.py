"""
S-04: The Balancer task curriculum stages (mutations).
"""

from __future__ import annotations

from typing import Any, Dict, List
import re


def update_task_description_for_visible_changes(base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """
    Update task description to reflect visible physical changes.
    """
    description = base_description
    
    if target_terrain_config.get("obstacle_active"):
        description += "\n- **Obstacle Detected**: A static obstruction has been placed in the environment. You must design your structure to avoid or bypass it."
        
    if target_terrain_config.get("drop_load"):
        description = description.replace(
            "It will automatically attach (weld) to your structure if any part of your design is built within 0.5m of (3,0).",
            "The load will be DROPPED from above at x=3.0. You must catch and balance it without it touching the ground."
        )
        
    if target_terrain_config.get("wind_active"):
        description += "\n- **Wind Active**: A strong lateral wind force is continuously blowing. This will generate significant torque depending on your structure's mass distribution and shape."
            
    return description


def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """
    Update success criteria to reflect visible physical changes.
    """
    criteria = base_success_criteria
    
    if target_terrain_config.get("drop_load"):
        criteria = criteria.replace(
            "Successfully connect to the heavy load at (3,0).",
            "Successfully catch the falling load and prevent it from touching the ground."
        )
    
    return criteria


def get_s04_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns ordered stage configs for S-04: The Balancer task variants.
    """
    return [
        {
            "stage_id": "Stage-1",
            "title": "Structural Obstruction",
            "mutation_description": "Static obstacle placed on the counterweight side. Requires spatial reasoning to build around it.",
            "task_description_suffix": """
## Environmental Warning
A physical obstruction is blocking the standard counterbalance path.
Colliding with the obstacle during construction or oscillation will destabilize your design.
""",
            "terrain_config": {
                "force_pivot_joint": True,
                "obstacle_active": True,
                "obstacle_rect": [-3.5, -0.1, -1.0, 5.0], # Blocks almost all counterweight space
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-2",
            "title": "Dynamic Impact Loading",
            "mutation_description": "The payload is dropped from above instead of gently welding. Requires impact absorption.",
            "task_description_suffix": """
## Environmental Warning
Dynamic loading detected. The payload is no longer stationary.
The impact force from the drop will induce massive rotational momentum that must be absorbed and canceled.
""",
            "terrain_config": {
                "force_pivot_joint": True,
                "drop_load": True,
                "load_mass": 3000.0, # Extreme mass
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-3",
            "title": "Lateral Wind Torque",
            "mutation_description": "A continuous wind pushes all masses to the right, causing a net torque that must be statically counteracted.",
            "task_description_suffix": """
## Environmental Warning
Severe lateral wind forces detected.
The wind exerts a constant horizontal force on all structural components.
Due to the pivot, this will translate into a powerful overturning torque that cannot be solved by symmetric mass balancing alone.
""",
            "terrain_config": {
                "force_pivot_joint": True,
                "wind_active": True,
                "wind_force_multiplier": 200.0, # Extreme wind
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-4",
            "title": "The Perfect Storm",
            "mutation_description": "Obstacle + Drop Load + Wind + High Gravity.",
            "task_description_suffix": """
## Environmental Warning
Multiple critical failure modes active simultaneously.
You must navigate obstacles, catch a falling mass, and manage continuous wind torque under extreme gravity.
""",
            "terrain_config": {
                "force_pivot_joint": True,
                "obstacle_active": True,
                "obstacle_rect": [-3.5, -0.1, -1.0, 5.0],
                "drop_load": True,
                "wind_active": True,
                "wind_force_multiplier": 50.0,
                "load_mass": 1000.0,
            },
            "physics_config": {
                "gravity": (0, -20.0),
            },
        },
    ]
