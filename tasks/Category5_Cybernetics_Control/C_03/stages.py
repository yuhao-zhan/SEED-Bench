"""
C-03: The Seeker task curriculum stages (mutations).

Four mutated tasks in total: Stage-1 through Stage-4, difficulty ascending.
"""

from __future__ import annotations
from typing import Any, Dict, List

def get_c03_curriculum_stages() -> List[Dict[str, Any]]:
    task_description_suffix = "## Environmental Anomalies Detected"
    return [
        {
            "stage_id": "Stage-1",
            "title": "Sonic Storm",
            "mutation_description": "Target speed increased, budget tightened.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {
                "target_speed": 1.8,
                "impulse_budget": 25000.0,
                "track_distance": 15.0,
                "obstacles": [],
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-2",
            "title": "Hurricane Void",
            "mutation_description": "Zero friction + Opposing wind.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {
                "ground_friction": 0.0,
                "impulse_budget": 100000.0,
                "spawn_x": 15.0,
                "obstacles": [],
            },
            "physics_config": {
                "gravity": (-5.0, 0.0), # Lateral gravity only
            },
        },
        {
            "stage_id": "Stage-3",
            "title": "Submerged Abyss",
            "mutation_description": "Extreme linear damping.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {
                "impulse_budget": 200000.0,
                "obstacles": [],
            },
            "physics_config": {
                "linear_damping": 5.0,
            },
        },
        {
            "stage_id": "Stage-4",
            "title": "Critical Resource Scarcity",
            "mutation_description": "Extremely tight impulse budget.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {
                "impulse_budget": 8000.0,
                "obstacles": [],
            },
            "physics_config": {},
        },
    ]
