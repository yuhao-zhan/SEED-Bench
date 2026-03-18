"""
E-03: Slippery World task curriculum stages (mutations).

All mutations change INVISIBLE physics parameters (global friction, gravity,
linear/angular damping, momentum drain, thrust-scale zone).
The solver agent is NOT told the exact parameter changes; it must infer from feedback.

Stages ordered by difficulty: Stage-1 (easiest, one param) -> Stage-4 (hardest, multiple params).
Each stage is designed so the original reference solution FAILS (environment adaptability).
"""
from __future__ import annotations

from typing import Any, Dict, List


TASK_DESCRIPTION_SUFFIX = """
## Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables **MIGHT** have changed from the initial environment, **NOT ALL** of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
- **Surface Friction**: Resistance encountered when sliding or moving across the terrain may have changed.
- **Gravity**: The magnitude and direction of the gravitational acceleration may differ from standard.
- **Momentum Drain**: The rate at which the system loses momentum over time may be altered.
- **Atmospheric Damping**: Air resistance and motion drag may vary.
- **Propulsion Efficiency**: The scaling factor affecting thrust output may be adjusted.

**Discovery via feedback**: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., how the sled loses speed, fails to reach a checkpoint, or overshoots the target) to infer the hidden constraints and adapt your design.
"""


def update_task_description_for_visible_changes(base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update task description for visible changes."""
    return base_description


def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update success criteria for visible changes."""
    return base_success_criteria


def get_e03_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns ordered stage configs for E-03 variants.
    Each stage: terrain_config, physics_config, task_description_suffix (uniform warning;
    only invisible params are mutated, so no visible prompt updates).
    Stage-1/2: one physical parameter change each (hard enough so ref fails).
    Stage-3/4: multiple parameter changes (increasing difficulty).
    """
    return [
        {
            "stage_id": "Stage-1",
            "title": "Higher global friction",
            "mutation_description": "Ground and sled friction increased (0.02 -> 0.14). Momentum is lost faster; ref's fixed gains may not overcome drain zone in time.",
            "task_description_suffix": TASK_DESCRIPTION_SUFFIX,
            "terrain_config": {
                "ground_friction": 0.14,
                "sled_friction": 0.14,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-2",
            "title": "Stronger gravity",
            "mutation_description": "Gravity increased (0, -10) -> (0, -15). Vertical control harder; ref's gravity compensation and climb to checkpoint A may be insufficient.",
            "task_description_suffix": TASK_DESCRIPTION_SUFFIX,
            "terrain_config": {},
            "physics_config": {
                "gravity": (0, -15),
            },
        },
        {
            "stage_id": "Stage-3",
            "title": "Stronger drain + damping",
            "mutation_description": "Momentum drain factor 0.85 -> 0.70; linear_damping 0.5. Velocity decays faster; ref may not reach B or final target in time.",
            "task_description_suffix": TASK_DESCRIPTION_SUFFIX,
            "terrain_config": {},
            "physics_config": {
                "momentum_drain_factor": 0.70,
                "linear_damping": 0.5,
            },
        },
        {
            "stage_id": "Stage-4",
            "title": "Multi-parameter shift",
            "mutation_description": "Gravity (0,-18), friction 0.10, linear_damping 0.6, momentum_drain 0.68, thrust_scale_factor 0.38. Ref's fixed gains and 2x thrust compensation fail.",
            "task_description_suffix": TASK_DESCRIPTION_SUFFIX,
            "terrain_config": {
                "ground_friction": 0.10,
                "sled_friction": 0.10,
            },
            "physics_config": {
                "gravity": (0, -18),
                "linear_damping": 0.6,
                "momentum_drain_factor": 0.68,
                "thrust_scale_factor": 0.38,
            },
        },
    ]
