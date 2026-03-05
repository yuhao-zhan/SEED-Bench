"""
S-02: The Skyscraper task curriculum stages (mutations).
"""

from __future__ import annotations

from typing import Any, Dict, List
import re

def update_task_description_for_visible_changes(base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Updates the task description for VISIBLE changes (none currently for S-02)."""
    return base_description

def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Updates the success criteria for VISIBLE changes (none currently for S-02)."""
    return base_success_criteria

def get_s02_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns ordered stage configs for S-02: The Skyscraper task variants.
    Difficulty is escalated through fundamental structural challenges and non-linear physical interactions.
    """

    UNIFORM_SUFFIX = """
## Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables **MIGHT** have changed from the initial environment, **NOT ALL** of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
 - **Structural Integrity Thresholds**: Joints between beams may now have finite breaking limits for both force and torque.
 - **Seismic Dynamics**: The foundation's oscillation may exhibit varying amplitudes, frequencies, or even evolve in intensity over time.
 - **Atmospheric Loading**: Lateral wind forces may change in magnitude, height-dependent shear, or periodic pulsation (oscillation).
 - **Gravitational Constant**: The local vertical acceleration may be significantly higher than standard earth gravity.

**Discovery via feedback**: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., where a joint breaks or how the tower sways) to infer the hidden constraints and adapt your design.
"""

    return [
        {
            "stage_id": "Stage-1",
            "title": "The Brittle Foundation",
            "mutation_description": "Extreme structural torque limit at the base. Standard heavy towers will snap their foundation joints immediately upon oscillation.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "earthquake_amplitude": 0.4,
            },
            "physics_config": {
                "max_joint_torque": 1200.0,  # Critical bottleneck: force agent to build light/balanced
                "max_joint_force": 50000.0,
            },
        },
        {
            "stage_id": "Stage-2",
            "title": "Atmospheric Resonance",
            "mutation_description": "Wind pulsates at a frequency that induces structural resonance. Without active damping (TMD), the tower will oscillate to destruction.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "wind_force": 2500.0,
                "wind_oscillation_frequency": 5.0,  # High-frequency wind gusts
                "wind_height_threshold": 5.0,     # Wind starts much lower
            },
            "physics_config": {
                "max_joint_force": 50000.0,
                "max_joint_torque": 100000.0,
            },
        },
        {
            "stage_id": "Stage-3",
            "title": "Seismic Amplification",
            "mutation_description": "The earthquake intensity evolves non-linearly over time. A tower that survives the start will collapse as the energy builds.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "earthquake_amplitude": 0.4,
                "earthquake_frequency": 5.0,
                "earthquake_amplitude_evolution": 0.1, 
            },
            "physics_config": {
                "max_joint_force": 500000.0,
                "max_joint_torque": 1000000.0,
            },
        },
        {
            "stage_id": "Stage-4",
            "title": "The Gravity Well Collapse",
            "mutation_description": "Extreme gravity combined with high-intensity chaotic seismic and wind loads. Structural weight becomes the enemy.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "earthquake_amplitude": 1.5,
                "earthquake_frequency": 8.0,
                "wind_force": 500.0,
                "wind_shear_factor": 2.0,
            },
            "physics_config": {
                "gravity": (0, -25.0), # Extreme gravity
                "max_joint_force": 250000.0,
                "max_joint_torque": 500000.0,
            },
        },
    ]
