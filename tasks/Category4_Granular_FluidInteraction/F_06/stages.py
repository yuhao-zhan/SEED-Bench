"""
F-06: The Pipeline task curriculum stages (mutations).
"""
from __future__ import annotations

from typing import Any, Dict, List
import re


def update_task_description_for_visible_changes(
    base_description: str,
    target_terrain_config: Dict[str, Any],
    base_terrain_config: Dict[str, Any],
    target_physics_config: Dict[str, Any] = None,
    base_physics_config: Dict[str, Any] = None,
) -> str:
    """Update task description for visible changes using format: [new_value] (originally [old_value] in the source environment)."""
    description = base_description
    target_physics_config = target_physics_config or {}
    base_physics_config = base_physics_config or {}

    # Target zone height
    target_y_min = target_terrain_config.get("target_y_min", 0.0)
    target_y_max = target_terrain_config.get("target_y_max", 1.5)
    base_y_min = base_terrain_config.get("target_y_min", 0.0)
    base_y_max = base_terrain_config.get("target_y_max", 1.5)

    if target_y_min != base_y_min or target_y_max != base_y_max:
        pattern = r"(y in \[)(\d+\.?\d*)(, )(\d+\.?\d*)(\] m)"
        description = re.sub(
            pattern,
            f"\\g<1>{target_y_min:.1f}, {target_y_max:.1f}\\g<5> (originally y in [{base_y_min:.1f}, {base_y_max:.1f}] m in the source environment)",
            description,
        )

    target_delivery = target_terrain_config.get("min_delivery_ratio", 0.90)
    base_delivery = base_terrain_config.get("min_delivery_ratio", 0.90)
    if target_delivery != base_delivery:
        pattern = r"(at least )(\d+)(% of released fluid particles)"
        description = re.sub(
            pattern,
            f"\\g<1>{int(target_delivery*100)}\\g<3> (originally {int(base_delivery*100)}% in the source environment)",
            description,
        )

    # Fluid particle count (visible in "A batch of 60 small fluid particles")
    target_fluid = target_terrain_config.get("fluid", {})
    base_fluid = base_terrain_config.get("fluid", {})
    target_count = int(target_fluid.get("count", 60))
    base_count = int(base_fluid.get("count", 60))
    if target_count != base_count:
        pattern = r"(A batch of )(\d+)( small fluid particles)"
        if re.search(pattern, description):
            description = re.sub(
                pattern,
                f"\\g<1>{target_count}\\g<3> (originally {base_count} in the source environment)",
                description,
            )

    # Force budget is stated in success_criteria only; synced in update_success_criteria_for_visible_changes

    return description


def update_success_criteria_for_visible_changes(
    base_success_criteria: str,
    target_terrain_config: Dict[str, Any],
    base_terrain_config: Dict[str, Any],
    target_physics_config: Dict[str, Any] = None,
    base_physics_config: Dict[str, Any] = None,
) -> str:
    """Update success criteria for visible changes."""
    criteria = base_success_criteria
    target_physics_config = target_physics_config or {}
    base_physics_config = base_physics_config or {}

    target_delivery = target_terrain_config.get("min_delivery_ratio", 0.90)
    base_delivery = base_terrain_config.get("min_delivery_ratio", 0.90)
    if target_delivery != base_delivery:
        pattern = r"(At least )(\d+)(% of released particles)"
        criteria = re.sub(
            pattern,
            f"\\g<1>{int(target_delivery*100)}\\g<3> (originally {int(base_delivery*100)}% in the source environment)",
            criteria,
        )

    # Force budget in success criteria ("must not exceed 12000 N per step")
    default_force_budget = 12000.0
    target_force = float(target_physics_config.get("force_budget", default_force_budget))
    base_force = float(base_physics_config.get("force_budget", default_force_budget))
    if target_force != base_force:
        pattern = r"(must not exceed )(\d+)( N per step\.)"
        if re.search(pattern, criteria):
            criteria = re.sub(
                pattern,
                f"\\g<1>{int(target_force)} N per step (originally {int(base_force)} N per step in the source environment).",
                criteria,
            )

    return criteria


def get_f06_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns ordered stage configs for F-06 mutated tasks.
    """
    UNIFORM_SUFFIX = """
## Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables **MIGHT** have changed from the initial environment, **NOT ALL** of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
- **Fluid Viscosity**: The resistance of the medium may be altered.
- **Gravity**: The acceleration due to the local gravitational field may vary.
- **Atmospheric Resistance**: Headwinds acting against the flow may be present.
- **Operational Resource Limit**: The per-step force budget available for particle manipulation may be adjusted.
- **Target zone (vertical extent)**: The vertical range (y) of the target zone may differ.
- **Delivery ratio threshold**: The required fraction of particles that must reach the target may differ.
- **Fluid particle count**: The number of fluid particles released from the source may differ.

**Discovery via feedback**: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode to infer the hidden constraints and adapt your design.
"""
    return [
        {
            "stage_id": "Stage-1",
            "title": "High-Viscosity Fluid",
            "mutation_description": "Fluid viscosity increased significantly.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "fluid": {"viscosity": 20.0, "count": 20},
                "min_delivery_ratio": 0.45,
            },
            "physics_config": {
                "max_steps": 2400,
                "max_time_seconds": 40.0,
                "force_budget": 5000.0,
            },
        },
        {
            "stage_id": "Stage-2",
            "title": "Raised Delivery Target",
            "mutation_description": "Target zone moved to higher elevation.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "target_y_min": 2.5,
                "target_y_max": 4.0,
                "fluid": {"count": 20},
                "min_delivery_ratio": 0.45,
            },
            "physics_config": {
                "max_steps": 2400,
                "max_time_seconds": 40.0,
                "force_budget": 12000.0,
            },
        },
        {
            "stage_id": "Stage-3",
            "title": "Extreme Viscosity",
            "mutation_description": "Extremely high fluid viscosity.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "fluid": {"viscosity": 30.0, "count": 20},
                "min_delivery_ratio": 0.45,
            },
            "physics_config": {
                "max_steps": 2400,
                "max_time_seconds": 40.0,
                "force_budget": 12000.0,
            },
        },
        {
            "stage_id": "Stage-4",
            "title": "Hostile Pipeline",
            "mutation_description": "Raised target + viscosity + gravity.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "target_y_min": 2.5,
                "target_y_max": 4.0,
                "fluid": {"viscosity": 2.0, "count": 20},
                "min_delivery_ratio": 0.45,
            },
            "physics_config": {
                "gravity": (0, -15.0),
                "max_steps": 2400,
                "max_time_seconds": 40.0,
                "force_budget": 12000.0,
            },
        },
    ]
