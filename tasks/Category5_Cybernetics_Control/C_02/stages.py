"""
C-02: The Lander task curriculum stages (mutations).

All mutations use invisible physics parameters (gravity mutation, fuel limits,
damping, thrust delay, wind). The solver agent is NOT told exact values;
it must infer from feedback.
Stages ordered by difficulty: Stage-1 (single param) -> Stage-4 (multiple params).
"""

from __future__ import annotations

from typing import Any, Dict, List


def update_task_description_for_visible_changes(base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update task description for visible changes."""
    return base_description


def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update success criteria for visible changes."""
    return base_success_criteria


def get_c02_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns ordered stage configs for C-02: The Lander task variants.
    Each stage: stage_id, title, mutation_description, task_description_suffix,
    terrain_config, physics_config.
    """
    return [
        {
            "stage_id": "Stage-1",
            "title": "Gravity spike",
            "mutation_description": "Gravity suddenly increases from 10 to 16 m/s² at step 180.",
            "task_description_suffix": """
## Environmental Warning
Localized gravitational anomalies may occur during flight.
Use simulation feedback to detect and adapt to any changes in the descent rate.
""",
            "terrain_config": {},
            "physics_config": {
                "gravity_mutation": {
                    "at_step": 180,
                    "gravity_after": (0, -16.0),
                },
            },
        },
        {
            "stage_id": "Stage-2",
            "title": "Fuel scarcity",
            "mutation_description": "Total fuel reduced, min fuel remaining at landing increased.",
            "task_description_suffix": """
## Environmental Warning
Fuel availability or consumption behavior may differ from nominal conditions.
Use feedback to ensure your trajectory remains within the required efficiency limits.
""",
            "terrain_config": {},
            "physics_config": {
                "total_fuel_impulse": 3800.0,
                "min_fuel_remaining_at_landing": 420.0,
            },
        },
        {
            "stage_id": "Stage-3",
            "title": "Gravity spike and fuel scarcity",
            "mutation_description": "Gravity mutation at step 200 plus reduced fuel budget.",
            "task_description_suffix": """
## Environmental Warning
Multiple environmental factors have shifted. Gravity and fuel constraints differ from nominal.
Infer the new environment from simulation feedback and adapt your strategy.
""",
            "terrain_config": {},
            "physics_config": {
                "gravity_mutation": {"at_step": 200, "gravity_after": (0, -15.5)},
                "total_fuel_impulse": 4000.0,
                "min_fuel_remaining_at_landing": 400.0,
            },
        },
        {
            "stage_id": "Stage-4",
            "title": "Hostile environment",
            "mutation_description": "Gravity mutation, limited fuel, longer thrust delay, stronger wind.",
            "task_description_suffix": """
## Environmental Warning
Several physical parameters have changed simultaneously. Gravity, fuel, actuation delay, and external disturbances all differ from nominal.
You must infer the new environment from simulation feedback and adapt your strategy accordingly.
""",
            "terrain_config": {},
            "physics_config": {
                "gravity_mutation": {"at_step": 150, "gravity_after": (0, -17.0)},
                "total_fuel_impulse": 3600.0,
                "min_fuel_remaining_at_landing": 450.0,
                "thrust_delay_steps": 6,
                "wind_amplitude": 48.0,
                "gust_amplitude": 75.0,
                "gust_prob": 0.08,
            },
        },
    ]
