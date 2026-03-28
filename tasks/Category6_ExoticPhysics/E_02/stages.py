"""
E-02: Thick Air task curriculum stages (mutations) with Essential Difficulty Escalation.

Stages are designed to be fundamentally harder, requiring physical reasoning
about constant forces, damping, and multi-variable constraints.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

# Default from environment.py (used when base_physics is empty)
_DEFAULT_OVERHEAT_LIMIT = 72000.0


def update_task_description_for_visible_changes(
    base_description: str,
    target_terrain_config: Dict[str, Any],
    base_terrain_config: Dict[str, Any],
    target_physics_config: Dict[str, Any] = None,
    base_physics_config: Dict[str, Any] = None,
    *,
    stage: Dict[str, Any] = None,
) -> str:
    """
    Update task description with visible changes using format:
    [new_value] (originally [old_value] in the source environment).
    Callers may pass stage=stage so that physics_config (e.g. overheat_limit) is synced from the stage dict.
    """
    description = base_description
    target_physics_config = target_physics_config or {}
    base_physics_config = base_physics_config or {}
    if stage is not None:
        target_physics_config = dict(stage.get("physics_config") or {})
        base_physics_config = {}
    target_overheat = float(target_physics_config.get("overheat_limit", _DEFAULT_OVERHEAT_LIMIT))
    base_overheat = float(base_physics_config.get("overheat_limit", _DEFAULT_OVERHEAT_LIMIT))
    if target_overheat != base_overheat:
        # "The overheat limit is 72000 N·s; exceeding it causes mission failure."
        pattern = r"(The overheat limit is )(\d+\.?\d*)( N·s; exceeding it causes mission failure\.)"
        if re.search(pattern, description):
            description = re.sub(
                pattern,
                lambda m: f"{m.group(1)}{target_overheat:.0f} N·s (originally {base_overheat:.0f} N·s in the source environment); exceeding it causes mission failure.",
                description,
            )
    return description


def update_success_criteria_for_visible_changes(
    base_success_criteria: str,
    target_terrain_config: Dict[str, Any],
    base_terrain_config: Dict[str, Any],
    target_physics_config: Dict[str, Any] = None,
    base_physics_config: Dict[str, Any] = None,
    *,
    stage: Dict[str, Any] = None,
) -> str:
    """Update success criteria with visible overheat limit changes. Callers may pass stage= so physics_config is synced from the stage dict."""
    criteria = base_success_criteria
    target_physics_config = target_physics_config or {}
    base_physics_config = base_physics_config or {}
    if stage is not None:
        target_physics_config = dict(stage.get("physics_config") or {})
        base_physics_config = {}
    target_overheat = float(target_physics_config.get("overheat_limit", _DEFAULT_OVERHEAT_LIMIT))
    base_overheat = float(base_physics_config.get("overheat_limit", _DEFAULT_OVERHEAT_LIMIT))
    if target_overheat != base_overheat:
        # "2. **Thermal Safety**: Craft heat stays below the overheat limit (72000 N·s)."
        pattern = r"(2\. \*\*Thermal Safety\*\*: Craft heat stays below the overheat limit \()(\d+\.?\d*)( N·s\)\.)"
        if re.search(pattern, criteria):
            criteria = re.sub(
                pattern,
                lambda m: f"{m.group(1)}{target_overheat:.0f} N·s (originally {base_overheat:.0f} N·s in the source environment)).",
                criteria,
            )
    return criteria


# --- DYNAMICALLY GENERATED UNIFORM SUFFIX ---
# Union of all physical variables modified across all stages:
# - linear_damping
# - constant_force_x (Atmospheric Headwind/Tailwind)
# - constant_force_y (Updraft/Downdraft)
# - drain_velocity_factor (Momentum Drain)
# - slip_backward_force (Zone Resistance)
# - gravity (Gravitational Constant)
# - overheat_limit (Thermal Capacity)
# - wind_amplitude (Oscillating Disturbances)

TASK_DESCRIPTION_SUFFIX = """
## Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables **MIGHT** have changed from the initial environment, **NOT ALL** of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
- **Atmospheric Damping**: Air resistance and motion drag may be significantly altered, affecting terminal velocity.
- **Lateral Atmospheric Flow**: Constant horizontal forces (headwinds or tailwinds) may bias craft movement.
- **Vertical Pressure Gradients**: Constant vertical forces (updrafts or downdrafts) may interfere with altitude maintenance.
- **Kinetic Momentum Drain**: specialized zones may alter velocity or kinetic energy at varying rates per simulation step.
- **Slippery Resistive Forces**: Directional forces in slipping regions may have changed in magnitude or direction.
- **Gravitational Variance**: The local gravitational acceleration vector may differ from standard.
- **Thermal Threshold**: The maximum overheat limit for safe operation may be adjusted.
- **Dynamic Wind Intensity**: Amplitude and frequency of atmospheric disturbances may differ.

**Discovery via feedback**: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., thermal exhaustion, stalling in resistive zones, or failing to reach the target) to infer the hidden constraints and adapt your design.
"""

def get_e02_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns ordered stage configs for E-02 variants (difficulty ascending).
    """
    return [
        {
            "stage_id": "Stage-1",
            "title": "Constant Headwind (Lateral Bias)",
            "mutation_description": "A constant horizontal force pushes against the craft, requiring higher baseline thrust to maintain forward progress.",
            "task_description_suffix": TASK_DESCRIPTION_SUFFIX,
            "terrain_config": {},
            "physics_config": {
                "constant_force_x": -75.0,  # Mass is 25, so this is -3m/s^2 equivalent acceleration force.
            },
        },
        {
            "stage_id": "Stage-2",
            "title": "Persistent Updraft (Vertical Bias)",
            "mutation_description": "A constant upward force pushes the craft, making it difficult to pass through low-clearance gates without overshooting.",
            "task_description_suffix": TASK_DESCRIPTION_SUFFIX,
            "terrain_config": {},
            "physics_config": {
                "constant_force_y": 150.0, # Strong updraft, overcomes base gravity (25 * -3 = -75)
            },
        },
        {
            "stage_id": "Stage-3",
            "title": "Viscous Drain (Multi-variable: Damping + Drain + Slip)",
            "mutation_description": "High air resistance combined with extreme momentum drain and slip forces. Requires high power but risks overheating.",
            "task_description_suffix": TASK_DESCRIPTION_SUFFIX,
            "terrain_config": {},
            "physics_config": {
                "linear_damping": 8.0,
                "drain_velocity_factor": 0.05,
                "slip_backward_force": -50.0,
                "gravity": (0, -5.0), # Heavier gravity too
            },
        },
        {
            "stage_id": "Stage-4",
            "title": "The Perfect Storm (Extreme Multi-variable)",
            "mutation_description": "High damping, headwind, strong oscillating wind, and a severely tight heat budget.",
            "task_description_suffix": TASK_DESCRIPTION_SUFFIX,
            "terrain_config": {},
            "physics_config": {
                "linear_damping": 1.5,
                "constant_force_x": -10.0,
                "wind_amplitude": 50.0,
                "wind_omega": 0.15,
                "overheat_limit": 40000.0, # Default 72000
                "gravity": (0, -6.0),
            },
        },
    ]
