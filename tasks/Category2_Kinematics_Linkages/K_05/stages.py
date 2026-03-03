"""
K-05: The Lifter task curriculum stages (mutations).

All stage definitions live under tasks/Category2_Kinematics_Linkages/K_05.
The solver agent is NOT told exact invisible parameter changes; it must infer from feedback.
Visible changes (e.g. target lift height) are reflected in task_description_suffix.
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
    Difficulty: Stage-1 < Stage-2 < Stage-3 < Stage-4.
    Stage-1/2: single parameter change (invisible). Stage-3/4: multiple (with visible target height when changed).

    Each stage dict fields:
      - stage_id: str
      - title: str
      - mutation_description: str (for logs, not shown to solver)
      - task_description_suffix: str (generic warning for invisible; explicit for visible e.g. target height)
      - terrain_config: dict (passed to Sandbox)
      - physics_config: dict (passed to Sandbox)
    """
    return [
        {
            "stage_id": "Stage-1",
            "title": "Increased Gravity",
            "mutation_description": "Gravity increased from -10 to -28 m/s². Structure and motors experience much higher loads.",
            "task_description_suffix": """
## Environmental Warning
Physical conditions in this region have changed.
Structures and actuators experience significantly increased loads.
Your lifter must be designed to withstand higher structural stresses and deliver sufficient torque.
""",
            "terrain_config": {},
            "physics_config": {
                "gravity": (0, -28.0),
            },
        },
        {
            "stage_id": "Stage-2",
            "title": "Heavier Object",
            "mutation_description": "Object mass increased from 20kg to 50kg. Much higher load on structure and motors.",
            "task_description_suffix": """
## Environmental Warning
The load to be lifted has changed.
Your lifter must be able to support and lift the object reliably to the target height.
""",
            "terrain_config": {
                "object": {"mass": 50.0, "friction": 0.6},
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-3",
            "title": "Higher Target + Heavier Object",
            "mutation_description": "Target height 10.5m (was 9m), object mass 42kg. Visible: target height; invisible: mass.",
            "task_description_suffix": """
## Environmental Warning (visible change)
**The target lift height has been changed.** The object must be lifted to **at least 9.5 meters above ground (y >= 10.5m)**.
The red line in the environment indicates the new required height.
Load conditions may also differ; your lifter must adapt to reach and sustain the new target.
""",
            "terrain_config": {
                "target_object_y": 10.5,
                "object": {"mass": 42.0, "friction": 0.6},
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-4",
            "title": "Multi-Parameter Challenge",
            "mutation_description": "Gravity -16, object 46kg, target 10m, reduced ground friction 0.4. Combined stress.",
            "task_description_suffix": """
## Environmental Warning (visible change)
**The target lift height has been changed.** The object must be lifted to **at least 9 meters above ground (y >= 10m)**.
The red line indicates the new required height.
Multiple physical conditions have changed; structures experience higher loads and contact behavior may differ.
Your lifter must be designed to reach the new height and sustain the object under these conditions.
""",
            "terrain_config": {
                "target_object_y": 10.0,
                "ground_friction": 0.4,
                "object": {"mass": 46.0, "friction": 0.6},
            },
            "physics_config": {
                "gravity": (0, -16.0),
            },
        },
    ]
