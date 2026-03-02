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
    
    # Leakage rate
    target_leakage = target_terrain_config.get("max_leakage_rate", 0.001) # Default 0.1%
    base_leakage = base_terrain_config.get("max_leakage_rate", 0.001)
    
    if target_leakage != base_leakage:
        pattern = r"(leakage remains below )(\d+\.?\d*%)"
        description = re.sub(pattern, f"\\g<1>\\g<2> (FROM: {base_leakage*100:.2f}%, TO: {target_leakage*100:.2f}%)", description)
        
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
        pattern = r"(Leakage Rate\*\*: Total leakage < )(\d+\.?\d*%)"
        criteria = re.sub(pattern, f"\\g<1>\\g<2> (FROM: < {base_leakage*100:.2f}%, TO: < {target_leakage*100:.2f}%)", criteria)
        
    return criteria


def get_f01_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns ordered stage configs for F-01: The Dam (difficulty ascending).
    Each stage: stage_id, title, mutation_description, task_description_suffix,
    terrain_config, physics_config. All changes are invisible (fluid density, joint break,
    gravity, etc.); prompt only gets generic environmental warning.
    """
    return [
        {
            "stage_id": "Stage-1",
            "title": "Heavier fluid",
            "mutation_description": "Fluid density increased; higher hydrostatic pressure on dam, more leakage or joint stress.",
            "task_description_suffix": """
## Environmental Warning
The reservoir fluid behaves differently than nominal conditions. Containment and structure stress may be affected.
Use simulation feedback to adapt your design.
""",
            "terrain_config": {
                "fluid": {"density": 1850.0},  # default 1000; ref passed at 1450
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-2",
            "title": "Weaker joints",
            "mutation_description": "Joint break force lowered; welds fail more easily under surge and debris.",
            "task_description_suffix": """
## Environmental Warning
Structural conditions have changed. Joints may fail under load more easily than in nominal conditions.
Use feedback to ensure your dam remains intact.
""",
            "terrain_config": {
                "joint_break_force": 22000.0,  # default 50000
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-3",
            "title": "Higher head and heavier fluid",
            "mutation_description": "Fluid density and fill height increased; joint break force reduced. Multiple stress factors.",
            "task_description_suffix": """
## Environmental Warning
Multiple reservoir and structural conditions differ from nominal. Pressure and integrity thresholds are affected.
Infer the new behavior from simulation feedback and adapt your design.
""",
            "terrain_config": {
                "fluid_height": 8.2,
                "fluid": {"density": 1550.0},
                "joint_break_force": 26000.0,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-4",
            "title": "Extreme environment",
            "mutation_description": "Stronger gravity, heavier fluid, higher fill, weaker joints, stronger surges, stricter leakage threshold.",
            "task_description_suffix": """
## Environmental Warning
Several physical and structural parameters have changed. Gravity, fluid behavior, joint strength, and success criteria may all differ from nominal.
You must infer the new environment from simulation feedback and design a dam that meets the (possibly stricter) containment and integrity requirements.
""",
            "terrain_config": {
                "fluid_height": 7.5,
                "fluid": {"density": 1250.0},
                "joint_break_force": 26000.0,
                "surge_impulses": [0.82, 0.98, 1.15, 1.32, 1.5, 1.62, 1.73, 1.85, 1.95],
                "max_leakage_rate": 0.0005,  # 0.05% — stricter than baseline 0.1%
            },
            "physics_config": {
                "gravity": (0, -13.0),
            },
        },
    ]
