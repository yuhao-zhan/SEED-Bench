"""
C-06: The Governor task curriculum stages (mutations).

Mutation dimensions used here: measurement delay, torque deadzone, low-speed torque limit,
step-load timing, cogging/stiction strength, quadratic drag coefficient.

Each stage contains hidden `physics_config` overrides so the environment behavior changes
without revealing precise numeric values to the agent prompt (agents must infer from feedback).

UNIFORM_SUFFIX lists only the union of physics keys actually overridden across Stage-1..Stage-4
(disturb_period / disturb_torque / step_load_extra are not mutated in this curriculum).

IMPORTANT: `mutation_description` and `title` are for logs/orchestration only—do not inject
them into the agent-visible prompt (would leak mutation direction vs UNIFORM_SUFFIX tone).
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from tasks.Category5_Cybernetics_Control.C_06.environment import (
    DEFAULT_WHEEL_ANGULAR_DAMPING,
    DEFAULT_WHEEL_MASS_KG,
    DEFAULT_WHEEL_RADIUS_M,
    MEAN_SPEED_ERROR_THRESHOLD,
    MEASURE_DELAY_STEPS,
    REGULATION_START_STEP,
    STALL_SPEED_THRESHOLD,
    STALL_STEPS_THRESHOLD,
    STICTION_SPEED_BAND,
    TARGET_SPEED_RAD_S,
    TORQUE_DEADZONE,
    TORQUE_LIMIT_AT_ZERO,
)


def _c06_mutated_curriculum_union_suffix() -> str:
    """
    Bullets for every physics_config dimension mutated in at least one of Stage-1..Stage-4.
    No numeric values or directions; no variables that never change in this curriculum.
    """
    return """
## Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables **MIGHT** have changed from the initial environment, **NOT ALL** of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
- **Sensing latency (Velocity)**: Latency in the rotational speed measurements may occur.
- **Low-speed torque availability**: The maximum torque available at low rotational speeds may differ.
- **Sustained load onset**: The timing of additional load application may differ.
- **Actuator deadzones**: The range of control inputs that yield zero motor response may differ.
- **Rotational resistance**: Speed-dependent resisting torque (e.g. drag) may differ.
- **Mechanical resistance profile (cogging)**: Angle-dependent resisting torque may differ.
- **Static friction behavior (stiction)**: Low-speed resisting torque behavior may differ.

