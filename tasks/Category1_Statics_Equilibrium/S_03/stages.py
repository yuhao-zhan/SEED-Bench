"""
S-03: The Cantilever task curriculum stages (mutations).
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
        description += "\n- **Obstacle Detected**: A static obstruction has been placed in the path. You must design your structure to avoid or bypass it."
    
    if target_terrain_config.get("drop_load"):
        description = description.replace(
            "A second heavy weight will attach later to a node within the x=[5, 10] range.",
            "A heavy payload will be DROPPED from above onto your structure at x=7.5m. You must catch and support it."
        )
        
    if target_terrain_config.get("forbidden_anchor_y"):
        ymin, ymax = target_terrain_config["forbidden_anchor_y"]
        description += f"\n- **Corroded Wall Zone**: The wall section between y={ymin}m and y={ymax}m is structurally unsound. Anchors CANNOT be placed in this zone."

    return description


def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """
    Update success criteria to reflect visible physical changes.
    """
    criteria = base_success_criteria
    
    if target_terrain_config.get("drop_load"):
        criteria = criteria.replace(
            "Successfully holds both loads for the duration of the test.",
            "Successfully catches and holds the falling payload without structural failure."
        )
    
    return criteria


def get_s03_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns ordered stage configs for S-03: The Cantilever task variants.
    """
    return [
        {
            "stage_id": "Stage-1",
            "title": "Structural Obstruction",
            "mutation_description": "Static obstacle placed in the span. Requires spatial reasoning to build around/over it.",
            "task_description_suffix": """
## Environmental Warning
A physical obstruction is blocking the standard cantilever path.
Colliding with the obstacle during construction or under load may destabilize your design.
""",
            "terrain_config": {
                "obstacle_active": True,
                "obstacle_rect": [6.0, 0.0, 8.5, 3.5], # Tall block
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-2",
            "title": "Dynamic Impact Loading",
            "mutation_description": "Secondary load is dropped instead of welded. Requires impact absorption and high stiffness.",
            "task_description_suffix": """
## Environmental Warning
Dynamic loading detected. The secondary payload is no longer stationary.
The impact force from the drop will be significantly higher than the static weight.
""",
            "terrain_config": {
                "drop_load": True,
                "drop_mass": 400.0,
                "drop_x": 7.5,
                "drop_y": 12.0,
                "drop_time": 8.0,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-3",
            "title": "Restricted Anchor Zones",
            "mutation_description": "Corroded wall section prevents ideal anchor spacing. Combined with high gravity.",
            "task_description_suffix": """
## Environmental Warning
Corrosion detected on the support wall. 
A significant vertical section of the wall cannot support structural anchors.
This will restrict your leverage and amplify torque on remaining joints.
""",
            "terrain_config": {
                "forbidden_anchor_y": [0.5, 1.5],
                "target_reach": 14.5,
            },
            "physics_config": {
                "gravity": (0, -18.0),
            },
        },
        {
            "stage_id": "Stage-4",
            "title": "The Perfect Storm",
            "mutation_description": "Obstacle + Drop Load + Forbidden Zone + High Gravity + Weak Anchors.",
            "task_description_suffix": """
## Environmental Warning
Multiple critical failure modes active.
You must navigate obstacles, catch a falling mass, and manage extreme gravity with restricted wall attachment points.
""",
            "terrain_config": {
                "obstacle_active": True,
                "obstacle_rect": [5.5, -1.0, 7.5, 2.0],
                "drop_load": True,
                "drop_mass": 500.0,
                "drop_x": 9.5,
                "drop_y": 15.0,
                "drop_time": 7.0,
                "forbidden_anchor_y": [0.2, 1.8],
                "max_anchor_torque": 1200.0,
                "target_reach": 16.0,
            },
            "physics_config": {
                "gravity": (0, -15.0),
            },
        },
    ]
