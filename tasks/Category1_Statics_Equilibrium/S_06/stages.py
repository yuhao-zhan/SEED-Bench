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
    default_stability_time = 10.0
    default_floor_length = 20.0

    # Update Table geometry (floor_length → table surface range)
    # Table is centered at x=-10.0; right edge = -10.0 + floor_length/2.
    target_floor_length = target_terrain_config.get("floor_length", default_floor_length)
    base_floor_length = base_terrain_config.get("floor_length", default_floor_length)
    if target_floor_length != base_floor_length:
        target_edge = -10.0 + target_floor_length / 2.0
        base_edge = -10.0 + base_floor_length / 2.0
        # Pattern matches: "- **Table**: A horizontal surface extending from x=-20 to x=0. The table edge is at x=0."
        pattern = r"(- \*\*Table\*\*: A horizontal surface extending from x=)-20(\.0 to x=)(\d+\.?\d*)(\. The table edge is at x=)(\d+\.?\d*)(\.)"
        if re.search(pattern, description):
            description = re.sub(
                pattern,
                f"\\g<1>-20.0 to x={target_edge:.1f}. The table edge is at x={target_edge:.1f} (originally x={base_edge:.1f} in the source environment).",
                description,
            )

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
        # Pattern: group1 = prefix, group2 = number (e.g. "0.8"), group3 = trailing '.'
        # The original pattern (\d+\.?\d*)(\.) misbehaves on "0.8." because \d+ captures "0",
        # \. captures the first ".", and \d* captures "8" — making group2 = "08" (drops decimal).
        # Fixed: use (\d+\.\d+) to properly capture the floating-point number.
        pattern = r"(\s*-\s*\*\*Table Friction\*\*: Table friction coefficient is )(\d+\.\d+)(\.)"
        if re.search(pattern, description):
            description = re.sub(pattern, f"\\g<1>{target_friction:.1f} (originally {base_friction:.1f} in the source environment)\\g<3>", description)

    # Update Spawn Zone
    target_spawn = target_terrain_config.get("spawn_zone", default_spawn)
    base_spawn = base_terrain_config.get("spawn_zone", default_spawn)
    if target_spawn != base_spawn:
        # The prompt text is: **Spawn Rule**: Blocks must be initialized within the permitted build access zone: x in [-10.0, 0.0].
        # Note: there is NO leading dash before **Spawn Rule** (it's not a bullet point), so the pattern must NOT require -\s*.
        pattern = r"(\*\*Spawn Rule\*\*: Blocks must be initialized within the permitted build access zone: x in )(\[.*?\])(\.)"
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

    # Update Block Friction
    default_block_friction = 0.6
    target_block_friction = target_terrain_config.get("block_friction", default_block_friction)
    base_block_friction = base_terrain_config.get("block_friction", default_block_friction)
    if target_block_friction != base_block_friction:
        pattern = r"(\s*-\s*\*\*Block Friction\*\*: Block-to-block friction coefficient is )(\d+\.\d+)(\.)"
        if re.search(pattern, description):
            description = re.sub(pattern, f"\\g<1>{target_block_friction:.1f} (originally {base_block_friction:.1f} in the source environment)\\g<3>", description)

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

    # Update Table Friction in success criteria (if mentioned)
    target_friction = target_terrain_config.get("table_friction", 0.8)
    base_friction = base_terrain_config.get("table_friction", 0.8)
    if target_friction != base_friction:
        # The base success_criteria does not mention friction, but add defensively for future changes
        pattern = r"(\s*-\s*\*\*Table Friction\*\*: Table friction coefficient is )(\d+\.\d+)(\.)"
        if re.search(pattern, criteria):
            criteria = re.sub(pattern, f"\\g<1>{target_friction:.1f} (originally {base_friction:.1f} in the source environment)\\g<3>", criteria)

    # Update Mass Budget in constraints (avoid duplicating " units." by ending with ".")
    target_mass = target_terrain_config.get("max_total_mass", 20000.0)
    base_mass = base_terrain_config.get("max_total_mass", 20000.0)
    if target_mass != base_mass:
        pattern = r"(\s*-\s*\*\*Mass Budget\*\*: Total mass must be <= )(\d+\.?\d*)( units\.)"
        if re.search(pattern, criteria):
            criteria = re.sub(pattern, f"\\g<1>{target_mass:.1f} units (originally {base_mass:.1f} units in the source environment).", criteria)

    # Update Stability Time
    target_stability_time = target_terrain_config.get("stability_time", 10.0)
    base_stability_time = base_terrain_config.get("stability_time", 10.0)
    if target_stability_time != base_stability_time:
        pattern = r"(\s*-\s*\*\*Stability Time\*\*: Structure must remain motionless for at least )(\d+\.?\d*)( seconds\.)"
        if re.search(pattern, criteria):
            criteria = re.sub(pattern, f"\\g<1>{target_stability_time:.1f} (originally {base_stability_time:.1f} in the source environment)\\g<3>", criteria)

    # Update Block Friction in success criteria
    default_block_friction = 0.6
    target_block_friction = target_terrain_config.get("block_friction", default_block_friction)
    base_block_friction = base_terrain_config.get("block_friction", default_block_friction)
    if target_block_friction != base_block_friction:
        pattern = r"(\s*-\s*\*\*Block Friction\*\*: Block-to-block friction coefficient is )(\d+\.\d+)(\.)"
        if re.search(pattern, criteria):
            criteria = re.sub(pattern, f"\\g<1>{target_block_friction:.1f} (originally {base_block_friction:.1f} in the source environment)\\g<3>", criteria)

    return criteria

