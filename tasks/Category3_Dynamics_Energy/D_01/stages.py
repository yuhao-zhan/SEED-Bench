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
    Update task description for visible terrain/config changes.
    """
    out = base_description

    # Target Zone
    tx_min = target_terrain_config.get("target_x_min", base_terrain_config.get("target_x_min", 40.0))
    tx_max = target_terrain_config.get("target_x_max", base_terrain_config.get("target_x_max", 45.0))
    base_tx_min = base_terrain_config.get("target_x_min", 40.0)
    base_tx_max = base_terrain_config.get("target_x_max", 45.0)

    if tx_min != base_tx_min or tx_max != base_tx_max:
        pattern = r"(x from 40 m to 45 m)"
        if re.search(pattern, out):
            out = re.sub(pattern, f"x from {tx_min:.1f} m to {tx_max:.1f} m (originally 40 m to 45 m in the source environment)", out)
    
    ty_min = target_terrain_config.get("target_y_min", base_terrain_config.get("target_y_min", 2.0))
    ty_max = target_terrain_config.get("target_y_max", base_terrain_config.get("target_y_max", 5.0))
    base_ty_min = base_terrain_config.get("target_y_min", 2.0)
    base_ty_max = base_terrain_config.get("target_y_max", 5.0)

    if ty_min != base_ty_min or ty_max != base_ty_max:
        pattern = r"(y from 2 m to 5 m)"
        if re.search(pattern, out):
            out = re.sub(pattern, f"y from {ty_min:.1f} m to {ty_max:.1f} m (originally 2 m to 5 m in the source environment)", out)

    # Build Zone
    bx_min = target_terrain_config.get("build_zone_x_min", base_terrain_config.get("build_zone_x_min", 5.0))
    bx_max = target_terrain_config.get("build_zone_x_max", base_terrain_config.get("build_zone_x_max", 15.0))
    base_bx_min = base_terrain_config.get("build_zone_x_min", 5.0)
    base_bx_max = base_terrain_config.get("build_zone_x_max", 15.0)

    if bx_min != base_bx_min or bx_max != base_bx_max:
        pattern = r"(x=\[5, 15\] m)"
        if re.search(pattern, out):
            out = re.sub(pattern, f"x=[{bx_min:.1f}, {bx_max:.1f}] m (originally [5, 15] m in the source environment)", out)
            
    by_min = target_terrain_config.get("build_zone_y_min", base_terrain_config.get("build_zone_y_min", 1.5))
    by_max = target_terrain_config.get("build_zone_y_max", base_terrain_config.get("build_zone_y_max", 8.0))
    base_by_min = base_terrain_config.get("build_zone_y_min", 1.5)
    base_by_max = base_terrain_config.get("build_zone_y_max", 8.0)
    
    if by_min != base_by_min or by_max != base_by_max:
        pattern = r"(y=\[1.5, 8\] m)"
        if re.search(pattern, out):
            out = re.sub(pattern, f"y=[{by_min:.1f}, {by_max:.1f}] m (originally [1.5, 8] m in the source environment)", out)

    # Projectile Spawn
    ps_x = target_terrain_config.get("projectile_spawn_x", base_terrain_config.get("projectile_spawn_x", 10.0))
    ps_y = target_terrain_config.get("projectile_spawn_y", base_terrain_config.get("projectile_spawn_y", 3.0))
    base_ps_x = base_terrain_config.get("projectile_spawn_x", 10.0)
    base_ps_y = base_terrain_config.get("projectile_spawn_y", 3.0)
    
    if ps_x != base_ps_x or ps_y != base_ps_y:
        pattern = r"(position \(10, 3\) m)"
        if re.search(pattern, out):
            out = re.sub(pattern, f"position ({ps_x:.1f}, {ps_y:.1f}) m (originally (10, 3) m in the source environment)", out)

    return out


def update_success_criteria_for_visible_changes(
    base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]
) -> str:
    """Update success criteria for visible changes (e.g. target zone bounds)."""
    out = base_success_criteria

    # Target Zone
    tx_min = target_terrain_config.get("target_x_min", base_terrain_config.get("target_x_min", 40.0))
    tx_max = target_terrain_config.get("target_x_max", base_terrain_config.get("target_x_max", 45.0))
    base_tx_min = base_terrain_config.get("target_x_min", 40.0)
    base_tx_max = base_terrain_config.get("target_x_max", 45.0)

    if tx_min != base_tx_min or tx_max != base_tx_max:
        pattern = r"(x in \[40, 45\] m)"
        if re.search(pattern, out):
            out = re.sub(
                pattern,
                f"x in [{tx_min:.1f}, {tx_max:.1f}] m (originally [40, 45] m in the source environment)",
                out,
            )
            
    ty_min = target_terrain_config.get("target_y_min", base_terrain_config.get("target_y_min", 2.0))
    ty_max = target_terrain_config.get("target_y_max", base_terrain_config.get("target_y_max", 5.0))
    base_ty_min = base_terrain_config.get("target_y_min", 2.0)
    base_ty_max = base_terrain_config.get("target_y_max", 5.0)
    
    if ty_min != base_ty_min or ty_max != base_ty_max:
        pattern = r"(y in \[2, 5\] m)"
        if re.search(pattern, out):
            out = re.sub(
                pattern,
                f"y in [{ty_min:.1f}, {ty_max:.1f}] m (originally [2, 5] m in the source environment)",
                out,
            )

    # Mass Budget
    max_mass = target_terrain_config.get("max_structure_mass", base_terrain_config.get("max_structure_mass", 500.0))
    base_max_mass = base_terrain_config.get("max_structure_mass", 500.0)
    if max_mass != base_max_mass:
        pattern = r"(- \*\*Mass Budget\*\*: Total structure mass must not exceed )(\d+)( kg)"
        if re.search(pattern, out):
            out = re.sub(
                pattern,
                rf"\g<1>{max_mass:.0f} kg (originally 500 kg in the source environment)",
                out,
            )

    return out


def get_mutated_prompt(base_prompt: Dict[str, Any], stage_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a mutated prompt based on the curriculum stage configuration.
    """
    new_prompt = base_prompt.copy()
    terrain_config = stage_config.get("terrain_config", {})
    
    # Use baseline values for comparison
    base_terrain_config = {
        "target_x_min": 40.0,
        "target_x_max": 45.0,
        "target_y_min": 2.0,
        "target_y_max": 5.0,
        "build_zone_x_min": 5.0,
        "build_zone_x_max": 15.0,
        "build_zone_y_min": 1.5,
        "build_zone_y_max": 8.0,
        "projectile_spawn_x": 10.0,
        "projectile_spawn_y": 3.0,
        "max_structure_mass": 500.0,
    }

    new_prompt["task_description"] = update_task_description_for_visible_changes(
        base_prompt["task_description"], terrain_config, base_terrain_config
    )
    new_prompt["success_criteria"] = update_success_criteria_for_visible_changes(
        base_prompt["success_criteria"], terrain_config, base_terrain_config
    )

    if "task_description_suffix" in stage_config:
        new_prompt["task_description"] += stage_config["task_description_suffix"]

    return new_prompt



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
