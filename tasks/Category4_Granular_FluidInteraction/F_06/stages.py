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
        description = re.sub(pattern, f"\\g<1>\\g<2>\\g<3>\\g<4>\\g<5> (FROM: y=[{base_y_min:.1f}, {base_y_max:.1f}], TO: y=[{target_y_min:.1f}, {target_y_max:.1f}])", description)
        
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
The fluid in this environment behaves differently (slower response to forces). In addition, **a pit is now active** in the corridor (x about 13.5–15.5); particles entering it are lost. You must route particles above the pit and adapt to the fluid behavior using feedback.
""",
            "terrain_config": {
                "fluid": {"viscosity": 4.0},  # high drag
                "pit1_y_max": 1.5,  # enable pit: ref strategy pushes low and loses many
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
The **target zone has been moved to a higher elevation**. The delivery zone is now in the band y=[2.0, 3.5] (same x range as before).
You must push particles to this higher target; strategies that only reach ground level will not succeed.
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
Multiple physical conditions have changed. The fluid responds more slowly to forces, and gravity is stronger.
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
The **target zone is at a higher elevation** (y=[2.5, 4.0]). In addition, several physical conditions have changed:
stronger headwind, a deeper gravity well, and a tighter per-step force budget. Use feedback to adapt.
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
