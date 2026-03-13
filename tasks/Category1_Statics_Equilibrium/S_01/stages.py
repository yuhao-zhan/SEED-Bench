"""
S-01: The Bridge task curriculum stages (mutations).
"""

from __future__ import annotations

from typing import Any, Dict, List
import re


def update_task_description_for_visible_changes(
    base_description: str,
    target_terrain_config: Dict[str, Any],
    base_terrain_config: Dict[str, Any],
    target_physics_config: Dict[str, Any] = None,
    base_physics_config: Dict[str, Any] = None,
    *,
    stage: Dict[str, Any] = None,
) -> str:
    """
    Update task description with visible changes using format: [new_value] (originally [old_value] in the source environment).
    Callers may pass stage=stage so that physics_config (joint/anchor limits) is synced from the stage dict.
    """
    description = base_description
    default_gap_width = 15.0
    default_max_structure_mass = 2000.0

    target_terrain_config = target_terrain_config or {}
    base_terrain_config = base_terrain_config or {}
    target_physics_config = target_physics_config or {}
    base_physics_config = base_physics_config or {}
    if stage is not None:
        target_physics_config = dict(stage.get("physics_config") or {})
        base_physics_config = {}

    target_gap_width = target_terrain_config.get("gap_width", default_gap_width)
    base_gap_width = base_terrain_config.get("gap_width", default_gap_width)
    target_right_cliff_start = 10.0 + target_gap_width
    base_right_cliff_start = 10.0 + base_gap_width
    
    target_max_mass = target_terrain_config.get("max_structure_mass", default_max_structure_mass)
    base_max_mass = base_terrain_config.get("max_structure_mass", default_max_structure_mass)

    if target_gap_width != base_gap_width:
        # Update Right Cliff description
        right_cliff_pattern = r"(- \*\*Right Cliff\*\*: Starts at x=)(\d+\.?\d*)m(, y=[\d.]+m\.)?"
        if re.search(right_cliff_pattern, description):
            description = re.sub(
                right_cliff_pattern,
                lambda m: f"{m.group(1)}{target_right_cliff_start:.1f}m (originally {base_right_cliff_start:.1f}m in the source environment){m.group(3) if m.group(3) else '.'}",
                description
            )
        
        # Update Build Zone description
        build_zone_pattern = r"(- \*\*Build Zone\*\*: Structure must be built within x=\[10, )(\d+\.?\d*)(\], y=\[5, 15\].)"
        if re.search(build_zone_pattern, description):
            description = re.sub(
                build_zone_pattern,
                lambda m: f"{m.group(1)}{target_right_cliff_start:.1f}{m.group(3)} (originally [10, {base_right_cliff_start:.1f}] in the source environment)",
                description
            )
            
        # Update Target description
        base_target_x = base_right_cliff_start + 5.0
        target_x = target_right_cliff_start + 5.0
        target_desc_pattern = r"(- \*\*Target\*\*: The vehicle must fully cross the gap and reach at least x=)(\d+\.?\d*)m( on the right side.)"
        if re.search(target_desc_pattern, description):
            description = re.sub(
                target_desc_pattern,
                lambda m: f"{m.group(1)}{target_x:.1f}m (originally {base_target_x:.1f}m in the source environment){m.group(3)}",
                description
            )

    if target_max_mass != base_max_mass:
        # Update Mass Budget in constraints
        mass_desc_pattern = r"(- \*\*Mass Budget\*\*: Total structure mass must be less than )(\d+\.?\d*) kg\."
        if re.search(mass_desc_pattern, description):
            description = re.sub(
                mass_desc_pattern,
                f"\\g<1>{target_max_mass:.0f} kg (originally {base_max_mass:.0f} kg in the source environment).",
                description
            )

    # Sync Joint/Anchor Strength if mutated
    for key, label, default in [
        ("joint_max_force", "Joint Strength", 80.0),
        ("joint_max_torque", "Joint Strength", 300.0),
        ("anchor_max_force", "Anchor Strength", 100.0),
        ("anchor_max_torque", "Anchor Strength", 500.0)
    ]:
        target_val = target_physics_config.get(key, default)
        base_val = base_physics_config.get(key, default)
        if target_val != base_val:
            if "force" in key:
                pattern = rf"(- \*\*{label}\*\*: Maximum linear force for .* is )(\d+\.?\d*);"
                replacement = f"\\g<1>{target_val:.1f} (originally {base_val:.1f} in the source environment);"
            else:
                pattern = rf"(- \*\*{label}\*\*: .* maximum torque is )(\d+\.?\d*)\."
                replacement = f"\\g<1>{target_val:.1f} (originally {base_val:.1f} in the source environment)."
            
            if re.search(pattern, description):
                description = re.sub(pattern, replacement, description)

    return description


