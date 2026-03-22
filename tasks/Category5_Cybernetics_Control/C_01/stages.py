from __future__ import annotations

import math
import re
from typing import Any, Dict, List

# Baseline (source) values for C-01 prompt
_BASE_POLE_START_ANGLE = 0.0
_BASE_POLE_LENGTH = 2.0
_BASE_TRACK_CENTER_X = 10.0
_BASE_MAX_STEPS = 20000
_BASE_CART_MASS = 10.0
_BASE_POLE_MASS = 1.0
_BASE_SAFE_HALF_RANGE = 8.5
_BASE_SENSOR_DELAY_ANGLE_STEPS = 0
_BASE_SENSOR_DELAY_OMEGA_STEPS = 0


def _scalar_physics_differs(a: float, b: float) -> bool:
    """True if two physical scalars differ enough to require prompt sync (no coarse skip bands)."""
    return not math.isclose(float(a), float(b), rel_tol=1e-12, abs_tol=1e-9)


def update_task_description_for_visible_changes(
    base_description: str,
    target_terrain_config: Dict[str, Any],
    base_terrain_config: Dict[str, Any],
    target_physics_config: Dict[str, Any] = None,
    base_physics_config: Dict[str, Any] = None,
    *,
    stage: Dict[str, Any] = None,
) -> str:
    description = base_description
    base_physics_config = dict(base_physics_config or {})
    target_physics_config = target_physics_config or {}
    if stage is not None:
        target_physics_config = dict(stage.get("physics_config") or {})
    else:
        target_physics_config = dict(target_physics_config)

    target_track_center = target_physics_config.get("track_center_x", _BASE_TRACK_CENTER_X)
    target_max_steps = target_physics_config.get("max_steps", _BASE_MAX_STEPS)
    target_cart_mass = target_physics_config.get("cart_mass", _BASE_CART_MASS)
    target_pole_mass = target_physics_config.get("pole_mass", _BASE_POLE_MASS)
    target_safe_range = target_physics_config.get("safe_half_range", _BASE_SAFE_HALF_RANGE)
    target_pole_length = target_physics_config.get("pole_length", _BASE_POLE_LENGTH)
    target_pole_start_angle = target_physics_config.get("pole_start_angle", _BASE_POLE_START_ANGLE)
    target_sensor_delay_angle = int(target_physics_config.get("sensor_delay_angle_steps", _BASE_SENSOR_DELAY_ANGLE_STEPS))
    target_sensor_delay_omega = int(target_physics_config.get("sensor_delay_omega_steps", _BASE_SENSOR_DELAY_OMEGA_STEPS))

    display_base_center = float(base_physics_config.get("track_center_x", _BASE_TRACK_CENTER_X))
    display_base_steps = int(base_physics_config.get("max_steps", _BASE_MAX_STEPS))
    display_base_safe = float(base_physics_config.get("safe_half_range", _BASE_SAFE_HALF_RANGE))
    display_base_cart_mass = float(base_physics_config.get("cart_mass", _BASE_CART_MASS))
    display_base_pole_mass = float(base_physics_config.get("pole_mass", _BASE_POLE_MASS))
    display_base_pole_length = float(base_physics_config.get("pole_length", _BASE_POLE_LENGTH))
    display_base_pole_start_angle = float(base_physics_config.get("pole_start_angle", _BASE_POLE_START_ANGLE))
    display_base_sensor_delay_angle = int(base_physics_config.get("sensor_delay_angle_steps", _BASE_SENSOR_DELAY_ANGLE_STEPS))
    display_base_sensor_delay_omega = int(base_physics_config.get("sensor_delay_omega_steps", _BASE_SENSOR_DELAY_OMEGA_STEPS))

    # Track center (matches base or prior "(originally …)" mutation line)
    if _scalar_physics_differs(target_track_center, display_base_center):
        center_pat = re.compile(
            r"center x=\d+\.?\d*m(?: \(originally \d+\.?\d*m in the source environment\))?"
        )
        if center_pat.search(description):
            description = center_pat.sub(
                f"center x={target_track_center:.1f}m (originally {display_base_center:.1f}m in the source environment)",
                description,
                count=1,
            )
            
    # Safe Range (match pristine or already-mutated "safe range ±…" segment)
    if _scalar_physics_differs(target_safe_range, display_base_safe):
        safe_flex = re.compile(
            r"safe range ±\d+\.?\d*m inclusive(?: \(originally ±\d+\.?\d*m in the source environment\))?"
        )
        if safe_flex.search(description):
            description = safe_flex.sub(
                f"safe range ±{target_safe_range:.1f}m inclusive (originally ±{display_base_safe:.1f}m in the source environment)",
                description,
                count=1,
            )

    # Episode length
    if target_max_steps != display_base_steps:
        steps_pattern = rf"- \*\*Episode length\*\*: At most {display_base_steps} simulation steps"
        if re.search(steps_pattern, description):
            description = re.sub(
                steps_pattern,
                f"- **Episode length**: At most {target_max_steps} simulation steps (originally {display_base_steps} simulation steps in the source environment)",
                description,
            )
        else:
            steps_pattern_fallback = rf"At most {display_base_steps} simulation steps"
            description = re.sub(
                steps_pattern_fallback,
                f"At most {target_max_steps} simulation steps (originally {display_base_steps} simulation steps in the source environment)",
                description,
                count=1,
            )

    # Cart Mass (preserve "**Cart**: A body" capitalization)
    if _scalar_physics_differs(target_cart_mass, display_base_cart_mass):
        cart_pattern = re.compile(
            rf"(\*\*Cart\*\*: )[Aa] body of mass {display_base_cart_mass:g} kg"
        )
        if cart_pattern.search(description):

            def _cart_mass_repl(m: re.Match) -> str:
                return (
                    f"{m.group(1)}A body of mass {target_cart_mass:g} kg "
                    f"(originally {display_base_cart_mass:g} kg in the source environment)"
                )

            description = cart_pattern.sub(_cart_mass_repl, description, count=1)

    # Pole Mass
    if _scalar_physics_differs(target_pole_mass, display_base_pole_mass):
        pole_pattern = rf"\*\*Pole\*\*: Mass {display_base_pole_mass:g} kg"
        if re.search(pole_pattern, description):
            description = re.sub(
                pole_pattern,
                f"**Pole**: Mass {target_pole_mass:g} kg (originally {display_base_pole_mass:g} kg in the source environment)",
                description,
                count=1,
            )

    # Pole length (matches "**Length**: 2.0m." in base prompt)
    if _scalar_physics_differs(target_pole_length, display_base_pole_length):
        len_pattern = rf"\*\*Length\*\*: {display_base_pole_length:.1f}m\."
        if re.search(len_pattern, description):
            description = re.sub(
                len_pattern,
                f"**Length**: {target_pole_length:.1f}m (originally {display_base_pole_length:.1f}m in the source environment).",
                description,
                count=1,
            )

    # Initial pole angle: only automated sync from upright baseline (source angle = 0).
    if (
        abs(display_base_pole_start_angle) < 1e-5
        and abs(target_pole_start_angle - display_base_pole_start_angle) > 1e-5
    ):
        ang_deg = math.degrees(target_pole_start_angle)
        base_ang_pattern = r"Initially upright \(angle = 0° or 0rad\)\."
        replacement = (
            f"Initially at angle = {ang_deg:.1f}° ({target_pole_start_angle:.3f} rad) "
            f"(originally 0° / 0 rad in the source environment)."
        )
        if re.search(base_ang_pattern, description):
            description = re.sub(base_ang_pattern, replacement, description, count=1)

    # Sensor delay — angle (matches current value and optional prior mutation)
    if target_sensor_delay_angle != display_base_sensor_delay_angle:
        sd_ang_pat = re.compile(
            r"- \*\*Sensor reporting \(angle\)\*\*: (\d+) simulation steps of delay from true state"
            r"(?: \(originally \d+ simulation steps of delay in the source environment\))?\."
        )
        if sd_ang_pat.search(description):
            description = sd_ang_pat.sub(
                f"- **Sensor reporting (angle)**: {target_sensor_delay_angle} simulation steps of delay from true state "
                f"(originally {display_base_sensor_delay_angle} simulation steps of delay in the source environment).",
                description,
                count=1,
            )

    # Sensor delay — angular velocity
    if target_sensor_delay_omega != display_base_sensor_delay_omega:
        sd_om_pat = re.compile(
            r"- \*\*Sensor reporting \(angular velocity\)\*\*: (\d+) simulation steps of delay from true state"
            r"(?: \(originally \d+ simulation steps of delay in the source environment\))?\."
        )
        if sd_om_pat.search(description):
            description = sd_om_pat.sub(
                f"- **Sensor reporting (angular velocity)**: {target_sensor_delay_omega} simulation steps of delay from true state "
                f"(originally {display_base_sensor_delay_omega} simulation steps of delay in the source environment).",
                description,
                count=1,
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
    description = base_success_criteria
    base_physics_config = dict(base_physics_config or {})
    target_physics_config = target_physics_config or {}
    if stage is not None:
        target_physics_config = dict(stage.get("physics_config") or {})
    else:
        target_physics_config = dict(target_physics_config)

    target_max_steps = target_physics_config.get("max_steps", _BASE_MAX_STEPS)
    target_track_center = target_physics_config.get("track_center_x", _BASE_TRACK_CENTER_X)
    target_safe_range = target_physics_config.get("safe_half_range", _BASE_SAFE_HALF_RANGE)
    display_base_steps = int(base_physics_config.get("max_steps", _BASE_MAX_STEPS))
    display_base_center = float(base_physics_config.get("track_center_x", _BASE_TRACK_CENTER_X))
    display_base_safe = float(base_physics_config.get("safe_half_range", _BASE_SAFE_HALF_RANGE))

    # Episode length
    if target_max_steps != display_base_steps:
        steps_pattern = rf"At most {display_base_steps} steps"
        if re.search(steps_pattern, description):
            description = re.sub(
                steps_pattern,
                f"At most {target_max_steps} steps (originally {display_base_steps} steps in the source environment)",
                description,
                count=1,
            )

    # Track center in criteria (base or prior mutation)
    if _scalar_physics_differs(target_track_center, display_base_center):
        center_pat = re.compile(
            r"\|x - \d+\.?\d*\|(?: \(originally \|x - \d+\.?\d*\| in the source environment\))?"
        )
        if center_pat.search(description):
            description = center_pat.sub(
                f"|x - {target_track_center:.1f}| (originally |x - {display_base_center:.1f}| in the source environment)",
                description,
                count=1,
            )

    # Safe Range in criteria (pristine or already-mutated half-width clause)
    if _scalar_physics_differs(target_safe_range, display_base_safe):
        crit_safe = re.compile(
            r"≤ \d+\.?\d*m(?: \(originally ≤ \d+\.?\d*m in the source environment\))?"
        )
        if crit_safe.search(description):
            description = crit_safe.sub(
                f"≤ {target_safe_range:.1f}m (originally ≤ {display_base_safe:.1f}m in the source environment)",
                description,
                count=1,
            )

    return description


# Union of all physical variables modified across Stage-1–4:
# Variables: sensor_delay_angle_steps, sensor_delay_omega_steps, gravity, pole_mass, cart_mass, track_center_x, max_steps
UNIFORM_SUFFIX = """
## Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables MIGHT have changed from the initial environment, NOT ALL of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
 - Sensor delay: Latency in measurement acquisition may affect how reported state tracks the true dynamics.
 - Gravitational acceleration: Vertical loads may be significantly different, affecting the system's dynamic response.
 - Pole and Cart mass: The distribution of inertia within the assembly may be altered.
 - Track Center Position: The horizontal center of the safe balancing zone may have been relocated.
 - Episode length: The required duration of the stability task may be significantly different.

Discovery via feedback: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., cart position, pole angle trends, or loss of stability) to infer the hidden constraints and adapt your design.
"""


def curriculum_stages() -> List[Dict[str, Any]]:
    return [
        {
            "stage_id": "Stage-1",
            "title": "Curriculum stage 1",
            "task_description_suffix": UNIFORM_SUFFIX,
            "physics_config": {
                "track_center_x": 50.0,
                "max_steps": 1000,
            },
        },
        {
            "stage_id": "Stage-2",
            "title": "Curriculum stage 2",
            "task_description_suffix": UNIFORM_SUFFIX,
            "physics_config": {
                "track_center_x": 50.0,
                "gravity": 15.0,
                "max_steps": 1000,
            },
        },
        {
            "stage_id": "Stage-3",
            "title": "Curriculum stage 3",
            "task_description_suffix": UNIFORM_SUFFIX,
            "physics_config": {
                "track_center_x": 50.0,
                "sensor_delay_angle_steps": 2,
                "sensor_delay_omega_steps": 2,
                "max_steps": 1000,
            },
        },
        {
            "stage_id": "Stage-4",
            "title": "Curriculum stage 4",
            "task_description_suffix": UNIFORM_SUFFIX,
            "physics_config": {
                "track_center_x": 50.0,
                "pole_mass": 3.0,
                "cart_mass": 7.0,
                "max_steps": 1000,
            },
        },
    ]


def get_stages():
    curriculum = curriculum_stages()
    result = []
    for s in curriculum:
        pid = s["stage_id"]
        num = pid.split("-")[1]
        result.append({
            "name": pid,
            "description": s.get("title", pid),
            "build_fn": f"build_agent_stage_{num}",
            "action_fn": f"agent_action_stage_{num}",
            "config_overrides": s.get("physics_config", {}),
        })
    return result
