"""
S-02: The Skyscraper task curriculum stages (mutations).
"""

from __future__ import annotations

from typing import Any, Dict, List
import re

def update_task_description_for_visible_changes(base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any], target_physics_config: Dict[str, Any] = None, base_physics_config: Dict[str, Any] = None) -> str:
    """
    Updates the task description for VISIBLE changes (joint strength).
    Callers must pass target_physics_config and base_physics_config for mutated joint limits
    to be reflected in the prompt with the required '[new_value] (originally [old_value] in the source environment)' format.
    """
    description = base_description

    target_physics_config = target_physics_config or {}
    base_physics_config = base_physics_config or {}

    # Sync Joint Strength if mutated (torque pattern uses (inf|\d+\.?\d*) so trailing period is not consumed)
    for key, pattern, default in [
        ("max_joint_force", r"(- \*\*Joint Strength\*\*: Maximum linear force for a joint is )(inf|\d+\.?\d*)", float('inf')),
        ("max_joint_torque", r"(; maximum torque is )(inf|\d+\.?\d*)", float('inf'))
    ]:
        target_val = target_physics_config.get(key, default)
        base_val = base_physics_config.get(key, default)
        
        if target_val != base_val:
            target_str = f"{target_val:.1f}" if target_val != float('inf') else "inf"
            base_str = f"{base_val:.1f}" if base_val != float('inf') else "inf"
            
            if re.search(pattern, description):
                description = re.sub(
                    pattern,
                    f"\\g<1>{target_str} (originally {base_str} in the source environment)",
                    description
                )

    # Sync Wind Height Threshold
    key = "wind_height_threshold"
    pattern = r"(at altitudes above )(\d+\.?\d*m)(, simulating wind pressure)"
    target_val = target_terrain_config.get(key, 20.0)
    base_val = base_terrain_config.get(key, 20.0)
    if target_val != base_val:
        if re.search(pattern, description):
            description = re.sub(
                pattern,
                f"\\g<1>{target_val:.1f}m (originally {base_val:.1f}m in the source environment)\\g<3>",
                description
            )
    
    return description

def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Updates the success criteria for VISIBLE changes (none currently for S-02 besides those in description)."""
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
 - **Structural Integrity Thresholds**: Joints between beams may have altered breaking limits for both force and torque.
 - **Seismic Dynamics**: The foundation's oscillation may exhibit varying amplitudes, frequencies, or evolve in intensity over time.
 - **Atmospheric Loading**: Lateral wind forces may change in magnitude, height thresholds, shear, or periodic oscillation.
 - **Gravitational Constant**: The local vertical acceleration may differ from standard earth gravity, altering the weight of the structure.

**Discovery via feedback**: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., where a joint breaks or how the tower sways) to infer the hidden constraints and adapt your design.
"""

    return [
        {
            "stage_id": "Stage-1",
            "title": "The Brittle Foundation",
            "mutation_description": "Structural torque limit at the base. Heavy towers will snap foundation joints upon oscillation; agent must build light/balanced.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "earthquake_amplitude": 0.4,
            },
            "physics_config": {
                "max_joint_torque": 80000.0,  # Light tower passes; initial (heavy) fails
                "max_joint_force": 50000.0,
            },
        },
        {
            "stage_id": "Stage-2",
            "title": "Atmospheric Resonance",
            "mutation_description": "Sustained oscillating wind from low altitude drives structural resonance; standard tower without tuned damping fails.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "wind_force": 2.5,
                "wind_oscillation_frequency": 0.35,
                "wind_height_threshold": 14.0,
            },
            "physics_config": {
                "max_joint_force": 60000.0,
                "max_joint_torque": 120000.0,
            },
        },
        {
            "stage_id": "Stage-3",
            "title": "Seismic Amplification",
            "mutation_description": "Sustained moderate-amplitude seismic load; heavy towers sway beyond width limit without tuned damping.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "earthquake_amplitude": 0.36,
                "earthquake_frequency": 1.75,
                "earthquake_amplitude_evolution": 0.0,
            },
            "physics_config": {
                "max_joint_force": 250000.0,
                "max_joint_torque": 200000.0,
            },
        },
        {
            "stage_id": "Stage-4",
            "title": "The Gravity Well Collapse",
            "mutation_description": "High gravity plus strong seismic and wind create conflicting constraints; weight and lateral load must be balanced.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "earthquake_amplitude": 0.34,
                "earthquake_frequency": 1.75,
                "wind_force": 22.0,
                "wind_height_threshold": 16.0,
                "wind_shear_factor": 0.06,
            },
            "physics_config": {
                "gravity": (0, -12.5),
                "max_joint_force": 80000.0,
                "max_joint_torque": 90000.0,
            },
        },
    ]
