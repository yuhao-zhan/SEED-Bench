"""
D-06: The Catch curriculum stages (mutations).

Stage-1: single-variable structural threshold — peak joint reaction limit sits in a narrow band below the
         baseline lattice’s impact spikes so the reference lattice survives but the sparse baseline shatters.
Stage-2: cropped +x build footprint (unchanged curriculum slot).
Stage-3: multi-axis storm (density, joints, speeds, cadence, gravity pulse).
Stage-4: Stage-3 hazards plus higher ball restitution, lower self-damping, and stronger structural wind.
"""
from __future__ import annotations

from typing import Any, Dict, List

import re

# Defaults aligned with `environment.Sandbox` / `TASK_PROMPT` baseline.
_DEFAULT_DENSITY = 95.0
_LAUNCH_KEYS = (
    ("second_ball_launch_time", 0.4),
    ("third_ball_launch_time", 1.0),
    ("fourth_ball_launch_time", 1.3),
    ("fifth_ball_launch_time", 1.8),
    ("sixth_ball_launch_time", 2.2),
    ("seventh_ball_launch_time", 2.7),
)
_VEL_KEYS = (
    ("ball_velocity_x", -24.0),
    ("ball2_velocity_x", -26.0),
    ("ball3_velocity_x", -24.0),
    ("ball4_velocity_x", -28.0),
    ("ball5_velocity_x", -25.0),
    ("ball6_velocity_x", -26.0),
    ("ball7_velocity_x", -25.0),
)


def _merge_terrain(
    base_terrain_config: Dict[str, Any], target_terrain_config: Dict[str, Any]
) -> Dict[str, Any]:
    merged = dict(base_terrain_config or {})
    merged.update(target_terrain_config or {})
    return merged


def _fmt_time_val(v: float) -> str:
    """Keep exact configured timing precision while avoiding trailing zeros."""
    return f"{float(v):g}"


def _launch_schedule_sentence(tc: Dict[str, Any]) -> str:
    parts = []
    for i, (key, dflt) in enumerate(_LAUNCH_KEYS, start=2):
        v = float(tc.get(key, dflt))
        parts.append(f"ball {i} at t={_fmt_time_val(v)} s")
    return ", ".join(parts)


def _speed_list_sentence(tc: Dict[str, Any]) -> str:
    bits = []
    for i, (key, dflt) in enumerate(_VEL_KEYS, start=1):
        v = float(tc.get(key, dflt))
        if abs(v - round(v)) < 1e-9:
            bits.append(f"ball{i}={int(round(v))}")
        else:
            bits.append(f"ball{i}={v:g}")
    return ", ".join(bits)


