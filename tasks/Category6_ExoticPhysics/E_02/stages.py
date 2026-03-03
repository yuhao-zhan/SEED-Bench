"""
E-02: Thick Air task curriculum stages (mutations).

All mutations use invisible physical parameters (air resistance, damping, zone strengths,
overheat limit). The solver agent is NOT told the exact parameter changes; it must infer from feedback.
Stages are ordered by increasing difficulty (Stage-1 easiest, Stage-4 hardest).
"""
from __future__ import annotations

from typing import Any, Dict, List
import re


def update_task_description_for_visible_changes(base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update task description for visible changes."""
    return base_description


def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update success criteria for visible changes."""
    criteria = base_success_criteria
    
    # Overheat limit (visible threshold change)
    target_limit = target_terrain_config.get("overheat_limit")
    base_limit = base_terrain_config.get("overheat_limit", 72000.0)
    
    if target_limit is not None and target_limit != base_limit:
        # Note: Original prompt might not have the numeric limit in text, 
        # but if it did, we'd replace it. Let's add a note if it's different.
        pattern = r"(\*\*Thermal Safety\*\*: Craft does not overheat)"
        if re.search(pattern, criteria):
            criteria = re.sub(
                pattern,
                f"\\g<1> (limit: {target_limit:.0f}, originally {base_limit:.0f} in the source environment)",
                criteria
            )
            
    return criteria


def get_e02_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns ordered stage configs for E-02 variants (difficulty ascending).
    Each stage uses physics_config only; no visible terrain changes.
    task_description_suffix is empty so the agent is not told what changed.
    """
    return [
        {
            "stage_id": "Stage-1",
            "title": "Thicker Air (higher linear damping)",
            "mutation_description": "Linear damping (air resistance) increased; craft loses speed faster.",
            "task_description_suffix": "",  # Invisible param — do not reveal
            "terrain_config": {},
            "physics_config": {
                "linear_damping": 9.0,  # default 4.0 → 9.0
            },
        },
        {
            "stage_id": "Stage-2",
            "title": "Stronger momentum drain",
            "mutation_description": "Momentum-drain zone reduces velocity much more per step; original thrust profile is insufficient.",
            "task_description_suffix": "",
            "terrain_config": {},
            "physics_config": {
                "drain_velocity_factor": 0.03,  # default 0.5 → 0.03 (extreme drain)
                "slip_backward_force": -45.0,   # default -28 → -45
                "linear_damping": 5.5,          # slightly higher air resistance so combined effect fails original
            },
        },
        {
            "stage_id": "Stage-3",
            "title": "Multiple physics shifts (damping + drain + slip)",
            "mutation_description": "Higher linear/angular damping, stronger drain, stronger slip.",
            "task_description_suffix": "",
            "terrain_config": {},
            "physics_config": {
                "linear_damping": 7.0,
                "angular_damping": 5.0,
                "drain_velocity_factor": 0.35,
                "slip_backward_force": -38.0,  # default -28 → -38
            },
        },
        {
            "stage_id": "Stage-4",
            "title": "Heavy environment (high drag, strong zones, tight heat budget)",
            "mutation_description": "Very high linear damping, strong drain, stronger wind, lower overheat limit.",
            "task_description_suffix": "",
            "terrain_config": {},
            "physics_config": {
                "linear_damping": 10.0,
                "drain_velocity_factor": 0.2,
                "wind_amplitude": 35.0,   # default 20 → 35
                "overheat_limit": 48000.0,  # default 72000 → 48000
            },
        },
    ]
