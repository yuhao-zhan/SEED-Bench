"""
K-02: The Climber task curriculum stages (mutations).

All stage definitions live under tasks/Category2_Kinematics_Linkages/K_02.
The solver agent is NOT told the exact parameter changes; it must infer from feedback.
Stages are ordered by increasing difficulty: Stage-1 (single change) → Stage-4 (multiple, extreme).
"""

from __future__ import annotations

from typing import Any, Dict, List


def update_task_description_for_visible_changes(base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """
    Update task description to reflect visible physical changes only.
    """
    return base_description


def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update success criteria for visible changes only."""
    return base_success_criteria


def get_k02_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns ordered stage configs for K-02: The Climber task variants.
    Difficulty: Stage-1 < Stage-2 < Stage-3 < Stage-4.
    Each stage is designed so the reference solution (suction pads + rotating legs) fails;
    the solver must adapt (e.g. more pads, different friction, motor timing) to pass.

    Each stage dict fields:
      - stage_id: str
      - title: str
      - mutation_description: str (for logs, not shown to solver)
      - task_description_suffix: str (generic warning, no exact numeric changes)
      - terrain_config: dict (passed to Sandbox)
      - physics_config: dict (passed to Sandbox)
    """
    return [
        {
            "stage_id": "Stage-1",
            "title": "Low Wall Friction",
            "mutation_description": "Wall friction reduced from 1.0 to 0.12. Legs and pads slip very easily; original grip is insufficient.",
            "task_description_suffix": """
## Environmental Warning
Physical conditions at the wall have changed.
Surface contact properties may differ from standard assumptions.
Your climber must achieve reliable attachment and upward motion under these conditions.
""",
            "terrain_config": {
                "wall_friction": 0.12,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-2",
            "title": "Increased Gravity",
            "mutation_description": "Gravity increased from -8 to -20 m/s². Climber experiences much higher effective weight; pads and motors insufficient.",
            "task_description_suffix": """
## Environmental Warning
Physical conditions in this region have changed.
Structures experience significantly increased loads.
Your climber must be designed to maintain wall attachment and upward motion under higher stress.
""",
            "terrain_config": {},
            "physics_config": {
                "gravity": (0, -20.0),
            },
        },
        {
            "stage_id": "Stage-3",
            "title": "Reduced Friction + Increased Gravity",
            "mutation_description": "Wall friction 0.20, gravity -16 m/s². Combined: harder to grip and heavier; original design slips or cannot lift.",
            "task_description_suffix": """
## Environmental Warning
Physical conditions and surface contact properties have changed simultaneously.
Loads are higher and grip may be reduced.
Your climber must adapt to maintain wall attachment and sustained upward motion.
""",
            "terrain_config": {
                "wall_friction": 0.20,
            },
            "physics_config": {
                "gravity": (0, -16.0),
            },
        },
        {
            "stage_id": "Stage-4",
            "title": "Extreme: Low Friction + High Gravity + Weaker Suction",
            "mutation_description": "Wall friction 0.14, gravity -20 m/s², pad force scale 35 and max 22 N. Maximum difficulty: slip, weight, and reduced adhesion.",
            "task_description_suffix": """
## Environmental Warning
Multiple environmental factors have changed.
Loads, surface properties, and adhesion conditions differ from standard assumptions.
Your climber must be robust to these combined changes to maintain wall attachment and upward motion.
""",
            "terrain_config": {
                "wall_friction": 0.14,
            },
            "physics_config": {
                "gravity": (0, -20.0),
                "pad_force_scale": 35.0,
                "max_pad_force": 22.0,
            },
        },
    ]
