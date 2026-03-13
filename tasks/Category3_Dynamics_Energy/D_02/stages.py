"""
D-02: The Jumper task curriculum stages (mutations).

Mutated tasks vary physical parameters: gravity, wind, damping, and slot geometry.
The solver is NOT told exact values; it must infer from feedback.
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
- **Atmospheric Wind**: Strong currents may exert forces in various directions, significantly altering the flight path and momentum.
- **Air Resistance**: Atmospheric drag may be altered, affecting momentum over time and jump range.
- **Terrain Geometry**: The configuration and elevation of obstacle slots may have shifted, requiring a completely different trajectory.

**Discovery via feedback**: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., where a joint breaks or how a body moves) to infer the hidden constraints and adapt your design.
"""


def get_d02_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Return ordered stage configs for D-02 mutated tasks (difficulty ascending).
    Stage-1/2: single physical parameter change (innovation).
    Stage-3/4: multiple parameter changes with conflicting constraints.
    """
    return [
        {
            "stage_id": "Stage-1",
            "title": "Extreme Updraft",
            "mutation_description": "A powerful upward wind force has been detected; the jumper will fly much higher than usual.",
            "task_description_suffix": _D02_SUFFIX,
            "terrain_config": {},
            "physics_config": {
                "wind": (0.0, 35.0),
            },
        },
        {
            "stage_id": "Stage-2",
            "title": "Deep Shift",
            "mutation_description": "Seismic activity has lowered the elevation of all barrier slots; a much lower trajectory is required.",
            "task_description_suffix": _D02_SUFFIX,
            "terrain_config": {
                "slot1_floor": 9.7,
                "slot1_ceil": 11.2,
                "slot3_floor": 8.9,
                "slot3_ceil": 10.7,
                "slot2_floor": 7.8,
                "slot2_ceil": 9.8,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-3",
            "title": "Gale and Gravity",
            "mutation_description": "Combination of high gravity and a strong headwind; momentum will be lost rapidly.",
            "task_description_suffix": _D02_SUFFIX,
            "terrain_config": {},
            "physics_config": {
                "gravity": (0, -35.0),
                "wind": (-20.0, 0),
            },
        },
        {
            "stage_id": "Stage-4",
            "title": "Hurricane Tunnel",
            "mutation_description": "Extreme environment with high gravity, headwind, and air resistance.",
            "task_description_suffix": _D02_SUFFIX,
            "terrain_config": {},
            "physics_config": {
                "gravity": (0, -30.0),
                "wind": (-15.0, 0),
                "linear_damping": 1.0,
            },
        },
    ]
