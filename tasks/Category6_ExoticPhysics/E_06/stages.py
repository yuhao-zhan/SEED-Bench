"""
E-06: The Brownian task curriculum stages (mutations).

All mutations use invisible physics parameters (noise strength, impact frequency,
joint/damage thresholds, beam fatigue, etc.). Visible mutations (joint_break_force,
joint_break_torque, damage_limit) are synced into the prompt via update_*_for_visible_changes.

Stages ordered by difficulty: Stage-1 (single param) -> Stage-4 (multiple params).
"""
from __future__ import annotations
import re
from typing import Any, Dict, List


# Base (source) values from environment.py — used when base_physics_config omits a key
DEFAULT_JOINT_BREAK_FORCE = 78.0
DEFAULT_JOINT_BREAK_TORQUE = 115.0
DEFAULT_DAMAGE_LIMIT = 100.0


TASK_DESCRIPTION_SUFFIX = """
## Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables **MIGHT** have changed from the initial environment, **NOT ALL** of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
- **Noise Strength**: The intensity of random thermal and environmental disturbances may vary.
- **Joint and Damage Thresholds**: The force, torque, and damage limits of structural components may be altered.
- **Coherent Pulses**: The frequency and magnitude of periodic energy impacts may have changed.
- **Motion Damping**: Resistance affecting the dissipation of kinetic energy may be adjusted.
- **Shock Propagation**: The severity of damage cascading through the structure may differ from standard.
- **Fatigue Dynamics**: Thresholds for angular velocity-induced structural wear may vary.
- **Environmental Storms**: Multipliers for storm intensity and burst probability may be altered.

**Discovery via feedback**: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., where a joint breaks or how a body moves) to infer the hidden constraints and adapt your design.
"""


def update_task_description_for_visible_changes(
    base_description: str,
    target_terrain_config: Dict[str, Any],
    base_terrain_config: Dict[str, Any],
    target_physics_config: Dict[str, Any] = None,
    base_physics_config: Dict[str, Any] = None,
) -> str:
    """
    Update task description with visible physics changes.
    Format: [new_value] (originally [old_value] in the source environment).
    """
    description = base_description
    target_physics_config = target_physics_config or {}
    base_physics_config = base_physics_config or {}

    target_force = target_physics_config.get("joint_break_force", DEFAULT_JOINT_BREAK_FORCE)
    base_force = base_physics_config.get("joint_break_force", DEFAULT_JOINT_BREAK_FORCE)
    target_torque = target_physics_config.get("joint_break_torque", DEFAULT_JOINT_BREAK_TORQUE)
    base_torque = base_physics_config.get("joint_break_torque", DEFAULT_JOINT_BREAK_TORQUE)
    target_damage = target_physics_config.get("damage_limit", DEFAULT_DAMAGE_LIMIT)
    base_damage = base_physics_config.get("damage_limit", DEFAULT_DAMAGE_LIMIT)

    if target_force != base_force:
        pattern = r"(Joints fail above )(\d+\.?\d*)( N reaction force)"
        if re.search(pattern, description):
            description = re.sub(
                pattern,
                f"\\g<1>{target_force:.0f} N (originally {base_force:.0f} N in the source environment) reaction force",
                description,
            )
    if target_torque != base_torque:
        pattern = r"(or )(\d+\.?\d*)( N·m reaction torque)"
        if re.search(pattern, description):
            description = re.sub(
                pattern,
                f"\\g<1>{target_torque:.0f} N·m (originally {base_torque:.0f} N·m in the source environment) reaction torque",
                description,
            )
    if target_damage != base_damage:
        pattern = r"(cumulative damage fails at )(\d+\.?\d*)( pts\.)"
        if re.search(pattern, description):
            description = re.sub(
                pattern,
                f"\\g<1>{target_damage:.0f} pts (originally {base_damage:.0f} pts in the source environment).",
                description,
            )
    return description


