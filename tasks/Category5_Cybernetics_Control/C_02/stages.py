"""
C-02: The Lander task curriculum stages (mutations).

Visible parameters that differ from the source environment (spawn, lander
mass/size, ground reference/length, corridor, platform size, thrust/torque caps,
delay, fuel totals, success thresholds) are updated in the prompt via
update_*_for_visible_changes.

Invisible parameters (gravity profile over time, wind/gust magnitudes,
contact/damping/friction details, gravity-after magnitudes) stay out of the base
TASK_PROMPT body; the curriculum suffix may name categories only.
mutation_description is for logs/orchestration only and must NOT be shown to the agent.
"""

from __future__ import annotations

import importlib.util
import os
import re
import math
import warnings
from typing import Any, Dict, List, Optional

# Load this task's environment by path. A bare `from environment import ...` breaks when
# C_01 runs first in the same process: sys.modules['environment'] is C_01's module.
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "environment.py")
_env_spec = importlib.util.spec_from_file_location(
    "davinci_category5_c02_environment_stages_only",
    _env_path,
)
_env_mod = importlib.util.module_from_spec(_env_spec)
assert _env_spec.loader is not None
_env_spec.loader.exec_module(_env_mod)
DEFAULT_BARRIER_X_LEFT = _env_mod.BARRIER_X_LEFT
DEFAULT_BARRIER_X_RIGHT = _env_mod.BARRIER_X_RIGHT
DEFAULT_BARRIER_Y_BOTTOM = _env_mod.BARRIER_Y_BOTTOM
DEFAULT_BARRIER_Y_TOP = _env_mod.BARRIER_Y_TOP
# Default |angle| limit at landing from environment.py (radians), not the Stage-2 curriculum override.
ENV_DEFAULT_MAX_LANDING_ANGLE_RAD = _env_mod.MAX_LANDING_ANGLE
DEFAULT_MAX_SAFE_VERTICAL_SPEED = _env_mod.MAX_SAFE_VERTICAL_SPEED
DEFAULT_MAX_THRUST = _env_mod.MAX_THRUST
DEFAULT_MAX_TORQUE = _env_mod.MAX_TORQUE
DEFAULT_MIN_FUEL_REMAINING_AT_LANDING = _env_mod.MIN_FUEL_REMAINING_AT_LANDING
DEFAULT_PLATFORM_AMPLITUDE = _env_mod.PLATFORM_AMPLITUDE
DEFAULT_PLATFORM_CENTER_BASE = _env_mod.PLATFORM_CENTER_BASE
DEFAULT_PLATFORM_HALF_WIDTH = _env_mod.PLATFORM_HALF_WIDTH
DEFAULT_PLATFORM_PERIOD = _env_mod.PLATFORM_PERIOD
DEFAULT_SPAWN_X = _env_mod.SPAWN_X
DEFAULT_SPAWN_Y = _env_mod.SPAWN_Y
DEFAULT_THRUST_DELAY_STEPS = _env_mod.THRUST_DELAY_STEPS
DEFAULT_TOTAL_FUEL_IMPULSE = _env_mod.TOTAL_FUEL_IMPULSE
DEFAULT_MAX_EPISODE_STEPS = _env_mod.MAX_EPISODE_STEPS
DEFAULT_TIME_STEP = _env_mod.DEFAULT_TIME_STEP
DEFAULT_TIME_STEP_LABEL = _env_mod.DEFAULT_TIME_STEP_LABEL
DEFAULT_LAND_TOLERANCE = _env_mod.LAND_TOLERANCE
DEFAULT_LANDER_MASS = _env_mod.LANDER_MASS
DEFAULT_LANDER_HALF_WIDTH = _env_mod.LANDER_HALF_WIDTH
DEFAULT_LANDER_HALF_HEIGHT = _env_mod.LANDER_HALF_HEIGHT
DEFAULT_GROUND_Y_TOP = _env_mod.GROUND_Y_TOP
DEFAULT_GROUND_LENGTH = _env_mod.GROUND_LENGTH
DEFAULT_GROUND_SLAB_HEIGHT = _env_mod.GROUND_SLAB_HEIGHT
CURRICULUM_STAGE2_MAX_LANDING_ANGLE_RAD = _env_mod.CURRICULUM_STAGE2_MAX_LANDING_ANGLE_RAD
del _env_path, _env_spec, _env_mod

# Numeric token as rendered in TASK_PROMPT (includes scientific notation, e.g. 1e+05)
_PROMPT_SCALAR = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
# Prior prompt annotations from an earlier mutation pass (any wording ending with this suffix)
_ORIG_ANY = r"(?: \(originally .+? in the source environment\))?"


def _format_time_step_for_prompt(seconds: float) -> str:
    """Human-readable Δt for prompt lines (prefer simple fractions when exact)."""
    common = ((1, 60), (1, 30), (1, 120), (1, 100), (1, 50))
    for num, den in common:
        if abs(seconds - num / float(den)) < 1e-9:
            return f"{num}/{den}"
    if abs(seconds - DEFAULT_TIME_STEP) < 1e-9:
        return DEFAULT_TIME_STEP_LABEL
    return f"{seconds:g}"


