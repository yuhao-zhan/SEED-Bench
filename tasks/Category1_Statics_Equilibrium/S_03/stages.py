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
        
    return description


def update_success_criteria_for_visible_criteria(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
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
 - **Terrain Geometry & Obstructions**: Static obstructions may block standard construction paths, requiring navigation through narrow corridors.
 - **Target Reach Distance**: The required horizontal extension from the anchor wall may have been significantly adjusted.
 - **Payload Dynamics & Impact Forces**: Payloads may be applied as static forces or dropped from height, introducing high-energy dynamic impacts.
 - **Gravitational Acceleration**: Local gravity may be significantly higher, affecting structural weight, sag, and load-bearing capacity.
 - **Anchor & Joint Strength**: The capacity of wall anchors to withstand force and torque may vary, potentially exhibiting spatial gradients in strength.
 - **Atmospheric Conditions**: Constant or periodic oscillatory wind forces may exert lateral or vertical pressure on the structure.
 - **Structural Mass Budget**: The total allowed mass for your cantilever design may be restricted to specific limits.
 - **Wall Anchor Zoning**: Certain vertical regions of the wall may be unsuitable for anchoring or forbidden for structural use.

**Discovery via feedback**: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., where an anchor breaks or how the structure sags) to infer the hidden constraints and adapt your design.
"""

    return [
        {
            "stage_id": "Stage-1",
            "title": "The Slalom Tunnel",
            "mutation_description": "Multiple obstacles creating a narrow winding path. Single variable: environment geometry.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "obstacle_active": True,
                "obstacle_rects": [
                    [5.0, 0.0, 7.0, 6.0],   # Lower block
                    [10.0, 8.0, 12.0, 20.0], # Upper block
                    [15.0, 0.0, 17.0, 4.0],  # Lower block
                ],
                "target_reach": 25.0, 
                "load_mass": 800.0, 
                "max_structure_mass": 8000.0,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-2",
            "title": "Impact Resilience",
            "mutation_description": "Dropped loads + increased gravity. Hidden mechanic: loads are dynamic impacts.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "load_type": "dropped",
                "drop_height": 10.0,
                "target_reach": 25.0,
                "load_mass": 1000.0,
                "max_structure_mass": 8000.0,
            },
            "physics_config": {
                "gravity": (0, -15.0),
            },
        },
        {
            "stage_id": "Stage-3",
            "title": "The Weak Foundation",
            "mutation_description": "Anchor strength gradient + constant wind + high gravity.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "target_reach": 28.0,
                "anchor_strength_map": [
                    (0.0, 1.0, 1.0, 1.0),   # Strong zone
                    (1.0, 4.0, 0.2, 0.1),   # Weak zone
                    (4.0, 5.0, 1.0, 1.0),   # Strong zone
                ],
                "load_mass": 1200.0,
                "max_structure_mass": 10000.0,
            },
            "physics_config": {
                "gravity": (0, -18.0),
                "wind": {
                    "force": (500.0, 0), # Lateral wind pushing right
                    "oscillatory": False
                }
            },
        },
        {
            "stage_id": "Stage-4",
            "title": "The Perfect Storm",
            "mutation_description": "Oscillatory wind + Extreme Reach + Fragmented Wall + Dropped Loads.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "obstacle_active": True,
                "obstacle_rects": [
                    [10.0, -5.0, 12.0, 5.0],
                    [20.0, 5.0, 22.0, 15.0],
                ],
                "load_type": "dropped",
                "drop_height": 12.0,
                "forbidden_anchor_y": [1.0, 4.0],
                "anchor_strength_map": [
                    (0.0, 1.0, 0.5, 0.3),
                    (4.0, 5.0, 0.5, 0.3),
                ],
                "target_reach": 35.0, 
                "load_mass": 1500.0, 
                "max_structure_mass": 15000.0,
            },
            "physics_config": {
                "gravity": (0, -20.0), 
                "wind": {
                    "force": (0, 1000.0), # Vertical oscillatory wind
                    "oscillatory": True,
                    "frequency": 0.5
                }
            },
        },
    ]
