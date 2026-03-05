"""
K-05: The Lifter task curriculum stages (mutations).

All stage definitions live under tasks/Category2_Kinematics_Linkages/K_05.
The solver agent is NOT told exact invisible parameter changes; it must infer from feedback.
"""

from __future__ import annotations

from typing import Any, Dict, List
import re


def update_task_description_for_visible_changes(base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """
    Update task description to reflect visible physical changes.
    """
    description = base_description
    target_y = target_terrain_config.get("target_object_y", 9.0)
    base_y = base_terrain_config.get("target_object_y", 9.0)
    
    if target_y != base_y:
        # Update "at least y=9.0m"
        pattern = r"(at least y=)(\d+\.?\d*)m"
        description = re.sub(pattern, f"\\g<1>{target_y:.1f}m (originally y={base_y:.1f}m in the source environment)", description)
        
        # Update "at or above y=9.0m"
        pattern2 = r"(at or above y=)(\d+\.?\d*)m"
        description = re.sub(pattern2, f"\\g<1>{target_y:.1f}m (originally y={base_y:.1f}m in the source environment)", description)
        
    return description


def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update success criteria to reflect visible physical changes."""
    criteria = base_success_criteria
    target_y = target_terrain_config.get("target_object_y", 9.0)
    base_y = base_terrain_config.get("target_object_y", 9.0)
    
    if target_y != base_y:
        # Update "Reaches y >= 9.0m"
        pattern = r"(Reaches y >= )(\d+\.?\d*)m"
        criteria = re.sub(pattern, f"\\g<1>{target_y:.1f}m (originally y >= {base_y:.1f}m in the source environment)", criteria)
        
        # Update "holds the object at or above y=9.0m"
        pattern2 = r"(at or above y=)(\d+\.?\d*)m"
        criteria = re.sub(pattern2, f"\\g<1>{target_y:.1f}m (originally y={base_y:.1f}m in the source environment)", criteria)
        
    return criteria


def get_k05_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns ordered stage configs for K-05: The Lifter task variants.
    """
    task_description_suffix = """
## Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables **MIGHT** have changed from the initial environment, **NOT ALL** of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
- **Gravity**: The magnitude and direction of the gravitational force may differ from standard.
- **Object Mass**: The total mass and inertia of the target object may have changed.
- **Target Height**: The required vertical elevation for task completion may be adjusted.
- **Ground Friction**: The traction and slipperiness of the base surface may be altered.

**Discovery via feedback**: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., where a joint breaks or how a body moves) to infer the hidden constraints and adapt your design.
"""
    return [
        {
            "stage_id": "Stage-1",
            "title": "Increased Gravity",
            "mutation_description": "Gravity increased from -10 to -28 m/s\u00b2.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {},
            "physics_config": {"gravity": (0, -28.0)},
        },
        {
            "stage_id": "Stage-2",
            "title": "Heavier Object",
            "mutation_description": "Object mass increased from 20kg to 50kg.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {"object": {"mass": 50.0, "friction": 0.6}},
            "physics_config": {},
        },
        {
            "stage_id": "Stage-3",
            "title": "Higher Target + Heavier Object",
            "mutation_description": "Target height 10.5m, object mass 42kg.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {
                "target_object_y": 10.5,
                "object": {"mass": 42.0, "friction": 0.6},
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-4",
            "title": "Multi-Parameter Challenge",
            "mutation_description": "Gravity -16, object 46kg, target 10m, friction 0.4.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {
                "target_object_y": 10.0,
                "ground_friction": 0.4,
                "object": {"mass": 46.0, "friction": 0.6},
            },
            "physics_config": {"gravity": (0, -16.0)},
        },
    ]
