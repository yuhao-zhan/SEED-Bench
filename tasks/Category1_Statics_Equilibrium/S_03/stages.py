"""
S-03: The Cantilever task curriculum stages (mutations).

Mutated tasks vary invisible physical parameters: obstacle positions, dynamic loads,
forbidden anchor zones, anchor strength, target reach, gravity.
"""

from __future__ import annotations

from typing import Any, Dict, List
import re


def update_task_description_for_visible_changes(base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update task description for visible changes."""
    description = base_description
    target_reach = target_terrain_config.get("target_reach", 12.0)
    base_reach = base_terrain_config.get("target_reach", 12.0)
    if target_reach != base_reach:
        pattern = r"(- \*\*Goal\*\*: Reach x >= )(\d+\.?\d*)m"
        description = re.sub(pattern, f"\\g<1>{target_reach:.1f}m (originally {base_reach:.1f}m)", description)
    return description


def update_success_criteria_for_visible_criteria(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update success criteria for visible changes."""
    criteria = base_success_criteria
    target_reach = target_terrain_config.get("target_reach", 12.0)
    base_reach = base_terrain_config.get("target_reach", 12.0)
    if target_reach != base_reach:
        pattern = r"(Tip reaches x >= )(\d+\.?\d*)m"
        criteria = re.sub(pattern, f"\\g<1>{target_reach:.1f}m (originally {base_reach:.1f}m)", criteria)
    return criteria


def get_s03_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns ordered stage configs for S-03: The Cantilever task variants.
    Targets set to 30m+ to ensure the ~24m reference agents fail.
    """
    return [
        {
            "stage_id": "Stage-1",
            "title": "Structural Obstruction",
            "mutation_description": "Obstacle + extreme reach. Mutated solution must reach 30m.",
            "task_description_suffix": """
## Environmental Warning
A structural obstruction is present. The target reach has been significantly increased.
""",
            "terrain_config": {
                "obstacle_active": True,
                "obstacle_rect": [6.0, 0.0, 8.5, 3.5],
                "target_reach": 30.0, 
                "load_mass": 1500.0, 
                "max_structure_mass": 5000.0,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-2",
            "title": "Dynamic Impact Loading",
            "mutation_description": "Impact load + extreme reach.",
            "task_description_suffix": """
## Environmental Warning
Secondary loads involve dynamic impacts. Target reach and mass budget updated.
""",
            "terrain_config": {
                "drop_load": True,
                "drop_mass": 800.0,
                "target_reach": 30.0,
                "forbidden_anchor_y": [0.8, 1.2],
                "load_mass": 1200.0,
                "max_structure_mass": 5000.0,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-3",
            "title": "Restricted Anchor Zones",
            "mutation_description": "Corroded wall. Target reach 30m.",
            "task_description_suffix": """
## Environmental Warning
Anchor heights are restricted. Local gravity is higher. Target reach updated.
""",
            "terrain_config": {
                "forbidden_anchor_y": [0.5, 1.5],
                "target_reach": 30.0,
                "max_anchor_force": 1200.0, 
                "load_mass": 800.0,
                "max_structure_mass": 5000.0,
            },
            "physics_config": {
                "gravity": (0, -15.0),
            },
        },
        {
            "stage_id": "Stage-4",
            "title": "The Perfect Storm",
            "mutation_description": "Extreme challenge. Target reach 32m.",
            "task_description_suffix": """
## Environmental Warning
Multiple extreme factors present. Target reach updated.
""",
            "terrain_config": {
                "obstacle_active": True,
                "obstacle_rect": [5.5, -1.0, 7.5, 2.0],
                "drop_load": True,
                "forbidden_anchor_y": [0.2, 1.8],
                "max_anchor_force": 1000.0,
                "target_reach": 32.0, 
                "load_mass": 1500.0, 
                "max_structure_mass": 6000.0,
            },
            "physics_config": {
                "gravity": (0, -18.0), 
            },
        },
    ]
