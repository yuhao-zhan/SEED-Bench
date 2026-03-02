"""
C-01: The Cart-Pole task curriculum stages (mutations).

Mutation dimensions: pole length/mass, gravity, sensor delay, actuator rate limit, damping.
The solver agent is NOT told the exact parameter changes; it must infer from feedback.
Stages ordered by difficulty: Stage-1 (easiest, one param) -> Stage-4 (hardest, multiple params).
"""

from __future__ import annotations

from typing import Any, Dict, List


def get_c01_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns ordered stage configs for C-01: The Cart-Pole task variants.
    Each stage dict: stage_id, title, mutation_description, task_description_suffix,
    terrain_config, physics_config.
    All mutations are invisible (no exact numeric changes in task_description_suffix).
    """
    return [
        {
            "stage_id": "Stage-1",
            "title": "Delayed Sensing",
            "mutation_description": "Sensor delay (angle and omega) increased; phase feedback is lagged.",
            "task_description_suffix": """
## Environmental Warning
Sensing may be subject to additional latency. Observed state may not reflect the current physical state.
Use feedback to infer and compensate for any lag.
""",
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
            "task_description_suffix": """
## Environmental Warning
Local gravity differs from nominal. The dynamics of the pole may feel different.
Infer from feedback and adapt your control strategy.
""",
            "terrain_config": {},
            "physics_config": {
                "gravity": (0, -28),
            },
        },
        {
            "stage_id": "Stage-3",
            "title": "Long Pole and Damping",
            "mutation_description": "Pole length and angular damping increased; natural frequency and energy decay change.",
            "task_description_suffix": """
## Environmental Warning
The system's inertia and dissipation have changed. Swing-up and balance may require different timing and gains.
Use feedback to discover and adapt.
""",
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
            "task_description_suffix": """
## Environmental Warning
Multiple environmental factors have shifted. Sensing, actuation, and dynamics may all differ from nominal.
Infer from feedback and adapt your strategy accordingly.
""",
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
