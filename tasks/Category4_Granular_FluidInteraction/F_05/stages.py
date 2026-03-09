"""
F-05: The Boat task curriculum stages (mutations).

Mutated tasks vary physical parameters: wave amplitude, deck friction,
joint max force (fragility), build zone, current, restoring torque, gravity, etc.
Invisible changes: solver is NOT told exact values; it must infer from feedback.
Stage-1/2: single parameter change. Stage-3/4: multiple parameter changes.
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
        
        # Update Build Zone description
        # Matches: - **Build Zone**: Structure must be attached to the boat body within x=[12.0, 18.0], y=[2.0, 4.5].
        pattern = r"(- \*\*Build Zone\*\*: Structure must be attached to the boat body within x=\[)([\d.]+), ([\d.]+)(\], y=\[)([\d.]+), ([\d.]+)(\]\.)"
        
        # Use .1f for x and y_max, but .2f for y_min if it's mutated to 2.55 etc.
        # Actually, let's use a more flexible formatting for the target values.
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
    Returns ordered stage configs for F-05: The Boat (difficulty ascending).
    Stages implement essential difficulty escalation via structural innovation.
    """
    
    # UNIFORM_SUFFIX generated based on the UNION of all mutated variables across Stages 1-4.
    UNIFORM_SUFFIX = """
## Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables MIGHT have changed from the initial environment, NOT ALL of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
 - **Joint Load Tolerance**: The maximum stress joints can withstand before structural failure (breaking).
 - **Hazard Density**: The presence, size, and vertical distribution of submerged or floating obstacles.
 - **Integration Zone Constraints**: The vertical and horizontal boundaries where structures can be securely anchored to the vessel hull.
 - **Deck Surface Traction**: The friction coefficient of the vessel's deck, affecting how easily cargo slides.
 - **Wave Dynamics**: The amplitude of primary and secondary wave patterns, affecting vessel roll and heave.
 - **Fluid Current**: The strength of the water's flow, impacting the vessel's drift and station-keeping.
 - **Stability Coefficients**: The restoring torque and self-righting capacity of the vessel.
 - **Gravity**: The local gravitational acceleration, influencing displacement and stability.
 - **Impulsive Disturbances**: The magnitude and timing of periodic rogue waves and lateral gusts.

**Discovery via feedback**: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., where a joint breaks or how a body moves) to infer the hidden constraints and adapt your design.
"""

    return [
        {
            "stage_id": "Stage-1",
            "title": "Fragile Anchor Points",
            "mutation_description": "Introduces a finite maximum force for joints. Heavy or poorly balanced structures will cause joints to break under wave acceleration.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "joint_max_force": 1100.0,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-2",
            "title": "Restricted Anchor Zone",
            "mutation_description": "The vertical range of the build zone where joints can be attached to the hull is reduced. Standard ballast placement may fail to anchor correctly.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "build_zone_y_min": 2.55,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-3",
            "title": "Slippery Deck & Rough Sea",
            "mutation_description": "Combined challenge: zero deck friction, increased waves, fragile joints, and narrowed anchor zone.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "joint_max_force": 1500.0,
                "deck_friction": 0.001,
                "wave_amplitude": 18.0,
                "build_zone_y_min": 2.45,
                "current_strength": 0.6,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-4",
            "title": "Abyssal Storm",
            "mutation_description": "Maximum difficulty: higher gravity, extreme waves, slippery deck, restricted anchor zone, and fragile joints.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "joint_max_force": 1200.0,
                "deck_friction": 0.0,
                "wave_amplitude": 25.0,
                "build_zone_y_min": 2.52,
                "current_strength": 0.85,
                "restoring_coeff": 1000.0,
                "rogue_amplitude": 20.0,
                "rocks": [
                    {"x": 13.0, "y": 1.7, "r": 0.6},
                    {"x": 15.0, "y": 1.6, "r": 0.7},
                    {"x": 17.0, "y": 1.7, "r": 0.6},
                ],
            },
            "physics_config": {
                "gravity": (0, -15.0),
            },
        },
    ]
