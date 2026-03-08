"""
K-03: The Gripper task curriculum stages (mutations).

All stage definitions live under tasks/Category2_Kinematics_Linkages/K_03 as requested.
The solver agent is NOT told the exact parameter changes (invisible params); it must infer from feedback.
Visible changes (e.g. object shape) are explicitly stated in the task description.
"""

from __future__ import annotations

from typing import Any, Dict, List


def update_task_description_for_visible_changes(base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """
    Update task description to reflect visible physical changes.
    """
    target_objects = target_terrain_config.get("objects") or {}
    target_shape = target_objects.get("shape", "box")
    
    base_objects = base_terrain_config.get("objects") or {}
    base_shape = base_objects.get("shape", "box")
    
    if target_shape != base_shape:
        extra = f"\n\n**Note (this environment)**: The object to grasp is now **{target_shape}** in cross-section (was **{base_shape}**). Design your gripper and grasp strategy accordingly."
        return base_description.rstrip() + extra
        
    return base_description


def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """
    Update success criteria to reflect visible physical changes.
    """
    return base_success_criteria


def get_k03_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns ordered stage configs for K-03: The Gripper task variants.
    """
    task_description_suffix = """
## Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables **MIGHT** have changed from the initial environment, **NOT ALL** of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
- **Object Friction**: The surface traction and slipperiness of the target object may be altered.
- **Gravity**: The magnitude and direction of the gravitational force may differ from standard.
- **Damping**: The rate at which the object's momentum and motion are dissipated may vary.
- **Object Geometry**: The physical shape and cross-section of the target object may have changed.

**Discovery via feedback**: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., where a joint breaks or how a body moves) to infer the hidden constraints and adapt your design.
"""
    return [
        {
            "stage_id": "Stage-1",
            "title": "Slippery Object",
            "mutation_description": "Object surface friction reduced from 0.6 to 0.09.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {"objects": {"shape": "box", "mass": 1.0, "friction": 0.09, "x": 5.0, "y": 2.0}},
            "physics_config": {},
        },
        {
            "stage_id": "Stage-2",
            "title": "Heavy World",
            "mutation_description": "Gravity increased from -10 to -17 m/s\u00b2.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {"objects": {"shape": "box", "mass": 1.0, "friction": 0.6, "x": 5.0, "y": 2.0}},
            "physics_config": {"gravity": (0, -17.0)},
        },
        {
            "stage_id": "Stage-3",
            "title": "Slippery Object + Heavy World + Damping",
            "mutation_description": "Object friction 0.12, gravity -14, linear/angular damping 0.75.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {"objects": {"shape": "box", "mass": 1.0, "friction": 0.12, "x": 5.0, "y": 2.0}},
            "physics_config": {
                "gravity": (0, -14.0),
                "linear_damping": 0.75,
                "angular_damping": 0.75,
            },
        },
        {
            "stage_id": "Stage-4",
            "title": "Circular Object + Slippery + Heavy + Damping",
            "mutation_description": "Object shape=circle, friction 0.11, gravity -15, damping 0.6.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {"objects": {"shape": "circle", "mass": 1.0, "friction": 0.11, "x": 5.0, "y": 2.0}},
            "physics_config": {
                "gravity": (0, -15.0),
                "linear_damping": 0.6,
                "angular_damping": 0.6,
            },
        },
    ]
