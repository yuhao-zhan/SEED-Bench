"""
E-03: Slippery World task curriculum stages (mutations).

All mutations change INVISIBLE physics parameters (global friction, gravity,
linear/angular damping, momentum drain, thrust-scale zone).
The solver agent is NOT told the exact parameter changes; it must infer from feedback.

Stages ordered by difficulty: Stage-1 (easiest, one param) -> Stage-4 (hardest, multiple params).
Each stage is designed so the original reference solution FAILS (environment adaptability).
"""
from __future__ import annotations

from typing import Any, Dict, List


TASK_DESCRIPTION_SUFFIX = """
## Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables **MIGHT** have changed from the initial environment, **NOT ALL** of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
- **Surface Friction**: Resistance encountered when sliding or moving across the terrain may have changed.
- **Gravity**: The magnitude and direction of the gravitational acceleration may differ from standard.
- **Momentum Drain**: The rate at which the system loses momentum over time may be altered.
- **Atmospheric Damping**: Air resistance and motion drag may vary.
- **Propulsion Efficiency**: The scaling factor affecting thrust output may be adjusted.

**Discovery via feedback**: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., how the sled loses speed, fails to reach a checkpoint, or overshoots the target) to infer the hidden constraints and adapt your design.
"""


import re


def update_task_description_for_visible_changes(base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update task description for visible changes (Sled start, Checkpoints, Target, Speed Penalty)."""
    description = base_description
    
    # Defaults
    defaults = {
        "sled_start_x": 8.0, "sled_start_y": 2.0,
        "target_x_min": 28.0, "target_x_max": 32.0,
        "target_y_min": 2.2, "target_y_max": 2.8,
        "checkpoint_a_x_lo": 17.5, "checkpoint_a_x_hi": 19.0,
        "checkpoint_a_y_lo": 3.8, "checkpoint_a_y_hi": 4.5,
        "checkpoint_b_x_lo": 23.0, "checkpoint_b_x_hi": 24.5,
        "checkpoint_b_y_lo": 2.5, "checkpoint_b_y_hi": 3.2,
        "speed_penalty_threshold": 4.0,
        "speed_penalty_x_lo": 22.0, "speed_penalty_x_hi": 26.0,
        "vert_reverse_x_lo": 26.5, "vert_reverse_x_hi": 28.5,
        "reverse_thrust_x_lo": 20.0, "reverse_thrust_x_hi": 25.0,
        "momentum_drain_x_lo": 11.0, "momentum_drain_x_hi": 17.0,
        "wind_zone_x_lo": 14.0, "wind_zone_x_hi": 28.0,
        "thrust_scale_x_lo": 19.5, "thrust_scale_x_hi": 21.0,
        "oscillating_fx_x_lo": 21.0, "oscillating_fx_x_hi": 27.0,
    }

    # Sled position update
    target_sx = target_terrain_config.get("sled_start_x", defaults["sled_start_x"])
    base_sx = base_terrain_config.get("sled_start_x", defaults["sled_start_x"])
    target_sy = target_terrain_config.get("sled_start_y", defaults["sled_start_y"])
    base_sy = base_terrain_config.get("sled_start_y", defaults["sled_start_y"])

    if target_sx != base_sx or target_sy != base_sy:
        sled_pattern = r"(It starts at position \(x=)([\d.]+)( m, y=)([\d.]+)( m\)\.)"
        description = re.sub(
            sled_pattern,
            lambda m: f"{m.group(1)}{target_sx:.1f} (originally {base_sx:.1f} in the source environment){m.group(3)}{target_sy:.1f} (originally {base_sy:.1f} in the source environment){m.group(5)}",
            description
        )

    # Checkpoint Alpha update
    ax0 = target_terrain_config.get("checkpoint_a_x_lo", defaults["checkpoint_a_x_lo"])
    ax1 = target_terrain_config.get("checkpoint_a_x_hi", defaults["checkpoint_a_x_hi"])
    ay0 = target_terrain_config.get("checkpoint_a_y_lo", defaults["checkpoint_a_y_lo"])
    ay1 = target_terrain_config.get("checkpoint_a_y_hi", defaults["checkpoint_a_y_hi"])
    
    bx0_base = base_terrain_config.get("checkpoint_a_x_lo", defaults["checkpoint_a_x_lo"])
    bx1_base = base_terrain_config.get("checkpoint_a_x_hi", defaults["checkpoint_a_x_hi"])
    by0_base = base_terrain_config.get("checkpoint_a_y_lo", defaults["checkpoint_a_y_lo"])
    by1_base = base_terrain_config.get("checkpoint_a_y_hi", defaults["checkpoint_a_y_hi"])

    if ax0 != bx0_base or ax1 != bx1_base or ay0 != by0_base or ay1 != by1_base:
        alpha_pattern = r"(- \*\*First checkpoint \(Alpha\)\*\*: Sled center must enter the zone x in \[)([\d.]+), ([\d.]+)(\] m, y in \[)([\d.]+), ([\d.]+)(\] m\.)"
        description = re.sub(
            alpha_pattern,
            lambda m: f"{m.group(1)}{ax0:.1f}, {ax1:.1f}] (originally [{bx0_base:.1f}, {bx1_base:.1f}] in the source environment){m.group(4)}{ay0:.1f}, {ay1:.1f}] (originally [{by0_base:.1f}, {by1_base:.1f}] in the source environment){m.group(7)}",
            description
        )

    # Checkpoint Beta update
    bx0 = target_terrain_config.get("checkpoint_b_x_lo", defaults["checkpoint_b_x_lo"])
    bx1 = target_terrain_config.get("checkpoint_b_x_hi", defaults["checkpoint_b_x_hi"])
    by0 = target_terrain_config.get("checkpoint_b_y_lo", defaults["checkpoint_b_y_lo"])
    by1 = target_terrain_config.get("checkpoint_b_y_hi", defaults["checkpoint_b_y_hi"])
    
    bbx0_base = base_terrain_config.get("checkpoint_b_x_lo", defaults["checkpoint_b_x_lo"])
    bbx1_base = base_terrain_config.get("checkpoint_b_x_hi", defaults["checkpoint_b_x_hi"])
    bby0_base = base_terrain_config.get("checkpoint_b_y_lo", defaults["checkpoint_b_y_lo"])
    bby1_base = base_terrain_config.get("checkpoint_b_y_hi", defaults["checkpoint_b_y_hi"])

    if bx0 != bbx0_base or bx1 != bbx1_base or by0 != bby0_base or by1 != bby1_base:
        beta_pattern = r"(- \*\*Second checkpoint \(Beta\)\*\*: Sled center must enter the zone x in \[)([\d.]+), ([\d.]+)(\] m, y in \[)([\d.]+), ([\d.]+)(\] m\.)"
        description = re.sub(
            beta_pattern,
            lambda m: f"{m.group(1)}{bx0:.1f}, {bx1:.1f}] (originally [{bbx0_base:.1f}, {bbx1_base:.1f}] in the source environment){m.group(4)}{by0:.1f}, {by1:.1f}] (originally [{bby0_base:.1f}, {bby1_base:.1f}] in the source environment){m.group(7)}",
            description
        )

    # Speed Penalty update
    sp_thresh = target_terrain_config.get("speed_penalty_threshold", defaults["speed_penalty_threshold"])
    sp_thresh_base = base_terrain_config.get("speed_penalty_threshold", defaults["speed_penalty_threshold"])
    sp_x0 = target_terrain_config.get("speed_penalty_x_lo", defaults["speed_penalty_x_lo"])
    sp_x1 = target_terrain_config.get("speed_penalty_x_hi", defaults["speed_penalty_x_hi"])
    sp_x0_base = base_terrain_config.get("speed_penalty_x_lo", defaults["speed_penalty_x_lo"])
    sp_x1_base = base_terrain_config.get("speed_penalty_x_hi", defaults["speed_penalty_x_hi"])

    if sp_thresh != sp_thresh_base or sp_x0 != sp_x0_base or sp_x1 != sp_x1_base:
        sp_pattern = r"(- \*\*Speed Penalty Zone\*\*: Between x=)([\d.]+) m and x=([\d.]+) m, a speed limit of ([\d.]+) m/s is enforced;"
        description = re.sub(
            sp_pattern,
            lambda m: f"{m.group(1)}{sp_x0:.1f} m and x={sp_x1:.1f} m (originally Between x={sp_x0_base:.1f} m and x={sp_x1_base:.1f} m in the source environment), a speed limit of {sp_thresh:.1f} m/s (originally {sp_thresh_base:.1f} m/s in the source environment) is enforced;",
            description
        )

    # Vertical Thrust Reverse update
    v_x0 = target_terrain_config.get("vert_reverse_x_lo", defaults["vert_reverse_x_lo"])
    v_x1 = target_terrain_config.get("vert_reverse_x_hi", defaults["vert_reverse_x_hi"])
    v_x0_base = base_terrain_config.get("vert_reverse_x_lo", defaults["vert_reverse_x_lo"])
    v_x1_base = base_terrain_config.get("vert_reverse_x_hi", defaults["vert_reverse_x_hi"])

    if v_x0 != v_x0_base or v_x1 != v_x1_base:
        v_pattern = r"(- \*\*Vertical Thrust Reverse Zone\*\*: Between x=)([\d.]+) m and x=([\d.]+) m,"
        description = re.sub(
            v_pattern,
            lambda m: f"{m.group(1)}{v_x0:.1f} m and x={v_x1:.1f} m (originally Between x={v_x0_base:.1f} m and x={v_x1_base:.1f} m in the source environment),",
            description
        )

    # Horizontal Thrust Reverse update
    h_x0 = target_terrain_config.get("reverse_thrust_x_lo", defaults["reverse_thrust_x_lo"])
    h_x1 = target_terrain_config.get("reverse_thrust_x_hi", defaults["reverse_thrust_x_hi"])
    h_x0_base = base_terrain_config.get("reverse_thrust_x_lo", defaults["reverse_thrust_x_lo"])
    h_x1_base = base_terrain_config.get("reverse_thrust_x_hi", defaults["reverse_thrust_x_hi"])

    if h_x0 != h_x0_base or h_x1 != h_x1_base:
        h_pattern = r"(- \*\*Horizontal Thrust Reverse Zone\*\*: Between x=)([\d.]+) m and x=([\d.]+) m,"
        description = re.sub(
            h_pattern,
            lambda m: f"{m.group(1)}{h_x0:.1f} m and x={h_x1:.1f} m (originally Between x={h_x0_base:.1f} m and x={h_x1_base:.1f} m in the source environment),",
            description
        )

    # Momentum Drain update
    md_x0 = target_terrain_config.get("momentum_drain_x_lo", defaults["momentum_drain_x_lo"])
    md_x1 = target_terrain_config.get("momentum_drain_x_hi", defaults["momentum_drain_x_hi"])
    md_x0_base = base_terrain_config.get("momentum_drain_x_lo", defaults["momentum_drain_x_lo"])
    md_x1_base = base_terrain_config.get("momentum_drain_x_hi", defaults["momentum_drain_x_hi"])
    if md_x0 != md_x0_base or md_x1 != md_x1_base:
        md_pattern = r"(- \*\*Momentum Drain Zone\*\*: Between x=)([\d.]+) m and x=([\d.]+) m,"
        description = re.sub(
            md_pattern,
            lambda m: f"{m.group(1)}{md_x0:.1f} m and x={md_x1:.1f} m (originally Between x={md_x0_base:.1f} m and x={md_x1_base:.1f} m in the source environment),",
            description
        )

    # Wind Zone update
    wz_x0 = target_terrain_config.get("wind_zone_x_lo", defaults["wind_zone_x_lo"])
    wz_x1 = target_terrain_config.get("wind_zone_x_hi", defaults["wind_zone_x_hi"])
    wz_x0_base = base_terrain_config.get("wind_zone_x_lo", defaults["wind_zone_x_lo"])
    wz_x1_base = base_terrain_config.get("wind_zone_x_hi", defaults["wind_zone_x_hi"])
    if wz_x0 != wz_x0_base or wz_x1 != wz_x1_base:
        wz_pattern = r"(- \*\*Wind Zone\*\*: Between x=)([\d.]+) m and x=([\d.]+) m,"
        description = re.sub(
            wz_pattern,
            lambda m: f"{m.group(1)}{wz_x0:.1f} m and x={wz_x1:.1f} m (originally Between x={wz_x0_base:.1f} m and x={wz_x1_base:.1f} m in the source environment),",
            description
        )

    # Thrust Scaling update
    ts_x0 = target_terrain_config.get("thrust_scale_x_lo", defaults["thrust_scale_x_lo"])
    ts_x1 = target_terrain_config.get("thrust_scale_x_hi", defaults["thrust_scale_x_hi"])
    ts_x0_base = base_terrain_config.get("thrust_scale_x_lo", defaults["thrust_scale_x_lo"])
    ts_x1_base = base_terrain_config.get("thrust_scale_x_hi", defaults["thrust_scale_x_hi"])
    if ts_x0 != ts_x0_base or ts_x1 != ts_x1_base:
        ts_pattern = r"(- \*\*Thrust Scaling Zone\*\*: Between x=)([\d.]+) m and x=([\d.]+) m,"
        description = re.sub(
            ts_pattern,
            lambda m: f"{m.group(1)}{ts_x0:.1f} m and x={ts_x1:.1f} m (originally Between x={ts_x0_base:.1f} m and x={ts_x1_base:.1f} m in the source environment),",
            description
        )

    # Oscillating Force update
    of_x0 = target_terrain_config.get("oscillating_fx_x_lo", defaults["oscillating_fx_x_lo"])
    of_x1 = target_terrain_config.get("oscillating_fx_x_hi", defaults["oscillating_fx_x_hi"])
    of_x0_base = base_terrain_config.get("oscillating_fx_x_lo", defaults["oscillating_fx_x_lo"])
    of_x1_base = base_terrain_config.get("oscillating_fx_x_hi", defaults["oscillating_fx_x_hi"])
    if of_x0 != of_x0_base or of_x1 != of_x1_base:
        of_pattern = r"(- \*\*Oscillating Force Zone\*\*: Between x=)([\d.]+) m and x=([\d.]+) m,"
        description = re.sub(
            of_pattern,
            lambda m: f"{m.group(1)}{of_x0:.1f} m and x={of_x1:.1f} m (originally Between x={of_x0_base:.1f} m and x={of_x1_base:.1f} m in the source environment),",
            description
        )

    # Target update
    tx0 = target_terrain_config.get("target_x_min", defaults["target_x_min"])
    tx1 = target_terrain_config.get("target_x_max", defaults["target_x_max"])
    ty0 = target_terrain_config.get("target_y_min", defaults["target_y_min"])
    ty1 = target_terrain_config.get("target_y_max", defaults["target_y_max"])
    
    btx0_base = base_terrain_config.get("target_x_min", defaults["target_x_min"])
    btx1_base = base_terrain_config.get("target_x_max", defaults["target_x_max"])
    bty0_base = base_terrain_config.get("target_y_min", defaults["target_y_min"])
    bty1_base = base_terrain_config.get("target_y_max", defaults["target_y_max"])

    if tx0 != btx0_base or tx1 != btx1_base or ty0 != bty0_base or ty1 != bty1_base:
        target_pattern = r"(- \*\*Final target\*\*: Sled center must enter the zone x in \[)([\d.]+), ([\d.]+)(\] m, y in \[)([\d.]+), ([\d.]+)(\] m\.)"
        description = re.sub(
            target_pattern,
            lambda m: f"{m.group(1)}{tx0:.1f}, {tx1:.1f}] (originally [{btx0_base:.1f}, {btx1_base:.1f}] in the source environment){m.group(4)}{ty0:.1f}, {ty1:.1f}] (originally [{bty0_base:.1f}, {bty1_base:.1f}] in the source environment){m.group(7)}",
            description
        )

    return description


def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update success criteria for visible changes (Target Reach, Speed Limit)."""
    criteria = base_success_criteria
    
    # Target Defaults
    tx0_def, tx1_def = 28.0, 32.0
    ty0_def, ty1_def = 2.2, 2.8
    sp_thresh_def = 4.0
    sp_x0_def, sp_x1_def = 22.0, 26.0

    tx0 = target_terrain_config.get("target_x_min", tx0_def)
    tx1 = target_terrain_config.get("target_x_max", tx1_def)
    ty0 = target_terrain_config.get("target_y_min", ty0_def)
    ty1 = target_terrain_config.get("target_y_max", ty1_def)
    
    btx0_base = base_terrain_config.get("target_x_min", tx0_def)
    btx1_base = base_terrain_config.get("target_x_max", tx1_def)
    bty0_base = base_terrain_config.get("target_y_min", ty0_def)
    bty1_base = base_terrain_config.get("target_y_max", ty1_def)

    if tx0 != btx0_base or tx1 != btx1_base or ty0 != bty0_base or ty1 != bty1_base:
        target_pattern = r"(\*\*Target Reach\*\*: Sled center enters the final target zone \(x in \[)([\d.]+), ([\d.]+)(\], y in \[)([\d.]+), ([\d.]+)(\]\)\.)"
        criteria = re.sub(
            target_pattern,
            lambda m: f"{m.group(1)}{tx0:.1f}, {tx1:.1f}] (originally [{btx0_base:.1f}, {btx1_base:.1f}] in the source environment){m.group(4)}{ty0:.1f}, {ty1:.1f}] (originally [{bty0_base:.1f}, {bty1_base:.1f}] in the source environment){m.group(7)}",
            criteria
        )

    # Speed Limit Constraint update
    sp_thresh = target_terrain_config.get("speed_penalty_threshold", sp_thresh_def)
    sp_thresh_base = base_terrain_config.get("speed_penalty_threshold", sp_thresh_def)
    sp_x0 = target_terrain_config.get("speed_penalty_x_lo", sp_x0_def)
    sp_x1 = target_terrain_config.get("speed_penalty_x_hi", sp_x1_def)
    sp_x0_base = base_terrain_config.get("speed_penalty_x_lo", sp_x0_def)
    sp_x1_base = base_terrain_config.get("speed_penalty_x_hi", sp_x1_def)

    if sp_thresh != sp_thresh_base or sp_x0 != sp_x0_base or sp_x1 != sp_x1_base:
        sp_pattern = r"(- \*\*Speed Limit\*\*: Maintain speed below )([\d.]+) m/s while in the penalty zone \(x in \[)([\d.]+), ([\d.]+)(\]\) to avoid significant momentum loss\.)"
        criteria = re.sub(
            sp_pattern,
            lambda m: f"{m.group(1)}{sp_thresh:.1f} m/s (originally {sp_thresh_base:.1f} m/s in the source environment) while in the penalty zone (x in [{sp_x0:.1f}, {sp_x1:.1f}] (originally [{sp_x0_base:.1f}, {sp_x1_base:.1f}] in the source environment)){m.group(5)}",
            criteria
        )

    return criteria


def get_e03_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns ordered stage configs for E-03 variants.
    Each stage: terrain_config, physics_config, task_description_suffix (uniform warning;
    only invisible params are mutated, so no visible prompt updates).
    Stage-1/2: one physical parameter change each (hard enough so ref fails).
    Stage-3/4: multiple parameter changes (increasing difficulty).
    """
    return [
        {
            "stage_id": "Stage-1",
            "title": "Higher global friction",
            "mutation_description": "Ground and sled friction increased (0.02 -> 0.14). Momentum is lost faster; ref's fixed gains may not overcome drain zone in time.",
            "task_description_suffix": TASK_DESCRIPTION_SUFFIX,
            "terrain_config": {
                "ground_friction": 0.14,
                "sled_friction": 0.14,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-2",
            "title": "Stronger gravity",
            "mutation_description": "Gravity increased (0, -10) -> (0, -15). Vertical control harder; ref's gravity compensation and climb to checkpoint A may be insufficient.",
            "task_description_suffix": TASK_DESCRIPTION_SUFFIX,
            "terrain_config": {},
            "physics_config": {
                "gravity": (0, -15),
            },
        },
        {
            "stage_id": "Stage-3",
            "title": "Stronger drain + damping",
            "mutation_description": "Momentum drain factor 0.85 -> 0.70; linear_damping 0.5. Velocity decays faster; ref may not reach B or final target in time.",
            "task_description_suffix": TASK_DESCRIPTION_SUFFIX,
            "terrain_config": {},
            "physics_config": {
                "momentum_drain_factor": 0.70,
                "linear_damping": 0.5,
            },
        },
        {
            "stage_id": "Stage-4",
            "title": "Multi-parameter shift",
            "mutation_description": "Gravity (0,-18), friction 0.10, linear_damping 0.6, momentum_drain 0.68, thrust_scale_factor 0.38. Ref's fixed gains and 2x thrust compensation fail.",
            "task_description_suffix": TASK_DESCRIPTION_SUFFIX,
            "terrain_config": {
                "ground_friction": 0.10,
                "sled_friction": 0.10,
            },
            "physics_config": {
                "gravity": (0, -18),
                "linear_damping": 0.6,
                "momentum_drain_factor": 0.68,
                "thrust_scale_factor": 0.38,
            },
        },
    ]
