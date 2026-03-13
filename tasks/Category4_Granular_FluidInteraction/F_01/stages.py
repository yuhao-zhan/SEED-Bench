"""
F-01: The Dam task curriculum stages (mutations).

Mutated tasks vary invisible physical parameters: fluid density/height, joint strength,
gravity, damping, surge strength, leakage threshold. The solver is NOT told exact values;
it must infer from feedback.
Stage-1/2: single parameter change. Stage-3/4: multiple parameter changes.
Ordered by difficulty (ascending).
"""
from __future__ import annotations

from typing import Any, Dict, List
import re


def update_task_description_for_visible_changes(
    base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]
) -> str:
    """Update task description for visible changes."""
    description = base_description
    
    # Leakage rate (success criteria often in description too)
    target_leakage = target_terrain_config.get("max_leakage_rate", 0.001)
    base_leakage = base_terrain_config.get("max_leakage_rate", 0.001)
    
    if target_leakage != base_leakage:
        pattern = r"(leakage rate remains below )(\d+\.?\d*%)"
        description = re.sub(
            pattern,
            f"\\g<1>{target_leakage*100:.2f}% (originally {base_leakage*100:.2f}% in the source environment)",
            description
        )
        
    return description


def update_success_criteria_for_visible_changes(
    base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]
) -> str:
    """Update success criteria for visible changes."""
    criteria = base_success_criteria
    
    # Leakage rate
    target_leakage = target_terrain_config.get("max_leakage_rate", 0.001)
    base_leakage = base_terrain_config.get("max_leakage_rate", 0.001)
    
    if target_leakage != base_leakage:
        pattern = r"(1\. \*\*Leakage Rate\*\*: Total leakage < )(\d+\.?\d*%)"
        criteria = re.sub(
            pattern,
            f"\\g<1>{target_leakage*100:.2f}% (originally < {base_leakage*100:.2f}% in the source environment)",
            criteria
        )
        
    return criteria


def get_f01_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns ordered stage configs for F-01: The Dam (difficulty ascending).
    Each stage: stage_id, title, mutation_description, task_description_suffix,
    terrain_config, physics_config. All changes are invisible (fluid density, joint break,
    gravity, etc.); prompt only gets generic environmental warning.
    """
    task_description_suffix = """
## Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables **MIGHT** have changed from the initial environment,
**NOT ALL** of them will necessarily be mutated in any given task. You must use
active interaction and environmental feedback to deduce which specific conditions apply:
 - **Fluid density**: Mass per unit volume of the water particles; affects hydrostatic pressure.
 - **Joint break force**: The force threshold above which beam-to-beam welds can fail.
 - **Reservoir fill height**: The vertical fill level of the reservoir; affects pressure at the base.
 - **Gravitational acceleration**: The strength and direction of the vertical gravitational force.

**Discovery via feedback**: Your objective is to identify the underlying physical
rules of this specific environment through active interaction and observation.
Initial standard solutions may require adjustment; analyze structural stresses
and containment efficiency to deduce the hidden constraints and adapt your design.
"""
    return [
        {
            "stage_id": "Stage-1",
            "title": "Heavier fluid",
            "mutation_description": "Fluid density increased to 1500 kg/m^3. Higher hydrostatic pressure.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {
                "fluid": {"density": 1500.0},
                "max_leakage_rate": 0.02, # 2.0%
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-2",
            "title": "Weaker joints",
            "mutation_description": "Joint break force lowered to 35000 N. Structure is more fragile.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {
                "joint_break_force": 35000.0,
                "max_leakage_rate": 0.02, # 2.0%
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-3",
            "title": "Higher head",
            "mutation_description": "Fluid height increased to 7.5m. More pressure at base.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {
                "fluid_height": 7.5,
                "fluid": {"density": 1200.0},
                "max_leakage_rate": 0.02, # 2.0%
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-4",
            "title": "Jovian gravity",
            "mutation_description": "Gravity increased to -12.0 m/s^2. Density 1100 kg/m^3.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {
                "fluid": {"density": 1100.0},
                "joint_break_force": 40000.0,
                "max_leakage_rate": 0.02, # 2.0%
            },
            "physics_config": {
                "gravity": (0, -12.0),
            },
        },
    ]
