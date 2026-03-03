"""
F-06: The Pipeline task curriculum stages (mutations).

Mutated tasks vary physical parameters: fluid viscosity, delivery height (target zone),
gravity, headwind, gravity well, force budget. Invisible params are not revealed in prompt;
visible change (target at higher elevation) is stated in task_description_suffix.
Stage-1/2: single parameter change each. Stage-3/4: multiple changes.
Ordered by difficulty ascending.
"""
from __future__ import annotations

from typing import Any, Dict, List
import re


def update_task_description_for_visible_changes(base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update task description for visible changes."""
    description = base_description
    
    # Target zone height
    target_y_min = target_terrain_config.get("target_y_min", 5.0) # Prompt default
    target_y_max = target_terrain_config.get("target_y_max", 10.0)
    base_y_min = base_terrain_config.get("target_y_min", 5.0)
    base_y_max = base_terrain_config.get("target_y_max", 10.0)
    
    if target_y_min != base_y_min or target_y_max != base_y_max:
        pattern = r"(y in \[)(\d+\.?\d*)(, )(\d+\.?\d*)(\] m)"
        description = re.sub(
            pattern,
            f"\\g<1>{target_y_min:.1f}, {target_y_max:.1f}\\g<5> (originally y in [{base_y_min:.1f}, {base_y_max:.1f}] m in the source environment)",
            description
        )
        
    return description


def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update success criteria for visible changes."""
    return base_success_criteria


def get_f06_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns ordered stage configs for F-06 mutated tasks.
    Each stage: terrain_config + physics_config. Original solution (push to ground target,
    55% delivery) should fail in all mutated stages.
    """
    return [
        {
            "stage_id": "Stage-1",
            "title": "High-Viscosity Fluid",
            "mutation_description": "Fluid viscosity increased significantly; particles respond slowly to forces.",
            "task_description_suffix": """
## Environmental Warning
Environmental hazards in the corridor have changed. A new region of particle loss (pit) is active.
In addition, the fluid in this region behaves differently than nominal conditions.
Use simulation feedback to adapt your strategy.
""",
            "terrain_config": {
                "fluid": {"viscosity": 4.0},
                "pit1_y_max": 1.5,
            },
            "physics_config": {
                "force_budget": 10000.0,
            },
        },
        {
            "stage_id": "Stage-2",
            "title": "Raised Delivery Target",
            "mutation_description": "Target zone moved to higher elevation; ground-level push strategy fails.",
            "task_description_suffix": """
## Environmental Warning
The **target zone has been moved to a different elevation**.
The delivery zone coordinates have been updated in the task description.
You must adapt your routing strategy to reach this new target.
""",
            "terrain_config": {
                "target_y_min": 2.0,
                "target_y_max": 3.5,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-3",
            "title": "Viscous Fluid and Stronger Gravity",
            "mutation_description": "Higher fluid viscosity + stronger gravity; arcs fall short, delivery drops.",
            "task_description_suffix": """
## Environmental Warning
Multiple physical conditions in the transport corridor have changed. Fluid resistance and particle dynamics differ from nominal.
Infer the new dynamics from simulation feedback and adapt your strategy.
""",
            "terrain_config": {
                "fluid": {"viscosity": 1.8},
            },
            "physics_config": {
                "gravity": (0, -15.0),
                "force_budget": 9500.0,
            },
        },
        {
            "stage_id": "Stage-4",
            "title": "Hostile Pipeline",
            "mutation_description": "Raised target + high viscosity + stronger headwind + deeper gravity well + reduced force budget.",
            "task_description_suffix": """
## Environmental Warning
The **target zone is at a new elevation**.
In addition, several environmental conditions have changed: fluid resistance, external forces, and resource constraints differ from nominal.
Use simulation feedback to adapt and meet the delivery requirements.
""",
            "terrain_config": {
                "target_y_min": 2.5,
                "target_y_max": 4.0,
                "fluid": {"viscosity": 1.2},
                "headwind_fx_base": -100.0,
                "gravwell_fy": -28.0,
            },
            "physics_config": {
                "gravity": (0, -12.0),
                "force_budget": 9000.0,
            },
        },
    ]
