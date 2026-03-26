"""
D-02: The Jumper task curriculum stages (mutations).

Mutated tasks vary physical parameters: gravity, wind, damping, and slot geometry.
The solver is NOT told exact values; it must infer from feedback.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

# Source (base) slot dimensions used when base_terrain_config does not override
_DEFAULT_SLOT1_FLOOR, _DEFAULT_SLOT1_CEIL = 13.2, 14.7
_DEFAULT_SLOT2_FLOOR, _DEFAULT_SLOT2_CEIL = 11.3, 13.3
_DEFAULT_SLOT3_FLOOR, _DEFAULT_SLOT3_CEIL = 12.4, 14.2


def update_task_description_for_visible_changes(
    base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]
) -> str:
    """Update task description for visible changes using format: [new_value] (originally [old_value] in the source environment)."""
    description = base_description
    target = target_terrain_config or {}
    base = base_terrain_config or {}

    # 1. Left Platform End X
    t_lex = target.get("left_platform_end_x", 8.0)
    b_lex = base.get("left_platform_end_x", 8.0)
    if t_lex != b_lex:
        lex_pattern = r"(The left platform ends at x = )(\d+\.?\d*)( m)"
        description = re.sub(
            lex_pattern,
            lambda m: f"{m.group(1)}{t_lex:.1f} m (originally {b_lex:.1f} m in the source environment)",
            description,
        )

    # 1b. Right Platform extent
    t_pw = target.get("pit_width", 18.0)
    b_pw = base.get("pit_width", 18.0)
    t_rx = t_lex + t_pw
    b_rx = b_lex + b_pw
    t_rend = t_rx + 15.0
    b_rend = b_rx + 15.0
    if t_rx != b_rx:
        platform_pattern = r"(The right platform extends from x = )(\d+\.?\d*)( m to x = )(\d+\.?\d*)( m)"
        description = re.sub(
            platform_pattern,
            lambda m: f"{m.group(1)}{t_rx:.1f} m (originally {b_rx:.1f} m in the source environment) to x = {t_rend:.1f} m (originally {b_rend:.1f} m in the source environment)",
            description,
        )

    # 2. Jumper dimensions and mass
    t_dens = target.get("jumper_density", 50.0)
    b_dens = base.get("jumper_density", 50.0)
    t_w = target.get("jumper_width", 0.8)
    b_w = base.get("jumper_width", 0.8)
    t_h = target.get("jumper_height", 0.6)
    b_h = base.get("jumper_height", 0.6)
    t_mass = t_dens * t_w * t_h
    b_mass = b_dens * b_w * b_h
    
    if t_w != b_w or t_h != b_h:
        # Update width and height surgically
        dim_pattern = r"(jumper body has width )(\d+\.?\d*)( m, height )(\d+\.?\d*)( m)"
        def dim_repl(m):
            w_str = f"{t_w:.1f} m (originally {b_w:.1f} m in the source environment)" if t_w != b_w else f"{m.group(2)}{m.group(3)}"
            h_str = f"{t_h:.1f} m (originally {b_h:.1f} m in the source environment)" if t_h != b_h else f"{m.group(4)}{m.group(5)}"
            return f"{m.group(1)}{w_str}, height {h_str}"
        description = re.sub(dim_pattern, dim_repl, description)
    
    if t_mass != b_mass:
        # Update mass surgically
        mass_pattern = r"(\*\*mass )(\d+\.?\d*)( kg\*\*;)"
        description = re.sub(
            mass_pattern,
            lambda m: f"{m.group(1)}{t_mass:.1f} kg (originally {b_mass:.1f} kg in the source environment)**;",
            description,
        )
        
    # 3. Jumper center y clearance (derived from height and 0.05 m margin)
    t_clearance = t_h / 2.0 + 0.05
    b_clearance = b_h / 2.0 + 0.05
    if t_h != b_h:
        h_mention_pattern = r"(With jumper height )(\d+\.?\d*)( m,)"
        description = re.sub(
            h_mention_pattern,
            lambda m: f"{m.group(1)}{t_h:.1f} m (originally {b_h:.1f} m in the source environment),",
            description,
        )
    if t_clearance != b_clearance:
        clearance_pattern = r"(jumper center y must therefore lie in \[floor\+)(\d+\.?\d*)(, ceiling[−-]?)(\d+\.?\d*)(\] for that slot)"
        description = re.sub(
            clearance_pattern,
            lambda m: f"{m.group(1)}{t_clearance:.2f}{m.group(3)}{t_clearance:.2f}{m.group(5)} (originally [floor+{b_clearance:.2f}, ceiling−{b_clearance:.2f}] in the source environment)",
            description,
        )

    # 4. Jumper spawn position
    t_sx = target.get("jumper_spawn_x", 5.0)
    t_sy = target.get("jumper_spawn_y", 5.0)
    b_sx = base.get("jumper_spawn_x", 5.0)
    b_sy = base.get("jumper_spawn_y", 5.0)
    if (t_sx, t_sy) != (b_sx, b_sy):
        spawn_pattern = r"(starts at position )(\(\d+\.?\d*, \d+\.?\d*\) m \(center\))(\.)"
        description = re.sub(
            spawn_pattern,
            lambda m: f"{m.group(1)}({t_sx:.1f}, {t_sy:.1f}) m (center) (originally {m.group(2)} in the source environment){m.group(3)}",
            description,
        )

    # 5. Build Zone
    t_bx_min = target.get("build_zone_x_min", 1.5)
    t_bx_max = target.get("build_zone_x_max", 6.5)
    t_by_min = target.get("build_zone_y_min", 2.5)
    t_by_max = target.get("build_zone_y_max", 5.5)
    b_bx_min = base.get("build_zone_x_min", 1.5)
    b_bx_max = base.get("build_zone_x_max", 6.5)
    b_by_min = base.get("build_zone_y_min", 2.5)
    b_by_max = base.get("build_zone_y_max", 5.5)
    if (t_bx_min, t_bx_max, t_by_min, t_by_max) != (b_bx_min, b_bx_max, b_by_min, b_by_max):
        bz_pattern = r"(\*\*Build Zone\*\*: x in \[)(\d+\.?\d*), (\d+\.?\d*)(\] m, y in \[)(\d+\.?\d*), (\d+\.?\d*)(\] m)"
        def bz_repl(m):
            x_str = f"[{t_bx_min:.1f}, {t_bx_max:.1f}] m (originally [{b_bx_min:.1f}, {b_bx_max:.1f}] m in the source environment)" if (t_bx_min, t_bx_max) != (b_bx_min, b_bx_max) else f"[{m.group(2)}, {m.group(3)}] m"
            y_str = f"[{t_by_min:.1f}, {t_by_max:.1f}] m (originally [{b_by_min:.1f}, {b_by_max:.1f}] m in the source environment)" if (t_by_min, t_by_max) != (b_by_min, b_by_max) else f"[{m.group(5)}, {m.group(6)}] m"
            return f"**Build Zone**: x in {x_str}, y in {y_str}"
        description = re.sub(bz_pattern, bz_repl, description)

    # 6. Right platform (Goal x)
    t_pw = target.get("pit_width", 18.0)
    b_pw = base.get("pit_width", 18.0)
    t_rx = t_lex + t_pw
    b_rx = b_lex + b_pw
    if t_rx != b_rx:
        goal_x_pattern = r"(x >= )(\d+\.?\d*)( m)"
        description = re.sub(
            goal_x_pattern,
            lambda m: f"{m.group(1)}{t_rx:.1f} m (originally {b_rx:.1f} m in the source environment)",
            description,
        )

    # 7. Pit failure threshold (y >= 0 m)
    t_pfy = target.get("pit_bottom_y", 0.0)
    b_pfy = base.get("pit_bottom_y", 0.0)
    if t_pfy != b_pfy:
        pfy_pattern = r"(Jumper center must remain at y [≥>=] )(\d+\.?\d*)( m; below y = )(\d+\.?\d*)( m is considered in the pit)"
        description = re.sub(
            pfy_pattern,
            lambda m: f"{m.group(1)}{t_pfy:.1f} m (originally {b_pfy:.1f} m in the source environment); below y = {t_pfy:.1f} m (originally {b_pfy:.1f} m in the source environment) is considered in the pit",
            description,
        )

    # 8. Barrier Intro approximate X
    # Match the specific sentence to avoid over-replacing.
    intro_sent_pattern = r"(positioned in the pit at approximately .*?\.)"
    def intro_sent_repl(m_sent):
        sentence = m_sent.group(1)
        for s_idx, s_num in enumerate([1, 3, 2]): # Match prompt order: 1, 3, 2
            t_sx = target.get(f"slot{s_num}_x", [17.0, 21.0, 19.0][s_num-1])
            b_sx = base.get(f"slot{s_num}_x", [17.0, 21.0, 19.0][s_num-1])
            if t_sx != b_sx:
                # Use word boundaries around the number to be safe.
                # Regex matches 'x ≈ 17' and replaces '17'
                sentence = re.sub(
                    rf"(x ≈ ){b_sx:g}(\b)",
                    f"\\g<1>{t_sx:.1f} (originally {b_sx:.1f} in the source environment)\\g<2>",
                    sentence
                )
        return sentence
    description = re.sub(intro_sent_pattern, intro_sent_repl, description)

    # 9. Slot X-Ranges
    for s_num in [1, 2, 3]:
        t_sx = target.get(f"slot{s_num}_x", [17.0, 21.0, 19.0][s_num-1])
        b_sx = base.get(f"slot{s_num}_x", [17.0, 21.0, 19.0][s_num-1])
        if t_sx != b_sx:
            t_min, t_max = t_sx - 0.5, t_sx + 0.5
            b_min, b_max = b_sx - 0.5, b_sx + 0.5
            sx_pattern = rf"(\*\*Slot {s_num}\*\* x in \[)(\d+\.?\d*), (\d+\.?\d*)(\] m)"
            description = re.sub(
                sx_pattern,
                lambda m: f"{m.group(1)}{t_min:.1f}, {t_max:.1f}] m (originally [{b_min:.1f}, {b_max:.1f}] m in the source environment)",
                description,
            )

    # 10. Slot Y-Ranges (Floor/Ceil) and their internal X-mentions
    t_s_dims = {
        1: (target.get("slot1_floor", _DEFAULT_SLOT1_FLOOR), target.get("slot1_ceil", _DEFAULT_SLOT1_CEIL), target.get("slot1_x", 17.0)),
        2: (target.get("slot2_floor", _DEFAULT_SLOT2_FLOOR), target.get("slot2_ceil", _DEFAULT_SLOT2_CEIL), target.get("slot2_x", 21.0)),
        3: (target.get("slot3_floor", _DEFAULT_SLOT3_FLOOR), target.get("slot3_ceil", _DEFAULT_SLOT3_CEIL), target.get("slot3_x", 19.0)),
    }
    b_s_dims = {
        1: (base.get("slot1_floor", _DEFAULT_SLOT1_FLOOR), base.get("slot1_ceil", _DEFAULT_SLOT1_CEIL), base.get("slot1_x", 17.0)),
        2: (base.get("slot2_floor", _DEFAULT_SLOT2_FLOOR), base.get("slot2_ceil", _DEFAULT_SLOT2_CEIL), base.get("slot2_x", 21.0)),
        3: (base.get("slot3_floor", _DEFAULT_SLOT3_FLOOR), base.get("slot3_ceil", _DEFAULT_SLOT3_CEIL), base.get("slot3_x", 19.0)),
    }

    for s_num in [1, 3, 2]:
        t_f, t_c, t_x = t_s_dims[s_num]
        b_f, b_c, b_x = b_s_dims[s_num]

        # Pattern matches: **Slot 1** (x ≈ 17 m): y in [13.2, 14.7]
        # We use a non-greedy .*? and don't hardcode the X value to be robust.
        slot_pattern = rf"(\*\*Slot {s_num}\*\* \(x ≈ )(\d+\.?\d*)( m\): y in )\[(\d+\.?\d*), (\d+\.?\d*)\]"

        def slot_repl(m):
            res = m.group(1)
            # Update X if changed
            if t_x != b_x:
                res += f"{t_x:.1f} m (originally {b_x:.1f} m in the source environment)): y in "
            else:
                res += f"{m.group(2)}{m.group(3)}"

            # Update Y if changed
            if (t_f, t_c) != (b_f, b_c):
                res += f"[{t_f:.1f}, {t_c:.1f}] (originally [{b_f:.1f}, {b_c:.1f}] in the source environment)"
            else:
                res += f"[{m.group(4)}, {m.group(5)}]"
            return res

        description = re.sub(slot_pattern, slot_repl, description)

    return description


def update_success_criteria_for_visible_changes(
    base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]
) -> str:
    """Update success criteria for visible changes (Mass budget, Target X, Target Y, Pit Safety)."""
    description = base_success_criteria
    target = target_terrain_config or {}
    base = base_terrain_config or {}

    # 1. Mass Budget
    t_mass_max = target.get("max_structure_mass", 180.0)
    b_mass_max = base.get("max_structure_mass", 180.0)
    if t_mass_max != b_mass_max:
        mass_max_pattern = r"(Total structure mass < )(\d+\.?\d*)( kg)"
        description = re.sub(
            mass_max_pattern,
            lambda m: f"Total structure mass < {t_mass_max:.1f} kg (originally {b_mass_max:.1f} kg in the source environment)",
            description,
        )

    # 2. Target Reach
    t_lex = target.get("left_platform_end_x", 8.0)
    t_pw = target.get("pit_width", 18.0)
    b_lex = base.get("left_platform_end_x", 8.0)
    b_pw = base.get("pit_width", 18.0)
    t_rx = t_lex + t_pw
    b_rx = b_lex + b_pw
    t_ry = target.get("landing_min_y", 1.0)
    b_ry = base.get("landing_min_y", 1.0)
    if t_rx != b_rx or t_ry != b_ry:
        target_reach_pattern = r"\(x >= (\d+\.?\d*) m, y >= (\d+\.?\d*) m\)"
        def target_repl(m):
            x_part = f"x >= {t_rx:.1f} m (originally {b_rx:.1f} m in the source environment)" if t_rx != b_rx else f"x >= {m.group(1)} m"
            y_part = f"y >= {t_ry:.1f} m (originally {b_ry:.1f} m in the source environment)" if t_ry != b_ry else f"y >= {m.group(2)} m"
            return f"({x_part}, {y_part})"
        description = re.sub(target_reach_pattern, target_repl, description)

    # 3. Pit Safety (y >= 0 m)
    t_pfy = target.get("pit_bottom_y", 0.0)
    b_pfy = base.get("pit_bottom_y", 0.0)
    if t_pfy != b_pfy:
        pit_safety_pattern = r"(Jumper center y must be [≥>=] )(\d+\.?\d*)( m \(below )(\d+\.?\d*)( m = failure\))"
        description = re.sub(
            pit_safety_pattern,
            lambda m: f"{m.group(1)}{t_pfy:.1f} m (originally {b_pfy:.1f} m in the source environment) (below {t_pfy:.1f} m (originally {b_pfy:.1f} m in the source environment) = failure)",
            description,
        )

    return description



_D02_SUFFIX = """
## Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables **MIGHT** have changed from the initial environment, **NOT ALL** of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
- **Gravitational Flux**: Variations in the gravitational constant may drastically alter the parabolic trajectory and time-of-flight, requiring recalibration of launch force.
- **Atmospheric Currents**: Significant horizontal or vertical wind vectors may exert continuous forces, causing the jumper to drift or alter momentum.
- **Viscous Air Resistance**: Changes in atmospheric damping can alter velocity retention, affecting the effective jump range.
- **Structural Shifts**: The elevation and configuration of barrier slots may have shifted, invalidating trajectories that were previously optimal.