**Discovery via feedback**: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., how the system stalls or oscillates) to infer the hidden constraints and adapt your control design.
"""


def _c06_wheel_line(
    target_mass: float,
    base_mass: float,
    target_radius: float,
    base_radius: float,
    target_damping: float,
    base_damping: float,
) -> str:
    """Wheel bullet with [new] (originally [old] in the source environment) per changed dimension."""
    if abs(target_mass - base_mass) < 1e-9:
        mass_part = f"{target_mass:g} kg"
    else:
        mass_part = (
            f"{target_mass:g} kg (originally {base_mass:g} kg in the source environment)"
        )
    if abs(target_radius - base_radius) < 1e-9:
        rad_part = f"{target_radius:g} m"
    else:
        rad_part = (
            f"{target_radius:g} m (originally {base_radius:g} m in the source environment)"
        )
    if abs(target_damping - base_damping) < 1e-9:
        damping_part = f"{target_damping:g} simulator units"
    else:
        damping_part = (
            f"{target_damping:g} simulator units (originally {base_damping:g} simulator units in the source environment)"
        )
    return (
        f"- **Wheel**: Single circular body (mass {mass_part}, radius {rad_part}) "
        "rotating about a fixed vertical axis through its center (revolute joint to the environment). "
        f"The wheel body is subject to angular damping ({damping_part}; adds speed-proportional resistance). "
        "Additional resisting torques and dynamics may be present\u2014infer behavior from data rather than "
        "assuming a simple first-order plant."
    )


_WHEEL_BLOCK_PATTERN = (
    r"- \*\*Wheel\*\*: Single circular body \(mass .+? kg, radius .+? m\) "
    r"rotating about a fixed vertical axis through its center \(revolute joint to the environment\)\. "
    r"The wheel body is subject to angular damping \(.+? simulator units; adds speed-proportional resistance\)\. "
    r"Additional resisting torques and dynamics may be present\u2014infer behavior from data rather than "
    r"assuming a simple first-order plant\."
)


def _c06_apply_target_speed_line(description: str, tt: float, bt: float) -> str:
    if abs(tt - bt) < 1e-12:
        return description
    pat = (
        r"(Only the \*\*initial\*\* segment speed is stated here: )"
        r"(?:\d+\.?\d* rad/s(?: \(originally \d+\.?\d* rad/s in the source environment\))?)"
        r"([\u2014\-]later setpoints must be read from the API\.)"
    )

    def _repl(m):
        return (
            f"{m.group(1)}{tt:g} rad/s (originally {bt:g} rad/s in the source environment)"
            f"{m.group(2)}"
        )

    if not re.search(pat, description):
        return description
    return re.sub(pat, _repl, description, count=1)


def _c06_apply_regulation_start(description: str, tr: int, br: int) -> str:
    if tr == br:
        return description
    d = re.sub(
        r"A startup phase of \d+ steps(?: \(originally \d+ steps in the source environment\))? precedes",
        f"A startup phase of {tr} steps (originally {br} steps in the source environment) precedes",
        description,
        count=1,
    )
    d = re.sub(
        r"step index \u2265 \d+(?: \(originally \d+ in the source environment\))?(?= \(after startup\))",
        f"step index \u2265 {tr} (originally {br} in the source environment)",
        d,
        count=1,
    )
    return d


def update_task_description_for_visible_changes(
    base_description: str,
    target_terrain_config: Dict[str, Any],
    base_terrain_config: Dict[str, Any],
    target_physics_config: Optional[Dict[str, Any]] = None,
    base_physics_config: Optional[Dict[str, Any]] = None,
    *,
    stage: Optional[Dict[str, Any]] = None,
) -> str:
    """Sync wheel (mass, radius), target speed, regulation index, delay, torque, and deadzone."""
    target_terrain_config = dict(target_terrain_config or {})
    base_terrain_config = dict(base_terrain_config or {})
    tp = dict(target_physics_config or {})
    bp = dict(base_physics_config or {})
    if stage is not None:
        tp = {**tp, **(stage.get("physics_config") or {})}

    description = base_description

    # Wheel
    bm = float(base_terrain_config.get("wheel_mass", DEFAULT_WHEEL_MASS_KG))
    brad = float(base_terrain_config.get("wheel_radius", DEFAULT_WHEEL_RADIUS_M))
    bdamp = float(base_terrain_config.get("wheel_angular_damping", DEFAULT_WHEEL_ANGULAR_DAMPING))
    tm = float(target_terrain_config.get("wheel_mass", DEFAULT_WHEEL_MASS_KG))
    trad = float(target_terrain_config.get("wheel_radius", DEFAULT_WHEEL_RADIUS_M))
    tdamp = float(target_terrain_config.get("wheel_angular_damping", DEFAULT_WHEEL_ANGULAR_DAMPING))

    if abs(tm - bm) >= 1e-9 or abs(trad - brad) >= 1e-9 or abs(tdamp - bdamp) >= 1e-9:
        description = re.sub(_WHEEL_BLOCK_PATTERN, _c06_wheel_line(tm, bm, trad, brad, tdamp, bdamp), description, count=1, flags=re.DOTALL)

    # Targets
    bt = float(base_terrain_config.get("target_speed_rad_s", TARGET_SPEED_RAD_S))
    tt = float(target_terrain_config.get("target_speed_rad_s", TARGET_SPEED_RAD_S))
    description = _c06_apply_target_speed_line(description, tt, bt)

    brs = int(base_terrain_config.get("regulation_start_step", REGULATION_START_STEP))
    trs = int(target_terrain_config.get("regulation_start_step", REGULATION_START_STEP))
    description = _c06_apply_regulation_start(description, trs, brs)

    # Delay
    bd = int(base_physics_config.get("measure_delay_steps", MEASURE_DELAY_STEPS))
    td = int(tp.get("measure_delay_steps", MEASURE_DELAY_STEPS))
    if bd != td:
        description = re.sub(r"\*\*delayed\*\* by \d+ steps", f"**delayed** by {td} steps (originally {bd} steps in the source environment)", description)

    # Torque limit
    btl = float(base_physics_config.get("torque_limit_at_zero", TORQUE_LIMIT_AT_ZERO))
    ttl = float(tp.get("torque_limit_at_zero", TORQUE_LIMIT_AT_ZERO))
    if abs(btl - ttl) > 1e-9:
        description = re.sub(r"at rest, the limit is \d+\.?\d* N·m", f"at rest, the limit is {ttl:g} N·m (originally {btl:g} N·m in the source environment)", description)

    # Deadzone
    btd = float(base_physics_config.get("torque_deadzone", TORQUE_DEADZONE))
    ttd = float(tp.get("torque_deadzone", TORQUE_DEADZONE))
    if abs(btd - ttd) > 1e-9:
        description = re.sub(r"\*\*deadzone\*\* of \d+\.?\d* N·m", f"**deadzone** of {ttd:g} N·m (originally {btd:g} N·m in the source environment)", description)

    return description



def _c06_stall_success_line(ts: float, bs: float, tst: int, bst: int) -> str:
    sp = (
        f"{ts} rad/s"
        if abs(ts - bs) < 1e-12
        else f"{ts} rad/s (originally {bs} rad/s in the source environment)"
    )
    if tst == bst:
        step_clause = f"{tst} or more consecutive steps"
    else:
        step_clause = (
            f"{tst} or more consecutive steps (originally {bst} or more consecutive steps in the source environment)"
        )
    return (
        f"2. **No Stall**: From the start of the episode through the end, sustained **true** "
        f"instantaneous angular speed below {sp} for {step_clause} counts as failure."
    )


def update_success_criteria_for_visible_changes(
    base_success_criteria: str,
    target_terrain_config: Dict[str, Any],
    base_terrain_config: Dict[str, Any],
    target_physics_config: Optional[Dict[str, Any]] = None,
    base_physics_config: Optional[Dict[str, Any]] = None,
    *,
    stage: Optional[Dict[str, Any]] = None,
) -> str:
    """Sync mean-error and stall criteria when terrain_config overrides visible thresholds."""
    target_terrain_config = target_terrain_config or {}
    base_terrain_config = base_terrain_config or {}
    c = base_success_criteria

    bm = float(base_terrain_config.get("mean_speed_error_threshold", MEAN_SPEED_ERROR_THRESHOLD))
    tm = float(target_terrain_config.get("mean_speed_error_threshold", MEAN_SPEED_ERROR_THRESHOLD))
    if abs(tm - bm) > 1e-15:
        pat = (
            r"(1\. \*\*Speed Regulation\*\*: .*?must stay <= )"
            r"[\d.]+ rad/s(?: \(originally [\d.]+ rad/s in the source environment\))?\."
        )
        if re.search(pat, c, flags=re.DOTALL):
            rep = (
                f"\\g<1>{tm} rad/s (originally {bm} rad/s in the source environment)."
            )
            c = re.sub(pat, rep, c, count=1, flags=re.DOTALL)

    bs = float(base_terrain_config.get("stall_speed_threshold", STALL_SPEED_THRESHOLD))
    ts = float(target_terrain_config.get("stall_speed_threshold", STALL_SPEED_THRESHOLD))
    bst = int(base_terrain_config.get("stall_steps_threshold", STALL_STEPS_THRESHOLD))
    tst = int(target_terrain_config.get("stall_steps_threshold", STALL_STEPS_THRESHOLD))
    if abs(ts - bs) > 1e-12 or tst != bst:
        stall_pat = r"2\. \*\*No Stall\*\*:.*counts as failure\."
        if re.search(stall_pat, c, flags=re.DOTALL):
            c = re.sub(
                stall_pat,
                _c06_stall_success_line(ts, bs, tst, bst),
                c,
                count=1,
                flags=re.DOTALL,
            )

    return c


def get_c06_curriculum_stages() -> List[Dict[str, Any]]:
    """Returns ordered stage configs for C-06: The Governor task variants.

    Order: Stage-1..Stage-4 increasing difficulty.
    """
    task_description_suffix = _c06_mutated_curriculum_union_suffix()
    return [
        {
            "stage_id": "Stage-1",
            "title": "Curriculum variant 1",
            "mutation_description": "Curriculum Stage-1 physics overrides.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {},
            "physics_config": {
                "measure_delay_steps": 7,
            },
        },
        {
            "stage_id": "Stage-2",
            "title": "Curriculum variant 2",
            "mutation_description": "Curriculum Stage-2 physics overrides.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {},
            "physics_config": {
                "cogging_amplitude": 3.0,
            },
        },
        {
            "stage_id": "Stage-3",
            "title": "Curriculum variant 3",
            "mutation_description": "Curriculum Stage-3 physics overrides.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {},
            "physics_config": {
                "step_load_at_step": 3200,
                "torque_limit_at_zero": 3.0,
            },
        },
        {
            "stage_id": "Stage-4",
            "title": "Curriculum variant 4",
            "mutation_description": "Curriculum Stage-4 physics overrides.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {},
            "physics_config": {
                "measure_delay_steps": 6,
                "torque_deadzone": 2.5,
                # Slightly above break-even vs stiction×base load so standstill is not a deadlock
                "torque_limit_at_zero": 3.18,
                "k_drag": 0.6,
                "cogging_amplitude": 2.0,
                "stiction_factor": 1.5,
            },
        },
    ]
