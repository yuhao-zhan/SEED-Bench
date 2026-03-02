"""
D-04: The Swing curriculum stages (mutations).

Stage-1 and Stage-2: one physical parameter change each (invisible).
Stage-3 and Stage-4: multiple parameter changes. Difficulty increases Stage-1 → Stage-4.
All changes here are invisible (gravity, damping, wind period); do NOT tell the agent
exact values in the prompt — they must infer from environment feedback.
"""

from __future__ import annotations

from typing import Any, Dict, List

# Generic warning for invisible env changes (no exact parameter values)
_INVISIBLE_ENV_WARNING = """
## Environmental Note
Physical conditions in this stage may differ from the default. Use simulation feedback to adapt your strategy.
"""


def update_task_description_for_visible_changes(base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update task description for visible changes."""
    return base_description


def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update success criteria for visible changes."""
    return base_success_criteria


def get_d04_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Return ordered stage configs for D-04 mutated tasks.
    Order: Stage-1 (one param) → Stage-2 (one param) → Stage-3 (multi) → Stage-4 (multi).
    Difficulty increases so that the reference solution fails in each mutated environment.
    """
    return [
        {
            "stage_id": "Stage-1",
            "title": "Stronger Gravity",
            "mutation_description": "Gravity increased to -15.5 m/s². Swing period shorter, apex lower; original tuning under-pumps.",
            "task_description_suffix": _INVISIBLE_ENV_WARNING,
            "terrain_config": {},
            "physics_config": {"gravity": (0, -15.5)},
        },
        {
            "stage_id": "Stage-2",
            "title": "High Damping",
            "mutation_description": "Seat linear/angular damping increased. More energy loss per cycle.",
            "task_description_suffix": _INVISIBLE_ENV_WARNING,
            "terrain_config": {
                "seat_linear_damping": 0.28,
                "seat_angular_damping": 0.28,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-3",
            "title": "Heavy World and Damping",
            "mutation_description": "Gravity -13 m/s² + increased seat damping. Dual invisible params.",
            "task_description_suffix": _INVISIBLE_ENV_WARNING,
            "terrain_config": {
                "seat_linear_damping": 0.22,
                "seat_angular_damping": 0.22,
            },
            "physics_config": {"gravity": (0, -13.0)},
        },
        {
            "stage_id": "Stage-4",
            "title": "Extreme Conditions",
            "mutation_description": "Gravity -15 m/s² + high seat damping + different wind period. Original wind-aware timing fails.",
            "task_description_suffix": _INVISIBLE_ENV_WARNING,
            "terrain_config": {
                "seat_linear_damping": 0.32,
                "seat_angular_damping": 0.32,
                "wind_period": 2.2,
            },
            "physics_config": {"gravity": (0, -15.0)},
        },
    ]
