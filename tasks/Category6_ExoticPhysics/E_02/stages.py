"""
E-02: Thick Air task curriculum stages (mutations) with Essential Difficulty Escalation.

Stages are designed to be fundamentally harder, requiring physical reasoning
about constant forces, damping, and multi-variable constraints.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

# Defaults from environment.py (used when base configs are empty)
_DEFAULT_OVERHEAT_LIMIT = 72000.0
_DEFAULT_CRAFT_START = (8.0, 2.0)
_DEFAULT_TARGET_X = (28.0, 32.0)
_DEFAULT_TARGET_Y = (2.0, 5.0)
_DEFAULT_GATE1_X = (12.0, 14.0)
_DEFAULT_GATE1_Y = (1.0, 2.8)
_DEFAULT_GATE2_X = (22.0, 24.0)
_DEFAULT_GATE2_Y = (1.8, 3.0)
_DEFAULT_MAX_STEPS = 10000


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
    """
    description = base_description
    target_physics_config = target_physics_config or {}
    base_physics_config = base_physics_config or {}
    target_terrain_config = target_terrain_config or {}
    base_terrain_config = base_terrain_config or {}

    if stage is not None:
        target_physics_config = dict(stage.get("physics_config") or {})
        target_terrain_config = dict(stage.get("terrain_config") or {})
        base_physics_config = {}
        base_terrain_config = {}

    # 1. Overheat Limit
    target_overheat = float(target_physics_config.get("overheat_limit", _DEFAULT_OVERHEAT_LIMIT))
    base_overheat = float(base_physics_config.get("overheat_limit", _DEFAULT_OVERHEAT_LIMIT))
    if target_overheat != base_overheat:
        pattern = r"(The overheat limit is )(\d+\.?\d*)( N·s; exceeding it causes mission failure\.)"
        description = re.sub(
            pattern,
            lambda m: f"{m.group(1)}{target_overheat:.0f} N·s (originally {base_overheat:.0f} N·s in the source environment); exceeding it causes mission failure.",
            description,
        )

    # 2. Craft Start
    t_sx = float(target_terrain_config.get("craft_start_x", _DEFAULT_CRAFT_START[0]))
    t_sy = float(target_terrain_config.get("craft_start_y", _DEFAULT_CRAFT_START[1]))
    b_sx = float(base_terrain_config.get("craft_start_x", _DEFAULT_CRAFT_START[0]))
    b_sy = float(base_terrain_config.get("craft_start_y", _DEFAULT_CRAFT_START[1]))
    if t_sx != b_sx or t_sy != b_sy:
        pattern = r"(\(x=)(\d+\.?\d*)( m, y=)(\d+\.?\d*)( m\))"
        description = re.sub(
            pattern,
            lambda m: f"(x={t_sx:.1f} m (originally {b_sx:.1f} m in the source environment), y={t_sy:.1f} m (originally {b_sy:.1f} m in the source environment))",
            description,
        )

    # 3. Target Zone
    t_txm = float(target_terrain_config.get("target_x_min", _DEFAULT_TARGET_X[0]))
    t_txM = float(target_terrain_config.get("target_x_max", _DEFAULT_TARGET_X[1]))
    t_tym = float(target_terrain_config.get("target_y_min", _DEFAULT_TARGET_Y[0]))
    t_tyM = float(target_terrain_config.get("target_y_max", _DEFAULT_TARGET_Y[1]))
    
    b_txm = float(base_terrain_config.get("target_x_min", _DEFAULT_TARGET_X[0]))
    b_txM = float(base_terrain_config.get("target_x_max", _DEFAULT_TARGET_X[1]))
    b_tym = float(base_terrain_config.get("target_y_min", _DEFAULT_TARGET_Y[0]))
    b_tyM = float(base_terrain_config.get("target_y_max", _DEFAULT_TARGET_Y[1]))

    if (t_txm, t_txM, t_tym, t_tyM) != (b_txm, b_txM, b_tym, b_tyM):
        pattern = r"(target coordinate \(x in \[)(\d+\.?\d*)(, )(\d+\.?\d*)(\], y in \[)(\d+\.?\d*)(, )(\d+\.?\d*)(\]\))"
        description = re.sub(
            pattern,
            lambda m: (f"target coordinate (x in [{t_txm:.1f}, {t_txM:.1f}] (originally [{b_txm:.1f}, {b_txM:.1f}] in the source environment), "
                       f"y in [{t_tym:.1f}, {t_tyM:.1f}] (originally [{b_tym:.1f}, {b_tyM:.1f}] in the source environment))"),
            description,
        )

    # 4. Gates
    # Gate 1
    t_g1xm = float(target_terrain_config.get("gate1_x_lo", _DEFAULT_GATE1_X[0]))
    t_g1xM = float(target_terrain_config.get("gate1_x_hi", _DEFAULT_GATE1_X[1]))
    t_g1ym = float(target_terrain_config.get("gate1_y_lo", _DEFAULT_GATE1_Y[0]))
    t_g1yM = float(target_terrain_config.get("gate1_y_hi", _DEFAULT_GATE1_Y[1]))
    
    b_g1xm = float(base_terrain_config.get("gate1_x_lo", _DEFAULT_GATE1_X[0]))
    b_g1xM = float(base_terrain_config.get("gate1_x_hi", _DEFAULT_GATE1_X[1]))
    b_g1ym = float(base_terrain_config.get("gate1_y_lo", _DEFAULT_GATE1_Y[0]))
    b_g1yM = float(base_terrain_config.get("gate1_y_hi", _DEFAULT_GATE1_Y[1]))

    if (t_g1xm, t_g1xM, t_g1ym, t_g1yM) != (b_g1xm, b_g1xM, b_g1ym, b_g1yM):
        pattern = r"(\*\*Gate 1\*\*: x in \[)(\d+\.?\d*)(, )(\d+\.?\d*)(\] m, y in \[)(\d+\.?\d*)(, )(\d+\.?\d*)(\] m)"
        description = re.sub(
            pattern,
            lambda m: (f"**Gate 1**: x in [{t_g1xm:.1f}, {t_g1xM:.1f}] m (originally [{b_g1xm:.1f}, {b_g1xM:.1f}] m in the source environment), "
                       f"y in [{t_g1ym:.1f}, {t_g1yM:.1f}] m (originally [{b_g1ym:.1f}, {b_g1yM:.1f}] m in the source environment)"),
            description,
        )

    # Gate 2
    t_g2xm = float(target_terrain_config.get("gate2_x_lo", _DEFAULT_GATE2_X[0]))
    t_g2xM = float(target_terrain_config.get("gate2_x_hi", _DEFAULT_GATE2_X[1]))
    t_g2ym = float(target_terrain_config.get("gate2_y_lo", _DEFAULT_GATE2_Y[0]))
    t_g2yM = float(target_terrain_config.get("gate2_y_hi", _DEFAULT_GATE2_Y[1]))
    
    b_g2xm = float(base_terrain_config.get("gate2_x_lo", _DEFAULT_GATE2_X[0]))
    b_g2xM = float(base_terrain_config.get("gate2_x_hi", _DEFAULT_GATE2_X[1]))
    b_g2ym = float(base_terrain_config.get("gate2_y_lo", _DEFAULT_GATE2_Y[0]))
    b_g2yM = float(base_terrain_config.get("gate2_y_hi", _DEFAULT_GATE2_Y[1]))

    if (t_g2xm, t_g2xM, t_g2ym, t_g2yM) != (b_g2xm, b_g2xM, b_g2ym, b_g2yM):
        pattern = r"(\*\*Gate 2\*\*: x in \[)(\d+\.?\d*)(, )(\d+\.?\d*)(\] m, y in \[)(\d+\.?\d*)(, )(\d+\.?\d*)(\] m)"
        description = re.sub(
            pattern,
            lambda m: (f"**Gate 2**: x in [{t_g2xm:.1f}, {t_g2xM:.1f}] m (originally [{b_g2xm:.1f}, {b_g2xM:.1f}] m in the source environment), "
                       f"y in [{t_g2ym:.1f}, {t_g2yM:.1f}] m (originally [{b_g2ym:.1f}, {b_g2yM:.1f}] m in the source environment)"),
            description,
        )

    # 5. Max Steps
    t_ms = int(target_physics_config.get("max_steps", _DEFAULT_MAX_STEPS))
    b_ms = int(base_physics_config.get("max_steps", _DEFAULT_MAX_STEPS))
    if t_ms != b_ms:
        pattern = r"(at most )(\d+)( simulation steps)"
        description = re.sub(
            pattern,
            lambda m: f"{m.group(1)}{t_ms} simulation steps (originally {b_ms} simulation steps in the source environment)",
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
    """Update success criteria with visible changes."""
    criteria = base_success_criteria
    target_physics_config = target_physics_config or {}
    base_physics_config = base_physics_config or {}
    target_terrain_config = target_terrain_config or {}
    base_terrain_config = base_terrain_config or {}

    if stage is not None:
        target_physics_config = dict(stage.get("physics_config") or {})
        target_terrain_config = dict(stage.get("terrain_config") or {})
        base_physics_config = {}
        base_terrain_config = {}

    # 1. Overheat Limit
    target_overheat = float(target_physics_config.get("overheat_limit", _DEFAULT_OVERHEAT_LIMIT))
    base_overheat = float(base_physics_config.get("overheat_limit", _DEFAULT_OVERHEAT_LIMIT))
    if target_overheat != base_overheat:
        pattern = r"(2\. \*\*Thermal Safety\*\*: Craft heat stays below the overheat limit \()(\d+\.?\d*)( N·s\)\.)"
        criteria = re.sub(
            pattern,
            lambda m: f"{m.group(1)}{target_overheat:.0f} N·s (originally {base_overheat:.0f} N·s in the source environment)).",
            criteria,
        )

    # 2. Target Zone
    t_txm = float(target_terrain_config.get("target_x_min", _DEFAULT_TARGET_X[0]))
    t_txM = float(target_terrain_config.get("target_x_max", _DEFAULT_TARGET_X[1]))
    t_tym = float(target_terrain_config.get("target_y_min", _DEFAULT_TARGET_Y[0]))
    t_tyM = float(target_terrain_config.get("target_y_max", _DEFAULT_TARGET_Y[1]))
    
    b_txm = float(base_terrain_config.get("target_x_min", _DEFAULT_TARGET_X[0]))
    b_txM = float(base_terrain_config.get("target_x_max", _DEFAULT_TARGET_X[1]))
    b_tym = float(base_terrain_config.get("target_y_min", _DEFAULT_TARGET_Y[0]))
    b_tyM = float(base_terrain_config.get("target_y_max", _DEFAULT_TARGET_Y[1]))

    if (t_txm, t_txM, t_tym, t_tyM) != (b_txm, b_txM, b_tym, b_tyM):
        pattern = r"(1\. \*\*Target Reach\*\*: Craft center enters the target zone \(x in \[)(\d+\.?\d*)(, )(\d+\.?\d*)(\], y in \[)(\d+\.?\d*)(, )(\d+\.?\d*)(\]\)\.)"
        criteria = re.sub(
            pattern,
            lambda m: (f"1. **Target Reach**: Craft center enters the target zone (x in [{t_txm:.1f}, {t_txM:.1f}] (originally [{b_txm:.1f}, {b_txM:.1f}] in the source environment), "
                       f"y in [{t_tym:.1f}, {t_tyM:.1f}] (originally [{b_tym:.1f}, {b_tyM:.1f}] in the source environment))."),
            criteria,
        )

    return criteria


# --- DYNAMICALLY GENERATED UNIFORM SUFFIX ---
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
                "constant_force_x": -75.0,
            },
        },
        {
            "stage_id": "Stage-2",
            "title": "Persistent Updraft (Vertical Bias)",
            "mutation_description": "A constant upward force pushes the craft, making it difficult to pass through low-clearance gates without overshooting.",
            "task_description_suffix": TASK_DESCRIPTION_SUFFIX,
            "terrain_config": {},
            "physics_config": {
                "constant_force_y": 150.0,
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
                "gravity": (0, -5.0),
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
                "overheat_limit": 40000.0,
                "gravity": (0, -6.0),
            },
        },
    ]