def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    criteria = base_success_criteria
    default_gap_width = 15.0
    default_max_structure_mass = 2000.0
    target_gap_width = target_terrain_config.get("gap_width", default_gap_width)
    base_gap_width = base_terrain_config.get("gap_width", default_gap_width)
    target_right_cliff_start = 10.0 + target_gap_width
    base_right_cliff_start = 10.0 + base_gap_width
    target_max_mass = target_terrain_config.get("max_structure_mass", default_max_structure_mass)
    base_max_mass = base_terrain_config.get("max_structure_mass", default_max_structure_mass)
    if target_gap_width != base_gap_width:
        base_target_x = base_right_cliff_start + 5.0
        target_x = target_right_cliff_start + 5.0
        target_pattern = r"(1\. \*\*Passage\*\*: Vehicle reaches x >= )(\d+\.?\d*)m\."
        if re.search(target_pattern, criteria):
            criteria = re.sub(
                target_pattern,
                f"\\g<1>{target_x:.1f}m (originally {base_target_x:.1f}m in the source environment).",
                criteria
            )
    if target_max_mass != base_max_mass:
        mass_pattern = r"(- \*\*Mass Budget\*\*: < )(\d+\.?\d*) kg\."
        if re.search(mass_pattern, criteria):
            criteria = re.sub(
                mass_pattern,
                f"\\g<1>{target_max_mass:.0f} kg (originally {base_max_mass:.0f} kg in the source environment).",
                criteria
            )
    return criteria


def get_s01_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns ordered stage configs for S-01: The Bridge task variants.
    Information Hiding: Uniform suffix for all stages to test physical reasoning.
    mutation_description is for logs/orchestration only and must NOT be shown to the agent.
    """
    
    UNIFORM_SUFFIX = """
## Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables **MIGHT** have changed from the initial environment, **NOT ALL** of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
 - **Joint torque resilience**: The maximum torque structural joints can withstand before failing.
 - **Anchor torque resilience**: The maximum torque cliff anchors can withstand before breaking.
 - **Joint force resilience**: The maximum linear force structural joints can withstand before failing.
 - **Anchor force resilience**: The maximum linear force cliff anchors can withstand before breaking.
 - **Mass limit**: The total allowed mass budget for your structure.
 - **Gravitational acceleration**: The strength and direction of the vertical gravitational force.
 - **Atmospheric wind**: Constant lateral and vertical forces acting on all bodies in the environment.
 - **Terrain gap width**: The horizontal distance between the starting cliff and the destination cliff.

**Discovery via feedback**: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., where a joint breaks or how a body moves) to infer the hidden constraints and adapt your design.
"""

    return [
        {
            "stage_id": "Stage-1",
            "title": "Brittle Material",
            "mutation_description": "Joints cannot withstand torque and must act purely as pivots.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {},
            "physics_config": {
                "joint_max_torque": 0.1,
                "anchor_max_torque": 0.1,
            },
        },
        {
            "stage_id": "Stage-2",
            "title": "Fragile Joints",
            "mutation_description": "Structural joints are very weak.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {},
            "physics_config": {
                "joint_max_force": 8.0,
                "joint_max_torque": 15.0,
            },
        },
        {
            "stage_id": "Stage-3",
            "title": "The Vortex Gorge",
            "mutation_description": "Stronger gravity, significant wind, wider gap, and reduced joint and anchor strength.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "gap_width": 20.0,
                "max_structure_mass": 1200.0,
            },
            "physics_config": {
                "gravity": (0, -22.0),
                "wind_force": (-20.0, -5.0),
                "joint_max_force": 20.0,
                "anchor_max_force": 30.0,
                "joint_max_torque": 40.0,
            },
        },
        {
            "stage_id": "Stage-4",
            "title": "Abyssal Crossing",
            "mutation_description": "Wider gap, stronger gravity, significant wind, and adjusted mass budget.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "gap_width": 25.0,
                "max_structure_mass": 1500.0,
            },
            "physics_config": {
                "gravity": (0, -25.0),
                "wind_force": (-35.0, -10.0),
                "joint_max_force": 40.0,
                "anchor_max_force": 60.0,
                "joint_max_torque": 50.0,
            },
        },
    ]
