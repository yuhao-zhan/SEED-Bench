"""
D-02: The Jumper task curriculum stages (mutations).

Mutated tasks vary invisible physical parameters: gravity, take-off ground elasticity,
linear/angular damping. The solver is NOT told exact values; it must infer from feedback.
"""

from __future__ import annotations

from typing import Any, Dict, List


def update_task_description_for_visible_changes(
    base_description: str, terrain_config: Dict[str, Any]
) -> str:
    """Update task description for visible changes. No visible terrain changes in current mutations."""
    return base_description


def update_success_criteria_for_visible_changes(
    base_success_criteria: str, terrain_config: Dict[str, Any]
) -> str:
    """Update success criteria for visible changes. No visible terrain changes in current mutations."""
    return base_success_criteria


def get_d02_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Return ordered stage configs for D-02 mutated tasks (difficulty ascending).
    Stage-1/2: single physical parameter change.
    Stage-3/4: multiple parameter changes.
    All changes are invisible (gravity, damping, restitution); prompt only gets generic warning.
    """
    return [
        {
            "stage_id": "Stage-1",
            "title": "Heavier World",
            "mutation_description": "Gravity increased; trajectory drops faster, same impulse may hit bars or fall short.",
            "task_description_suffix": """
## Environmental Warning
Local gravity has changed. Trajectories will differ from nominal conditions.
You must find a launch that still passes through all three gaps and lands on the right platform.
""",
            "terrain_config": {},
            "physics_config": {"gravity": (0, -21.0)},
        },
        {
            "stage_id": "Stage-2",
            "title": "Resistive Air",
            "mutation_description": "Linear and angular damping increased; jumper loses speed over time.",
            "task_description_suffix": """
## Environmental Warning
The atmosphere is more resistive. Momentum is reduced over time.
A launch that would otherwise reach the platform may fall short; adjust accordingly.
""",
            "terrain_config": {},
            "physics_config": {
                "linear_damping": 1.8,
                "angular_damping": 1.8,
            },
        },
        {
            "stage_id": "Stage-3",
            "title": "Heavy and Resistive",
            "mutation_description": "Stronger gravity and moderate damping; trajectory and range both affected.",
            "task_description_suffix": """
## Environmental Warning
Both gravity and atmospheric resistance have changed. Trajectories and range will differ from nominal.
Find a launch that passes through all three gaps and lands on the right platform.
""",
            "terrain_config": {},
            "physics_config": {
                "gravity": (0, -20.0),
                "linear_damping": 1.2,
                "angular_damping": 1.2,
            },
        },
        {
            "stage_id": "Stage-4",
            "title": "Extreme Environment",
            "mutation_description": "High gravity, high damping, and bouncy take-off surface; full re-tuning required.",
            "task_description_suffix": """
## Environmental Warning
Multiple physical conditions have changed: gravity, atmospheric resistance, and take-off surface behavior.
You must infer the new dynamics from simulation feedback and adapt your launch to pass all three gaps and land on the right platform.
""",
            "terrain_config": {
                "left_platform_restitution": 0.5,
            },
            "physics_config": {
                "gravity": (0, -23.0),
                "linear_damping": 2.0,
                "angular_damping": 2.0,
            },
        },
    ]