def _config_float(
    physics: Dict[str, Any],
    terrain: Dict[str, Any],
    key: str,
    default: float,
) -> float:
    """Match Sandbox: physics_config overrides, then terrain_config, then default."""
    if key in physics and physics[key] is not None:
        return float(physics[key])
    if key in terrain and terrain[key] is not None:
        return float(terrain[key])
    return float(default)


def update_task_description_for_visible_changes(
    base_description: str,
    target_terrain_config: Dict[str, Any],
    base_terrain_config: Dict[str, Any],
    target_physics_config: Dict[str, Any] = None,
    base_physics_config: Dict[str, Any] = None,
    *,
    stage: Optional[Dict[str, Any]] = None,
) -> str:
    description = base_description
    target_terrain_config = dict(target_terrain_config or {})
    base_terrain_config = dict(base_terrain_config or {})
    if stage is not None:
        target_terrain_config = {
            **(stage.get("terrain_config") or {}),
            **target_terrain_config,
        }
    target_physics_config = dict(target_physics_config or {})
    base_physics_config = dict(base_physics_config or {})
    if stage is not None:
        sp = stage.get("physics_config") or {}
        target_physics_config = {**sp, **target_physics_config}

    target_sx = float(target_terrain_config.get("spawn_x", DEFAULT_SPAWN_X))
    base_sx = float(base_terrain_config.get("spawn_x", DEFAULT_SPAWN_X))
    target_sy = float(target_terrain_config.get("spawn_y", DEFAULT_SPAWN_Y))
    base_sy = float(base_terrain_config.get("spawn_y", DEFAULT_SPAWN_Y))
    if target_sx != base_sx or target_sy != base_sy:
        # Per-axis: `x=T m (originally B m in the source environment)` only when that axis changes.
        _spawn_orig_m = rf"(?: \(originally {_PROMPT_SCALAR} m in the source environment\))?"
        p_spawn = (
            rf"(Starting position \(spawn x=)({_PROMPT_SCALAR})( m){_spawn_orig_m}(\s*,\s*y=)({_PROMPT_SCALAR})( m){_spawn_orig_m}(\)\.)"
        )
        if re.search(p_spawn, description):

            def _spawn_repl(m: re.Match) -> str:
                ox = (
                    f" (originally {base_sx:.1f} m in the source environment)"
                    if abs(target_sx - base_sx) > 1e-9
                    else ""
                )
                oy = (
                    f" (originally {base_sy:.1f} m in the source environment)"
                    if abs(target_sy - base_sy) > 1e-9
                    else ""
                )
                return (
                    f"{m.group(1)}{target_sx:.1f}{m.group(3)}{ox}{m.group(4)}"
                    f"{target_sy:.1f}{m.group(6)}{oy}{m.group(7)}"
                )

            description = re.sub(p_spawn, _spawn_repl, description)
        else:
            warnings.warn(
                "C_02 stages: spawn coordinates changed but Starting position regex did not match; "
                "task_description left unchanged.",
                RuntimeWarning,
                stacklevel=2,
            )

    target_mass = float(target_terrain_config.get("lander_mass", DEFAULT_LANDER_MASS))
    base_mass = float(base_terrain_config.get("lander_mass", DEFAULT_LANDER_MASS))
    if target_mass != base_mass:
        p_mass = (
            rf"(\*\*Lander\*\*: Mass )({_PROMPT_SCALAR}) kg"
            rf"(?: \(originally {_PROMPT_SCALAR} kg in the source environment\))?"
            rf"(, rectangular hull )"
        )
        if re.search(p_mass, description):
            description = re.sub(
                p_mass,
                lambda m: (
                    f"{m.group(1)}{target_mass:.0f} kg (originally {base_mass:.0f} kg in the source environment)"
                    f"{m.group(3)}"
                ),
                description,
            )
        else:
            warnings.warn(
                "C_02 stages: lander_mass changed but Lander mass regex did not match; "
                "task_description left unchanged.",
                RuntimeWarning,
                stacklevel=2,
            )

    target_lhw = float(target_terrain_config.get("lander_half_width", DEFAULT_LANDER_HALF_WIDTH))
    base_lhw = float(base_terrain_config.get("lander_half_width", DEFAULT_LANDER_HALF_WIDTH))
    target_lhh = float(target_terrain_config.get("lander_half_height", DEFAULT_LANDER_HALF_HEIGHT))
    base_lhh = float(base_terrain_config.get("lander_half_height", DEFAULT_LANDER_HALF_HEIGHT))
    if target_lhw != base_lhw or target_lhh != base_lhh:
        target_fw, target_fh = 2.0 * target_lhw, 2.0 * target_lhh
        base_fw, base_fh = 2.0 * base_lhw, 2.0 * base_lhh

        def _hull_m_seg(target: float, base: float) -> str:
            if abs(target - base) > 1e-9:
                return (
                    f"{target:.1f} m (originally {base:.1f} m in the source environment)"
                )
            return f"{target:.1f} m"

        p_hull = re.compile(
            r"(rectangular hull ).+?( Starting position \(spawn x=)",
        )
        if p_hull.search(description):
            core = (
                f"{_hull_m_seg(target_fw, base_fw)} × {_hull_m_seg(target_fh, base_fh)} "
                f"(half-width {_hull_m_seg(target_lhw, base_lhw)}, "
                f"half-height {_hull_m_seg(target_lhh, base_lhh)})"
            )
            description = p_hull.sub(
                lambda m: f"{m.group(1)}{core}{m.group(2)}",
                description,
                count=1,
            )
        else:
            warnings.warn(
                "C_02 stages: lander half-dims changed but hull anchor regex did not match; "
                "task_description left unchanged.",
                RuntimeWarning,
                stacklevel=2,
            )

    target_gy = float(target_terrain_config.get("ground_y_top", DEFAULT_GROUND_Y_TOP))
    base_gy = float(base_terrain_config.get("ground_y_top", DEFAULT_GROUND_Y_TOP))
    target_glen = float(target_terrain_config.get("ground_length", DEFAULT_GROUND_LENGTH))
    base_glen = float(base_terrain_config.get("ground_length", DEFAULT_GROUND_LENGTH))
    target_gslab = float(
        target_terrain_config.get("ground_slab_height", DEFAULT_GROUND_SLAB_HEIGHT)
    )
    base_gslab = float(
        base_terrain_config.get("ground_slab_height", DEFAULT_GROUND_SLAB_HEIGHT)
    )
    if target_gy != base_gy or target_glen != base_glen or target_gslab != base_gslab:
        p_ground = (
            r"(\*\*Ground\*\*: The landing surface \(ground and platform\) is at y=)"
            rf"({_PROMPT_SCALAR})( m)(?: \(originally {_PROMPT_SCALAR} m in the source environment\))?"
            r"(; the static ground fixture extends downward from that plane by )"
            rf"({_PROMPT_SCALAR})( m \(slab thickness\)\.)(?: \(originally {_PROMPT_SCALAR} m in the source environment\))?"
            r"( The terrain extends horizontally over roughly )"
            rf"({_PROMPT_SCALAR})( m)(?: \(originally {_PROMPT_SCALAR} m in the source environment\))?"
            r"(\. Touchdown is detected when the craft's lowest point is within )"
        )
        if re.search(p_ground, description):

            def _ground_repl(m: re.Match) -> str:
                y_o = (
                    f" (originally {base_gy:.1f} m in the source environment)"
                    if abs(target_gy - base_gy) > 1e-9
                    else ""
                )
                slab_o = (
                    f" (originally {base_gslab:.1f} m in the source environment)"
                    if abs(target_gslab - base_gslab) > 1e-9
                    else ""
                )
                len_o = (
                    f" (originally {base_glen:.0f} m in the source environment)"
                    if abs(target_glen - base_glen) > 1e-9
                    else ""
                )
                return (
                    f"{m.group(1)}{target_gy:.1f}{m.group(3)}{y_o}{m.group(4)}"
                    f"{target_gslab:.1f}{m.group(6)}{slab_o}{m.group(7)}"
                    f"{target_glen:.0f}{m.group(9)}{len_o}{m.group(10)}"
                )

            description = re.sub(p_ground, _ground_repl, description)
        else:
            warnings.warn(
                "C_02 stages: ground_y_top, ground_slab_height, or ground_length changed but Ground "
                "regex did not match; task_description left unchanged.",
                RuntimeWarning,
                stacklevel=2,
            )

    target_bl = _config_float(
        target_physics_config,
        target_terrain_config,
        "barrier_x_left",
        DEFAULT_BARRIER_X_LEFT,
    )
    base_bl = _config_float(
        base_physics_config,
        base_terrain_config,
        "barrier_x_left",
        DEFAULT_BARRIER_X_LEFT,
    )
    target_br = _config_float(
        target_physics_config,
        target_terrain_config,
        "barrier_x_right",
        DEFAULT_BARRIER_X_RIGHT,
    )
    base_br = _config_float(
        base_physics_config,
        base_terrain_config,
        "barrier_x_right",
        DEFAULT_BARRIER_X_RIGHT,
    )
    if target_bl != base_bl or target_br != base_br:
        # Interval form: `[L, R] m (originally [L0, R0] m in the source environment).`
        p_bx = (
            r"(A vertical corridor at x in \[)([^\]]+)(\]\s*m)"
            r"(?: \(originally \[[^\]]+\] m in the source environment\))?"
            r"(\.| \(left endpoint originally .+? m in the source environment, right endpoint originally .+? m in the source environment\)\.)"
        )
        if re.search(p_bx, description):
            new_interior = f"{target_bl:.1f}, {target_br:.1f}"
            orig = (
                f" (originally [{base_bl:.1f}, {base_br:.1f}] m in the source environment)"
            )
            description = re.sub(
                p_bx,
                lambda m: f"{m.group(1)}{new_interior}{m.group(3)}{orig}.",
                description,
            )
        else:
            warnings.warn(
                "C_02 stages: barrier x-range changed but corridor regex did not match; "
                "task_description left unchanged.",
                RuntimeWarning,
                stacklevel=2,
            )

    target_barrier_bottom = _config_float(
        target_physics_config,
        target_terrain_config,
        "barrier_y_bottom",
        DEFAULT_BARRIER_Y_BOTTOM,
    )
    base_barrier_bottom = _config_float(
        base_physics_config,
        base_terrain_config,
        "barrier_y_bottom",
        DEFAULT_BARRIER_Y_BOTTOM,
    )
    target_barrier_top = _config_float(
        target_physics_config,
        target_terrain_config,
        "barrier_y_top",
        DEFAULT_BARRIER_Y_TOP,
    )
    base_barrier_top = _config_float(
        base_physics_config,
        base_terrain_config,
        "barrier_y_top",
        DEFAULT_BARRIER_Y_TOP,
    )

    if target_barrier_top != base_barrier_top:
        p_lower = (
            rf"(The lower bound is y=)({_PROMPT_SCALAR})(\s*m)"
            rf"(?: \(originally {_PROMPT_SCALAR} m in the source environment\))?"
            rf"(\s*\(ground-based obstacle top\);)"
        )
        if re.search(p_lower, description):
            description = re.sub(
                p_lower,
                lambda m: (
                    f"{m.group(1)}{target_barrier_top:.1f}{m.group(3)} "
                    f"(originally {base_barrier_top:.1f} m in the source environment)"
                    f"{m.group(4)}"
                ),
                description,
            )
        else:
            warnings.warn(
                "C_02 stages: barrier_y_top changed but lower-bound regex did not match; "
                "task_description left unchanged.",
                RuntimeWarning,
                stacklevel=2,
            )

    if target_barrier_bottom != base_barrier_bottom:
        p_upper = (
            rf"(the upper bound is y=)({_PROMPT_SCALAR})(\s*m)"
            rf"(?: \(originally {_PROMPT_SCALAR} m in the source environment\))?"
            rf"(\s*\(ceiling\) within that x band\.)"
        )
        if re.search(p_upper, description):
            description = re.sub(
                p_upper,
                lambda m: (
                    f"{m.group(1)}{target_barrier_bottom:.1f}{m.group(3)} "
                    f"(originally {base_barrier_bottom:.1f} m in the source environment)"
                    f"{m.group(4)}"
                ),
                description,
            )
        else:
            warnings.warn(
                "C_02 stages: barrier_y_bottom changed but upper-bound regex did not match; "
                "task_description left unchanged.",
                RuntimeWarning,
                stacklevel=2,
            )

    target_pc = float(
        target_physics_config.get("platform_center_base", DEFAULT_PLATFORM_CENTER_BASE)
    )
    base_pc = float(
        base_physics_config.get("platform_center_base", DEFAULT_PLATFORM_CENTER_BASE)
    )
    target_pa = float(
        target_physics_config.get("platform_amplitude", DEFAULT_PLATFORM_AMPLITUDE)
    )
    base_pa = float(
        base_physics_config.get("platform_amplitude", DEFAULT_PLATFORM_AMPLITUDE)
    )
    target_pp = float(
        target_physics_config.get("platform_period", DEFAULT_PLATFORM_PERIOD)
    )
    base_pp = float(base_physics_config.get("platform_period", DEFAULT_PLATFORM_PERIOD))

    def _plat_seg(t: float, b: float, unit: str) -> str:
        if abs(t - b) < 1e-9:
            return f"{t:.1f}{unit}"
        return f"{t:.1f}{unit} (originally {b:.1f}{unit} in the source environment)"

    if target_pc != base_pc or target_pa != base_pa or target_pp != base_pp:
        p_plat = re.compile(
            r"(Its center oscillates around x=.*?)(?=\s*The valid landing area is)",
            re.DOTALL,
        )
        if p_plat.search(description):
            new_plat = (
                f"Its center oscillates around x={_plat_seg(target_pc, base_pc, ' m')} "
                f"with an amplitude of {_plat_seg(target_pa, base_pa, ' m')} "
                f"and a period of {_plat_seg(target_pp, base_pp, ' s')}."
            )
            description = p_plat.sub(new_plat, description, count=1)
        else:
            warnings.warn(
                "C_02 stages: platform motion parameters changed but platform paragraph regex did not match; "
                "task_description left unchanged.",
                RuntimeWarning,
                stacklevel=2,
            )

    target_hw = target_physics_config.get(
        "platform_half_width", DEFAULT_PLATFORM_HALF_WIDTH
    )
    base_hw = base_physics_config.get(
        "platform_half_width", DEFAULT_PLATFORM_HALF_WIDTH
    )
    if target_hw != base_hw:
        target_width = 2.0 * target_hw
        base_width = 2.0 * base_hw
        # Flat form: `W m total (center ± h m) (originally W0 m total (center ± h0 m) in the source environment) and ...`
        pattern = (
            rf"(The valid landing area is )({_PROMPT_SCALAR})( m total \(center ± )({_PROMPT_SCALAR})( m\))"
            rf"(?: \(originally {_PROMPT_SCALAR} m total \(center ± {_PROMPT_SCALAR} m\) in the source environment\))?"
            rf"( and its position depends on the time of landing\.)"
        )
        if re.search(pattern, description):
            description = re.sub(
                pattern,
                lambda m: (
                    f"{m.group(1)}{target_width:.1f}{m.group(3)}{target_hw:.1f}{m.group(5)} "
                    f"(originally {base_width:.1f} m total (center ± {base_hw:.1f} m) in the source environment)"
                    f"{m.group(6)}"
                ),
                description,
            )
        else:
            warnings.warn(
                "C_02 stages: platform_half_width changed but landing-area width regex did not match; "
                "task_description left unchanged.",
                RuntimeWarning,
                stacklevel=2,
            )

    target_fuel = target_physics_config.get(
        "total_fuel_impulse", DEFAULT_TOTAL_FUEL_IMPULSE
    )
    base_fuel = base_physics_config.get(
        "total_fuel_impulse", DEFAULT_TOTAL_FUEL_IMPULSE
    )
    if target_fuel != base_fuel:
        def _fmt_ns(v: float) -> str:
            v = float(v)
            return str(int(v)) if abs(v - round(v)) < 1e-9 else f"{v:g}"
        pattern = (
            rf"(Total fuel impulse is )({_PROMPT_SCALAR})"
            rf"( N·s){_ORIG_ANY}(\.)"
        )
        if re.search(pattern, description):
            description = re.sub(
                pattern,
                lambda m: (
                    f"{m.group(1)}{_fmt_ns(target_fuel)}{m.group(3)} "
                    f"(originally {_fmt_ns(base_fuel)} N·s in the source environment)"
                    f"{m.group(4)}"
                ),
                description,
            )
        else:
            warnings.warn(
                "C_02 stages: total_fuel_impulse changed but fuel regex did not match; "
                "task_description left unchanged.",
                RuntimeWarning,
                stacklevel=2,
            )

    target_max_thrust = target_physics_config.get("max_thrust", DEFAULT_MAX_THRUST)
    base_max_thrust = base_physics_config.get("max_thrust", DEFAULT_MAX_THRUST)
    if target_max_thrust != base_max_thrust:
        # Must match prompt.py: "... axis (world +y when upright; max {MAX_THRUST:g} N); steering ..."
        pattern = (
            rf"(\(world \+y when upright; max )({_PROMPT_SCALAR})"
            rf"( N){_ORIG_ANY}(\);)"
        )
        if re.search(pattern, description):
            description = re.sub(
                pattern,
                lambda m: (
                    f"{m.group(1)}{target_max_thrust:g}{m.group(3)} "
                    f"(originally {base_max_thrust:g} N in the source environment)"
                    f"{m.group(4)}"
                ),
                description,
            )
        else:
            warnings.warn(
                "C_02 stages: max_thrust changed but thrust regex did not match; "
                "task_description left unchanged.",
                RuntimeWarning,
                stacklevel=2,
            )

    target_max_torque = target_physics_config.get("max_torque", DEFAULT_MAX_TORQUE)
    base_max_torque = base_physics_config.get("max_torque", DEFAULT_MAX_TORQUE)
    if target_max_torque != base_max_torque:
        pattern = (
            rf"(steering thrusters provide torque \(max )({_PROMPT_SCALAR})"
            rf"( N·m){_ORIG_ANY}(\)\.)"
        )
        if re.search(pattern, description):
            description = re.sub(
                pattern,
                lambda m: (
                    f"{m.group(1)}{target_max_torque:g}{m.group(3)} "
                    f"(originally {base_max_torque:g} N·m in the source environment)"
                    f"{m.group(4)}"
                ),
                description,
            )
        else:
            warnings.warn(
                "C_02 stages: max_torque changed but torque regex did not match; "
                "task_description left unchanged.",
                RuntimeWarning,
                stacklevel=2,
            )

    target_delay = int(
        target_physics_config.get("thrust_delay_steps", DEFAULT_THRUST_DELAY_STEPS)
    )
    base_delay = int(
        base_physics_config.get("thrust_delay_steps", DEFAULT_THRUST_DELAY_STEPS)
    )
    if target_delay != base_delay:
        p_delay = (
            r"(\*\*Control Latency\*\*: Pipeline delay is \*\*)(\d+)"
            r"(\*\* simulation steps)"
            r"(?: \(originally (?:\*\*)?\d+(?:\*\*)? simulation steps in the source environment\))?"
            r"( between issuing thrust/steering commands and their physical effect \(fixed\)\.)"
        )
        if re.search(p_delay, description):
            description = re.sub(
                p_delay,
                lambda m: (
                    f"{m.group(1)}{target_delay}{m.group(3)} "
                    f"(originally {base_delay} simulation steps in the source environment)"
                    f"{m.group(4)}"
                ),
                description,
            )
        else:
            warnings.warn(
                "C_02 stages: thrust_delay_steps changed but Pipeline delay prompt line did not match; "
                "description left unchanged.",
                RuntimeWarning,
                stacklevel=2,
            )

    target_steps = int(
        target_physics_config.get("max_episode_steps", DEFAULT_MAX_EPISODE_STEPS)
    )
    base_steps = int(
        base_physics_config.get("max_episode_steps", DEFAULT_MAX_EPISODE_STEPS)
    )
    if target_steps != base_steps:
        # Prompt uses "**{N} simulation steps**" (one bold span), not "**{N}** simulation steps**"
        p_eps = (
            r"(Each evaluation run is limited to \*\*)(\d+)( simulation steps\*\*)"
            r"(?: \(originally \*\*\d+\*\* simulation steps in the source environment\))?"
            r"(?: \(originally \d+ simulation steps in the source environment\))?"
        )
        if re.search(p_eps, description):
            description = re.sub(
                p_eps,
                lambda m: (
                    f"{m.group(1)}{target_steps}{m.group(3)} "
                    f"(originally {base_steps} simulation steps in the source environment)"
                ),
                description,
            )
        else:
            warnings.warn(
                "C_02 stages: max_episode_steps changed but episode-limit regex did not match; "
                "task_description left unchanged.",
                RuntimeWarning,
                stacklevel=2,
            )

    target_ts = float(target_physics_config.get("time_step", DEFAULT_TIME_STEP))
    base_ts = float(base_physics_config.get("time_step", DEFAULT_TIME_STEP))
    if abs(target_ts - base_ts) > 1e-12:
        p_ts = (
            r"(Fixed time step )(.+?)( s per step\.)"
            r"(?: \(originally .+? in the source environment\))?"
        )
        if re.search(p_ts, description):
            nl = _format_time_step_for_prompt(target_ts)
            ol = _format_time_step_for_prompt(base_ts)
            description = re.sub(
                p_ts,
                lambda m: (
                    f"{m.group(1)}{nl}{m.group(3)} "
                    f"(originally {ol} in the source environment)"
                ),
                description,
                count=1,
            )
        else:
            warnings.warn(
                "C_02 stages: time_step changed but fixed-timestep regex did not match; "
                "task_description left unchanged.",
                RuntimeWarning,
                stacklevel=2,
            )

    target_lt = float(target_physics_config.get("land_tolerance", DEFAULT_LAND_TOLERANCE))
    base_lt = float(base_physics_config.get("land_tolerance", DEFAULT_LAND_TOLERANCE))
    if abs(target_lt - base_lt) > 1e-12:

        def _fmt_lt(x: float) -> str:
            return f"{int(round(x))}" if abs(x - round(x)) < 1e-9 else f"{x:g}"

        p_lt = (
            rf"(Touchdown is detected when the craft's lowest point is within )({_PROMPT_SCALAR})( m of the ground surface\.)"
            + _ORIG_ANY
        )
        if re.search(p_lt, description):
            t_s, b_s = _fmt_lt(target_lt), _fmt_lt(base_lt)
            description = re.sub(
                p_lt,
                lambda m: (
                    f"{m.group(1)}{t_s}{m.group(3)} "
                    f"(originally {b_s} m in the source environment)"
                ),
                description,
            )
        else:
            warnings.warn(
                "C_02 stages: land_tolerance changed but touchdown-tolerance regex did not match; "
                "task_description left unchanged.",
                RuntimeWarning,
                stacklevel=2,
            )
    return description


