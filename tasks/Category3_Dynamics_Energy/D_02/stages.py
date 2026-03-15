"""
D-02: The Jumper task curriculum stages (mutations).

Mutated tasks vary physical parameters: gravity, wind, damping, and slot geometry.
The solver is NOT told exact values; it must infer from feedback.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

# Source (base) slot dimensions used when base_terrain_config does not override
_DEFAULT_SLOT1_FLOOR, _DEFAULT_SLOT1_CEIL = 13.2, 14.7
_DEFAULT_SLOT2_FLOOR, _DEFAULT_SLOT2_CEIL = 11.3, 13.3
_DEFAULT_SLOT3_FLOOR, _DEFAULT_SLOT3_CEIL = 12.4, 14.2


def update_task_description_for_visible_changes(
    base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]
) -> str:
    """Update task description for visible changes using format: [new_value] (originally [old_value] in the source environment)."""
    description = base_description
    target = target_terrain_config or {}
    base = base_terrain_config or {}
    t_s1_f = target.get("slot1_floor", _DEFAULT_SLOT1_FLOOR)
    t_s1_c = target.get("slot1_ceil", _DEFAULT_SLOT1_CEIL)
    t_s2_f = target.get("slot2_floor", _DEFAULT_SLOT2_FLOOR)
    t_s2_c = target.get("slot2_ceil", _DEFAULT_SLOT2_CEIL)
    t_s3_f = target.get("slot3_floor", _DEFAULT_SLOT3_FLOOR)
    t_s3_c = target.get("slot3_ceil", _DEFAULT_SLOT3_CEIL)
    b_s1_f = base.get("slot1_floor", _DEFAULT_SLOT1_FLOOR)
    b_s1_c = base.get("slot1_ceil", _DEFAULT_SLOT1_CEIL)
    b_s2_f = base.get("slot2_floor", _DEFAULT_SLOT2_FLOOR)
    b_s2_c = base.get("slot2_ceil", _DEFAULT_SLOT2_CEIL)
    b_s3_f = base.get("slot3_floor", _DEFAULT_SLOT3_FLOOR)
    b_s3_c = base.get("slot3_ceil", _DEFAULT_SLOT3_CEIL)

    # Update slot vertical gaps if any slot changed
    if (t_s1_f, t_s1_c) != (b_s1_f, b_s1_c) or (t_s2_f, t_s2_c) != (b_s2_f, b_s2_c) or (t_s3_f, t_s3_c) != (b_s3_f, b_s3_c):
        # Slot 1: **Slot 1** (x ≈ 17 m): y in [13.2, 14.7];
        slot1_pattern = r"(\*\*Slot 1\*\* \(x ≈ 17 m\): y in )\[(\d+\.?\d*), (\d+\.?\d*)\]([;.])"
        if re.search(slot1_pattern, description):
            description = re.sub(
                slot1_pattern,
                lambda m: f"{m.group(1)}[{t_s1_f:.1f}, {t_s1_c:.1f}] (originally [{b_s1_f:.1f}, {b_s1_c:.1f}] in the source environment){m.group(4)}",
                description,
            )
        slot2_pattern = r"(\*\*Slot 2\*\* \(x ≈ 21 m\): y in )\[(\d+\.?\d*), (\d+\.?\d*)\]([;.])"
        if re.search(slot2_pattern, description):
            description = re.sub(
                slot2_pattern,
                lambda m: f"{m.group(1)}[{t_s2_f:.1f}, {t_s2_c:.1f}] (originally [{b_s2_f:.1f}, {b_s2_c:.1f}] in the source environment){m.group(4)}",
                description,
            )
        slot3_pattern = r"(\*\*Slot 3\*\* \(x ≈ 19 m\): y in )\[(\d+\.?\d*), (\d+\.?\d*)\]([;.])"
        if re.search(slot3_pattern, description):
            description = re.sub(
                slot3_pattern,
                lambda m: f"{m.group(1)}[{t_s3_f:.1f}, {t_s3_c:.1f}] (originally [{b_s3_f:.1f}, {b_s3_c:.1f}] in the source environment){m.group(4)}",
                description,
            )
    return description


def update_success_criteria_for_visible_changes(
    base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]
) -> str:
    """Update success criteria for visible changes (slot dimensions are only in task_description; success_criteria has no slot numbers)."""
    return base_success_criteria


_D02_SUFFIX = """
## Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables **MIGHT** have changed from the initial environment, **NOT ALL** of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
- **Gravity**: Variations in the gravitational field may alter the parabolic trajectory and time-of-flight of the jumper.
- **Atmospheric Wind**: Strong currents may exert forces in various directions, significantly altering the flight path and momentum.
- **Air Resistance**: Atmospheric drag may be altered, affecting momentum over time and jump range.
- **Terrain Geometry**: The configuration and elevation of obstacle slots may have shifted, requiring a completely different trajectory.

**Discovery via feedback**: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., how a body moves or where the trajectory fails) to infer the hidden constraints and adapt your design.
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