def update_task_description_for_visible_changes(
    base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]
) -> str:
    """Patch strings that appear in task_description when terrain_config mutates visible fields."""
    description = base_description
    base_tc = base_terrain_config or {}
    target_tc = target_terrain_config or {}
    base_m = _merge_terrain(base_tc, {})
    tgt_m = _merge_terrain(base_tc, target_tc)

    bx0 = float(base_tc.get("build_zone_x_min", 7.0))
    bx1 = float(base_tc.get("build_zone_x_max", 11.0))
    by0 = float(base_tc.get("build_zone_y_min", 0.5))
    by1 = float(base_tc.get("build_zone_y_max", 5.5))
    tx0 = float(target_tc.get("build_zone_x_min", bx0))
    tx1 = float(target_tc.get("build_zone_x_max", bx1))
    ty0 = float(target_tc.get("build_zone_y_min", by0))
    ty1 = float(target_tc.get("build_zone_y_max", by1))
    if (tx0, tx1, ty0, ty1) != (bx0, bx1, by0, by1):
        pattern = (
            r"(\*\*Build Zone\*\*: )x=\[[\d\.]+, [\d\.]+\] m, y=\[[\d\.]+, [\d\.]+\] m(\.)"
        )
        repl = (
            f"\\1x=[{tx0}, {tx1}] m, y=[{ty0}, {ty1}] m "
            f"(originally x=[{bx0}, {bx1}] m, y=[{by0}, {by1}] m in the source environment)\\2"
        )
        if re.search(pattern, description):
            description = re.sub(pattern, repl, description)

        obj_pat = (
            r"2\. Keeps all balls within the target zone \(x=\[[\d\.]+, [\d\.]+\], y=\[[\d\.]+, [\d\.]+\]\) "
            r"with a final speed < 0\.35 m/s\."
        )
        obj_new = (
            f"2. Keeps all balls within the target zone (x=[{tx0}, {tx1}], y=[{ty0}, {ty1}]) "
            f"(originally x=[{bx0}, {bx1}], y=[{by0}, {by1}] in the source environment) "
            f"with a final speed < 0.35 m/s."
        )
        if re.search(obj_pat, description):
            description = re.sub(obj_pat, obj_new, description)

    sched_new = _launch_schedule_sentence(tgt_m)
    sched_old = _launch_schedule_sentence(base_m)
    if sched_new != sched_old:
        sched_pat = (
            r"(receive horizontal velocity at the listed times \(simulation time in seconds after reset\): )"
            r"(ball 2 at t=[\d.]+ s, ball 3 at t=[\d.]+ s, ball 4 at t=[\d.]+ s, ball 5 at t=[\d.]+ s, "
            r"ball 6 at t=[\d.]+ s, ball 7 at t=[\d.]+ s)(\.)"
        )
        if re.search(sched_pat, description):
            description = re.sub(
                sched_pat,
                rf"\1[{sched_new}] (originally [{sched_old}] in the source environment)\3",
                description,
            )

    spd_new = _speed_list_sentence(tgt_m)
    spd_old = _speed_list_sentence(base_m)
    if spd_new != spd_old:
        spd_pat = (
            r"(Nominal horizontal speeds at release \(m/s\) are )"
            r"(ball1=-?\d+(?:\.\d+)?, ball2=-?\d+(?:\.\d+)?, ball3=-?\d+(?:\.\d+)?, "
            r"ball4=-?\d+(?:\.\d+)?, ball5=-?\d+(?:\.\d+)?, ball6=-?\d+(?:\.\d+)?, "
            r"ball7=-?\d+(?:\.\d+)?)(\.)"
        )
        if re.search(spd_pat, description):
            description = re.sub(
                spd_pat,
                rf"\1[{spd_new}] (originally [{spd_old}] in the source environment)\3",
                description,
            )

    base_d = float(base_tc.get("ball_density", _DEFAULT_DENSITY))
    target_d = float(target_tc.get("ball_density", base_d))
    if target_d != base_d:
        dens_pat = (
            r"(- \*\*Projectile inertia\*\*: Nominal ball density is )(\d+\.?\d*)"
            r"( \(2D areal density in simulation units\)\.)"
        )
        if re.search(dens_pat, description):
            description = re.sub(
                dens_pat,
                (
                    f"\\g<1>[{target_d:.1f}] (originally [{base_d:.1f}] in the source environment)"
                    f" (2D areal density in simulation units)."
                ),
                description,
            )

    return description


def update_success_criteria_for_visible_changes(
    base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]
) -> str:
    criteria = base_success_criteria

    default_mass = 10.0
    target_mass = target_terrain_config.get("max_structure_mass", default_mass)
    base_mass = base_terrain_config.get("max_structure_mass", default_mass)
    if target_mass != base_mass:
        pattern = (
            r"(- \*\*Mass Budget\*\*: Total structure mass must be strictly less than )(\d+\.?\d*)( kg\.)"
        )
        if re.search(pattern, criteria):
            criteria = re.sub(
                pattern,
                f"\\g<1>[{target_mass:.1f}] kg (originally [{base_mass:.1f}] kg in the source environment).",
                criteria,
            )

    default_beams = 9
    target_beams = target_terrain_config.get("max_beam_count", default_beams)
    base_beams = base_terrain_config.get("max_beam_count", default_beams)
    if target_beams != base_beams:
        pattern = r"(- \*\*Beam Limit\*\*: Maximum )(\d+)( beams\.)"
        if re.search(pattern, criteria):
            criteria = re.sub(
                pattern,
                f"\\g<1>[{target_beams}] beams (originally [{base_beams}] beams in the source environment).",
                criteria,
            )

    default_joint_force = 880.0
    target_joint = target_terrain_config.get("max_joint_force", default_joint_force)
    base_joint = base_terrain_config.get("max_joint_force", default_joint_force)
    if target_joint != base_joint:
        pattern = (
            r"(- \*\*Joint force limit\*\*: In any single simulation step, joints fail if the reaction force "
            r"magnitude reaches or exceeds )(\d+\.?\d*)( N \(peak failure\)\.)"
        )
        if re.search(pattern, criteria):
            criteria = re.sub(
                pattern,
                f"\\g<1>[{target_joint:.0f}] N (originally [{base_joint:.0f}] N in the source environment) (peak failure).",
                criteria,
            )

    default_fatigue = 760.0
    target_fatigue = target_terrain_config.get("joint_fatigue_threshold", default_fatigue)
    base_fatigue = base_terrain_config.get("joint_fatigue_threshold", default_fatigue)
    if target_fatigue != base_fatigue:
        pattern = (
            r"(Additionally, if the reaction force magnitude is strictly greater than )(\d+\.?\d*)"
            r"( N for two consecutive simulation steps, the joint fails \(fatigue\)\.)"
        )
        if re.search(pattern, criteria):
            criteria = re.sub(
                pattern,
                f"\\g<1>[{target_fatigue:.0f}] N (originally [{base_fatigue:.0f}] N in the source environment)"
                f" for two consecutive simulation steps, the joint fails (fatigue).",
                criteria,
            )

    return criteria


