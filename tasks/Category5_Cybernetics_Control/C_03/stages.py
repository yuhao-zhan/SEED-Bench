"""
C-03: The Seeker task curriculum stages (mutations).

Five tasks in total: baseline (no mutation) + Stage-1 through Stage-4, difficulty ascending.
Mutated tasks change invisible physical parameters (target speed, ground friction, damping, impulse budget).
Do NOT reveal exact parameter values in task_description_suffix; agent must infer from feedback.
- Stage-1 / Stage-2: single parameter change each (hard enough that reference solution fails).
- Stage-3 / Stage-4: multiple parameter changes; difficulty increases.
"""

from __future__ import annotations

from typing import Any, Dict, List


def update_task_description_for_visible_changes(base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update task description for visible changes."""
    return base_description


def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update success criteria for visible changes."""
    return base_success_criteria


def get_c03_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns ordered stage configs for C-03: The Seeker task variants.
    """
    return [
        {
            "stage_id": "Stage-1",
            "title": "Faster target",
            "mutation_description": "Target base speed increased; velocity matching and slot timing harder.",
            "task_description_suffix": """
## Environmental note
External object motion may be more dynamic than in the nominal setting. Use simulation feedback to adapt your approach and timing.
""",
            "terrain_config": {
                "target_speed": 2.2,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-2",
            "title": "Strict Rendezvous and Budget",
            "mutation_description": "Stricter rendezvous conditions and tight impulse budget.",
            "task_description_suffix": """
## Environmental note
Resource availability and rendezvous requirements differ from nominal. Precise, efficient control is required.
""",
            "terrain_config": {
                "rendezvous_distance": 2.5,
                "rendezvous_rel_speed": 0.8,
                "impulse_budget": 8500.0,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-3",
            "title": "Strict Rendezvous and Damping",
            "mutation_description": "Stricter distance and speed requirements for rendezvous with higher damping.",
            "task_description_suffix": """
## Environmental note
Rendezvous requirements and vehicle dynamics are more demanding in this region. Precise positioning and velocity matching are critical.
""",
            "terrain_config": {
                "rendezvous_distance": 3.0,
                "rendezvous_rel_speed": 1.0,
            },
            "physics_config": {
                "linear_damping": 0.85,
                "angular_damping": 0.85,
            },
        },
        {
            "stage_id": "Stage-4",
            "title": "Hostile Seeker Environment",
            "mutation_description": "Extreme target speed, negligible friction, very tight budget.",
            "task_description_suffix": """
## Environmental note
Physical environment is highly hostile. External dynamics, traction, and resource constraints differ severely from nominal.
""",
            "terrain_config": {
                "target_speed": 2.8,
                "ground_friction": 0.01,
                "impulse_budget": 9000.0,
                "rendezvous_distance": 2.5,
                "rendezvous_rel_speed": 0.8,
            },
            "physics_config": {
                "linear_damping": 0.9,
                "angular_damping": 0.9,
            },
        },
    ]
