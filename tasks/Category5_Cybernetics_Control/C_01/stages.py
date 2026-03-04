"""
C-01: The Cart-Pole task curriculum stages (mutations).

Mutation dimensions: pole length/mass, gravity, sensor delay, actuator rate limit, damping.
The solver agent is NOT told the exact parameter changes; it must infer from feedback.
Stages ordered by difficulty: Stage-1 (easiest, one param) -> Stage-4 (hardest, multiple params).
"""

from __future__ import annotations

from typing import Any, Dict, List


def update_task_description_for_visible_changes(base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update task description for visible changes."""
    return base_description


def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update success criteria for visible changes."""
    return base_success_criteria


def get_c01_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns ordered stage configs for C-01: The Cart-Pole task variants.
    Each stage dict: stage_id, title, mutation_description, task_description_suffix,
    terrain_config, physics_config.
    All mutations are invisible (no exact numeric changes in task_description_suffix).
    """
    task_description_suffix = """
Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables MIGHT have changed from the initial environment, NOT ALL of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
 - sensor_delay_angle_steps: Unexpected latency in orientation sensor data.
 - sensor_delay_omega_steps: Unexpected latency in angular velocity feedback.
 - gravity: Alterations in the gravitational field affecting system weight and balance.
 - pole_length: Modifications to the pendulum's structural dimensions.
 - pole_mass: Changes in the mass distribution and rotational inertia of the pole.
 - angular_damping: Increased resistance to rotational motion within the joints.
 - actuator_rate_limit: Limits on the speed at which control forces can be adjusted.

Discovery via feedback: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., where a joint breaks or how a body moves) to infer the hidden constraints and adapt your design.
"""
    return [
        {
            "stage_id": "Stage-1",
            "title": "Delayed Sensing",
            "mutation_description": "Sensor delay (angle and omega) increased; phase feedback is lagged.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {},
            "physics_config": {
                "sensor_delay_angle_steps": 35,
                "sensor_delay_omega_steps": 42,
            },
        },
        {
            "stage_id": "Stage-2",
            "title": "Stronger Gravity",
            "mutation_description": "Gravity magnitude increased; swing-up and balance dynamics change.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {},
            "physics_config": {
                "gravity": (0, -28),
            },
        },
        {
            "stage_id": "Stage-3",
            "title": "Long Pole and Damping",
            "mutation_description": "Pole length and angular damping increased; natural frequency and energy decay change.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {
                "pole_length": 4.5,
                "pole_mass": 2.2,
            },
            "physics_config": {
                "angular_damping": 0.75,
            },
        },
        {
            "stage_id": "Stage-4",
            "title": "Combined Perturbations",
            "mutation_description": "Gravity, sensor delay, actuator rate limit, and pole mass changed together.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {
                "pole_mass": 2.8,
            },
            "physics_config": {
                "gravity": (0, -24),
                "sensor_delay_angle_steps": 25,
                "sensor_delay_omega_steps": 30,
                "actuator_rate_limit": 25.0,
                "angular_damping": 0.65,
            },
        },
    ]