# Union of physical knobs touched across Stage-1 … Stage-4 in this file (no per-stage disclosure).
UNIFORM_SUFFIX = """
## Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables **MIGHT** have changed from the initial environment, **NOT ALL** of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
 - **Legal build footprint**: The axis-aligned region where beam centers may be placed may differ along x (and potentially y) relative to the source specification.
 - **Structural stress limits**: Peak joint reaction and sustained-load (fatigue) breakage thresholds may differ from the source nominal values, affecting how impacts snap welds or accumulate damage across steps.
 - **Projectile inertia**: Ball density may differ from the source nominal value, affecting momentum and internal loads for the same approach speeds.
 - **Inbound speeds and launch program**: Per-ball horizontal speeds at release and the staggered launch schedule may differ from the source nominal program, affecting the sequential stabilization window.
 - **Projectile damping and bounce**: Projectile linear damping, angular damping, and restitution may differ, affecting how quickly energy decays and whether secondary rebounds eject balls from pockets.
 - **Gravity bias and vertical modulation**: Effective weight may differ and/or a periodic vertical component of gravity may modulate slam timing and structural loading.
 - **Lateral gusts and structural coupling**: Oscillating side forces may act on the projectiles; in some regimes similar forcing may also load the catcher’s moving mass, compounding joint torque with catch dynamics.

**Discovery via feedback**: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., where a joint breaks or how a body moves) to infer the hidden constraints and adapt your design.
"""


def get_d06_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Ordered stage configs. Baseline reference (build_agent) must fail every stage;
    stage-specific references must pass their own stage.
    """
    return [
        {
            "stage_id": "Stage-1",
            "title": "Instantaneous weld rupture margin (peak joint only)",
            "mutation_description": "Curriculum variant: adjusted structural stress envelope (evaluation metadata only).",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "max_joint_force": 218.0,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-2",
            "title": "Cropped build corridor",
            "mutation_description": "Curriculum variant: tighter legal build footprint along x (evaluation metadata only).",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "build_zone_x_max": 10.38,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-3",
            "title": "Pulsed gravity + heavy storm",
            "mutation_description": "Curriculum variant: combined projectile, timing, and load anomalies (evaluation metadata only).",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "ball_density": 232.0,
                "max_joint_force": 300.0,
                "joint_fatigue_threshold": 225.0,
                "ball_velocity_x": -36.0,
                "ball2_velocity_x": -38.0,
                "ball3_velocity_x": -36.0,
                "ball4_velocity_x": -40.0,
                "ball5_velocity_x": -37.0,
                "ball6_velocity_x": -38.0,
                "ball7_velocity_x": -37.0,
                "second_ball_launch_time": 0.26,
                "third_ball_launch_time": 0.58,
                "fourth_ball_launch_time": 0.88,
                "fifth_ball_launch_time": 1.18,
                "sixth_ball_launch_time": 1.48,
                "seventh_ball_launch_time": 1.78,
                "gravity_pulse_amplitude": 3.5,
                "gravity_pulse_period": 1.0,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-4",
            "title": "Stage-3 storm + bouncy balls, lighter self-damping, stronger structural gusts",
            "mutation_description": "Curriculum variant: Stage-3-class hazards plus additional projectile and coupling stressors (evaluation metadata only).",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "ball_density": 232.0,
                "max_joint_force": 300.0,
                "joint_fatigue_threshold": 225.0,
                "ball_velocity_x": -36.0,
                "ball2_velocity_x": -38.0,
                "ball3_velocity_x": -36.0,
                "ball4_velocity_x": -40.0,
                "ball5_velocity_x": -37.0,
                "ball6_velocity_x": -38.0,
                "ball7_velocity_x": -37.0,
                "second_ball_launch_time": 0.26,
                "third_ball_launch_time": 0.58,
                "fourth_ball_launch_time": 0.88,
                "fifth_ball_launch_time": 1.18,
                "sixth_ball_launch_time": 1.48,
                "seventh_ball_launch_time": 1.78,
                "gravity_pulse_amplitude": 3.5,
                "gravity_pulse_period": 1.0,
                "wind_on_structure": True,
                "structure_wind_scale": 0.178,
                "wind_amplitude": 9.0,
                "ball_restitution": 0.24,
                "ball_linear_damping": 0.52,
            },
            "physics_config": {},
        },
    ]