def update_success_criteria_for_visible_changes(
    base_success_criteria: str,
    target_terrain_config: Dict[str, Any],
    base_terrain_config: Dict[str, Any],
    target_physics_config: Dict[str, Any] = None,
    base_physics_config: Dict[str, Any] = None,
    *,
    stage: Optional[Dict[str, Any]] = None,
) -> str:
    criteria = base_success_criteria
    target_terrain_config = dict(target_terrain_config or {})
    base_terrain_config = dict(base_terrain_config or {})
    if stage is not None:
        target_terrain_config = {
            **(stage.get("terrain_config") or {}),
            **target_terrain_config,
        }
    target_physics_config = dict(target_physics_config or {})
    base_physics_config = dict(base_physics_config or {})
    if stage is not None:
        sp = stage.get("physics_config") or {}
        target_physics_config = {**sp, **target_physics_config}

    target_vy = target_terrain_config.get(
        "max_safe_vertical_speed", DEFAULT_MAX_SAFE_VERTICAL_SPEED
    )
    base_vy = base_terrain_config.get(
        "max_safe_vertical_speed", DEFAULT_MAX_SAFE_VERTICAL_SPEED
    )
    if target_vy != base_vy:
        pattern = (
            r"(1\. \*\*Soft Landing\*\*: At touchdown, vertical speed magnitude must satisfy \|\s*vy\s*\|\s*<=\s*"
            rf")({_PROMPT_SCALAR})(\s*m/s)"
            + _ORIG_ANY
            + r"(\. Measurement uses world-frame vertical velocity \(\+y upward; evaluator uses \|vy\| at first ground contact\)\.)"
        )
        if re.search(pattern, criteria):
            criteria = re.sub(
                pattern,
                lambda m: (
                    f"{m.group(1)}{target_vy:.2f}{m.group(3)} "
                    f"(originally {base_vy:.2f} m/s in the source environment)"
                    f"{m.group(4)}"
                ),
                criteria,
            )
        else:
            warnings.warn(
                "C_02 stages: max_safe_vertical_speed changed but Soft Landing regex did not match; "
                "success_criteria left unchanged.",
                RuntimeWarning,
                stacklevel=2,
            )

    target_angle_rad = target_terrain_config.get(
        "max_landing_angle", ENV_DEFAULT_MAX_LANDING_ANGLE_RAD
    )
    base_angle_rad = base_terrain_config.get(
        "max_landing_angle", ENV_DEFAULT_MAX_LANDING_ANGLE_RAD
    )
    if target_angle_rad != base_angle_rad:
        target_angle_deg = math.degrees(target_angle_rad)
        base_angle_deg = math.degrees(base_angle_rad)
        pattern = (
            r"(Land with the craft within the stated angular limit \(\|\s*angle\s*\|\s*<=\s*)"
            rf"({_PROMPT_SCALAR})(\s*degrees)"
            + _ORIG_ANY
            + r"(\)\.)"
        )
        if re.search(pattern, criteria):
            criteria = re.sub(
                pattern,
                lambda m: (
                    f"{m.group(1)}{target_angle_deg:.2f}{m.group(3)} "
                    f"(originally {base_angle_deg:.2f} degrees in the source environment)"
                    f"{m.group(4)}"
                ),
                criteria,
            )
        else:
            warnings.warn(
                "C_02 stages: max_landing_angle changed but upright-orientation regex did not match; "
                "success_criteria left unchanged.",
                RuntimeWarning,
                stacklevel=2,
            )

    target_min_fuel = target_physics_config.get(
        "min_fuel_remaining_at_landing", DEFAULT_MIN_FUEL_REMAINING_AT_LANDING
    )
    base_min_fuel = base_physics_config.get(
        "min_fuel_remaining_at_landing", DEFAULT_MIN_FUEL_REMAINING_AT_LANDING
    )
    if target_min_fuel != base_min_fuel:
        def _fmt_min(v: float) -> str:
            v = float(v)
            return str(int(v)) if abs(v - round(v)) < 1e-9 else f"{v:g}"
        pattern = (
            rf"(Land with at least )({_PROMPT_SCALAR})( N·s)"
            + _ORIG_ANY
            + r"( of impulse budget remaining\.)"
        )
        if re.search(pattern, criteria):
            criteria = re.sub(
                pattern,
                lambda m: (
                    f"{m.group(1)}{_fmt_min(target_min_fuel)}{m.group(3)} "
                    f"(originally {_fmt_min(base_min_fuel)} N·s in the source environment)"
                    f"{m.group(4)}"
                ),
                criteria,
            )
        else:
            warnings.warn(
                "C_02 stages: min_fuel_remaining_at_landing changed but efficiency regex did not match; "
                "success_criteria left unchanged.",
                RuntimeWarning,
                stacklevel=2,
            )

    target_hw = target_physics_config.get(
        "platform_half_width", DEFAULT_PLATFORM_HALF_WIDTH
    )
    base_hw = base_physics_config.get(
        "platform_half_width", DEFAULT_PLATFORM_HALF_WIDTH
    )
    if target_hw != base_hw:
        tw = 2.0 * target_hw
        bw = 2.0 * base_hw
        pattern = (
            r"(3\. \*\*Accuracy\*\*: At touchdown, the craft's entire ground-contact width must lie within the valid landing platform: \*\*)"
            rf"({_PROMPT_SCALAR})( m total \(center ± )({_PROMPT_SCALAR})( m\))"
            rf"(?: \(originally {_PROMPT_SCALAR} m total \(center ± {_PROMPT_SCALAR} m\) in the source environment\))?"
            rf"(\*\*)"
            + r"( at the instant of landing \(zone position at that time; not only the center x\)\.)"
        )
        if re.search(pattern, criteria):
            criteria = re.sub(
                pattern,
                lambda m: (
                    f"{m.group(1)}{tw:.1f}{m.group(3)}{target_hw:.1f}{m.group(5)} "
                    f"(originally {bw:.1f} m total (center ± {base_hw:.1f} m) in the source environment)"
                    f"{m.group(6)}{m.group(7)}"
                ),
                criteria,
            )
        else:
            warnings.warn(
                "C_02 stages: platform_half_width changed but Accuracy success-criteria regex did not match; "
                "success_criteria left unchanged.",
                RuntimeWarning,
                stacklevel=2,
            )
    return criteria


