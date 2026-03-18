"""
E-04: Variable Mass task curriculum stages (mutations).

Mutated tasks vary invisible physical parameters (mass variation frequency/amplitude,
base excitation, joint limits, fatigue, damping). The solver agent is NOT told the exact
parameter changes; it must infer from feedback.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

# Nominal joint limits from environment.py (source defaults)
DEFAULT_JOINT_BREAK_FORCE = 6.0
DEFAULT_JOINT_BREAK_TORQUE = 10.0


def _fmt_limit(value: float) -> str:
    """Format force/torque limit for prompt (handles small values like 1e-10)."""
    if value == 0 or (abs(value) < 1e-6 and value != 0):
        return f"{value:.4g}"
    if abs(value) >= 1000 or (abs(value) < 0.001 and value != 0):
        return f"{value:.4g}"
    return f"{value:.4f}".rstrip("0").rstrip(".")


TASK_DESCRIPTION_SUFFIX = """
## Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables **MIGHT** have changed from the initial environment, **NOT ALL** of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
- **Aerodynamic Loading**: Constant lateral wind pressure that varies with structural profile area.
- **Connection Axial Strength**: The maximum linear (axial) force joints can withstand before failing.
- **Connection Torsional Yield**: The ability of joints to resist twisting moments may be altered.
- **Asymmetric Gravity**: Significant shifts in the gravitational field vector, creating massive continuous side-loading.
- **Dynamic Mass Resonance**: Altered frequencies and amplitudes of mass fluctuations that can trigger structural resonance.
- **Mass Variation Spatial Phase**: How the phase of mass oscillation varies with beam position along the structure.
- **Progressive Structural Fatigue**: Joint strength may decay over time; requiring redundant load paths and low-stress designs.

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
    Update task description with visible changes: joint limits (nominal) when mutated.
    Format: [new_value] (originally [old_value] in the source environment).
    """
    description = base_description
    target_physics_config = target_physics_config or {}
    base_physics_config = base_physics_config or {}

    base_force = base_physics_config.get("joint_break_force", DEFAULT_JOINT_BREAK_FORCE)
    base_torque = base_physics_config.get("joint_break_torque", DEFAULT_JOINT_BREAK_TORQUE)
    target_force = target_physics_config.get("joint_break_force", base_force)
    target_torque = target_physics_config.get("joint_break_torque", base_torque)

    if target_force != base_force:
        force_pattern = r"(- \*\*Joint Limits \(nominal\)\*\*: Joints fail if reaction force exceeds )(\d+\.?\d*e?-?\d*)( N or reaction torque exceeds )"
        if re.search(force_pattern, description):
            description = re.sub(
                force_pattern,
                lambda m: f"{m.group(1)}{_fmt_limit(target_force)} N (originally {_fmt_limit(base_force)} N in the source environment) or reaction torque exceeds ",
                description,
            )
        else:
            # Fallback: match "reaction force exceeds 6.0 N"
            alt_force_pattern = r"(reaction force exceeds )(\d+\.?\d*e?-?\d*)( N)"
            if re.search(alt_force_pattern, description):
                description = re.sub(
                    alt_force_pattern,
                    lambda m: f"{m.group(1)}{_fmt_limit(target_force)} N (originally {_fmt_limit(base_force)} N in the source environment)",
                    description,
                    1,
                )

    if target_torque != base_torque:
        torque_pattern = r"(reaction torque exceeds )(\d+\.?\d*e?-?\d*)( N·m )(\(before fatigue decay\))"
        if re.search(torque_pattern, description):
            description = re.sub(
                torque_pattern,
                lambda m: f"{m.group(1)}{_fmt_limit(target_torque)} N·m (originally {_fmt_limit(base_torque)} N·m in the source environment) {m.group(4)}",
                description,
            )
        else:
            alt_torque_pattern = r"(reaction torque exceeds )(\d+\.?\d*e?-?\d*)( N·m)"
            if re.search(alt_torque_pattern, description):
                description = re.sub(
                    alt_torque_pattern,
                    lambda m: f"{m.group(1)}{_fmt_limit(target_torque)} N·m (originally {_fmt_limit(base_torque)} N·m in the source environment)",
                    description,
                    1,
                )

    return description

def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update success criteria for visible changes."""
    return base_success_criteria

def get_e04_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns ordered stage configs for E-04 variants.
    Stages use fundamentally different physical challenges.
    """
    return [
        # Stage-1: High-Frequency Resonance + Low Limit
        {
            "stage_id": "Stage-1",
            "title": "Resonant Instability",
            "mutation_description": "Structural mass varies at high frequency with large amplitude, targeting standard beam resonance.",
            "task_description_suffix": TASK_DESCRIPTION_SUFFIX,
            "terrain_config": {},
            "physics_config": {
                "mass_freq_1": 1.5,
                "mass_amp_1": 0.4,
                "joint_break_force": 0.005,
                "joint_break_torque": 0.002,
            },
        },
        # Stage-2: Zero Torque (Purely Axial) + Wind
        {
            "stage_id": "Stage-2",
            "title": "The Weld-less Truss",
            "mutation_description": "Joints cannot resist ANY torque. Structure must be a perfect funicular arch or truss.",
            "task_description_suffix": TASK_DESCRIPTION_SUFFIX,
            "terrain_config": {},
            "physics_config": {
                "joint_break_torque": 1e-10,
                "wind_pressure": 10000.0,
                "fatigue_tau_seconds": 400.0,
            },
        },
        # Stage-3: Massive Lateral Load (Extreme Wind + Twisting Phase)
        {
            "stage_id": "Stage-3",
            "title": "The Lateral Vortex",
            "mutation_description": "Extreme wind pressure combined with high spatial mass phase gradient creating non-uniform twisting loads.",
            "task_description_suffix": TASK_DESCRIPTION_SUFFIX,
            "terrain_config": {},
            "physics_config": {
                "wind_pressure": 1500.0,
                "mass_phase_gradient": 15.0,
                "mass_amp_1": 0.4,
                "fatigue_tau_seconds": 400.0,
                "joint_break_torque": 0.05,
            },
        },

        # Stage-4: The Event Horizon (Lateral Gravity + Fatigue + Zero Torque)
        {
            "stage_id": "Stage-4",
            "title": "Gravitational Shear",
            "mutation_description": "Massive lateral gravity vector combined with zero torque capacity and rapid fatigue.",
            "task_description_suffix": TASK_DESCRIPTION_SUFFIX,
            "terrain_config": {},
            "physics_config": {
                "gravity": (15000.0, -30.0),
                "joint_break_torque": 1e-10,
                "fatigue_tau_seconds": 60.0,
            },
        },
    ]

