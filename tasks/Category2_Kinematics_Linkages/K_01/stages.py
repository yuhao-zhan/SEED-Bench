"""
K-01: The Walker task curriculum stages (mutations).

All stage definitions live under tasks/Category2_Kinematics_Linkages/K_01 as requested.
The solver agent is NOT told the exact parameter changes; it must infer from feedback.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List


def update_task_description_for_visible_changes(base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """
    Update task description to reflect visible physical changes.
    """
    # K-01 mutations use only invisible params
    return base_description


def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """
    Update success criteria to reflect visible physical changes.
    """
    return base_success_criteria


def get_k01_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns ordered stage configs for K-01: The Walker task variants.
    """
    task_description_suffix = """
## Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables **MIGHT** have changed from the initial environment, **NOT ALL** of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
- **Ground Friction**: The traction and slipperiness of the walking surface may be altered.
- **Joint Limits**: The permitted range of motion for the walker's pivot joints may have changed.
- **Gravity**: The magnitude and direction of the gravitational force may differ from standard.
- **Body Friction**: The friction coefficient of the walker's physical components may be adjusted.
- **Damping**: The rate at which mechanical energy and momentum are dissipated may vary.

**Discovery via feedback**: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., where a joint breaks or how a body moves) to infer the hidden constraints and adapt your design.
"""
    return [
        {
            "stage_id": "Stage-1",
            "title": "Low Ground Friction",
            "mutation_description": "Ground friction 0.01. Extremely slippery surface.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {"ground_friction": 0.01},
            "physics_config": {},
        },
        {
            "stage_id": "Stage-2",
            "title": "Restricted Joint Limits",
            "mutation_description": "Pivot joints have default angle limits \u00b1\u03c0/2 (90\u00b0). Leg rotation restricted.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {},
            "physics_config": {
                "default_joint_lower_limit": -math.pi / 2,
                "default_joint_upper_limit": math.pi / 2,
            },
        },
        {
            "stage_id": "Stage-3",
            "title": "Reduced Friction + Restricted Joints",
            "mutation_description": "Ground friction 0.12 + joint limits \u00b1\u03c0/2 (90\u00b0). Dual params.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {"ground_friction": 0.12},
            "physics_config": {
                "default_joint_lower_limit": -math.pi / 2,
                "default_joint_upper_limit": math.pi / 2,
            },
        },
        {
            "stage_id": "Stage-4",
            "title": "Extreme Challenge",
            "mutation_description": "Gravity -30, ground friction 0.01, max_body_friction 0.06, joint limits \u00b1\u03c0/2 (90\u00b0), damping 3.0.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {"ground_friction": 0.01},
            "physics_config": {
                "gravity": (0, -30.0),
                "max_body_friction": 0.06,
                "default_joint_lower_limit": -math.pi / 2,
                "default_joint_upper_limit": math.pi / 2,
                "linear_damping": 3.0,
                "angular_damping": 3.0,
            },
        },
    ]