def get_s06_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns ordered stage configs for S-06: The Overhang task variants.
    mutation_description is for logs/orchestration only and must NOT be shown to the agent.
    """
    # Define the uniform suffix based on the union of all mutated variables (Stage-1 to Stage-4)
    # NOTE: Only entries whose underlying physical variables ARE modified in ≥1 stage are included.
    # "Block Friction" is NOT modified in any stage → excluded.
    # "Mass Budget", "Stability Time", "Ceiling Y" are NOT modified in any stage → excluded.
    # Variables modified: target_overhang, spawn_zone, table_friction, gravity, wind_force
    UNIFORM_SUFFIX = """
Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables MIGHT have changed from the initial environment, NOT ALL of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
 - Horizontal reach requirements: The required extent beyond the table edge may differ from the initial specification.
 - Block placement boundaries: The permitted x-interval for placing blocks may be restricted differently.
 - Gravitational Intensity: The magnitude of the downward pull may have changed, affecting structural stress and balance.
 - Lateral Forces: Persistent horizontal force vectors may act on the structure; their presence or magnitude may differ from the initial environment.
 - Table Friction Coefficient: The friction coefficient between blocks and the table surface may have changed, affecting how effectively the base of the stack resists sliding.

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
                # floor_length=21.6: table center x=-10.0, half=10.8 → surface x ∈ [-20.8, 0.8].
                # Table edge at x=0.8 = target_overhang. Rightmost block (center x=0.3, edge x=0.8) sits on edge. ✓
                "floor_length": 21.6,
                "spawn_zone": [-10.0, 0.3],
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
                # floor_length=22.0: table center x=-10.0, half=11.0 → surface x ∈ [-21.0, 1.0].
                # Table edge at x=1.0 = target_overhang. Rightmost block (center x=0.5, edge x=1.0) sits on edge. ✓
                "floor_length": 22.0,
                "spawn_zone": [-10.0, 0.5],
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
                # floor_length=22.4: table center x=-10.0, half=11.2 → surface x ∈ [-21.2, 1.2].
                # Table edge at x=1.2 = target_overhang. Rightmost block (center x=0.7, edge x=1.2) sits on edge. ✓
                "floor_length": 22.4,
                "spawn_zone": [-10.0, 0.7],
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
                # floor_length=23.0: table center x=-10.0, half=11.5 → surface x ∈ [-21.5, 1.5].
                # Table edge at x=1.5 = target_overhang. Rightmost block (center x=1.0, edge x=1.5) sits on edge. ✓
                "floor_length": 23.0,
                "spawn_zone": [-10.0, 1.0],
            },
            "physics_config": {
                "gravity": (0, -10.0),
                "wind_force": 1.0,
            },
        },
    ]
