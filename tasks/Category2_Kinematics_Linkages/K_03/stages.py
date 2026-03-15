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
    target_mass = float(target_obj.get("mass", 1.0))
    base_mass = float(base_obj.get("mass", 1.0))
    target_friction = float(target_obj.get("friction", 0.6))
    base_friction = float(base_obj.get("friction", 0.6))
    
    if target_shape != base_shape:
        # Update Target Object description (shape); prompt line includes "of mass X kg" and optional platform friction
        pattern = r"(- \*\*Target Object\*\*: An object)( of mass \d+\.?\d* kg with surface friction coefficient \d+\.?\d* at x=5\.0m, y=2\.0m \(on a platform at y=1\.8m)(; platform surface friction coefficient 0\.25)?\)\."
        if re.search(pattern, description):
            shape_name = "a circular disk" if target_shape == "circle" else "a triangular block" if target_shape == "triangle" else "a rectangular block"
            orig_name = "a rectangular block" if base_shape == "box" else "a triangular block" if base_shape == "triangle" else "a circular disk"
            description = re.sub(
                pattern,
                lambda m: f"- **Target Object**: {shape_name} (originally {orig_name} in the source environment){m.group(2)}{m.group(3) or ''}).",
                description
            )
    
    if target_mass != base_mass:
        # Update object mass with format [new_value] (originally [old_value] in the source environment)
        # Only match the first "of mass X kg" not the one inside "(originally X kg ...)"
        mass_pattern = r"(of mass )(\d+\.?\d*)( kg)(?! \()"
        if re.search(mass_pattern, description):
            description = re.sub(
                mass_pattern,
                lambda m: f"{m.group(1)}{target_mass}{m.group(3)} (originally {m.group(2)} kg in the source environment)",
                description,
                count=1,
            )
    
    if target_friction != base_friction:
        # Update object friction with format [new_value] (originally [old_value] in the source environment)
        # Capture full position suffix including optional platform friction so output is not truncated
        friction_pattern = r"(with surface friction coefficient )(\d+\.?\d*)( at x=5\.0m, y=2\.0m \(on a platform at y=1\.8m)(; platform surface friction coefficient 0\.25)?\)\."
        if re.search(friction_pattern, description):
            description = re.sub(
                friction_pattern,
                lambda m: f"{m.group(1)}{target_friction} (originally {m.group(2)} in the source environment){m.group(3)}{m.group(4) or ''}).",
                description,
                count=1,
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
 - **Target object shape**: The geometry of the payload (e.g., rectangular, circular, or triangular).
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
            "mutation_description": "Target is a circular (disk) object with reduced surface friction. Added stabilization damping.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {"objects": {"shape": "circle", "mass": 1.0, "friction": 0.25, "x": 5.0, "y": 2.0}},
            "physics_config": {"linear_damping": 0.5, "angular_damping": 0.5},
        },
        {
            "stage_id": "Stage-2",
            "title": "Heavy World",
            "mutation_description": "Gravity increased; object mass increased. Added stabilization damping.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {"objects": {"shape": "box", "mass": 5.0, "friction": 0.6, "x": 5.0, "y": 2.0}},
            "physics_config": {"gravity": (0, -20.0), "linear_damping": 0.5, "angular_damping": 0.5},
        },
        {
            "stage_id": "Stage-3",
            "title": "Slippery Object + Heavy World + Damping",
            "mutation_description": "Object friction reduced; gravity increased; object mass increased; atmospheric damping present.",
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
            "mutation_description": "Target is a circular object (disk) with reduced friction; gravity increased; object mass increased; damping present.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {"objects": {"shape": "circle", "mass": 5.0, "friction": 0.2, "x": 5.0, "y": 2.0}},
            "physics_config": {
                "gravity": (0, -20.0),
                "linear_damping": 0.5,
                "angular_damping": 0.5,
            },
        },
    ]
