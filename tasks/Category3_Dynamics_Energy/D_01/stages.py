"""
D-01: The Launcher task curriculum stages (mutations).

Stage-1 and Stage-2: one physical parameter change each (invisible/visible).
Stage-3 and Stage-4: multiple parameter changes. Difficulty increases Stage-1 → Stage-4.
For invisible changes (air resistance, gravity): do NOT tell the agent exact values.
For visible changes (target zone position/size): MUST update task description and success criteria.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List


def update_task_description_for_visible_changes(
    base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]
) -> str:
    """
    Update task description for visible terrain/config changes (e.g. target zone position/size).
    """
    tx_min = target_terrain_config.get("target_x_min")
    tx_max = target_terrain_config.get("target_x_max")
    ty_min = target_terrain_config.get("target_y_min")
    ty_max = target_terrain_config.get("target_y_max")
    
    base_tx_min = base_terrain_config.get("target_x_min", 40.0)
    base_tx_max = base_terrain_config.get("target_x_max", 45.0)
    base_ty_min = base_terrain_config.get("target_y_min", 2.0)
    base_ty_max = base_terrain_config.get("target_y_max", 5.0)

    out = base_description
    # Replace target zone numbers when explicitly overridden
    if tx_min is not None and tx_max is not None and (tx_min != base_tx_min or tx_max != base_tx_max):
        # We use a more robust replacement that includes the transition
        out = re.sub(r"x from 40 m to 45 m", f"x from {tx_min:.0f} m to {tx_max:.0f} m (originally x from {base_tx_min:.0f} m to {base_tx_max:.0f} m in the source environment)", out)
        out = re.sub(r"\[40, 45\]", f"[{tx_min:.0f}, {tx_max:.0f}] (originally [{base_tx_min:.0f}, {base_tx_max:.0f}] in the source environment)", out)

    if ty_min is not None and ty_max is not None and (ty_min != base_ty_min or ty_max != base_ty_max):
        out = re.sub(r"y from 2 m to 5 m", f"y from {ty_min:.0f} m to {ty_max:.0f} m (originally y from {base_ty_min:.0f} m to {base_ty_max:.0f} m in the source environment)", out)
        out = re.sub(r"\[2, 5\]", f"[{ty_min:.0f}, {ty_max:.0f}] (originally [{base_ty_min:.0f}, {base_ty_max:.0f}] in the source environment)", out)

    return out


def update_success_criteria_for_visible_changes(
    base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]
) -> str:
    """Update success criteria for visible changes (e.g. target zone bounds)."""
    tx_min = target_terrain_config.get("target_x_min")
    tx_max = target_terrain_config.get("target_x_max")
    ty_min = target_terrain_config.get("target_y_min")
    ty_max = target_terrain_config.get("target_y_max")
    
    base_tx_min = base_terrain_config.get("target_x_min", 40.0)
    base_tx_max = base_terrain_config.get("target_x_max", 45.0)
    base_ty_min = base_terrain_config.get("target_y_min", 2.0)
    base_ty_max = base_terrain_config.get("target_y_max", 5.0)

    out = base_success_criteria
    if tx_min is not None and tx_max is not None and (tx_min != base_tx_min or tx_max != base_tx_max):
        out = re.sub(r"x in \[40, 45\]", f"x in [{tx_min:.0f}, {tx_max:.0f}] (originally x in [{base_tx_min:.0f}, {base_tx_max:.0f}] in the source environment)", out)
        out = re.sub(r"\[40, 45\]", f"[{tx_min:.0f}, {tx_max:.0f}] (originally [{base_tx_min:.0f}, {base_tx_max:.0f}] in the source environment)", out)
    if ty_min is not None and ty_max is not None and (ty_min != base_ty_min or ty_max != base_ty_max):
        out = re.sub(r"y in \[2, 5\]", f"y in [{ty_min:.0f}, {ty_max:.0f}] (originally y in [{base_ty_min:.0f}, {base_ty_max:.0f}] in the source environment)", out)
        out = re.sub(r"\[2, 5\]", f"[{ty_min:.0f}, {ty_max:.0f}] (originally [{base_ty_min:.0f}, {base_ty_max:.0f}] in the source environment)", out)
    return out


_D01_SUFFIX = """
## Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables **MIGHT** have changed from the initial environment, **NOT ALL** of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
- **Air Resistance**: Atmospheric drag may be altered, causing projectiles to lose energy and velocity differently during flight.
- **Target Zone Position**: The coordinates of the destination region may have been shifted, requiring adjustments to the required launch force or angle.
- **Gravity**: Variations in the gravitational field may alter the parabolic trajectory and time-of-flight of any launched object.

**Discovery via feedback**: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., where a joint breaks or how a body moves) to infer the hidden constraints and adapt your design.
"""


def get_d01_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Return ordered stage configs for D-01 mutated tasks.
    Order: Stage-1 (one param) → Stage-2 (one param) → Stage-3 (multi) → Stage-4 (multi).
    Difficulty increases so that the reference solution fails in each mutated environment.
    """
    return [
        {
            "stage_id": "Stage-1",
            "title": "The Dense Atmosphere",
            "mutation_description": "Air resistance (linear/angular damping) increased. Projectile loses energy in flight.",
            "task_description_suffix": _D01_SUFFIX,
            "terrain_config": {},
            "physics_config": {
                "linear_damping": 2.5,
                "angular_damping": 2.5,
            },
        },
        {
            "stage_id": "Stage-2",
            "title": "The Distant Target",
            "mutation_description": "Target zone moved further: x=[50, 55] m (visible change).",
            "task_description_suffix": _D01_SUFFIX,
            "terrain_config": {
                "target_x_min": 50.0,
                "target_x_max": 55.0,
                "target_y_min": 2.0,
                "target_y_max": 5.0,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-3",
            "title": "Heavy World and Drag",
            "mutation_description": "Gravity increased to -15 m/s² and air resistance (damping) added. Dual invisible params.",
            "task_description_suffix": _D01_SUFFIX,
            "terrain_config": {},
            "physics_config": {
                "gravity": (0, -15.0),
                "linear_damping": 1.5,
                "angular_damping": 1.5,
            },
        },
        {
            "stage_id": "Stage-4",
            "title": "Extreme Range and Conditions",
            "mutation_description": "Target at [52, 57] m (visible) + gravity -18 m/s² + linear/angular damping 1.2.",
            "task_description_suffix": _D01_SUFFIX,
            "terrain_config": {
                "target_x_min": 52.0,
                "target_x_max": 57.0,
                "target_y_min": 2.0,
                "target_y_max": 5.0,
            },
            "physics_config": {
                "gravity": (0, -18.0),
                "linear_damping": 1.2,
                "angular_damping": 1.2,
            },
        },
    ]
