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

    Args:
        base_description: Original task description
        target_terrain_config: Target terrain configuration
        base_terrain_config: Base terrain configuration to compare against

    Returns:
        Updated task description with visible changes explicitly marked
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

    Each stage dict fields:
      - stage_id: str
      - title: str
      - mutation_description: str (for logs, not shown to solver)
      - task_description_suffix: str (generic warning, no exact numeric changes)
      - terrain_config: dict (passed to Sandbox)
      - physics_config: dict (passed to Sandbox)

    Order: Stage-1 and Stage-2 each change one param; Stage-3 and Stage-4 change multiple.
    Difficulty increases from Stage-1 to Stage-4.
    """
    return [
        {
            "stage_id": "Stage-1",
            "title": "Low Ground Friction",
            "mutation_description": "Ground friction 0.01. Extremely slippery surface.",
            "task_description_suffix": """
## Environmental Warning
Surface contact properties in this region have changed.
The ground may provide different traction than in standard conditions.
Your walker must adapt to achieve stable forward locomotion.
""",
            "terrain_config": {
                "ground_friction": 0.01,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-2",
            "title": "Restricted Joint Limits",
            "mutation_description": "Pivot joints have default angle limits ±π/20 (9°). Leg rotation severely blocked.",
            "task_description_suffix": """
## Environmental Warning
Joint behavior in this region has changed.
Pivot joints may have restricted range of motion.
Your walker design must account for these constraints.
""",
            "terrain_config": {},
            "physics_config": {
                "default_joint_lower_limit": -math.pi / 20,   # -9°
                "default_joint_upper_limit": math.pi / 20,    # +9°
            },
        },
        {
            "stage_id": "Stage-3",
            "title": "Reduced Friction + Restricted Joints",
            "mutation_description": "Ground friction 0.12 + joint limits ±π/10 (18°). Dual params.",
            "task_description_suffix": """
## Environmental Warning
Both surface contact and joint behavior have changed in this region.
Your walker must adapt to achieve stable forward locomotion under these conditions.
""",
            "terrain_config": {
                "ground_friction": 0.12,
            },
            "physics_config": {
                "default_joint_lower_limit": -math.pi / 10,   # -18°
                "default_joint_upper_limit": math.pi / 10,    # +18°
            },
        },
        {
            "stage_id": "Stage-4",
            "title": "Extreme Challenge",
            "mutation_description": "Gravity -30, ground friction 0.01, max_body_friction 0.06, joint limits ±π/24 (7.5°), damping 3.0.",
            "task_description_suffix": """
## Environmental Warning
Multiple environmental anomalies detected simultaneously.
Gravity, surface contact, joint behavior, and momentum dissipation have all changed.
This is an extreme engineering challenge requiring optimal walker design.
""",
            "terrain_config": {
                "ground_friction": 0.01,
            },
            "physics_config": {
                "gravity": (0, -30.0),
                "max_body_friction": 0.06,
                "default_joint_lower_limit": -math.pi / 24,   # -7.5°
                "default_joint_upper_limit": math.pi / 24,    # +7.5°
                "linear_damping": 3.0,
                "angular_damping": 3.0,
            },
        },
    ]
