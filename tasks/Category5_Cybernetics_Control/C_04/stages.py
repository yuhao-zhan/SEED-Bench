"""
C-04: The Escaper task curriculum stages (mutations).
Solvable but distinct challenges.
"""

from __future__ import annotations

from typing import Any, Dict, List


def update_task_description_for_visible_changes(base_description: str, target_physics_config: Dict[str, Any], base_physics_config: Dict[str, Any]) -> str:
    return base_description

def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    return base_success_criteria

def get_c04_curriculum_stages() -> List[Dict[str, Any]]:
    return [
        {
            "stage_id": "Stage-1",
            "title": "Heavy Gravity",
            "mutation_description": "Gravity is -15. Cannot use ceiling for unlock.",
            "terrain_config": {},
            "physics_config": {
                "gravity": (0, -15),
            },
        },
        {
            "stage_id": "Stage-2",
            "title": "Inverted Gravity",
            "mutation_description": "Gravity is +5. Agent floats up. Must navigate ceiling.",
            "terrain_config": {},
            "physics_config": {
                "gravity": (0, 5),
            },
        },
        {
            "stage_id": "Stage-3",
            "title": "Sensor Delay",
            "mutation_description": "120-step sensor lag.",
            "terrain_config": {
                "whisker_delay_steps": 120,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-4",
            "title": "Strong Headwind",
            "mutation_description": "Strong backward current (35.0) and shear wind (80.0).",
            "terrain_config": {},
            "physics_config": {
                "current_force_back": 35.0,
                "shear_wind_gradient": 80.0,
            },
        },
    ]
