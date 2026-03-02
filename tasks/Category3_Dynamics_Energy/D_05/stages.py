"""
D-05: The Hammer curriculum stages (mutations).

Stage-1 and Stage-2: one physical parameter change each (invisible).
Stage-3 and Stage-4: multiple parameter changes. Difficulty increases Stage-1 → Stage-4.
All changes are invisible (shell hardness, slot bar phase/omega, gravity, damping);
do NOT tell the agent exact values in the prompt — they must infer from environment feedback.
"""
from __future__ import annotations
from typing import Any, Dict, List

# Generic warning for invisible env changes (no exact parameter values)
_INVISIBLE_ENV_WARNING = """
## Environmental Note
Physical conditions in this stage may differ from the default. Use simulation feedback to adapt your strategy (e.g. timing, impact strength).
"""


def update_task_description_for_visible_changes(base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update task description for visible changes."""
    return base_description


def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update success criteria for visible changes."""
    return base_success_criteria


def get_d05_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Return ordered stage configs for D-05 mutated tasks.
    Order: Stage-1 (one param) → Stage-2 (one param) → Stage-3 (multi) → Stage-4 (multi).
    Difficulty increases so that the reference solution fails in each mutated environment.
    """
    return [
        {
            "stage_id": "Stage-1",
            "title": "Harder Shell",
            "mutation_description": "Shell break threshold increased (16000 N). Original impact does not break.",
            "task_description_suffix": _INVISIBLE_ENV_WARNING,
            "terrain_config": {"shell_break_force": 16000.0},
            "physics_config": {},
        },
        {
            "stage_id": "Stage-2",
            "title": "Shifted Slot Bar Phase",
            "mutation_description": "Slot oscillating bar omega 0.014; safe window at step ~336. Original 380/398/408 timing hits bar.",
            "task_description_suffix": _INVISIBLE_ENV_WARNING,
            "terrain_config": {"slot_bar_omega": 0.014},
            "physics_config": {},
        },
        {
            "stage_id": "Stage-3",
            "title": "Harder Shell and Damping",
            "mutation_description": "Shell break 13000 N + angular damping 0.6. Less kinetic energy at impact; original swing insufficient.",
            "task_description_suffix": _INVISIBLE_ENV_WARNING,
            "terrain_config": {"shell_break_force": 13000.0},
            "physics_config": {"angular_damping": 0.6},
        },
        {
            "stage_id": "Stage-4",
            "title": "Gravity, Shell, Bar Phase and Damping",
            "mutation_description": "Gravity -14, shell 11000 N, slot_bar_omega 0.013, angular_damping 0.35. Multi-parameter; original timing and impact fail.",
            "task_description_suffix": _INVISIBLE_ENV_WARNING,
            "terrain_config": {"shell_break_force": 11000.0, "slot_bar_omega": 0.013},
            "physics_config": {"gravity": (0, -14.0), "angular_damping": 0.35},
        },
    ]
