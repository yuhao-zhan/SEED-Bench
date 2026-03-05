"""
F-05: The Boat task curriculum stages (mutations).

Mutated tasks vary physical parameters: wave amplitude, cargo friction (fixation difficulty),
current, restoring torque, lateral impulses, rogue waves, gravity, etc.
Invisible changes: solver is NOT told exact values; it must infer from feedback.
Stage-1/2: single parameter change. Stage-3/4: multiple parameter changes.
Ordered by difficulty (ascending).
"""
from __future__ import annotations

from typing import Any, Dict, List
import re


def update_task_description_for_visible_changes(
    base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]
) -> str:
    """Update task description if any visible terrain/config change."""
    return base_description


def update_success_criteria_for_visible_changes(
    base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]
) -> str:
    """Update success criteria for visible changes."""
    return base_success_criteria


def get_f05_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns ordered stage configs for F-05: The Boat (difficulty ascending).
    Each stage: stage_id, title, mutation_description, task_description_suffix,
    terrain_config, physics_config. All changes are invisible (waves, cargo friction,
    current, lateral impulses, etc.); prompt only gets generic environmental warning.
    """
    task_description_suffix = """
## Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables **MIGHT** have changed from the initial environment, **NOT ALL** of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
- **Wave Dynamics**: The amplitude and frequency of primary and secondary wave patterns may be altered, affecting vessel roll and heave.
- **Fluid Current**: The strength of the water's flow may vary, impacting the vessel's drift and required station-keeping.
- **Stability Coefficients**: The restoring torque and angular stiffness of the vessel may have changed, determining its ability to self-right after tilting.
- **Lateral Disturbances**: The magnitude and timing of impulsive side-forces or wind gusts acting on the structure may be adjusted.
- **Rogue Activity**: The presence and intensity of unpredictable, high-amplitude wave events may have changed.
- **Cargo Traction**: The surface friction of the transported objects may differ from standard, affecting how easily they slide across the deck.
- **Gravity**: The acceleration due to the local gravitational field may be altered, influencing displacement, weight distribution, and stability.

**Discovery via feedback**: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., where a joint breaks or how a body moves) to infer the hidden constraints and adapt your design.
"""
    return [
        {
            "stage_id": "Stage-1",
            "title": "Stronger waves",
            "mutation_description": "Primary wave amplitude, current, and lateral impulses increased; restoring torque reduced.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {
                "wave_amplitude": 60.0,
                "current_strength": 3.0,
                "restoring_coeff": 1200.0,
                "lateral_impulse_amplitude": 120.0,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-2",
            "title": "Slipperier cargo",
            "mutation_description": "Cargo friction reduced; cargo fixation harder, more likely to slide off.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {
                "cargo": {"friction": 0.12, "count": 10, "radius": 0.15, "density": 260.0, "seed": 42},
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-3",
            "title": "Stronger current and weaker restoring",
            "mutation_description": "Water current increased, restoring torque reduced; boat drifts and rolls more.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {
                "current_strength": 0.58,
                "restoring_coeff": 1150.0,
                "wave_amplitude": 13.0,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-4",
            "title": "Extreme sea and cargo",
            "mutation_description": "Larger waves, slipperier cargo, stronger/faster lateral gusts, stronger rogue, higher gravity.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {
                "wave_amplitude": 18.0,
                "wave2_amplitude": 9.0,
                "cargo": {"friction": 0.10, "count": 10, "radius": 0.15, "density": 260.0, "seed": 42},
                "lateral_impulse_amplitude": 105.0,
                "lateral_impulse_interval_steps": 140,
                "restoring_coeff": 1100.0,
                "rogue_amplitude": 20.0,
                "current_strength": 0.52,
            },
            "physics_config": {
                "gravity": (0, -13.0),
            },
        },
    ]
