"""
S-03: The Cantilever task curriculum stages (mutations).
"""

from __future__ import annotations

from typing import Any, Dict, List
import re


def update_task_description_for_visible_changes(base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    description = base_description
    
    # Update Reach Goal
    target_reach = target_terrain_config.get("target_reach", 12.0)
    base_reach = base_terrain_config.get("target_reach", 12.0)
    if target_reach != base_reach:
        pattern = r"(- \*\*Goal\*\*: Reach x >= )(\d+\.?\d*)m"
        description = re.sub(pattern, f"\\g<1>{target_reach:.1f}m (originally {base_reach:.1f}m)", description)
    
    # Update Mass Limit
    target_mass = target_terrain_config.get("max_structure_mass", 15000.0)
    base_mass = base_terrain_config.get("max_structure_mass", 15000.0)
    if target_mass != base_mass:
        pattern = r"(- \*\*Mass Limit\*\*: < )(\d+,?\d*) kg"
        description = re.sub(pattern, f"\\g<1>{target_mass:,.0f} kg (originally {base_mass:,.0f} kg)", description)
    
    # Update Obstacles visibility
    if target_terrain_config.get("obstacle_active", False):
        pattern = r"(- \*\*Obstacles\*\*: Static )"
        description = re.sub(pattern, f"\\g<1>A narrow winding path is present, created by several static ", description)
        
    return description


def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    criteria = base_success_criteria
    
    # Update Reach in Success Criteria
    target_reach = target_terrain_config.get("target_reach", 12.0)
    base_reach = base_terrain_config.get("target_reach", 12.0)
    if target_reach != base_reach:
        pattern = r"(Tip reaches x >= )(\d+\.?\d*)m"
        criteria = re.sub(pattern, f"\\g<1>{target_reach:.1f}m (originally {base_reach:.1f}m)", criteria)
    
    # Update Mass Budget in Success Criteria
    target_mass = target_terrain_config.get("max_structure_mass", 15000.0)
    base_mass = base_terrain_config.get("max_structure_mass", 15000.0)
    if target_mass != base_mass:
        pattern = r"(- \*\*Mass Budget\*\*: < )(\d+,?\d*) kg"
        criteria = re.sub(pattern, f"\\g<1>{target_mass:,.0f} kg (originally {base_mass:,.0f} kg)", criteria)
        
    return criteria


def get_s03_curriculum_stages() -> List[Dict[str, Any]]:
    # DYNAMICALLY GENERATED UNIFORM SUFFIX (Union of all mutated variables in S_03 Stages 1-4)
    UNIFORM_SUFFIX = """
## Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables MIGHT have changed from the initial environment, NOT ALL of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
 - **Target Reach Distance**: The required horizontal extension from the anchor wall may have been adjusted.
 - **Structural Mass Budget**: The total allowed mass for your cantilever design may be adjusted to specific limits.
 - **Internal Joint Fragility**: The internal structural joints connecting beams may be highly brittle, shattering if internal forces or torques exceed a low threshold.
 - **Spatial Force Fields**: An invisible spatial anomaly might exert strong repulsive or attractive forces on any structure entering its radius.
 - **Wall Anchor Zoning**: Large continuous vertical sections of the wall may be strictly forbidden for anchoring, forcing construction from extreme high or low points.
 - **Obstacle Blockades**: Massive static structures might block direct horizontal paths, demanding complex geometries to navigate around them.
 - **Payload Dynamics**: Payloads may be dropped dynamically, testing resilience to impact shocks.
 - **Atmospheric Wind**: Sustained or oscillatory wind forces may induce lateral swaying or vertical bouncing.

**Discovery via feedback**: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., where a joint breaks or how a body moves) to infer the hidden constraints and adapt your design.
"""

    return [
        {
            "stage_id": "Stage-1",
            "title": "The Brittle Connections",
            "mutation_description": "Single Variable: Extreme internal joint fragility.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "target_reach": 25.0, 
                "load_mass": 800.0, 
                "max_structure_mass": 8000.0,
                "max_internal_force": 200000.0,
                "max_internal_torque": 200000.0,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-2",
            "title": "The Magnetic Anomaly",
            "mutation_description": "Single Variable: Strong spatial repulsion field forcing a detour.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "target_reach": 25.0,
                "load_mass": 1000.0,
                "max_structure_mass": 8000.0,
            },
            "physics_config": {
                "spatial_force": {
                    "center": (12.5, 5.0),
                    "magnitude": 60000.0,
                    "radius": 10.0,
                    "type": "repulsion"
                }
            },
        },
        {
            "stage_id": "Stage-3",
            "title": "The Blockaded Wall",
            "mutation_description": "Multi-variable: Wall forbidden zone + Massive Obstacle. Forces extreme low construction.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "target_reach": 28.0,
                "load_mass": 1200.0,
                "max_structure_mass": 10000.0,
                "forbidden_anchor_y": [-5.0, 15.0],
                "obstacle_active": True,
                "obstacle_rects": [
                    [5.0, 5.0, 30.0, 25.0],
                ],
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-4",
            "title": "The Perfect Storm",
            "mutation_description": "Multi-variable: Fragile joints + Repulsion Field + Forbidden Wall + Dropped Loads + Oscillatory Wind.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "target_reach": 35.0,
                "load_mass": 1500.0,
                "max_structure_mass": 15000.0,
                "max_internal_force": 1000000.0,
                "max_internal_torque": 1000000.0,
                "forbidden_anchor_y": [0.0, 10.0],
                "load_type": "dropped",
                "drop_height": 8.0,
            },
            "physics_config": {
                "spatial_force": {
                    "center": (15.0, 8.0),
                    "magnitude": 40000.0,
                    "radius": 12.0,
                    "type": "repulsion"
                },
                "wind": {
                    "force": (0, 800.0),
                    "oscillatory": True,
                    "frequency": 0.5
                }
            },
        },
    ]
