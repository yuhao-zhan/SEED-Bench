"""
S-05: The Shelter task curriculum stages (mutations).
"""

from __future__ import annotations

from typing import Any, Dict, List
import re

# Base task defaults (must match environment.py and prompt.py)
DEFAULT_METEOR_COUNT = 12
DEFAULT_CORE_MAX_FORCE = 150.0
DEFAULT_MAX_MASS = 300.0
DEFAULT_METEOR_SPAWN_INTERVAL = 30


def update_task_description_for_visible_changes(base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    description = base_description
    
    target_core_force = target_terrain_config.get("max_core_force", DEFAULT_CORE_MAX_FORCE)
    base_core_force = base_terrain_config.get("max_core_force", DEFAULT_CORE_MAX_FORCE)
    
    target_max_mass = target_terrain_config.get("max_structure_mass", DEFAULT_MAX_MASS)
    base_max_mass = base_terrain_config.get("max_structure_mass", DEFAULT_MAX_MASS)
    
    target_meteor_count = target_terrain_config.get("meteor_count", DEFAULT_METEOR_COUNT)
    base_meteor_count = base_terrain_config.get("meteor_count", DEFAULT_METEOR_COUNT)

    if target_core_force != base_core_force:
        description = re.sub(r"exceeds \d+\.?\d*N", f"exceeds {target_core_force:.1f}N (originally {base_core_force:.1f}N in the source environment)", description, 1)
        description = re.sub(r"< \d+\.?\d*N", f"< {target_core_force:.1f}N (originally < {base_core_force:.1f}N in the source environment)", description, 1)

    if target_max_mass != base_max_mass:
        description = re.sub(
            r"less than \d+\.?\d* kg",
            f"less than {target_max_mass:.1f} kg (originally less than {base_max_mass:.1f} kg in the source environment)",
            description,
            1,
        )

    if target_meteor_count != base_meteor_count:
        description = re.sub(
            r"\d+ boulders",
            f"{target_meteor_count:.0f} boulders (originally {base_meteor_count} boulders in the source environment)",
            description,
            1,
        )

    return description


def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    criteria = base_success_criteria

    target_core_force = target_terrain_config.get("max_core_force", DEFAULT_CORE_MAX_FORCE)
    base_core_force = base_terrain_config.get("max_core_force", DEFAULT_CORE_MAX_FORCE)
    
    target_max_mass = target_terrain_config.get("max_structure_mass", DEFAULT_MAX_MASS)
    base_max_mass = base_terrain_config.get("max_structure_mass", DEFAULT_MAX_MASS)

    if target_core_force != base_core_force:
        criteria = re.sub(
            r"exceeding its \d+\.?\d*N",
            f"exceeding its {target_core_force:.1f}N (originally {base_core_force:.1f}N in the source environment)",
            criteria,
            1,
        )

    if target_max_mass != base_max_mass:
        criteria = re.sub(
            r"< \d+\.?\d* kg",
            f"< {target_max_mass:.1f} kg (originally < {base_max_mass:.1f} kg in the source environment)",
            criteria,
            1,
        )

    return criteria


def get_s05_curriculum_stages() -> List[Dict[str, Any]]:
    return [
        {
            "stage_id": "Stage-1",
            "title": "Extreme Gravity",
            "mutation_description": "Gravity increased to -40 m/s². The weak baseline shelter will fail under high-impact loads.",
            "task_description_suffix": """
## Environmental Warning
Gravity in this region is extremely high.
Falling objects gain immense kinetic energy.
Your shelter must be significantly more robust.
""",
            "terrain_config": {},
            "physics_config": {
                "gravity": (0, -40.0),
            },
        },
        {
            "stage_id": "Stage-2",
            "title": "Endless Bombardment",
            "mutation_description": "Meteor count increased to 128. Baseline shelter will fail due to sustained bombardment.",
            "task_description_suffix": """
## Environmental Warning
The meteor storm in this region is exceptionally long.
Expect a sustained barrage of boulders.
Your shelter must maintain structural integrity over many impacts.
""",
            "terrain_config": {
                "meteor_count": 128,
                "meteor_spawn_interval": 8,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-3",
            "title": "Fragile Core",
            "mutation_description": "Core max force reduced to 10.0N. Requires extreme precision in shock absorption.",
            "task_description_suffix": """
## Environmental Warning
The core in this region is dangerously fragile.
Only the most minimal impact forces are permitted.
Your shelter must be designed for maximum deflection or absorption.
""",
            "terrain_config": {
                "max_core_force": 10.0,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-4",
            "title": "Extreme Constraints",
            "mutation_description": "Gravity -30, 48 meteors, core force 80.0N, max mass 150.0kg.",
            "task_description_suffix": """
## Environmental Warning
Multiple severe environmental stressors are present.
High gravity, sustained barrage, and a fragile core, all with a limited mass budget.
This is the ultimate test of structural efficiency.
""",
            "terrain_config": {
                "meteor_count": 48,
                "meteor_spawn_interval": 10,
                "max_core_force": 80.0,
                "max_structure_mass": 150.0,
            },
            "physics_config": {
                "gravity": (0, -30.0),
            },
        },
    ]
