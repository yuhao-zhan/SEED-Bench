"""
S-06: The Overhang task curriculum stages (mutations).
Redesigned for extreme difficulty requiring multi-block structural optimization.
"""
from __future__ import annotations
from typing import Any, Dict, List
import re

def update_task_description_for_visible_changes(base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    description = base_description
    base_terrain_config = base_terrain_config or {}
    default_spawn = [-10.0, 0.0]
    default_ceiling = 100.0
    default_mass = 20000.0
    default_table_friction = 0.8

    # Update Target Overhang (group 3 = " beyond the edge." so replacement doesn't duplicate "m")
    target_overhang = target_terrain_config.get("target_overhang", 0.1)
    base_overhang = base_terrain_config.get("target_overhang", 0.1)
    if target_overhang != base_overhang:
        pattern = r"(\s*-\s*\*\*Goal\*\*: Reach x >= )(\d+\.?\d*)m( beyond the edge\.)"
        if re.search(pattern, description):
            description = re.sub(pattern, f"\\g<1>{target_overhang:.2f}m (originally {base_overhang:.2f}m in the source environment)\\g<3>", description)

    # Update Table Friction
    target_friction = target_terrain_config.get("table_friction", default_table_friction)
    base_friction = base_terrain_config.get("table_friction", default_table_friction)
    if target_friction != base_friction:
        pattern = r"(\s*-\s*\*\*Table Friction\*\*: Table friction coefficient is )(\d+\.?\d*)(\.)"
        if re.search(pattern, description):
            description = re.sub(pattern, f"\\g<1>{target_friction:.2f} (originally {base_friction:.2f} in the source environment)\\g<3>", description)

    # Update Spawn Zone
    target_spawn = target_terrain_config.get("spawn_zone", default_spawn)
    base_spawn = base_terrain_config.get("spawn_zone", default_spawn)
    if target_spawn != base_spawn:
        pattern = r"(\s*-\s*\*\*Spawn Rule\*\*: Blocks must be initialized within the permitted build access zone: x in )(\[.*?\])(\.)"
        if re.search(pattern, description):
            base_str = f"[{base_spawn[0]:.1f}, {base_spawn[1]:.1f}]"
            description = re.sub(pattern, f"\\g<1>[{target_spawn[0]:.1f}, {target_spawn[1]:.1f}] (originally {base_str} in the source environment)\\g<3>", description)

    # Update Ceiling Clearance (replacement ends with "." to avoid redundant "m.")
    target_ceiling = target_terrain_config.get("ceiling_y", default_ceiling)
    base_ceiling = base_terrain_config.get("ceiling_y", default_ceiling)
    if target_ceiling != base_ceiling:
        pattern = r"(\s*-\s*\*\*Clearance\*\*: Watch out for overhead obstacles \(ceilings\) in some regions. Current clearance y: )(\d+\.?\d*)(m\.)"
        if re.search(pattern, description):
            description = re.sub(pattern, f"\\g<1>{target_ceiling:.1f}m (originally {base_ceiling:.1f}m in the source environment).", description)

    # Update Mass Budget
    target_mass = target_terrain_config.get("max_total_mass", default_mass)
    base_mass = base_terrain_config.get("max_total_mass", default_mass)
    if target_mass != base_mass:
        pattern = r"(\s*-\s*\*\*Mass Budget\*\*: Total structure mass must be less than or equal to )(\d+\.?\d*)( units\.)"
        if re.search(pattern, description):
            description = re.sub(pattern, f"\\g<1>{target_mass:.1f} units (originally {base_mass:.1f} units in the source environment).", description)

    return description

def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    criteria = base_success_criteria
    base_terrain_config = base_terrain_config or {}

    # Update Reach in Success Criteria (match "x >= " to align with prompt)
    target_overhang = target_terrain_config.get("target_overhang", 0.1)
    base_overhang = base_terrain_config.get("target_overhang", 0.1)
    if target_overhang != base_overhang:
        pattern = r"(\(Tip reaches x >= )(\d+\.?\d*)(m\)\.)"
        if re.search(pattern, criteria):
            criteria = re.sub(pattern, f"\\g<1>{target_overhang:.2f}m (originally {base_overhang:.2f}m in the source environment)).", criteria)

    # Update Mass Budget in constraints (avoid duplicating " units." by ending with ".")
    target_mass = target_terrain_config.get("max_total_mass", 20000.0)
    base_mass = base_terrain_config.get("max_total_mass", 20000.0)
    if target_mass != base_mass:
        pattern = r"(\s*-\s*\*\*Mass Budget\*\*: Total mass must be <= )(\d+\.?\d*)( units\.)"
        if re.search(pattern, criteria):
            criteria = re.sub(pattern, f"\\g<1>{target_mass:.1f} units (originally {base_mass:.1f} units in the source environment).", criteria)

    return criteria

def get_s06_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns ordered stage configs for S-06: The Overhang task variants.
    mutation_description is for logs/orchestration only and must NOT be shown to the agent.
    """
    # Define the uniform suffix based on the union of all mutated variables (Stage-1 to Stage-4)
    UNIFORM_SUFFIX = """
Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables MIGHT have changed from the initial environment, NOT ALL of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
 - Target overhang / goal reach: The required horizontal extent beyond the table edge may differ from the initial specification.
 - Build access zone / spawn zone: The permitted x-interval for placing blocks may be restricted differently.
 - Gravitational Intensity: The magnitude of the downward pull may have changed, affecting structural stress and balance.
 - Surface Friction: The table's grip may have changed, affecting how well the structure anchors and resists sliding.
 - Atmospheric Wind: Lateral forces may act on the structure; their presence or strength may differ from the initial environment.

Discovery via feedback: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., where a joint breaks or how a body moves) to infer the hidden constraints and adapt your design.
"""

    return [
        {
            "stage_id": "Stage-1",
            "title": "The Harmonic Horizon",
            "mutation_description": "Fundamental Structural Challenge: Reach 0.8m overhang using 1.0m blocks.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "target_overhang": 0.8,
                "spawn_zone": [-10.0, 0.4],
            },
            "physics_config": {
                "gravity": (0, -10.0),
            },
        },
        {
            "stage_id": "Stage-2",
            "title": "The Slipstream Stacks",
            "mutation_description": "Structural + Physics: Reach 1.0m overhang with very low table friction (0.1).",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "target_overhang": 1.0,
                "spawn_zone": [-10.0, 0.6],
                "table_friction": 0.1,
            },
            "physics_config": {
                "gravity": (0, -10.0),
            },
        },
        {
            "stage_id": "Stage-3",
            "title": "The High-Gravity Reach",
            "mutation_description": "Structural + Physics: Reach 1.2m overhang under High Gravity (2x).",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "target_overhang": 1.2,
                "spawn_zone": [-10.0, 0.8],
            },
            "physics_config": {
                "gravity": (0, -20.0),
            },
        },
        {
            "stage_id": "Stage-4",
            "title": "The Hurricane Reach",
            "mutation_description": "The Ultimate Test: Reach 1.5m overhang with Lateral Wind (1.0).",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "target_overhang": 1.5,
                "spawn_zone": [-10.0, 1.1],
            },
            "physics_config": {
                "gravity": (0, -10.0),
                "wind_force": 1.0,
            },
        },
    ]
