"""
C-02: The Lander task curriculum stages (mutations).

All mutations use invisible physics parameters (gravity mutation, fuel limits,
damping, thrust delay, wind, impact tolerance, corridor constraints).
The solver agent is NOT told exact values; it must infer from feedback.
Stages ordered by difficulty: Stage-1 -> Stage-4.
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
    """
    # UNION of all physical variables modified across all stages
    task_description_suffix = """
## Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables MIGHT have changed from the initial environment, NOT ALL of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
 - **Structural Integrity Threshold**: The maximum safe impact velocity at touchdown may be significantly reduced.
 - **Actuation Latency**: The time delay between issuing a control command and the engine's physical response may have increased.
 - **Flight Corridor Constraints**: Atmospheric "ceilings" or upper no-fly zones may be present, creating a narrow gap for passage.
 - **Dynamic Gravitational Shifts**: The local gravity may suddenly increase or shift during flight.
 - **Resource Availability**: The total fuel impulse available for the mission may be restricted.
 - **Operational Safety Margins**: The minimum required fuel that must remain after landing may be higher.
 - **Atmospheric Disturbances**: Continuous horizontal wind forces and high-intensity gusts may be more severe.

Discovery via feedback: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., where a joint breaks or how a body moves) to infer the hidden constraints and adapt your design.
"""
    return [
        {
            "stage_id": "Stage-1",
            "title": "Fragile Touchdown",
            "mutation_description": "Structural integrity is compromised: max safe vertical speed reduced from 2.0 to 0.15 m/s.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {
                "max_safe_vertical_speed": 0.15,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-2",
            "title": "Severe Actuation Delay",
            "mutation_description": "Control system lag: thrust delay increased from 3 to 12 simulation steps.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {},
            "physics_config": {
                "thrust_delay_steps": 12,
            },
        },
        {
            "stage_id": "Stage-3",
            "title": "The Squeeze",
            "mutation_description": "Extremely narrow corridor (6.0-15.0m) combined with reduced fuel and a gravity spike at step 150 (max thrust increased to 1200 N).",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {
                "min_fuel_remaining_at_landing": 550.0,
            },
            "physics_config": {
                "barrier_y_bottom": 15.0,
                "total_fuel_impulse": 3800.0,
                "max_thrust": 1200.0,
                "gravity_mutation": {
                    "at_step": 150,
                    "gravity_after": (0, -18.0),
                },
            },
        },
        {
            "stage_id": "Stage-4",
            "title": "The Perfect Storm",
            "mutation_description": "Extreme combination: narrow corridor (6.0-20.0m), high latency, low fuel, strong wind, and fragile touchdown (1.5m/s).",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {
                "max_safe_vertical_speed": 1.5,
                "min_fuel_remaining_at_landing": 500.0,
            },
            "physics_config": {
                "barrier_y_bottom": 20.0,
                "thrust_delay_steps": 8,
                "total_fuel_impulse": 6000.0,
                "wind_amplitude": 60.0,
                "gust_amplitude": 85.0,
                "gust_prob": 0.12,
                "gravity_mutation": {
                    "at_step": 150,
                    "gravity_after": (0, -11.5),
                },
            },
        },
    ]
