"""
D-02: The Jumper task curriculum stages (mutations).

Mutated tasks vary invisible physical parameters: gravity, take-off ground elasticity,
linear/angular damping. The solver is NOT told exact values; it must infer from feedback.
"""

from __future__ import annotations

from typing import Any, Dict, List


def update_task_description_for_visible_changes(
    base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]
) -> str:
    """Update task description for visible changes."""
    return base_description


def update_success_criteria_for_visible_changes(
    base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]
) -> str:
    """Update success criteria for visible changes."""
    return base_success_criteria


_D02_SUFFIX = """
## Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables **MIGHT** have changed from the initial environment, **NOT ALL** of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
- **Gravity**: Variations in the gravitational field may alter the parabolic trajectory and time-of-flight of the jumper.
- **Air Resistance**: Atmospheric drag may be altered, affecting momentum over time and jump range.
- **Surface Behavior**: The elasticity or restitution of the launch surface may have changed, affecting the initial takeoff impulse.

**Discovery via feedback**: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., where a joint breaks or how a body moves) to infer the hidden constraints and adapt your design.
"""


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
            "task_description_suffix": _D02_SUFFIX,
            "terrain_config": {},
            "physics_config": {"gravity": (0, -21.0)},
        },
        {
            "stage_id": "Stage-2",
            "title": "Resistive Air",
            "mutation_description": "Linear and angular damping increased; jumper loses speed over time.",
            "task_description_suffix": _D02_SUFFIX,
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
            "task_description_suffix": _D02_SUFFIX,
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
            "task_description_suffix": _D02_SUFFIX,
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
