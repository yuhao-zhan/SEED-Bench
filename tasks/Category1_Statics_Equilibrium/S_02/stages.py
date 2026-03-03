"""
S-02: The Skyscraper task curriculum stages (mutations).

Mutated tasks change invisible physical parameters: earthquake amplitude/frequency, 
wind force, gravity, damping. The solver agent must infer from feedback.
"""

from __future__ import annotations

from typing import Any, Dict, List


def update_task_description_for_visible_changes(base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update task description for visible changes."""
    return base_description


def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update success criteria for visible changes."""
    return base_success_criteria


def get_s02_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns ordered stage configs for S-02: The Skyscraper task variants.
    """
    return [
        {
            "stage_id": "Stage-1",
            "title": "Increased Earthquake Amplitude",
            "mutation_description": "Earthquake amplitude increased significantly. Original design will fail due to larger displacement.",
            "task_description_suffix": """
## Environmental Warning
Seismic activity in this region is significantly more intense than nominal. 
Large ground displacements are expected. Your tower must be flexible yet stable.
""",
            "terrain_config": {
                "earthquake_amplitude": 12.0, # Increased from 5.0
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-2",
            "title": "Increased Wind Force",
            "mutation_description": "Wind force increased. Structure needs better lateral resistance.",
            "task_description_suffix": """
## Environmental Warning
High-altitude winds are much stronger than nominal. 
The lateral pressure on the upper sections of your tower will be severe.
""",
            "terrain_config": {
                "wind_force": 1200.0, # Increased from 400.0
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-3",
            "title": "High-Frequency Earthquake",
            "mutation_description": "Earthquake frequency increased significantly. Resonance tuning is critical.",
            "task_description_suffix": """
## Environmental Warning
The frequency of seismic oscillations has shifted. 
Structures with certain natural frequencies may experience resonance.
""",
            "terrain_config": {
                "earthquake_amplitude": 1.5,
                "earthquake_frequency": 15.0,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-4",
            "title": "The Perfect Storm",
            "mutation_description": "Combined high-frequency, high-amplitude earthquake and strong wind.",
            "task_description_suffix": """
## Environmental Warning
Multiple extreme environmental factors are present. 
High-frequency seismic waves and intense high-altitude winds occur simultaneously.
This is an extreme engineering challenge.
""",
            "terrain_config": {
                "earthquake_amplitude": 2.5,
                "earthquake_frequency": 12.0,
                "wind_force": 800.0,
            },
            "physics_config": {
                "gravity": (0, -12.0),
            },
        },
    ]
