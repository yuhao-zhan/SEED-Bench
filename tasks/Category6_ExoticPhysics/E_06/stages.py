"""
E-06: The Brownian task curriculum stages (mutations).

All mutations use invisible physics parameters (noise strength, impact frequency,
joint/damage thresholds, beam fatigue, etc.). No task_description_suffix — agent
must infer changes from environment feedback.

Stages ordered by difficulty: Stage-1 (single param) -> Stage-4 (multiple params).
"""
from __future__ import annotations
from typing import Any, Dict, List


TASK_DESCRIPTION_SUFFIX = """
Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables MIGHT have changed from the initial environment, NOT ALL of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
 - Noise Strength: The intensity of random thermal and environmental disturbances.
 - Joint and Damage Thresholds: The force, torque, and damage limits of structural components.
 - Coherent Pulses: The frequency and magnitude of periodic energy impacts.
 - Motion Damping: Resistance affecting the dissipation of kinetic energy.
 - Shock Propagation: The severity of damage cascading through the structure.
 - Fatigue Dynamics: Thresholds for angular velocity-induced structural wear.
 - Environmental Storms: Multipliers for storm intensity and burst probability.

Discovery via feedback: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., where a joint breaks or how a body moves) to infer the hidden constraints and adapt your design.
"""


def update_task_description_for_visible_changes(base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update task description for visible changes."""
    return base_description


def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update success criteria for visible changes."""
    return base_success_criteria


def get_e06_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns ordered stage configs (difficulty ascending).

    Each stage dict: stage_id, title, mutation_description (for logs),
    terrain_config, physics_config. No task_description_suffix (invisible params).
    """
    return [
        # Stage-1: Strong thermal noise — ref fails
        {
            "stage_id": "Stage-1",
            "title": "Higher thermal noise",
            "mutation_description": "Noise strength ~2.2x; joint/damage limits lowered so ref fails.",
            "task_description_suffix": TASK_DESCRIPTION_SUFFIX,
            "terrain_config": {},
            "physics_config": {
                "noise_strength": 100.0,
                "joint_break_force": 38.0,
                "joint_break_torque": 54.0,
                "damage_limit": 22.0,
                "damage_force_thresh": 7.0,
            },
        },
        # Stage-2: Frequent coherent pulses — ref fails
        {
            "stage_id": "Stage-2",
            "title": "Higher impact frequency",
            "mutation_description": "Coherent pulse much more frequent; joint/damage limits lowered so ref fails.",
            "task_description_suffix": TASK_DESCRIPTION_SUFFIX,
            "terrain_config": {},
            "physics_config": {
                "noise_strength": 95.0,
                "coherent_pulse_interval": 1,
                "coherent_pulse_force": 85.0,
                "joint_break_force": 22.0,
                "joint_break_torque": 35.0,
                "damage_limit": 12.0,
            },
        },
        # Stage-3: Multiple harsh params — ref fails
        {
            "stage_id": "Stage-3",
            "title": "Noisy, frequent, fragile joints",
            "mutation_description": "Higher noise, higher frequency, lower joint/damage limits so ref fails.",
            "task_description_suffix": TASK_DESCRIPTION_SUFFIX,
            "terrain_config": {},
            "physics_config": {
                "noise_strength": 90.0,
                "coherent_pulse_interval": 8,
                "coherent_pulse_force": 65.0,
                "joint_break_force": 36.0,
                "joint_break_torque": 52.0,
                "damage_limit": 20.0,
            },
        },
        # Stage-4: Multiple harsher params — ref solution should fail
        {
            "stage_id": "Stage-4",
            "title": "Hostile environment",
            "mutation_description": "High noise, high frequency, lower damping, faster beam fatigue, higher cascade.",
            "task_description_suffix": TASK_DESCRIPTION_SUFFIX,
            "terrain_config": {},
            "physics_config": {
                "noise_strength": 72.0,
                "coherent_pulse_interval": 22,
                "coherent_pulse_force": 50.0,
                "angular_damping": 0.9,           # default 1.8 — less dissipation
                "joint_break_force": 52.0,
                "joint_break_torque": 82.0,
                "damage_limit": 48.0,
                "damage_force_thresh": 9.0,      # default 13
                "damage_torque_thresh": 14.0,    # default 20
                "cascade_shock_damage": 38.0,    # default 24
                "beam_angvel_thresh": 1.6,       # default 2.4
                "beam_angvel_tolerance_steps": 5, # default 12
                "phased_storm_mult": 2.6,        # default 1.85
                "burst_prob": 0.048,             # default ~0.022
            },
        },
    ]
