"""
C-01: The Cart-Pole task curriculum stages (mutations).

Mutation dimensions: pole length/mass, gravity, sensor delay, actuator rate limit, damping.
The solver agent is NOT told the exact numeric physics changes; it must infer from feedback.
Stages ordered by difficulty: Stage-1 (easiest, one param) -> Stage-4 (hardest, multiple params).
"""

from __future__ import annotations

from typing import Any, Dict, List
import re

def update_task_description_for_visible_changes(base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update task description for visible changes."""
    description = base_description
    
    # 1. Update Initial State (Baseline is Upright, Mutants are Hanging)
    # The presence of any config (or specifically terrain_config) triggered hanging start in environment.py
    # We explicitly state this visible change.
    description = description.replace(
        "- **Pole**: Initially upright (angle = 0° or 0rad).",
        "- **Pole**: Initially hanging downward (angle = 180° or π)."
    )
    # Update objective to mention swing-up
    description = description.replace(
        "Design a control strategy:",
        "Design a two-phase control strategy:\n1. **Swing-up**: Inject energy into the pole until it reaches the upright region."
    )
    description = description.replace(
        "1. **Balance**:",
        "2. **Balance**:"
    )
    description = description.replace(
        "2. Observe state",
        "3. Observe state"
    )

    # 2. Update Pole Length
    target_length = target_terrain_config.get("pole_length")
    if target_length is not None and target_length != 2.0:
        pattern = r"(\*\*Length\*\*: )(\d+\.?\d*)(m\.)"
        description = re.sub(pattern, f"\\g<1>{target_length:.1f}m (originally 2.0m).", description)

    # 3. Update Pole Mass
    target_mass = target_terrain_config.get("pole_mass")
    if target_mass is not None and target_mass != 1.0:
        # Since mass isn't in the base description, we append it to the pole line
        pattern = r"(- \*\*Pole\*\*: .*?m\.)"
        description = re.sub(pattern, f"\\g<1> **Mass**: {target_mass:.1f}kg (originally 1.0kg).", description)

    return description


def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update success criteria for visible changes."""
    # Mutants require swing-up
    return base_success_criteria.replace("1. **Stability**:", "1. **Swing-up & Hold**:")


def get_c01_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns ordered stage configs for C-01: The Cart-Pole task variants.
    Each stage dict: stage_id, title, mutation_description, task_description_suffix,
    terrain_config, physics_config.
    """
    task_description_suffix = """
## Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables **MIGHT** have changed from the initial environment, **NOT ALL** of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
- **Sensing latency (Orientation)**: Unexpected latency in orientation sensor readings may occur, affecting balance timing.
- **Sensing latency (Angular Velocity)**: Unexpected latency in angular velocity feedback may occur, leading to delayed control responses.
- **Gravitational acceleration**: Alterations in the gravitational field may occur, significantly affecting system weight and balance dynamics.
- **Joint resistance**: Resistance to rotational motion within the joints (damping) may be altered.
- **Actuation speed limits**: Constraints on how quickly control forces can be adjusted by the actuator may have changed.

**Discovery via feedback**: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode to infer the hidden constraints and adapt your design.
"""
    return [
        {
            "stage_id": "Stage-1",
            "title": "Delayed Sensing",
            "mutation_description": "Sensor delay (angle and omega) increased; phase feedback is lagged.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {},
            "physics_config": {
                "sensor_delay_angle_steps": 8,
                "sensor_delay_omega_steps": 12,
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
                "sensor_delay_angle_steps": 6,
                "sensor_delay_omega_steps": 10,
                "actuator_rate_limit": 25.0,
                "angular_damping": 0.65,
            },
        },
    ]
