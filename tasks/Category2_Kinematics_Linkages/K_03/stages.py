"""
K-03: The Gripper task curriculum stages (mutations).
"""

from __future__ import annotations
from typing import Any, Dict, List
import re

def update_task_description_for_visible_changes(base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    description = base_description
    
    target_obj = target_terrain_config.get("objects", {})
    base_obj = base_terrain_config.get("objects", {})
    
    target_shape = target_obj.get("shape", "box")
    base_shape = base_obj.get("shape", "box")
    
    if target_shape != base_shape:
        # Update Target Object description
        pattern = r"(- \*\*Target Object\*\*: An object)( at x=5.0m, y=2.0m \(on a platform at y=1.8m\)\.)"
        if re.search(pattern, description):
            shape_name = "a circular disk" if target_shape == "circle" else "a triangular block" if target_shape == "triangle" else "a rectangular block"
            orig_name = "a rectangular block" if base_shape == "box" else "a circular disk"
            description = re.sub(
                pattern,
                lambda m: f"- **Target Object**: {shape_name} (originally {orig_name} in the source environment){m.group(2)}",
                description
            )
            
    return description

def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    # No visible changes in success criteria for K_03 currently
    return base_success_criteria

def get_k03_curriculum_stages():
    task_description_suffix = """
## Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables **MIGHT** have changed from the initial environment, **NOT ALL** of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
 - **Object surface friction**: The slipperiness of the payload.
 - **Gravitational acceleration**: The strength of the vertical gravitational force.
 - **Object mass**: The weight of the target payload.
 - **Atmospheric damping**: Linear and angular air resistance acting on all bodies.

**Discovery via feedback**: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., if the object slips out or the motor stalls) to infer the hidden constraints and adapt your design.
"""

    return [
        {
            "stage_id": "Stage-1",
            "title": "Slippery Object",
            "mutation_description": "Object surface friction reduced from 0.6 to 0.3. Added stabilization damping.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {"objects": {"shape": "box", "mass": 1.0, "friction": 0.3, "x": 5.0, "y": 2.0}},
            "physics_config": {"linear_damping": 0.5, "angular_damping": 0.5},
        },
        {
            "stage_id": "Stage-2",
            "title": "Heavy World",
            "mutation_description": "Gravity increased to -20 m/s², object mass to 5kg. Added stabilization damping.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {"objects": {"shape": "box", "mass": 5.0, "friction": 0.6, "x": 5.0, "y": 2.0}},
            "physics_config": {"gravity": (0, -20.0), "linear_damping": 0.5, "angular_damping": 0.5},
        },
        {
            "stage_id": "Stage-3",
            "title": "Slippery Object + Heavy World + Damping",
            "mutation_description": "Object friction 0.2, gravity -20, mass 5kg, damping 0.5.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {"objects": {"shape": "box", "mass": 5.0, "friction": 0.2, "x": 5.0, "y": 2.0}},
            "physics_config": {
                "gravity": (0, -20.0),
                "linear_damping": 0.5,
                "angular_damping": 0.5,
            },
        },
        {
            "stage_id": "Stage-4",
            "title": "Circular Object + Slippery + Heavy + Damping",
            "mutation_description": "Target is a circular object (disk), friction 0.2, gravity -20, mass 5kg, damping 0.5.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {"objects": {"shape": "circle", "mass": 5.0, "friction": 0.2, "x": 5.0, "y": 2.0}},
            "physics_config": {
                "gravity": (0, -20.0),
                "linear_damping": 0.5,
                "angular_damping": 0.5,
            },
        },
    ]