def update_success_criteria_for_visible_changes(
    base_success_criteria: str,
    target_terrain_config: Dict[str, Any],
    base_terrain_config: Dict[str, Any],
    target_physics_config: Dict[str, Any] = None,
    base_physics_config: Dict[str, Any] = None,
) -> str:
    """
    Update success criteria with visible physics changes.
    Format: [new_value] (originally [old_value] in the source environment).
    """
    criteria = base_success_criteria
    target_physics_config = target_physics_config or {}
    base_physics_config = base_physics_config or {}

    target_force = target_physics_config.get("joint_break_force", DEFAULT_JOINT_BREAK_FORCE)
    base_force = base_physics_config.get("joint_break_force", DEFAULT_JOINT_BREAK_FORCE)
    target_torque = target_physics_config.get("joint_break_torque", DEFAULT_JOINT_BREAK_TORQUE)
    base_torque = base_physics_config.get("joint_break_torque", DEFAULT_JOINT_BREAK_TORQUE)
    target_damage = target_physics_config.get("damage_limit", DEFAULT_DAMAGE_LIMIT)
    base_damage = base_physics_config.get("damage_limit", DEFAULT_DAMAGE_LIMIT)

    if target_force != base_force:
        pattern = r"(force > )(\d+\.?\d*)( N or)"
        if re.search(pattern, criteria):
            criteria = re.sub(
                pattern,
                f"\\g<1>{target_force:.0f} N (originally {base_force:.0f} N in the source environment) or",
                criteria,
            )
    if target_torque != base_torque:
        pattern = r"(torque > )(\d+\.?\d*)( N·m;)"
        if re.search(pattern, criteria):
            criteria = re.sub(
                pattern,
                f"\\g<1>{target_torque:.0f} N·m (originally {base_torque:.0f} N·m in the source environment);",
                criteria,
            )
    if target_damage != base_damage:
        pattern = r"(damage failure at )(\d+\.?\d*)( pts\.)"
        if re.search(pattern, criteria):
            criteria = re.sub(
                pattern,
                f"\\g<1>{target_damage:.0f} pts (originally {base_damage:.0f} pts in the source environment).",
                criteria,
            )
    return criteria


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
                "noise_strength": 120.0,
                "joint_break_force": 42.0,
                "joint_break_torque": 64.0,
                "damage_limit": 25.0,
                "damage_force_thresh": 7.0,
            },
        },
        # Stage-2: Frequent coherent pulses — Initial ref fails; Stage-2 ref (sturdier) passes
        {
            "stage_id": "Stage-2",
            "title": "Higher impact frequency",
            "mutation_description": "Coherent pulse much more frequent; joint/damage limits lowered so Initial ref fails.",
            "task_description_suffix": TASK_DESCRIPTION_SUFFIX,
            "terrain_config": {},
            "physics_config": {
                "noise_strength": 115.0,
                "coherent_pulse_interval": 1,
                "coherent_pulse_force": 108.0,
                "joint_break_force": 30.0,
                "joint_break_torque": 44.0,
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
                "noise_strength": 125.0,
                "coherent_pulse_interval": 5,
                "coherent_pulse_force": 105.0,
                "joint_break_force": 44.0,
                "joint_break_torque": 68.0,
                "damage_limit": 25.0,
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
                "angular_damping": 0.9,           # default 1.6 — less dissipation
                "joint_break_force": 52.0,
                "joint_break_torque": 82.0,
                "damage_limit": 48.0,
                "damage_force_thresh": 9.0,      # default 12.0
                "damage_torque_thresh": 14.0,    # default 18.0
                "cascade_shock_damage": 38.0,    # default 26.0
                "beam_angvel_thresh": 1.6,       # default 2.2
                "beam_angvel_tolerance_steps": 5, # default 10
                "phased_storm_mult": 2.6,        # default 1.9
                "burst_prob": 0.048,             # default 0.026
            },
        },
    ]
