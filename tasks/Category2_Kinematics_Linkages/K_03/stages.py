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
        # Update Target Object description (shape) and platform height
        # Matches "- **Target Object**: [Shape Description] of mass..." and replaces shape part.
        # Use more robust regex that doesn't hardcode mass/friction values
        pattern = r"(- \*\*Target Object\*\*: )(.*?)(?! \(originally)( of mass .*? kg with surface friction coefficient .*? at x=.*?m, y=.*?m \(on a platform at y=)(\d+\.?\d*)(.*?)"
        if re.search(pattern, description):
            shape_name = "A circular disk (radius 0.25m)" if target_shape == "circle" else "A triangular block (approx 0.4m)" if target_shape == "triangle" else "A rectangular block (0.4m x 0.4m)"
            orig_name = "A rectangular block (0.4m x 0.4m)" if base_shape == "box" else "A triangular block (approx 0.4m)" if base_shape == "triangle" else "A circular disk (radius 0.25m)"
            
            # Platform height depends on shape height: platform_top = obj_y - obj_h / 2
            # box: h=0.4 -> 1.8; triangle: h=0.4 -> 1.8; circle: h=0.5 -> 1.75
            target_platform_y = 1.75 if target_shape == "circle" else 1.8
            base_platform_y = 1.75 if base_shape == "circle" else 1.8
            
            if target_platform_y != base_platform_y:
                platform_y_str = f"{target_platform_y} (originally {base_platform_y} in the source environment)"
            else:
                platform_y_str = str(target_platform_y)

            description = re.sub(
                pattern,
                lambda m: f"{m.group(1)}{shape_name} (originally {orig_name} in the source environment){m.group(3)}{platform_y_str}{m.group(5)}",
                description
            )
    
    # Exhaustive sync for object position if it changes
    target_obj_x = float(target_obj.get("x", 5.0))
    base_obj_x = float(base_obj.get("x", 5.0))
    if target_obj_x != base_obj_x:
        obj_x_pattern = r"( at x=)(\d+\.?\d*)(m, y=)(?! \(originally)"
        description = re.sub(
            obj_x_pattern,
            lambda m: f"{m.group(1)}{target_obj_x}m (originally {m.group(2)}m in the source environment), y=",
            description
        )
    
    target_obj_y = float(target_obj.get("y", 2.0))
    base_obj_y = float(base_obj.get("y", 2.0))
    if target_obj_y != base_obj_y:
        obj_y_pattern = r"(, y=)(\d+\.?\d*)(m \(on a platform)(?! \(originally)"
        description = re.sub(
            obj_y_pattern,
            lambda m: f"{m.group(1)}{target_obj_y}m (originally {m.group(2)}m in the source environment) (on a platform",
            description
        )
    
    if target_mass != base_mass:
        # Update object mass with format [new_value] (originally [old_value] in the source environment)
        # Avoid double-replacement by checking for existing "(originally"
        mass_pattern = r"(of mass )(\d+\.?\d*)( kg)(?! \(originally)"
        if re.search(mass_pattern, description):
            description = re.sub(
                mass_pattern,
                lambda m: f"{m.group(1)}{target_mass}{m.group(3)} (originally {m.group(2)} kg in the source environment)",
                description,
                count=1,
            )
    
    if target_friction != base_friction:
        # Update object friction with format [new_value] (originally [old_value] in the source environment)
        friction_pattern = r"(with surface friction coefficient )(\d+\.?\d*)( at x=)(?! \(originally)"
        if re.search(friction_pattern, description):
            description = re.sub(
                friction_pattern,
                lambda m: f"{m.group(1)}{target_friction} (originally {m.group(2)} in the source environment){m.group(3)}",
                description,
                count=1,
            )

    # Exhaustive sync for other visible parameters if they change
    target_gantry_friction = float(target_terrain_config.get("gantry_friction", 0.6))
    base_gantry_friction = float(base_terrain_config.get("gantry_friction", 0.6))
    if target_gantry_friction != base_gantry_friction:
        gantry_pattern = r"(surface friction coefficient )(\d+\.?\d*)(\)\. Use `get_anchor_for_gripper\(\)`)(?! \(originally)"
        description = re.sub(
            gantry_pattern,
            lambda m: f"{m.group(1)}{target_gantry_friction} (originally {m.group(2)} in the source environment){m.group(3)}",
            description
        )

    target_platform_friction = float(target_terrain_config.get("platform_friction", 0.25))
    base_platform_friction = float(base_terrain_config.get("platform_friction", 0.25))
    if target_platform_friction != base_platform_friction:
        platform_friction_pattern = r"(platform surface friction coefficient )(\d+\.?\d*)(\))(?! \(originally)"
        description = re.sub(
            platform_friction_pattern,
            lambda m: f"{m.group(1)}{target_platform_friction} (originally {m.group(2)} in the source environment){m.group(3)}",
            description
        )

    target_budget = float(target_terrain_config.get("max_structure_mass", 30.0))
    base_budget = float(base_terrain_config.get("max_structure_mass", 30.0))
    if target_budget != base_budget:
        budget_pattern = r"(Mass Budget\*\*: .*?<= )(\d+\.?\d*)( kg)(?! \(originally)"
        description = re.sub(
            budget_pattern,
            lambda m: f"{m.group(1)}{target_budget}{m.group(3)} (originally {m.group(2)} kg in the source environment)",
            description
        )

    target_y = float(target_terrain_config.get("target_object_y", 3.5))
    base_y = float(base_terrain_config.get("target_object_y", 3.5))
    if target_y != base_y:
        # Update target height in multiple places
        y_pattern = r"(at least y=|above y=|reaches y >= )(\d+\.?\d*)(m)(?! \(originally)"
        description = re.sub(
            y_pattern,
            lambda m: f"{m.group(1)}{target_y}{m.group(3)} (originally {m.group(2)}m in the source environment)",
            description
        )

    target_time = float(target_terrain_config.get("min_simulation_time", 1.34))
    base_time = float(base_terrain_config.get("min_simulation_time", 1.34))
    if target_time != base_time:
        time_pattern = r"(for at least |Sustain\*\*: Object held at target height for >= )(\d+\.?\d*)( seconds)(?! \(originally)"
        description = re.sub(
            time_pattern,
            lambda m: f"{m.group(1)}{target_time}{m.group(3)} (originally {m.group(2)} seconds in the source environment)",
            description
        )
        
        # Also update the (approx. N steps) part
        steps_pattern = r"(\(approx\. )(\d+)( steps\))(?! \(originally)"
        target_steps = int(target_time / 0.016666666666666666)  # 1/60s
        description = re.sub(
            steps_pattern,
            lambda m: f"{m.group(1)}{target_steps} (originally {m.group(2)} in the source environment){m.group(3)}",
            description
        )

    target_ground_friction = float(target_terrain_config.get("ground_friction", 0.8))
    base_ground_friction = float(base_terrain_config.get("ground_friction", 0.8))
    if target_ground_friction != base_ground_friction:
        ground_pattern = r"(Ground surface friction )(\d+\.?\d*)(\.)(?! \(originally)"
        description = re.sub(
            ground_pattern,
            lambda m: f"{m.group(1)}{target_ground_friction} (originally {m.group(2)} in the source environment){m.group(3)}",
            description
        )
    
    target_min_h = float(target_terrain_config.get("min_object_height", 2.0))
    base_min_h = float(base_terrain_config.get("min_object_height", 2.0))
    if target_min_h != base_min_h:
        min_h_pattern = r"(falls below y=|below )(\d+\.?\d*)(m after being lifted)(?! \(originally)"
        description = re.sub(
            min_h_pattern,
            lambda m: f"{m.group(1)}{target_min_h}{m.group(3)} (originally {m.group(2)}m in the source environment)",
            description
        )
            
    return description

def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    # Use the same logic as task description since success criteria is part of the same prompt set
    return update_task_description_for_visible_changes(base_success_criteria, target_terrain_config, base_terrain_config)

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
