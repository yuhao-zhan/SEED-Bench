"""
F-05: The Boat task curriculum stages (mutations).

Mutated tasks vary physical parameters: wave amplitude, deck friction,
joint max force (fragility), build zone, current, gravity, and submerged reefs.
Stage-1 & Stage-2: Single variable limits (Threshold challenges).
Stage-3 & Stage-4: Multi-variable complexity (Conflicting constraints).
Ordered by difficulty (ascending).
"""
from __future__ import annotations

from typing import Any, Dict, List
import re


def update_task_description_for_visible_changes(
    base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]
) -> str:
    """Update task description if any visible terrain/config change (Build Zone)."""
    description = base_description
    
    target_x_min = target_terrain_config.get("build_zone_x_min", 12.0)
    target_x_max = target_terrain_config.get("build_zone_x_max", 18.0)
    target_y_min = target_terrain_config.get("build_zone_y_min", 2.0)
    target_y_max = target_terrain_config.get("build_zone_y_max", 4.5)

    base_x_min = base_terrain_config.get("build_zone_x_min", 12.0)
    base_x_max = base_terrain_config.get("build_zone_x_max", 18.0)
    base_y_min = base_terrain_config.get("build_zone_y_min", 2.0)
    base_y_max = base_terrain_config.get("build_zone_y_max", 4.5)

    if (target_x_min != base_x_min or target_x_max != base_x_max or 
        target_y_min != base_y_min or target_y_max != base_y_max):
        
        pattern = r"(- \*\*Build Zone\*\*: Structure must be attached to the boat body within x=\[)([\d.]+), ([\d.]+)(\], y=\[)([\d.]+), ([\d.]+)(\]\.)"
        y_min_str = f"{target_y_min:.2f}" if target_y_min % 0.1 != 0 else f"{target_y_min:.1f}"
        
        replacement = (f"\\g<1>{target_x_min:.1f}, {target_x_max:.1f}\\g<4>{y_min_str}, {target_y_max:.1f}\\g<7> "
                       f"(originally x=[{base_x_min:.1f}, {base_x_max:.1f}], y=[{base_y_min:.1f}, {base_y_max:.1f}] in the source environment)")
        
        description = re.sub(pattern, replacement, description)

    return description


def update_success_criteria_for_visible_changes(
    base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]
) -> str:
    """Update success criteria for visible changes."""
    return base_success_criteria


def get_f05_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns overhauled stage configs for F-05: The Boat.
    Stages focus on structural innovation and complex physical reasoning.
    """
    
    # UNIFORM_SUFFIX generated based on the UNION of all mutated variables across overhauled Stages 1-4.
    UNIFORM_SUFFIX = """
## Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables MIGHT have changed from the initial environment, NOT ALL of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
 - **Joint Load Tolerance**: The maximum stress joints can withstand before structural failure (breaking). Extremely low values require distributing weight across many anchor points.
 - **Deck Surface Traction**: The friction coefficient of the vessel's deck. Zero friction turns cargo into a highly mobile fluid-like mass.
 - **Submerged Hazard Density**: The presence and vertical height of underwater reefs. High reefs will strike deep keels, causing catastrophic structural failure.
 - **Integration Zone Constraints**: The vertical and horizontal boundaries where structures can be securely anchored to the vessel hull.
 - **Gravitational Acceleration**: Local gravity strength, which scales the forces applied to all bodies and joints.
 - **Wave & Current Dynamics**: The magnitude of oscillations and fluid flow affecting vessel roll and drift.

**Discovery via feedback**: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., where a joint breaks or how a body moves) to infer the hidden constraints and adapt your design.
"""

    return [
        {
            "stage_id": "Stage-1",
            "title": "Fragile Hull Integrity",
            "mutation_description": "Extremely low joint max force. Standard ballast placement will snap joints under wave acceleration. Forces weight distribution innovation.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "joint_max_force": 1500.0,
                "wave_amplitude": 12.0,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-2",
            "title": "Frictionless Deck",
            "mutation_description": "Zero deck friction combined with restricted build zone and increased rogue wave hits. Cargo slides perfectly, requiring a completely enclosed containment design.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "deck_friction": 0.0,
                "rogue_amplitude": 22.0,
                "wave_amplitude": 18.0,
                "build_zone_y_min": 2.5,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-3",
            "title": "The Reef Barrier",
            "mutation_description": "Submerged rocks are moved very close to the boat's bottom. Deep keels will collide with reefs, snapping joints. Requires lateral stabilization (outriggers) instead of vertical keels.",
            "terrain_config": {
                "rocks": [
                    {"x": 13.0, "y": 1.8, "r": 0.4},
                    {"x": 15.0, "y": 1.7, "r": 0.5},
                    {"x": 17.0, "y": 1.8, "r": 0.4},
                ],
                "build_zone_y_min": 2.45,
                "wave_amplitude": 12.0,
            },
            "physics_config": {},
            "task_description_suffix": UNIFORM_SUFFIX,
        },
        {
            "stage_id": "Stage-4",
            "title": "Cyclone at the Shallows",
            "mutation_description": "Maximum complexity: High gravity, fragile joints, zero friction, and high reefs. Conflicting constraints prevent both deep keels and heavy single-point structures.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "joint_max_force": 5000.0,
                "deck_friction": 0.0,
                "wave_amplitude": 20.0,
                "current_strength": 0.8,
                "rocks": [
                    {"x": 13.0, "y": 1.8, "r": 0.4},
                    {"x": 15.0, "y": 1.7, "r": 0.5},
                    {"x": 17.0, "y": 1.8, "r": 0.4},
                ],
                "build_zone_y_min": 2.5,
            },
            "physics_config": {
                "gravity": (0, -18.0),
            },
        },
    ]
