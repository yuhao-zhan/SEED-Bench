"""
S-03: The Cantilever task curriculum stages (mutations).
"""
from __future__ import annotations
from typing import Any, Dict, List
import re


def update_task_description_for_visible_changes(base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """
    Update task description to reflect visible physical changes (e.g., load mass, target reach).
    
    Args:
        base_description: Original task description
        target_terrain_config: Target terrain configuration
        base_terrain_config: Base terrain configuration to compare against
    """
    description = base_description
    
    # Default values (baseline task)
    default_load_mass = 600.0
    default_second_load_mass = 400.0
    default_target_reach = 14.0
    
    target_load_mass = target_terrain_config.get("load_mass", default_load_mass)
    base_load_mass = base_terrain_config.get("load_mass", default_load_mass)
    
    target_second_load_mass = target_terrain_config.get("second_load_mass", default_second_load_mass)
    base_second_load_mass = base_terrain_config.get("second_load_mass", default_second_load_mass)
    
    target_reach = target_terrain_config.get("target_reach", default_target_reach)
    base_reach = base_terrain_config.get("target_reach", default_target_reach)
    
    if target_load_mass != base_load_mass:
        load_pattern = r"(- \*\*Load 1 \(tip\)\*\*: A )(\d+\.?\d*)(kg weight attaches to your right-most node at t=5s\.)"
        if re.search(load_pattern, description):
            description = re.sub(
                load_pattern,
                f"\\g<1>\\g<2>kg (FROM: {base_load_mass:.0f}kg, TO: {target_load_mass:.0f}kg) weight attaches to your right-most node at t=5s.",
                description
            )
    
    if target_second_load_mass != base_second_load_mass:
        load2_pattern = r"(A )(\d+\.?\d*)(kg weight attaches at t=10s to the node)"
        if re.search(load2_pattern, description):
            description = re.sub(
                load2_pattern,
                f"\\g<1>\\g<2>kg (FROM: {base_second_load_mass:.0f}kg, TO: {target_second_load_mass:.0f}kg) weight attaches at t=10s to the node",
                description
            )
    
    if target_reach != base_reach:
        objective_pattern = r"(2\. Reaches at least x=)(\d+\.?\d*)m"
        if re.search(objective_pattern, description):
            description = re.sub(
                objective_pattern,
                f"\\g<1>\\g<2>m (FROM: x={base_reach:.1f}m, TO: x={target_reach:.1f}m)",
                description
            )
    
    return description


def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """
    Update success criteria to reflect visible physical changes (e.g., target reach, anchor torque limit, load mass).
    """
    criteria = base_success_criteria
    
    default_target_reach = 14.0
    default_max_anchor_torque = 2600.0
    default_load_mass = 600.0
    
    target_reach = target_terrain_config.get("target_reach", default_target_reach)
    base_reach = base_terrain_config.get("target_reach", default_target_reach)
    
    target_max_anchor_torque = target_terrain_config.get("max_anchor_torque", default_max_anchor_torque)
    base_max_anchor_torque = base_terrain_config.get("max_anchor_torque", default_max_anchor_torque)
    
    target_load_mass = target_terrain_config.get("load_mass", default_load_mass)
    base_load_mass = base_terrain_config.get("load_mass", default_load_mass)
    
    if target_reach != base_reach:
        reach_pattern = r"(1\. \*\*Reach\*\*: Tip x >= )(\d+\.?\d*)m\."
        if re.search(reach_pattern, criteria):
            criteria = re.sub(
                reach_pattern,
                f"\\g<1>\\g<2>m (FROM: >= {base_reach:.1f}m, TO: >= {target_reach:.1f}m).",
                criteria
            )
        geometry_pattern = r"(- \*\*Geometry\*\*: Must extend to at least x=)(\d+\.?\d*)m"
        if re.search(geometry_pattern, criteria):
            criteria = re.sub(
                geometry_pattern,
                f"\\g<1>\\g<2>m (FROM: x={base_reach:.1f}m, TO: x={target_reach:.1f}m)",
                criteria
            )
    
    if target_load_mass != base_load_mass:
        load_bearing_pattern = r"(Hold tip load \()(\d+\.?\d*)(kg)"
        if re.search(load_bearing_pattern, criteria):
            criteria = re.sub(
                load_bearing_pattern,
                f"\\g<1>\\g<2>kg (FROM: {base_load_mass:.0f}kg, TO: {target_load_mass:.0f}kg)",
                criteria
            )
    
    if target_max_anchor_torque != base_max_anchor_torque:
        torque_pattern = r"(- \*\*Anchor Strength\*\*: Each wall joint breaks if Torque > )(\d+\.?\d*)( Nm\. \(Key Challenge!\))"
        if re.search(torque_pattern, criteria):
            criteria = re.sub(
                torque_pattern,
                f"\\g<1>\\g<2> Nm (FROM: > {base_max_anchor_torque:.0f} Nm, TO: > {target_max_anchor_torque:.0f} Nm).\\g<3>",
                criteria
            )
    
    return criteria


def get_s03_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns ordered stage configs for S-03: The Cantilever task variants.

    Each stage dict fields:
      - stage_id: str
      - title: str
      - mutation_description: str (for logs, not shown to solver)
      - task_description_suffix: str (generic warning, no exact numeric changes)
      - terrain_config: dict (passed to DaVinciSandbox)
      - physics_config: dict (passed to DaVinciSandbox)
    """
    return [
        {
            "stage_id": "Stage-1",
            "title": "Heavier Suspended Loads",
            "mutation_description": "Tip and mid-span loads increased + stronger gravity (invisible). Requires stronger truss and better load path.",
            "task_description_suffix": """
## Environmental Warning
Payload anomalies have been detected.
Both tip and mid-span loads may be heavier than expected.
Design for stronger load paths and distribute forces across multiple members.
""",
            "terrain_config": {
                "load_mass": 1150.0,
                "second_load_mass": 720.0,
                "max_anchor_torque": 120.0,
            },
            "physics_config": {
                "gravity": (0, -16.0),
            },
        },
        {
            "stage_id": "Stage-2",
            "title": "Longer Required Reach",
            "mutation_description": "Target reach increased. Cantilever must extend further while staying stable.",
            "task_description_suffix": """
## Environmental Warning
The required operational reach may be farther than in the baseline scenario.
Longer spans amplify bending moments; efficient triangulation and stiffness become more important.
""",
            "terrain_config": {
                "target_reach": 16.0,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-3",
            "title": "Weaker Wall Anchors",
            "mutation_description": "Wall anchor torque reduced + stronger gravity + damping (invisible). Must further reduce anchor moment and distribute forces.",
            "task_description_suffix": """
## Environmental Warning
Anchor integrity is uncertain in this region.
Wall connections may be less robust than usual.
Reduce anchor loading via better geometry (triangulation) and load distribution.
""",
            "terrain_config": {
                "max_anchor_torque": 50.0,
                "target_reach": 14.5,
            },
            "physics_config": {
                "gravity": (0, -15.0),
                "linear_damping": 1.0,
                "angular_damping": 1.0,
            },
        },
        {
            "stage_id": "Stage-4",
            "title": "Extreme Combined Challenge",
            "mutation_description": "Combined: heavier loads + longer reach + increased gravity + weaker anchors. Maximum difficulty.",
            "task_description_suffix": """
## Environmental Warning
Multiple anomalies may be active simultaneously.
Expect larger loads, longer spans, and less forgiving constraints.
You may need a highly efficient truss geometry to keep anchor loading within safe margins.
""",
            "terrain_config": {
                "load_mass": 750.0,
                "second_load_mass": 500.0,
                "target_reach": 16.0,
                "max_anchor_torque": 2200.0,
            },
            "physics_config": {
                "gravity": (0, -14.0),
            },
        },
    ]
