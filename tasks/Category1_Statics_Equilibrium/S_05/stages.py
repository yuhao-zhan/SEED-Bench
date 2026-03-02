"""
S-05: The Shelter task curriculum stages (mutations).

All stage definitions live under tasks/Category1_Statics_Equilibrium/S_05.
The solver agent is NOT told the exact parameter changes; it must infer from feedback.
Base task (no mutation): 14N core, 120kg max mass, 28×260kg meteors, 0.85s spawn, 2/3 center, gravity -10, keep-out 1.3m, height 4.5m.
Stages are ordered by difficulty: Stage-1 (one invisible param) < Stage-2 (one) < Stage-3 (multi) < Stage-4 (multi, extreme).
"""

from __future__ import annotations

from typing import Any, Dict, List
import re

# Base task defaults (must match environment.py and prompt.py)
DEFAULT_METEOR_MASS = 260.0
DEFAULT_METEOR_COUNT = 28
DEFAULT_CORE_MAX_FORCE = 14.0
DEFAULT_MAX_MASS = 120.0
DEFAULT_METEOR_SPAWN_INTERVAL = 0.85


def update_task_description_for_visible_changes(base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """
    Update task description to reflect visible physical changes (e.g., meteor mass, core force limit, max mass).
    For invisible physical parameters (gravity, spawn_interval, earthquake, wind), changes are NOT reflected in description.
    """
    description = base_description

    target_meteor_mass = target_terrain_config.get("meteor_mass", DEFAULT_METEOR_MASS)
    base_meteor_mass = base_terrain_config.get("meteor_mass", DEFAULT_METEOR_MASS)
    
    target_core_force = target_terrain_config.get("core_max_force", DEFAULT_CORE_MAX_FORCE)
    base_core_force = base_terrain_config.get("core_max_force", DEFAULT_CORE_MAX_FORCE)
    
    target_max_mass = target_terrain_config.get("max_mass", DEFAULT_MAX_MASS)
    base_max_mass = base_terrain_config.get("max_mass", DEFAULT_MAX_MASS)
    
    target_meteor_count = target_terrain_config.get("meteor_count", DEFAULT_METEOR_COUNT)
    base_meteor_count = base_terrain_config.get("meteor_count", DEFAULT_METEOR_COUNT)

    if target_meteor_mass != base_meteor_mass:
        description = re.sub(
            r"28 boulders \(260kg each\)",
            f"28 boulders (260kg each) (FROM: {base_meteor_mass:.0f}kg, TO: {target_meteor_mass:.0f}kg)",
            description,
            1,
        )
        description = re.sub(
            r"Meteors are 260kg and",
            f"Meteors are 260kg (FROM: {base_meteor_mass:.0f}kg, TO: {target_meteor_mass:.0f}kg) and",
            description,
            1,
        )

    if target_core_force != base_core_force:
        description = re.sub(r"exceeds 14N", f"exceeds 14N (FROM: {base_core_force:.0f}N, TO: {target_core_force:.0f}N)", description, 1)
        description = re.sub(r"Force > 14N", f"Force > 14N (FROM: {base_core_force:.0f}N, TO: {target_core_force:.0f}N)", description, 1)
        description = re.sub(r"stay < 14N", f"stay < 14N (FROM: {base_core_force:.0f}N, TO: {target_core_force:.0f}N)", description, 1)

    if target_max_mass != base_max_mass:
        description = re.sub(
            r"mass budget \(120kg\)",
            f"mass budget (120kg) (FROM: {base_max_mass:.0f}kg, TO: {target_max_mass:.0f}kg)",
            description,
            1,
        )
        description = re.sub(
            r"must be < 120kg",
            f"must be < 120kg (FROM: {base_max_mass:.0f}kg, TO: {target_max_mass:.0f}kg)",
            description,
            1,
        )

    if target_meteor_count != base_meteor_count:
        description = re.sub(
            r"\d+ boulders \(\d+kg each\)",
            f"{target_meteor_count:.0f} boulders ({target_meteor_mass:.0f}kg each) (FROM: {base_meteor_count} meteors, TO: {target_meteor_count} meteors)",
            description,
            1,
        )

    return description


def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """
    Update success criteria to reflect visible physical changes (core force limit, max mass).
    """
    criteria = base_success_criteria

    target_core_force = target_terrain_config.get("core_max_force", DEFAULT_CORE_MAX_FORCE)
    base_core_force = base_terrain_config.get("core_max_force", DEFAULT_CORE_MAX_FORCE)
    
    target_max_mass = target_terrain_config.get("max_mass", DEFAULT_MAX_MASS)
    base_max_mass = base_terrain_config.get("max_mass", DEFAULT_MAX_MASS)

    if target_core_force != base_core_force:
        criteria = re.sub(
            r"exceed 14N",
            f"exceed 14N (FROM: {base_core_force:.0f}N, TO: {target_core_force:.0f}N)",
            criteria,
            1,
        )
        criteria = re.sub(
            r"stay < 14N",
            f"stay < 14N (FROM: {base_core_force:.0f}N, TO: {target_core_force:.0f}N)",
            criteria,
            1,
        )
        criteria = re.sub(
            r"Max force on core must stay < 14N",
            f"Max force on core must stay < 14N (FROM: {base_core_force:.0f}N, TO: {target_core_force:.0f}N)",
            criteria,
            1,
        )

    if target_max_mass != base_max_mass:
        criteria = re.sub(
            r"Max mass 120kg",
            f"Max mass 120kg (FROM: {base_max_mass:.0f}kg, TO: {target_max_mass:.0f}kg)",
            criteria,
            1,
        )
        criteria = re.sub(
            r"must be < 120kg",
            f"must be < 120kg (FROM: {base_max_mass:.0f}kg, TO: {target_max_mass:.0f}kg)",
            criteria,
            1,
        )

    return criteria


def get_s05_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns ordered stage configs for S-05: The Shelter task variants.
    Difficulty: Stage-1 < Stage-2 < Stage-3 < Stage-4.
    Stage-1/2: one physical/environment parameter each (prefer not directly visible).
    Stage-3/4: multiple parameters; Stage-4 is extreme.
    """
    return [
        {
            "stage_id": "Stage-1",
            "title": "Increased Gravity",
            "mutation_description": "Gravity increased from -10 to -32 m/s². Structural loads and meteor impact energy both rise significantly (invisible physical change).",
            "task_description_suffix": """
## Environmental Warning
Physical conditions in this region have changed.
Structures experience higher loads and impacts are more energetic.
Your shelter must be designed for these harsher conditions.
""",
            "terrain_config": {},
            "physics_config": {
                "gravity": (0, -40.0),  # Base is (0, -10); ref passed at -32
            },
        },
        {
            "stage_id": "Stage-2",
            "title": "Heavier Meteors",
            "mutation_description": "Meteor mass increased from 260kg to 340kg. Impacts are more energetic (one physical parameter).",
            "task_description_suffix": """
## Environmental Warning
Meteor characteristics have changed in this region.
Impactors are heavier and deliver more energy per impact.
Your shelter must absorb or deflect more energetic impacts.
""",
            "terrain_config": {
                "meteor_mass": 480.0,  # Base is 260; ref passed at 420
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-3",
            "title": "Stricter Core + Heavier Gravity + Denser Barrage",
            "mutation_description": "Core 6N, gravity -28, spawn 0.3s, earthquake 3Hz 6.5 m/s². Multiple physical/environment changes.",
            "task_description_suffix": """
## Environmental Warning
Multiple physical parameters have changed in this region.
The core is more fragile, structural loads are higher, impacts are more frequent, and seismic activity is present.
Your shelter must satisfy stricter protection and withstand combined stresses.
""",
            "terrain_config": {
                "core_max_force": 6.0,  # Very strict; ref solution fails
                "meteor_spawn_interval": 0.3,
            },
            "physics_config": {
                "gravity": (0, -28.0),
                "earthquake_enabled": True,
                "earthquake_frequency": 3.0,
                "earthquake_amplitude": 6.5,
                "earthquake_direction": "horizontal",
            },
        },
        {
            "stage_id": "Stage-4",
            "title": "Extreme Challenge",
            "mutation_description": "Gravity -22, earthquake (2.5Hz, 5.0 m/s²), wind 15 N/kg, core 12N, max mass 130kg. Multiple severe environmental stresses.",
            "task_description_suffix": """
## Environmental Warning
Multiple severe environmental anomalies are present simultaneously.
This region has increased gravity, continuous seismic activity, and strong wind.
The core is very fragile and material budget is reduced.
Your shelter must withstand all these forces while protecting the core with limited mass.
Consider robust joints, efficient layout, and deflection strategies.
""",
            "terrain_config": {
                "core_max_force": 12.0,
                "max_mass": 130.0,
            },
            "physics_config": {
                "gravity": (0, -22.0),
                "earthquake_enabled": True,
                "earthquake_frequency": 2.5,
                "earthquake_amplitude": 5.0,
                "earthquake_direction": "horizontal",
                "wind_enabled": True,
                "wind_force": 15.0,
                "wind_direction": 1.0,
            },
        },
    ]
