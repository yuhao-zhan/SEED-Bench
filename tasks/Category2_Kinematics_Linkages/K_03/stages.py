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
    Order: baseline (easiest) -> Stage-1, Stage-2 (one param each) -> Stage-3, Stage-4 (multiple params), difficulty increasing.
    
    Each stage dict fields:
      - stage_id: str
      - title: str
      - mutation_description: str (for logs, not shown to solver)
      - task_description_suffix: str (generic warning for invisible changes; no exact numeric values)
      - terrain_config: dict (passed to Sandbox)
      - physics_config: dict (passed to Sandbox)
    """
    return [
        # --- Baseline (initial task: same as no env_overrides) ---
        {
            "stage_id": "baseline",
            "title": "K-03 baseline",
            "mutation_description": "Default: box object, mass 1.0 (env default), friction 0.6, gravity -10. Same as initial task.",
            "task_description_suffix": "",
            "terrain_config": {},  # Empty = use environment.py defaults (box, friction 0.6, etc.)
            "physics_config": {},
        },
        # --- Stage-1: one invisible param — very low object surface friction (extremely slippery) ---
        {
            "stage_id": "Stage-1",
            "title": "Slippery Object",
            "mutation_description": "Object surface friction reduced from 0.6 to 0.09. Object is extremely slippery; original grip slips during lift.",
            "task_description_suffix": """
## Environmental Warning
Physical contact properties in this region have changed.
The object surface may be smoother than in standard conditions; grip and friction at contact may differ.
Your gripper must achieve and maintain a secure grasp under these conditions.
""",
            "terrain_config": {"objects": {"shape": "box", "mass": 1.0, "friction": 0.09, "x": 5.0, "y": 2.0}},
            "physics_config": {},
        },
        # --- Stage-2: one invisible param — strongly increased gravity ---
        {
            "stage_id": "Stage-2",
            "title": "Heavy World",
            "mutation_description": "Gravity increased from -10 to -17 m/s². Effective load on gripper and object is much higher; original lift fails.",
            "task_description_suffix": """
## Environmental Warning
Gravitational conditions in this region have changed.
Structures and objects experience significantly higher effective weight.
Your gripper must be able to grasp and lift the object under these loads.
""",
            "terrain_config": {"objects": {"shape": "box", "mass": 1.0, "friction": 0.6, "x": 5.0, "y": 2.0}},
            "physics_config": {"gravity": (0, -17.0)},
        },
        # --- Stage-3: multiple invisible params — very slippery + heavy + strong damping ---
        {
            "stage_id": "Stage-3",
            "title": "Slippery Object + Heavy World + Damping",
            "mutation_description": "Object friction 0.12, gravity -14, linear/angular damping 0.75. Very slippery, heavy load, strong motion damping.",
            "task_description_suffix": """
## Environmental Warning
Multiple physical conditions have changed: contact properties, gravitational load, and motion resistance.
The object may be harder to grip; effective weight is increased; and motion may be more damped.
Your gripper must adapt to all these conditions to grasp and lift successfully.
""",
            "terrain_config": {"objects": {"shape": "box", "mass": 1.0, "friction": 0.12, "x": 5.0, "y": 2.0}},
            "physics_config": {
                "gravity": (0, -14.0),
                "linear_damping": 0.75,
                "angular_damping": 0.75,
            },
        },
        # --- Stage-4: multiple params including visible (object shape) + invisible ---
        {
            "stage_id": "Stage-4",
            "title": "Circular Object + Slippery + Heavy + Damping",
            "mutation_description": "Object shape=circle, friction 0.11, gravity -15, damping 0.6. Different geometry and harsher physics; original strategy fails.",
            "task_description_suffix": """
## Environmental Warning
Physical conditions and object geometry have changed (see task description for object shape).
Contact properties, gravitational load, and motion resistance may also differ from standard conditions.
Your gripper must adapt to the object shape and all physical conditions to grasp and lift successfully.
""",
            "terrain_config": {"objects": {"shape": "circle", "mass": 1.0, "friction": 0.11, "x": 5.0, "y": 2.0}},
            "physics_config": {
                "gravity": (0, -15.0),
                "linear_damping": 0.6,
                "angular_damping": 0.6,
            },
        },
    ]
