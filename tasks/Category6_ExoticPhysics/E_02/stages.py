"""
E-02: Thick Air task curriculum stages (mutations).

All mutations use invisible physical parameters (air resistance, damping, zone strengths,
overheat limit). The solver agent is NOT told the exact parameter changes; it must infer from feedback.
Stages are ordered by increasing difficulty (Stage-1 easiest, Stage-4 hardest).
"""
from __future__ import annotations

from typing import Any, Dict, List
import re


TASK_DESCRIPTION_SUFFIX = """
Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables MIGHT have changed from the initial environment, NOT ALL of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
 - Atmospheric Damping: Air resistance and motion drag.
 - Velocity Drain: Rate of kinetic energy loss in specialized zones.
 - Slip Forces: Magnitude of directional forces in slipping regions.
 - Wind Intensity: Amplitude of atmospheric disturbances.
 - Thermal Threshold: Maximum overheat limit for safe operation.

Discovery via feedback: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., where a joint breaks or how a body moves) to infer the hidden constraints and adapt your design.
"""


def update_task_description_for_visible_changes(base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update task description for visible changes."""
    return base_description


def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update success criteria for visible changes."""
    return base_success_criteria


def get_e02_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns ordered stage configs for E-02 variants (difficulty ascending).
    Each stage uses physics_config only; no visible terrain changes.
    task_description_suffix is empty so the agent is not told what changed.
    """
    return [
        {
            "stage_id": "Stage-1",
            "title": "Thicker Air (higher linear damping)",
            "mutation_description": "Linear damping (air resistance) increased; craft loses speed faster.",
            "task_description_suffix": TASK_DESCRIPTION_SUFFIX,
            "terrain_config": {},
            "physics_config": {
                "linear_damping": 9.0,  # default 4.0 → 9.0
            },
        },
        {
            "stage_id": "Stage-2",
            "title": "Stronger momentum drain",
            "mutation_description": "Momentum-drain zone reduces velocity much more per step; original thrust profile is insufficient.",
            "task_description_suffix": TASK_DESCRIPTION_SUFFIX,
            "terrain_config": {},
            "physics_config": {
                "drain_velocity_factor": 0.03,  # default 0.5 → 0.03 (extreme drain)
                "slip_backward_force": -45.0,   # default -28 → -45
                "linear_damping": 5.5,          # slightly higher air resistance so combined effect fails original
            },
        },
        {
            "stage_id": "Stage-3",
            "title": "Multiple physics shifts (damping + drain + slip)",
            "mutation_description": "Higher linear/angular damping, stronger drain, stronger slip.",
            "task_description_suffix": TASK_DESCRIPTION_SUFFIX,
            "terrain_config": {},
            "physics_config": {
                "linear_damping": 7.0,
                "angular_damping": 5.0,
                "drain_velocity_factor": 0.35,
                "slip_backward_force": -38.0,  # default -28 → -38
            },
        },
        {
            "stage_id": "Stage-4",
            "title": "Heavy environment (high drag, strong zones, tight heat budget)",
            "mutation_description": "Very high linear damping, strong drain, stronger wind, lower overheat limit.",
            "task_description_suffix": TASK_DESCRIPTION_SUFFIX,
            "terrain_config": {},
            "physics_config": {
                "linear_damping": 10.0,
                "drain_velocity_factor": 0.2,
                "wind_amplitude": 35.0,   # default 20 → 35
                "overheat_limit": 48000.0,  # default 72000 → 48000
            },
        },
    ]
