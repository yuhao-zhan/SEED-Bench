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
    base_description: str, terrain_config: Dict[str, Any]
) -> str:
    """
    Update task description for visible terrain/config changes (e.g. target zone position/size).
    Invisible physical parameters (gravity, damping, friction) are NOT reflected here.
    """
    tx_min = terrain_config.get("target_x_min")
    tx_max = terrain_config.get("target_x_max")
    ty_min = terrain_config.get("target_y_min")
    ty_max = terrain_config.get("target_y_max")
    if tx_min is None and tx_max is None and ty_min is None and ty_max is None:
        return base_description

    out = base_description
    # Replace target zone numbers when explicitly overridden
    if tx_min is not None and tx_max is not None:
        out = re.sub(r"x from 40 m to 45 m", f"x from {tx_min:.0f} m to {tx_max:.0f} m", out)
        out = re.sub(r"\[40, 45\]", f"[{tx_min:.0f}, {tx_max:.0f}]", out)
        out = re.sub(r"40 m to 45 m", f"{tx_min:.0f} m to {tx_max:.0f} m", out)
        out = re.sub(r"x in \[40, 45\]", f"x in [{tx_min:.0f}, {tx_max:.0f}]", out)
    if ty_min is not None and ty_max is not None:
        out = re.sub(r"y from \*\*2 m to 5 m\*\*", f"y from **{ty_min:.0f} m to {ty_max:.0f} m**", out)
        out = re.sub(r"\[2, 5\]", f"[{ty_min:.0f}, {ty_max:.0f}]", out)
        out = re.sub(r"y from 2 m to 5 m", f"y from {ty_min:.0f} m to {ty_max:.0f} m", out)
        out = re.sub(r"y ∈ \[2, 5\]", f"y ∈ [{ty_min:.0f}, {ty_max:.0f}]", out)
        out = re.sub(r"y in \[2, 5\]", f"y in [{ty_min:.0f}, {ty_max:.0f}]", out)
        out = re.sub(r"y ∈ \[2, 5\] m", f"y ∈ [{ty_min:.0f}, {ty_max:.0f}] m", out)
        out = re.sub(r"y &lt; 2 m", f"y &lt; {ty_min:.0f} m", out)
    return out


def update_success_criteria_for_visible_changes(
    base_success_criteria: str, terrain_config: Dict[str, Any]
) -> str:
    """Update success criteria for visible changes (e.g. target zone bounds)."""
    tx_min = terrain_config.get("target_x_min")
    tx_max = terrain_config.get("target_x_max")
    ty_min = terrain_config.get("target_y_min")
    ty_max = terrain_config.get("target_y_max")
    if tx_min is None and tx_max is None and ty_min is None and ty_max is None:
        return base_success_criteria

    out = base_success_criteria
    if tx_min is not None and tx_max is not None:
        out = re.sub(r"x in \[40, 45\]", f"x in [{tx_min:.0f}, {tx_max:.0f}]", out)
        out = re.sub(r"\[40, 45\]", f"[{tx_min:.0f}, {tx_max:.0f}]", out)
    if ty_min is not None and ty_max is not None:
        out = re.sub(r"y in \*\*\[2, 5\]\*\*", f"y in **[{ty_min:.0f}, {ty_max:.0f}]**", out)
        out = re.sub(r"y &lt; 2 m", f"y &lt; {ty_min:.0f} m", out)
        out = re.sub(r"\[2, 5\]", f"[{ty_min:.0f}, {ty_max:.0f}]", out)
        out = re.sub(r"y ∈ \[2, 5\]", f"y ∈ [{ty_min:.0f}, {ty_max:.0f}]", out)
        out = re.sub(r"y ∈ \[2, 5\] m", f"y ∈ [{ty_min:.0f}, {ty_max:.0f}] m", out)
    return out


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
            "task_description_suffix": """
## Environmental Warning
Atmospheric conditions have changed. Air resistance is higher than in standard conditions.
Projectiles may lose energy more quickly in flight. Your launcher must compensate to reach the target.
""",
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
            "task_description_suffix": """
## Environmental Warning
The target zone has been relocated to a greater distance. The success criteria reflect the new zone position.
""",
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
            "task_description_suffix": """
## Environmental Warning
Gravity and atmospheric conditions in this region have changed. Projectiles follow different trajectories than in standard conditions.
Your launcher must adapt to reach the target zone.
""",
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
            "task_description_suffix": """
## Environmental Warning
The target zone is at greater distance and both gravity and atmospheric conditions have changed.
This is an extreme challenge; your launcher must be tuned for range and trajectory under these conditions.
""",
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
