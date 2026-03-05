"""
C-02: The Lander task curriculum stages (mutations).

All mutations use invisible physics parameters (gravity mutation, fuel limits,
damping, thrust delay, wind). The solver agent is NOT told exact values;
it must infer from feedback.
Stages ordered by difficulty: Stage-1 (single param) -> Stage-4 (multiple params).
"""

from __future__ import annotations

from typing import Any, Dict, List
import re

def update_task_description_for_visible_changes(base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update task description for visible changes."""
    return base_description


def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update success criteria for visible changes."""
    criteria = base_success_criteria
    target_fuel = target_terrain_config.get("min_fuel_remaining_at_landing")
    
    if target_fuel is not None and target_fuel != 450.0:
        pattern = r"(Efficiency\*\*: Land with at least )(\d+\.?\d*)( N·s of impulse budget remaining.)"
        criteria = re.sub(pattern, f"\\g<1>{target_fuel:.0f} N·s of impulse budget remaining (originally 450 N·s).", criteria)
    return criteria


def get_c02_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns ordered stage configs for C-02: The Lander task variants.
    Each stage: stage_id, title, mutation_description, task_description_suffix,
    terrain_config, physics_config.
    """
    task_description_suffix = """
## Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables **MIGHT** have changed from the initial environment, **NOT ALL** of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
- **Dynamic gravitational shifts**: Sudden shifts in gravitational acceleration may occur during the mission.
- **Resource availability**: The total fuel or energy available for the descent may be altered.
- **Operational safety margins**: Requirements for remaining resources at task completion may be adjusted.
- **Actuation latency**: Delay in engine or actuator response to control commands may have changed.
- **Atmospheric disturbances**: Continuous horizontal forces acting on the vehicle during flight may vary.
- **Transient turbulence**: Intermittent high-intensity environmental disturbances (gusts) may be present.
- **Disturbance frequency**: The likelihood of encountering environmental turbulence may have changed.

**Discovery via feedback**: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., how the vehicle deviates or crashes) to infer the hidden constraints and adapt your design.
"""
    return [
        {
            "stage_id": "Stage-1",
            "title": "Gravity spike",
            "mutation_description": "Gravity suddenly increases from 10 to 16 m/s² at step 180.",
            "task_description_suffix": task_description_suffix,
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
            "task_description_suffix": task_description_suffix,
            "terrain_config": {
                "min_fuel_remaining_at_landing": 420.0,
            },
            "physics_config": {
                "total_fuel_impulse": 3800.0,
            },
        },
        {
            "stage_id": "Stage-3",
            "title": "Gravity spike and fuel scarcity",
            "mutation_description": "Gravity mutation at step 200 plus reduced fuel budget.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {
                "min_fuel_remaining_at_landing": 400.0,
            },
            "physics_config": {
                "gravity_mutation": {"at_step": 200, "gravity_after": (0, -15.5)},
                "total_fuel_impulse": 4000.0,
            },
        },
        {
            "stage_id": "Stage-4",
            "title": "Hostile environment",
            "mutation_description": "Gravity mutation, limited fuel, longer thrust delay, stronger wind.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {
                "min_fuel_remaining_at_landing": 450.0,
            },
            "physics_config": {
                "gravity_mutation": {"at_step": 150, "gravity_after": (0, -17.0)},
                "total_fuel_impulse": 3600.0,
                "thrust_delay_steps": 6,
                "wind_amplitude": 48.0,
                "gust_amplitude": 75.0,
                "gust_prob": 0.08,
            },
        },
    ]
