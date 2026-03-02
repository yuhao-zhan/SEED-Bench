"""
F-05: The Boat task curriculum stages (mutations).

Mutated tasks vary physical parameters: wave amplitude, cargo friction (fixation difficulty),
current, restoring torque, lateral impulses, rogue waves, gravity, etc.
Invisible changes: solver is NOT told exact values; it must infer from feedback.
Stage-1/2: single parameter change. Stage-3/4: multiple parameter changes.
Ordered by difficulty (ascending).
"""
from __future__ import annotations

from typing import Any, Dict, List


def update_task_description_for_visible_changes(
    base_description: str, terrain_config: Dict[str, Any]
) -> str:
    """Update task description if any visible terrain/config change. Current mutations are invisible."""
    return base_description


def update_success_criteria_for_visible_changes(
    base_success_criteria: str, terrain_config: Dict[str, Any]
) -> str:
    """Update success criteria for visible changes. Current mutations are invisible."""
    return base_success_criteria


def get_f05_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns ordered stage configs for F-05: The Boat (difficulty ascending).
    Each stage: stage_id, title, mutation_description, task_description_suffix,
    terrain_config, physics_config. All changes are invisible (waves, cargo friction,
    current, lateral impulses, etc.); prompt only gets generic environmental warning.
    """
    return [
        {
            "stage_id": "Stage-1",
            "title": "Stronger waves",
            "mutation_description": "Primary wave amplitude increased; boat excitation and cargo bounce more severe.",
            "task_description_suffix": """
## Environmental Warning
Sea conditions have changed. Wave excitation and vessel motion may be more severe than in nominal conditions.
Use simulation feedback to adapt your design for stability and cargo retention.
""",
            "terrain_config": {
                "wave_amplitude": 17.0,  # default 10.0 — ~70% increase so ref solution loses cargo or capsizes
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-2",
            "title": "Slipperier cargo",
            "mutation_description": "Cargo friction reduced; cargo fixation harder, more likely to slide off.",
            "task_description_suffix": """
## Environmental Warning
Cargo handling conditions have changed. Cargo may be harder to contain than in nominal conditions.
Use feedback to ensure your containment and ballast remain effective.
""",
            "terrain_config": {
                "cargo": {"friction": 0.12, "count": 10, "radius": 0.15, "density": 260.0, "seed": 42},
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-3",
            "title": "Stronger current and weaker restoring",
            "mutation_description": "Water current increased, restoring torque reduced; boat drifts and rolls more.",
            "task_description_suffix": """
## Environmental Warning
Multiple hydrodynamic and stability conditions differ from nominal. Current, roll response, and wave loading may all be affected.
Infer the new behavior from simulation feedback and adapt your design.
""",
            "terrain_config": {
                "current_strength": 0.58,   # default 0.35
                "restoring_coeff": 1150.0,   # default 1600 — weaker righting moment
                "wave_amplitude": 13.0,      # slightly higher than default 10
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-4",
            "title": "Extreme sea and cargo",
            "mutation_description": "Larger waves, slipperier cargo, stronger/faster lateral gusts, stronger rogue, higher gravity.",
            "task_description_suffix": """
## Environmental Warning
Several physical and environmental parameters have changed. Waves, cargo behavior, lateral forces, and effective weight may all differ from nominal.
You must infer the new environment from simulation feedback and design so that all cargo is retained and the boat does not capsize.
""",
            "terrain_config": {
                "wave_amplitude": 18.0,
                "wave2_amplitude": 9.0,           # default 5.0
                "cargo": {"friction": 0.10, "count": 10, "radius": 0.15, "density": 260.0, "seed": 42},
                "lateral_impulse_amplitude": 105.0,   # default 68 — much stronger
                "lateral_impulse_interval_steps": 140,  # default 200 — more frequent
                "restoring_coeff": 1100.0,
                "rogue_amplitude": 20.0,         # default 14
                "current_strength": 0.52,        # default 0.35
            },
            "physics_config": {
                "gravity": (0, -13.0),           # default -10 — heavier effective load
            },
        },
    ]
