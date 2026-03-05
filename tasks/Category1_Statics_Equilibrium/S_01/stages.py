"""
S-01: The Bridge task curriculum stages (mutations).
"""

from __future__ import annotations

from typing import Any, Dict, List
import re


def update_task_description_for_visible_changes(base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    description = base_description
    default_gap_width = 15.0
    target_gap_width = target_terrain_config.get("gap_width", default_gap_width)
    base_gap_width = base_terrain_config.get("gap_width", default_gap_width)
    target_right_cliff_start = 10.0 + target_gap_width
    base_right_cliff_start = 10.0 + base_gap_width
    if target_gap_width != base_gap_width:
        right_cliff_pattern = r"(- \*\*Right Cliff\*\*: Starts at x=)(\d+\.?\d*)m(, y=[\d.]+m\.)?"
        if re.search(right_cliff_pattern, description):
            description = re.sub(
                right_cliff_pattern,
                lambda m: f"{m.group(1)}{target_right_cliff_start:.1f}m (originally x={base_right_cliff_start:.1f}m in the source environment){m.group(3) if m.group(3) else '.'}",
                description
            )
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
                f"\\g<1>{target_x:.1f}m (originally x >= {base_target_x:.1f}m in the source environment).",
                criteria
            )
    if target_max_mass != base_max_mass:
        mass_pattern = r"(- \*\*Mass Budget\*\*: < )(\d+\.?\d*) kg\."
        if re.search(mass_pattern, criteria):
            criteria = re.sub(
                mass_pattern,
                f"\\g<1>{target_max_mass:.0f} kg (originally < {base_max_mass:.0f} kg in the source environment).",
                criteria
            )
    return criteria


def get_s01_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns ordered stage configs for S-01: The Bridge task variants.
    Information Hiding: Uniform suffix for all stages to test physical reasoning.
    """
    
    UNIFORM_SUFFIX = """
## Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties. 
While the following variables **MIGHT** have changed from the initial environment, **NOT ALL** of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
- **Gravitational acceleration**: Vertical loads on the structure may be significantly different.
- **Atmospheric conditions**: Potential lateral forces (e.g., wind) may act on the vehicle and structure.
- **Structural integrity limits**: Critical force and torque thresholds for joints and anchors may have changed.
- **Resource availability**: The maximum allowed structure mass may differ from standard limits.
- **Terrain geometry**: The distance between cliffs or target location may have been adjusted.

**Discovery via feedback**: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., where a joint breaks or how the vehicle deviates) to infer the hidden constraints and adapt your design.
"""

    return [
        {
            "stage_id": "Stage-1",
            "title": "Fragile Anchor Points",
            "mutation_description": "Cliff anchors are weak (max_force: 15.0, max_torque: 50.0).",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {},
            "physics_config": {
                "anchor_max_force": 15.0,
                "anchor_max_torque": 50.0,
            },
        },
        {
            "stage_id": "Stage-2",
            "title": "Low Torque Resilience",
            "mutation_description": "Joints have low torque resistance (max_torque: 30.0).",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {},
            "physics_config": {
                "joint_max_torque": 30.0,
            },
        },
        {
            "stage_id": "Stage-3",
            "title": "The Stormy Gorge",
            "mutation_description": "High gravity (-15), horizontal wind (-5N), and reduced mass limit (1000kg).",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "max_structure_mass": 1000.0,
            },
            "physics_config": {
                "gravity": (0, -15.0),
                "wind_force": (-5.0, 0.0),
            },
        },
        {
            "stage_id": "Stage-4",
            "title": "Abyssal Crossing",
            "mutation_description": "Gap 25m, Gravity -20, Low mass limit (1000kg).",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "gap_width": 25.0,
                "max_structure_mass": 1000.0,
            },
            "physics_config": {
                "gravity": (0, -20.0),
            },
        },
    ]
