"""
E-04: Variable Mass task curriculum stages (mutations).

Mutated tasks vary invisible physical parameters (mass variation frequency/amplitude,
base excitation, joint limits, fatigue, damping). The solver agent is NOT told the exact
parameter changes; it must infer from feedback.
"""
from __future__ import annotations

from typing import Any, Dict, List


TASK_DESCRIPTION_SUFFIX = """
Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables MIGHT have changed from the initial environment, NOT ALL of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
 - Joint Strength: The force and torque limits before mechanical failure.
 - Structural Fatigue: The rate at which joints weaken over time.
 - Base Vibration: The frequency and amplitude of external oscillations.
 - Mass Dynamics: The frequency and amplitude of periodic mass fluctuations.
 - Gravity: The magnitude and direction of the gravitational field.

Discovery via feedback: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., where a joint breaks or how a body moves) to infer the hidden constraints and adapt your design.
"""


def update_task_description_for_visible_changes(base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update task description for visible changes."""
    return base_description


def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update success criteria for visible changes."""
    return base_success_criteria


def get_e04_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns ordered stage configs for E-04 variants (difficulty: Stage-1 < Stage-2 < Stage-3 < Stage-4).
    Each stage overrides physics via physics_config; prompt does NOT reveal exact parameter changes.
    """
    return [
        # Stage-1: Stricter joint limits (one param) — nominal limits lowered so reference exceeds them
        {
            "stage_id": "Stage-1",
            "title": "Weak joints",
            "mutation_description": "Joint break force/torque limits reduced; same reaction forces can break joints.",
            "task_description_suffix": TASK_DESCRIPTION_SUFFIX,
            "terrain_config": {},
            "physics_config": {
                "joint_break_force": 0.0004,
                "joint_break_torque": 0.0002,
            },
        },
        # Stage-2: Very fast joint fatigue (one param) — effective limits decay to near zero quickly
        {
            "stage_id": "Stage-2",
            "title": "Rapid joint fatigue",
            "mutation_description": "Joint fatigue time constant very small; effective limits drop to near zero within seconds.",
            "task_description_suffix": TASK_DESCRIPTION_SUFFIX,
            "terrain_config": {},
            "physics_config": {
                "fatigue_tau_seconds": 2.0,
            },
        },
        # Stage-3: Multiple — low joint limits + stronger base excitation + higher mass amplitude
        {
            "stage_id": "Stage-3",
            "title": "Harsh vibration and weak joints",
            "mutation_description": "Lower joint limits, stronger base excitation, higher mass variation amplitude.",
            "task_description_suffix": TASK_DESCRIPTION_SUFFIX,
            "terrain_config": {},
            "physics_config": {
                "joint_break_force": 0.0005,
                "joint_break_torque": 0.00025,
                "base_excitation_vertical_amplitude": 0.25,
                "base_excitation_horizontal_amplitude": 0.18,
                "base_excitation_frequency": 0.5,
                "mass_amp_1": 0.5,
                "mass_amp_2": 0.42,
            },
        },
        # Stage-4: Multiple — mass freq + amp + base + fast fatigue + gravity (hardest)
        {
            "stage_id": "Stage-4",
            "title": "Altered dynamics and fatigue",
            "mutation_description": "Mass freq/amp changed; stronger base excitation; fast fatigue; increased gravity.",
            "task_description_suffix": TASK_DESCRIPTION_SUFFIX,
            "terrain_config": {},
            "physics_config": {
                "mass_freq_1": 1.0,
                "mass_freq_2": 1.8,
                "mass_amp_1": 0.45,  # Adjusted from 0.55 to avoid amp sum > 1.0 (negative density crash)
                "mass_amp_2": 0.45,  # Adjusted from 0.48
                "base_excitation_frequency": 0.65,
                "base_excitation_vertical_amplitude": 0.28,
                "base_excitation_horizontal_amplitude": 0.20,
                "fatigue_tau_seconds": 4.0,
                "joint_break_force": 0.5,
                "joint_break_torque": 0.7,
                "gravity": (0, -30.0),
            },
        },
    ]