**Discovery via feedback**: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., how the jumper moves or where the trajectory fails) to infer the hidden constraints and adapt your design.
"""


def get_d02_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Return ordered stage configs for D-02 mutated tasks (difficulty ascending).
    Stage-1/2: single physical parameter change (innovation).
    Stage-3/4: multiple parameter changes with conflicting constraints.
    """
    return [
        {
            "stage_id": "Stage-1",
            "title": "Viscous Void",
            "mutation_description": "The atmospheric properties have shifted; the jumper's velocity retention and aerodynamic behavior are now governed by non-standard damping constants.",
            "task_description_suffix": _D02_SUFFIX,
            "terrain_config": {},
            "physics_config": {
                "linear_damping": 2.0,
            },
        },
        {
            "stage_id": "Stage-2",
            "title": "Abyssal Descent",
            "mutation_description": "Seismic activity has drastically lowered the elevation of all barrier slots; a precisely controlled, low-altitude trajectory is now required.",
            "task_description_suffix": _D02_SUFFIX,
            "terrain_config": {
                "slot1_floor": 8.0,
                "slot1_ceil": 9.5,
                "slot3_floor": 7.5,
                "slot3_ceil": 9.0,
                "slot2_floor": 7.0,
                "slot2_ceil": 8.5,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-3",
            "title": "Gale-Force Gravity",
            "mutation_description": "The environment now exhibits anomalous gravitational and atmospheric current conditions, significantly altering the required impulse and trajectory apex.",
            "task_description_suffix": _D02_SUFFIX,
            "terrain_config": {},
            "physics_config": {
                "gravity": (0, -35.0),
                "wind": (-20.0, 0),
            },
        },
        {
            "stage_id": "Stage-4",
            "title": "The Perfect Storm",
            "mutation_description": "A complex interaction of gravitational flux, atmospheric currents, and air resistance creates a multifaceted challenge for trajectory clearance.",
            "task_description_suffix": _D02_SUFFIX,
            "terrain_config": {},
            "physics_config": {
                "gravity": (0, -30.0),
                "wind": (-15.0, 0),
                "linear_damping": 1.0,
            },
        },
    ]