def apply_visible_prompt_updates(
    task_description: str,
    success_criteria: str,
    target_terrain_config: Dict[str, Any],
    base_terrain_config: Dict[str, Any],
    target_physics_config: Dict[str, Any] = None,
    base_physics_config: Dict[str, Any] = None,
    *,
    stage: Optional[Dict[str, Any]] = None,
) -> tuple[str, str]:
    """
    Apply both visible-text updaters in one call so task_description and success_criteria stay aligned
    (e.g. platform half-width appears consistently in both sections).
    """
    td = update_task_description_for_visible_changes(
        task_description,
        target_terrain_config,
        base_terrain_config,
        target_physics_config,
        base_physics_config,
        stage=stage,
    )
    sc = update_success_criteria_for_visible_changes(
        success_criteria,
        target_terrain_config,
        base_terrain_config,
        target_physics_config,
        base_physics_config,
        stage=stage,
    )
    return td, sc


def get_c02_curriculum_stages() -> List[Dict[str, Any]]:
    task_description_suffix = """
## Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables **MIGHT** have changed from the initial environment, **NOT ALL** of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
 - **Structural Integrity Threshold**: The allowed magnitude of world-frame vertical speed |vy| at touchdown may be different.
 - **Upright Orientation Tolerance**: The maximum allowed landing angle (deviation from vertical) may be different.
 - **Landing Zone Extent**: The horizontal width of the valid landing platform may be different.
 - **Actuation Latency**: The time delay between issuing a control command and the engine's physical response may be different.
 - **Flight Corridor Constraints**: Vertical limits of the no-fly corridor in the barrier region may be different.
 - **Engine Thrust Limit**: The maximum thrust the main engine can produce may be different.
 - **Effective Gravity**: The effective gravitational influence on the craft may be different.
 - **Resource Availability**: The total fuel impulse available for the mission may be different.
 - **Operational Safety Margins**: The minimum required fuel that must remain after landing may be different.
 - **Atmospheric Disturbances**: Lateral environmental forcing (including gust-like effects) may be different.

Discovery via feedback: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Use simulator feedback to refine your controller.
"""
    return [
        {
            "stage_id": "Stage-1",
            "title": "Fragile Touchdown",
            "mutation_description": "Log only: curriculum stage mutation (Stage-1).",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {
                "max_safe_vertical_speed": 0.8,
            },
            "physics_config": {
                "max_thrust": 800.0,
                "total_fuel_impulse": 7000.0,
                "platform_half_width": 1.0,
            },
        },
        {
            "stage_id": "Stage-2",
            "title": "Severe Actuation Delay",
            "mutation_description": "Log only: curriculum stage mutation (Stage-2).",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {
                "max_safe_vertical_speed": 2.5,
                "max_landing_angle": CURRICULUM_STAGE2_MAX_LANDING_ANGLE_RAD,
            },
            "physics_config": {
                "thrust_delay_steps": 12,
                "platform_half_width": 3.0,
                "max_thrust": 1000.0,
                "total_fuel_impulse": 8000.0,
            },
        },
        {
            "stage_id": "Stage-3",
            "title": "The Squeeze",
            "mutation_description": "Log only: curriculum stage mutation (Stage-3).",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {},
            "physics_config": {
                "barrier_y_bottom": 12.0,
                "total_fuel_impulse": 8000.0,
                "max_thrust": 1200.0,
                "min_fuel_remaining_at_landing": 400.0,
                "gravity_mutation": {
                    "at_step": 150,
                    "gravity_after": (0, -18.0),
                },
            },
        },
        {
            "stage_id": "Stage-4",
            "title": "The Perfect Storm",
            "mutation_description": "Log only: curriculum stage mutation (Stage-4).",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {
                "max_safe_vertical_speed": 2.6,
                "max_landing_angle": math.radians(7.0),
            },
            "physics_config": {
                "thrust_delay_steps": 12,
                "total_fuel_impulse": 100000.0,
                "max_thrust": 1200.0,
                "min_fuel_remaining_at_landing": 500.0,
                "wind_amplitude": 15.0,
                "gust_amplitude": 20.0,
                "platform_half_width": 1.5,
                "barrier_y_bottom": 15.5,
                "gravity_mutation": {
                    "at_step": 150,
                    "gravity_after": (0, -11.5),
                },
            },
        },
    ]
