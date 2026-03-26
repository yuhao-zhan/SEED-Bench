from __future__ import annotations

import importlib.util
import math
import os
import re
from typing import Any, Dict, List, Optional, Tuple

# Load this task's environment by path. A bare `import environment` breaks when another task
# ran first in the same process: sys.modules['environment'] may be C_02/C_03/etc., not C_01.
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "environment.py")
_env_spec = importlib.util.spec_from_file_location(
    "davinci_category5_c01_environment_stages_only",
    _env_path,
)
_env_mod = importlib.util.module_from_spec(_env_spec)
assert _env_spec.loader is not None
_env_spec.loader.exec_module(_env_mod)

# Baseline (source) values for C-01 — match environment.py; "(originally … in the source environment)" refers here.
_BASE_POLE_START_ANGLE = _env_mod.DEFAULT_POLE_START_ANGLE
_BASE_POLE_LENGTH = _env_mod.POLE_LENGTH
_BASE_TRACK_CENTER_X = _env_mod.TRACK_CENTER_X
_BASE_MAX_STEPS = _env_mod.MAX_STEPS
_BASE_CART_MASS = _env_mod.CART_MASS
_BASE_POLE_MASS = _env_mod.POLE_MASS
_BASE_SAFE_HALF_RANGE = _env_mod.SAFE_HALF_RANGE
_BASE_SENSOR_DELAY_ANGLE_STEPS = _env_mod.DEFAULT_SENSOR_DELAY_ANGLE_STEPS
_BASE_SENSOR_DELAY_OMEGA_STEPS = _env_mod.DEFAULT_SENSOR_DELAY_OMEGA_STEPS
_BASE_CART_FORCE_LIMIT_NEWTONS = _env_mod.CART_FORCE_LIMIT_NEWTONS
_BASE_CART_RAIL_CENTER_Y = _env_mod.CART_RAIL_CENTER_Y
_BASE_POLE_WIDTH = _env_mod.POLE_WIDTH
_BASE_BALANCE_ANGLE_DEG = _env_mod.BALANCE_ANGLE_DEG
_BASE_FAILURE_ANGLE_DEG = _env_mod.FAILURE_ANGLE_DEG
_BASE_BALANCE_HOLD_STEPS_REQUIRED = _env_mod.BALANCE_HOLD_STEPS_REQUIRED


def _fmt_track_center_m(x: float) -> str:
    """Match baseline prompt style: whole meters without a trailing “.0” (e.g. 10m)."""
    xf = float(x)
    if math.isclose(xf, round(xf), rel_tol=0.0, abs_tol=1e-6):
        return f"{int(round(xf))}m"
    return f"{xf:.1f}m"


def _fmt_track_center_num(x: float) -> str:
    """Track center as a bare number for |x - …| lines (aligned with _fmt_track_center_m, no trailing m)."""
    xf = float(x)
    if math.isclose(xf, round(xf), rel_tol=0.0, abs_tol=1e-6):
        return str(int(round(xf)))
    return f"{xf:.1f}"


def _scalar_physics_differs(a: float, b: float) -> bool:
    """True if two physical scalars differ enough to require prompt sync (no coarse skip bands)."""
    return not math.isclose(float(a), float(b), rel_tol=1e-12, abs_tol=1e-9)


def _parse_task_center_x(description: str) -> Optional[float]:
    m = re.search(r"center x\s*=\s*(\d+\.?\d*)m", description)
    return float(m.group(1)) if m else None


def _parse_task_safe_half(description: str) -> Optional[float]:
    m = re.search(r"safe range ±(\d+\.?\d*)m inclusive", description)
    return float(m.group(1)) if m else None


def _parse_task_episode_steps(description: str) -> Optional[int]:
    m = re.search(r"- \*\*Episode length\*\*: At most (\d+) simulation steps", description)
    return int(m.group(1)) if m else None


def _parse_task_balance_angle(description: str) -> Optional[float]:
    m = re.search(r"\|angle\| <= (\d+\.?\d*)°", description)
    return float(m.group(1)) if m else None


def _parse_task_failure_angle(description: str) -> Optional[float]:
    m = re.search(r"\|angle\| > (\d+\.?\d*)°", description)
    return float(m.group(1)) if m else None


def _parse_task_hold_steps(description: str) -> Optional[int]:
    m = re.search(r"for at least \*\*(\d+) consecutive simulation steps\*\*", description)
    return int(m.group(1)) if m else None


def _parse_success_track(description: str) -> Optional[Tuple[float, float]]:
    m = re.search(
        r"\*\*Track Limits\*\*: Cart remains within the safe zone \(\|x - (\d+\.?\d*)\| ≤ (\d+\.?\d*)m",
        description,
    )
    if not m:
        return None
    return float(m.group(1)), float(m.group(2))


def _parse_success_episode_steps(description: str) -> Optional[int]:
    m = re.search(r"3\. \*\*Episode length\*\*: At most (\d+) simulation steps", description)
    return int(m.group(1)) if m else None


def _parse_success_balance_angle(description: str) -> Optional[float]:
    m = re.search(r"\|angle\| <= (\d+\.?\d*)°\)", description)
    return float(m.group(1)) if m else None


def _parse_success_failure_angle(description: str) -> Optional[float]:
    m = re.search(r"\|angle\| > (\d+\.?\d*)°", description)
    return float(m.group(1)) if m else None


def _parse_success_hold_steps(description: str) -> Optional[int]:
    m = re.search(r"for at least (\d+) consecutive simulation steps", description)
    return int(m.group(1)) if m else None


def _success_track_limits_line(target_track_center: float, target_safe_range: float) -> str:
    """S-01-style inline (originally … in the source environment) for success criteria track limits."""
    target_cx = _fmt_track_center_num(target_track_center)
    core = f"|x - {target_cx}| ≤ {target_safe_range:.1f}m"
    if math.isclose(target_track_center, _BASE_TRACK_CENTER_X, rel_tol=0.0, abs_tol=1e-6) and math.isclose(
        target_safe_range, _BASE_SAFE_HALF_RANGE, rel_tol=0.0, abs_tol=1e-6
    ):
        return f"2. **Track Limits**: Cart remains within the safe zone ({core})."
    base_cx = _fmt_track_center_num(_BASE_TRACK_CENTER_X)
    return (
        f"2. **Track Limits**: Cart remains within the safe zone ({core} "
        f"(originally |x - {base_cx}| ≤ {_BASE_SAFE_HALF_RANGE:.1f}m in the source environment))."
    )


def _parse_task_cart_mass(description: str) -> Optional[float]:
    m = re.search(r"\*\*Cart\*\*: [Aa] body of mass (\d+\.?\d*) kg", description)
    return float(m.group(1)) if m else None


def _parse_task_pole_mass(description: str) -> Optional[float]:
    m = re.search(r"\*\*Pole\*\*: Mass (\d+\.?\d*) kg", description)
    return float(m.group(1)) if m else None


def _parse_task_pole_length_m(description: str) -> Optional[float]:
    m = re.search(r"\*\*Length\*\*: (\d+\.?\d*)m", description)
    return float(m.group(1)) if m else None


def _parse_task_actuator_limit_n(description: str) -> Optional[float]:
    m = re.search(r"\*\*Actuator Limit\*\*: The cart force is limited to ±(\d+(?:\.\d+)?)\s*N", description)
    return float(m.group(1)) if m else None


def _parse_task_rail_y(description: str) -> Optional[float]:
    m = re.search(
        r"horizontal track at y=(\d+\.?\d*)m(?: \(originally [\d.]+m in the source environment\))?",
        description,
    )
    return float(m.group(1)) if m else None


def _parse_task_pole_width(description: str) -> Optional[float]:
    m = re.search(r"width (\d+\.?\d*)m", description)
    return float(m.group(1)) if m else None


def _parse_task_pole_start_angle(description: str) -> Optional[float]:
    if "Initially upright (angle = 0° or 0rad)" in description:
        return 0.0
    m = re.search(r"Initially at angle = [\d.]+° \(([-\d.eE]+) rad\)", description)
    return float(m.group(1)) if m else None


def _verify_task_description_sync(
    description: str,
    target_track_center: float,
    target_safe_range: float,
    target_max_steps: int,
    target_cart_mass: float,
    target_pole_mass: float,
    target_pole_length: float,
    target_cart_force_limit: float,
    target_sensor_delay_angle: int,
    target_sensor_delay_omega: int,
    target_cart_rail_center_y: float,
    target_balance_angle: float,
    target_failure_angle: float,
    target_hold_steps: int,
    target_pole_width: float,
    target_pole_start_angle: float,
) -> None:
    pc = _parse_task_center_x(description)
    if pc is not None and not math.isclose(pc, target_track_center, rel_tol=0.0, abs_tol=1e-6):
        raise RuntimeError(
            f"C-01 prompt sync: task_description track center text ({pc}) != target ({target_track_center})."
        )
    ps = _parse_task_safe_half(description)
    if ps is not None and not math.isclose(ps, target_safe_range, rel_tol=0.0, abs_tol=1e-6):
        raise RuntimeError(
            f"C-01 prompt sync: task_description safe half-range text ({ps}) != target ({target_safe_range})."
        )
    pe = _parse_task_episode_steps(description)
    if pe is not None and pe != target_max_steps:
        raise RuntimeError(
            f"C-01 prompt sync: task_description episode steps text ({pe}) != target ({target_max_steps})."
        )
    pcm = _parse_task_cart_mass(description)
    if pcm is not None and not math.isclose(pcm, target_cart_mass, rel_tol=0.0, abs_tol=1e-6):
        raise RuntimeError(
            f"C-01 prompt sync: task_description cart mass text ({pcm}) != target ({target_cart_mass})."
        )
    ppm = _parse_task_pole_mass(description)
    if ppm is not None and not math.isclose(ppm, target_pole_mass, rel_tol=0.0, abs_tol=1e-6):
        raise RuntimeError(
            f"C-01 prompt sync: task_description pole mass text ({ppm}) != target ({target_pole_mass})."
        )
    plen = _parse_task_pole_length_m(description)
    if plen is not None and not math.isclose(plen, target_pole_length, rel_tol=0.0, abs_tol=1e-6):
        raise RuntimeError(
            f"C-01 prompt sync: task_description pole length text ({plen}) != target ({target_pole_length})."
        )
    pact = _parse_task_actuator_limit_n(description)
    if pact is not None and not math.isclose(pact, target_cart_force_limit, rel_tol=0.0, abs_tol=1e-6):
        raise RuntimeError(
            f"C-01 prompt sync: task_description actuator limit text ({pact}) != target ({target_cart_force_limit})."
        )
    pry = _parse_task_rail_y(description)
    if pry is not None and not math.isclose(pry, target_cart_rail_center_y, rel_tol=0.0, abs_tol=1e-6):
        raise RuntimeError(
            f"C-01 prompt sync: task_description rail y text ({pry}) != target ({target_cart_rail_center_y})."
        )
    pba = _parse_task_balance_angle(description)
    if pba is not None and not math.isclose(pba, target_balance_angle, rel_tol=0.0, abs_tol=1e-6):
        raise RuntimeError(
            f"C-01 prompt sync: task_description balance angle text ({pba}) != target ({target_balance_angle})."
        )
    pfa = _parse_task_failure_angle(description)
    if pfa is not None and not math.isclose(pfa, target_failure_angle, rel_tol=0.0, abs_tol=1e-6):
        raise RuntimeError(
            f"C-01 prompt sync: task_description failure angle text ({pfa}) != target ({target_failure_angle})."
        )
    phs = _parse_task_hold_steps(description)
    if phs is not None and phs != target_hold_steps:
        raise RuntimeError(
            f"C-01 prompt sync: task_description hold steps text ({phs}) != target ({target_hold_steps})."
        )
    ppw = _parse_task_pole_width(description)
    if ppw is not None and not math.isclose(ppw, target_pole_width, rel_tol=0.0, abs_tol=1e-6):
        raise RuntimeError(
            f"C-01 prompt sync: task_description pole width text ({ppw}) != target ({target_pole_width})."
        )
    pps = _parse_task_pole_start_angle(description)
    if pps is not None and not math.isclose(pps, target_pole_start_angle, rel_tol=0.0, abs_tol=1e-5):
        raise RuntimeError(
            f"C-01 prompt sync: task_description pole start angle text ({pps}) != target ({target_pole_start_angle})."
        )

    _require_task_description_parses(description)


def _require_task_description_parses(description: str) -> None:
    """Fail fast if canonical lines are missing so sync cannot be validated."""
    checks = [
        (_parse_task_center_x(description), "track center (center x=…m)"),
        (_parse_task_safe_half(description), "safe half-range (safe range ±…m inclusive)"),
        (_parse_task_episode_steps(description), "episode length line"),
        (_parse_task_cart_mass(description), "cart mass line"),
        (_parse_task_pole_mass(description), "pole mass line"),
        (_parse_task_pole_length_m(description), "pole length line"),
        (_parse_task_actuator_limit_n(description), "actuator limit line"),
        (_parse_task_rail_y(description), "cart rail y (horizontal track at y=…m)"),
        (_parse_task_balance_angle(description), "balance angle"),
        (_parse_task_failure_angle(description), "failure angle"),
        (_parse_task_hold_steps(description), "hold steps"),
        (_parse_task_pole_width(description), "pole width"),
        (_parse_task_pole_start_angle(description), "pole start angle"),
    ]
    for val, label in checks:
        if val is None:
            raise RuntimeError(f"C-01 prompt sync: could not parse {label} from task_description.")


def _parse_success_actuator_limit_n(description: str) -> Optional[float]:
    m = re.search(r"- \*\*Actuator\*\*: Cart force must not exceed ±(\d+(?:\.\d+)?)\s*N", description)
    return float(m.group(1)) if m else None


def _verify_success_criteria_sync(
    description: str,
    target_max_steps: int,
    target_track_center: float,
    target_safe_range: float,
    target_cart_force_limit: float,
    target_balance_angle: float,
    target_failure_angle: float,
    target_hold_steps: int,
    target_sensor_delay_angle: int,
    target_sensor_delay_omega: int,
) -> None:
    pt = _parse_success_episode_steps(description)
    if pt is not None and pt != target_max_steps:
        raise RuntimeError(
            f"C-01 prompt sync: success_criteria episode steps text ({pt}) != target ({target_max_steps})."
        )
    ptr = _parse_success_track(description)
    if ptr is not None:
        pc, ps = ptr
        if not math.isclose(pc, target_track_center, rel_tol=0.0, abs_tol=1e-6) or not math.isclose(
            ps, target_safe_range, rel_tol=0.0, abs_tol=1e-6
        ):
            raise RuntimeError(
                "C-01 prompt sync: success_criteria track limits text "
                f"(center={pc}, half-range={ps}) != target ({target_track_center}, {target_safe_range})."
            )
    sa = _parse_success_actuator_limit_n(description)
    if sa is not None and not math.isclose(sa, target_cart_force_limit, rel_tol=0.0, abs_tol=1e-6):
        raise RuntimeError(
            f"C-01 prompt sync: success_criteria actuator text ({sa}) != target ({target_cart_force_limit})."
        )
    sba = _parse_success_balance_angle(description)
    if sba is not None and not math.isclose(sba, target_balance_angle, rel_tol=0.0, abs_tol=1e-6):
        raise RuntimeError(
            f"C-01 prompt sync: success_criteria balance angle text ({sba}) != target ({target_balance_angle})."
        )
    sfa = _parse_success_failure_angle(description)
    if sfa is not None and not math.isclose(sfa, target_failure_angle, rel_tol=0.0, abs_tol=1e-6):
        raise RuntimeError(
            f"C-01 prompt sync: success_criteria failure angle text ({sfa}) != target ({target_failure_angle})."
        )
    shs = _parse_success_hold_steps(description)
    if shs is not None and shs != target_hold_steps:
        raise RuntimeError(
            f"C-01 prompt sync: success_criteria hold steps text ({shs}) != target ({target_hold_steps})."
        )

    _require_success_criteria_parses(description)


def _require_success_criteria_parses(description: str) -> None:
    checks = [
        (_parse_success_episode_steps(description), "episode length"),
        (_parse_success_track(description), "track limits"),
        (_parse_success_actuator_limit_n(description), "actuator limit"),
        (_parse_success_balance_angle(description), "balance angle"),
        (_parse_success_failure_angle(description), "failure angle"),
        (_parse_success_hold_steps(description), "hold steps"),
    ]
    for val, label in checks:
        if val is None:
            raise RuntimeError(f"C-01 prompt sync: could not parse {label} from success_criteria.")



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

    target_track_center = float(target_physics_config.get("track_center_x", _BASE_TRACK_CENTER_X))
    target_max_steps = int(target_physics_config.get("max_steps", _BASE_MAX_STEPS))
    target_cart_mass = float(target_physics_config.get("cart_mass", _BASE_CART_MASS))
    target_pole_mass = float(target_physics_config.get("pole_mass", _BASE_POLE_MASS))
    target_safe_range = float(target_physics_config.get("safe_half_range", _BASE_SAFE_HALF_RANGE))
    target_pole_length = float(target_physics_config.get("pole_length", _BASE_POLE_LENGTH))
    target_pole_start_angle = float(target_physics_config.get("pole_start_angle", _BASE_POLE_START_ANGLE))
    target_sensor_delay_angle = int(target_physics_config.get("sensor_delay_angle_steps", _BASE_SENSOR_DELAY_ANGLE_STEPS))
    target_sensor_delay_omega = int(target_physics_config.get("sensor_delay_omega_steps", _BASE_SENSOR_DELAY_OMEGA_STEPS))
    target_cart_force_limit = float(
        target_physics_config.get("cart_force_limit_newtons", _BASE_CART_FORCE_LIMIT_NEWTONS)
    )
    target_cart_rail_center_y = float(
        target_physics_config.get("cart_rail_center_y", _BASE_CART_RAIL_CENTER_Y)
    )
    target_pole_width = float(target_physics_config.get("pole_width", _BASE_POLE_WIDTH))
    target_balance_angle_deg = float(target_physics_config.get("balance_angle_deg", _BASE_BALANCE_ANGLE_DEG))
    target_failure_angle_deg = float(target_physics_config.get("failure_angle_deg", _BASE_FAILURE_ANGLE_DEG))
    target_hold_steps = int(target_physics_config.get("balance_hold_steps_required", _BASE_BALANCE_HOLD_STEPS_REQUIRED))

    # Track center: sync when description text disagrees with target (fixes pristine prompt + prior-stage physics).
    parsed_cx = _parse_task_center_x(description)
    if parsed_cx is not None and not math.isclose(parsed_cx, target_track_center, rel_tol=0.0, abs_tol=1e-6):
        center_pat = re.compile(
            r"center x\s*=\s*\d+\.?\d*m(?: \(originally \d+\.?\d*m in the source environment\))?"
        )
        if center_pat.search(description):
            if math.isclose(target_track_center, _BASE_TRACK_CENTER_X, rel_tol=0.0, abs_tol=1e-6):
                repl = f"center x={_fmt_track_center_m(target_track_center)}"
            else:
                repl = f"center x={_fmt_track_center_m(target_track_center)} (originally {_fmt_track_center_m(_BASE_TRACK_CENTER_X)} in the source environment)"
            description = center_pat.sub(repl, description, count=1)

    parsed_safe = _parse_task_safe_half(description)
    if parsed_safe is not None and not math.isclose(parsed_safe, target_safe_range, rel_tol=0.0, abs_tol=1e-6):
        safe_flex = re.compile(
            r"safe range ±\d+\.?\d*m inclusive(?: \(originally ±\d+\.?\d*m in the source environment\))?"
        )
        if safe_flex.search(description):
            if math.isclose(target_safe_range, _BASE_SAFE_HALF_RANGE, rel_tol=0.0, abs_tol=1e-6):
                repl = f"safe range ±{target_safe_range:.1f}m inclusive"
            else:
                repl = f"safe range ±{target_safe_range:.1f}m inclusive (originally ±{_BASE_SAFE_HALF_RANGE:.1f}m in the source environment)"
            description = safe_flex.sub(repl, description, count=1)

    parsed_ep = _parse_task_episode_steps(description)
    if parsed_ep is not None and parsed_ep != target_max_steps:
        ep_pat = re.compile(
            r"- \*\*Episode length\*\*: At most (\d+) simulation steps(?: \(originally [^)]+\))?"
        )
        if ep_pat.search(description):
            if target_max_steps == _BASE_MAX_STEPS:
                repl = f"- **Episode length**: At most {target_max_steps} simulation steps"
            else:
                repl = (
                    f"- **Episode length**: At most {target_max_steps} simulation steps "
                    f"(originally {_BASE_MAX_STEPS} simulation steps in the source environment)"
                )
            description = ep_pat.sub(repl, description, count=1)

    parsed_ry = _parse_task_rail_y(description)
    if parsed_ry is not None and not math.isclose(
        parsed_ry, target_cart_rail_center_y, rel_tol=0.0, abs_tol=1e-6
    ):
        rail_flex = re.compile(
            r"(horizontal track at y=)(\d+\.?\d*)m(?: \(originally [\d.]+m in the source environment\))?"
        )
        if rail_flex.search(description):
            if math.isclose(target_cart_rail_center_y, _BASE_CART_RAIL_CENTER_Y):
                description = rail_flex.sub(rf"\g<1>{target_cart_rail_center_y:.1f}m", description, count=1)
            else:
                description = rail_flex.sub(
                    rf"\g<1>{target_cart_rail_center_y:.1f}m (originally {_BASE_CART_RAIL_CENTER_Y:.1f}m in the source environment)",
                    description,
                    count=1,
                )

    # Cart / pole mass & length: refresh when current text value ≠ target (originally = source env).
    cart_flex = re.compile(
        r"(\*\*Cart\*\*: [Aa] body of mass )(\d+\.?\d*) kg(?: \(originally [\d.]+\s*kg in the source environment\))?"
    )
    cm = cart_flex.search(description)
    if cm and not math.isclose(float(cm.group(2)), target_cart_mass, rel_tol=0.0, abs_tol=1e-6):
        if math.isclose(target_cart_mass, _BASE_CART_MASS):
            description = cart_flex.sub(rf"\g<1>{target_cart_mass:g} kg", description, count=1)
        else:
            description = cart_flex.sub(
                rf"\g<1>{target_cart_mass:g} kg (originally {_BASE_CART_MASS:g} kg in the source environment)",
                description,
                count=1,
            )

    pole_flex = re.compile(
        r"(\*\*Pole\*\*: Mass )(\d+\.?\d*) kg(?: \(originally [\d.]+\s*kg in the source environment\))?"
    )
    pm = pole_flex.search(description)
    if pm and not math.isclose(float(pm.group(2)), target_pole_mass, rel_tol=0.0, abs_tol=1e-6):
        if math.isclose(target_pole_mass, _BASE_POLE_MASS):
            description = pole_flex.sub(rf"\g<1>{target_pole_mass:g} kg", description, count=1)
        else:
            description = pole_flex.sub(
                rf"\g<1>{target_pole_mass:g} kg (originally {_BASE_POLE_MASS:g} kg in the source environment)",
                description,
                count=1,
            )

    len_flex = re.compile(
        rf"(\*\*Length\*\*: )(\d+\.?\d*)m(?: \(originally [\d.]+m in the source environment\))?\."
    )
    lm = len_flex.search(description)
    if lm and not math.isclose(float(lm.group(2)), target_pole_length, rel_tol=0.0, abs_tol=1e-6):
        if math.isclose(target_pole_length, _BASE_POLE_LENGTH):
            description = len_flex.sub(rf"\g<1>{target_pole_length:.1f}m.", description, count=1)
        else:
            description = len_flex.sub(
                rf"\g<1>{target_pole_length:.1f}m (originally {_BASE_POLE_LENGTH:.1f}m in the source environment).",
                description,
                count=1,
            )

    # Pole width sync
    pw_flex = re.compile(
        r"(width )(\d+\.?\d*)m(?: \(originally [\d.]+m in the source environment\))?"
    )
    pwm = pw_flex.search(description)
    if pwm and not math.isclose(float(pwm.group(2)), target_pole_width, rel_tol=0.0, abs_tol=1e-6):
        if math.isclose(target_pole_width, _BASE_POLE_WIDTH):
            description = pw_flex.sub(rf"\g<1>{target_pole_width:g}m", description, count=1)
        else:
            description = pw_flex.sub(
                rf"\g<1>{target_pole_width:g}m (originally {_BASE_POLE_WIDTH:g}m in the source environment)",
                description,
                count=1,
            )

    # Initial pole angle
    ang_deg_new = math.degrees(target_pole_start_angle)
    upright_pat = r"Initially upright \(angle = 0° or 0rad\)\."
    mutated_ang_pat = re.compile(
        r"Initially at angle = ([\d.]+)° \(([-\d.eE]+) rad\) \(originally [\d.]+° / [-\d.eE]+ rad in the source environment\)\."
    )
    if math.isclose(target_pole_start_angle, _BASE_POLE_START_ANGLE, abs_tol=1e-5):
        # Revert to baseline if currently mutated
        if mutated_ang_pat.search(description):
            description = mutated_ang_pat.sub("Initially upright (angle = 0° or 0rad).", description, count=1)
    else:
        # Mutated state
        if re.search(upright_pat, description):
            replacement = (
                f"Initially at angle = {ang_deg_new:.1f}° ({target_pole_start_angle:.3f} rad) "
                f"(originally {math.degrees(_BASE_POLE_START_ANGLE):.1f}° / {_BASE_POLE_START_ANGLE:.3f} rad in the source environment)."
            )
            description = re.sub(upright_pat, replacement, description, count=1)
        else:
            am = mutated_ang_pat.search(description)
            if am:
                replacement = (
                    f"Initially at angle = {ang_deg_new:.1f}° ({target_pole_start_angle:.3f} rad) "
                    f"(originally {math.degrees(_BASE_POLE_START_ANGLE):.1f}° / {_BASE_POLE_START_ANGLE:.3f} rad in the source environment)."
                )
                description = mutated_ang_pat.sub(replacement, description, count=1)

    # Grading thresholds / Goal sync
    # 1. Primary Goal sentence
    goal_pat = re.compile(
        r"(Maintain the pole in the upright position \(\|angle\| <= )(\d+\.?\d*)(°\) for at least \*\*)(\d+)( consecutive simulation steps\*\*)"
        r"(?: \(originally [\d.]+° and \d+ steps in the source environment\))?"
    )
    if goal_pat.search(description):
        if math.isclose(target_balance_angle_deg, _BASE_BALANCE_ANGLE_DEG) and target_hold_steps == _BASE_BALANCE_HOLD_STEPS_REQUIRED:
            description = goal_pat.sub(rf"\g<1>{target_balance_angle_deg:g}\g<3>{target_hold_steps}\g<5>", description, count=1)
        else:
            description = goal_pat.sub(
                rf"\g<1>{target_balance_angle_deg:g}\g<3>{target_hold_steps}\g<5> (originally {_BASE_BALANCE_ANGLE_DEG:g}° and {_BASE_BALANCE_HOLD_STEPS_REQUIRED} steps in the source environment)",
                description,
                count=1,
            )

    # 2. Other occurrences of balance/failure angle in Goal section
    # Use negative lookahead for goal_pat's specific structure to avoid double provenance.
    bal_exceed_pat = re.compile(
        r"(\|angle\| (?:exceeds|briefly exceeds|<=) )(\d+\.?\d*)(°)(?: \(originally [\d.]+° in the source environment\))?(?!\) for at least \*\*[\d.]+ consecutive)"
    )
    description = bal_exceed_pat.sub(
        lambda m: (
            f"{m.group(1)}{target_balance_angle_deg:g}{m.group(3)}"
            if math.isclose(target_balance_angle_deg, _BASE_BALANCE_ANGLE_DEG)
            else (
                f"{m.group(1)}{target_balance_angle_deg:g}{m.group(3)} "
                f"(originally {_BASE_BALANCE_ANGLE_DEG:g}° in the source environment)"
            )
        ),
        description
    )

    obj_hold_pat = re.compile(
        r"(\*\*Balance\*\*: Achieve )(\d+)( consecutive simulation steps)"
        r"(?: \(originally \d+ steps in the source environment\))?"
    )
    if obj_hold_pat.search(description):
        if target_hold_steps == _BASE_BALANCE_HOLD_STEPS_REQUIRED:
            description = obj_hold_pat.sub(rf"\g<1>{target_hold_steps}\g<3>", description, count=1)
        else:
            description = obj_hold_pat.sub(
                rf"\g<1>{target_hold_steps}\g<3> (originally {_BASE_BALANCE_HOLD_STEPS_REQUIRED} steps in the source environment)",
                description,
                count=1,
            )

    fail_goal_pat = re.compile(
        r"(\|angle\| > )(\d+\.?\d*)(°)(?: \(originally [\d.]+° in the source environment\))?"
    )
    description = fail_goal_pat.sub(
        lambda m: (
            f"{m.group(1)}{target_failure_angle_deg:g}{m.group(3)}"
            if math.isclose(target_failure_angle_deg, _BASE_FAILURE_ANGLE_DEG)
            else (
                f"{m.group(1)}{target_failure_angle_deg:g}{m.group(3)} "
                f"(originally {_BASE_FAILURE_ANGLE_DEG:g}° in the source environment)"
            )
        ),
        description
    )

    # 3. "Grading vs sensors" line synchronization
    grading_vs_sensors_pat = re.compile(
        r"(All angle conditions above \()(\d+\.?\d*)(°, )(\d+\.?\d*)(°, lock-in count, and terminal check\))"
        r"(?: \(originally [\d.]+° and [\d.]+° in the source environment\))?"
    )
    if grading_vs_sensors_pat.search(description):
        if math.isclose(target_balance_angle_deg, _BASE_BALANCE_ANGLE_DEG) and math.isclose(target_failure_angle_deg, _BASE_FAILURE_ANGLE_DEG):
            description = grading_vs_sensors_pat.sub(rf"\g<1>{target_balance_angle_deg:g}\g<3>{target_failure_angle_deg:g}\g<5>", description, count=1)
        else:
            description = grading_vs_sensors_pat.sub(
                rf"\g<1>{target_balance_angle_deg:g}\g<3>{target_failure_angle_deg:g}\g<5> (originally {_BASE_BALANCE_ANGLE_DEG:g}° and {_BASE_FAILURE_ANGLE_DEG:g}° in the source environment)",
                description,
                count=1,
            )

    # Actuator limit (visible); "(originally …)" only when deviating from source clamp.
    act_task = re.compile(
        r"(\*\*Actuator Limit\*\*: The cart force is limited to ±)(\d+(?:\.\d+)?)\s*N\.?(?: \(originally [^)]+\))?"
    )
    am_act = act_task.search(description)
    if am_act:
        cur_fl = float(am_act.group(2))
        if not math.isclose(cur_fl, target_cart_force_limit, rel_tol=0.0, abs_tol=1e-6):
            fn = int(target_cart_force_limit) if float(target_cart_force_limit).is_integer() else target_cart_force_limit
            ob = int(_BASE_CART_FORCE_LIMIT_NEWTONS) if float(_BASE_CART_FORCE_LIMIT_NEWTONS).is_integer() else _BASE_CART_FORCE_LIMIT_NEWTONS
            if math.isclose(target_cart_force_limit, _BASE_CART_FORCE_LIMIT_NEWTONS):
                description = act_task.sub(rf"\g<1>{fn}N.", description, count=1)
            else:
                description = act_task.sub(
                    rf"\g<1>{fn}N. (originally {ob}N in the source environment)",
                    description,
                    count=1,
                )

    _verify_task_description_sync(
        description,
        target_track_center,
        target_safe_range,
        target_max_steps,
        target_cart_mass,
        target_pole_mass,
        target_pole_length,
        target_cart_force_limit,
        target_sensor_delay_angle,
        target_sensor_delay_omega,
        target_cart_rail_center_y,
        target_balance_angle_deg,
        target_failure_angle_deg,
        target_hold_steps,
        target_pole_width,
        target_pole_start_angle,
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

    target_max_steps = int(target_physics_config.get("max_steps", _BASE_MAX_STEPS))
    target_track_center = float(target_physics_config.get("track_center_x", _BASE_TRACK_CENTER_X))
    target_safe_range = float(target_physics_config.get("safe_half_range", _BASE_SAFE_HALF_RANGE))
    target_sensor_delay_angle = int(target_physics_config.get("sensor_delay_angle_steps", _BASE_SENSOR_DELAY_ANGLE_STEPS))
    target_sensor_delay_omega = int(target_physics_config.get("sensor_delay_omega_steps", _BASE_SENSOR_DELAY_OMEGA_STEPS))
    target_cart_force_limit = float(
        target_physics_config.get("cart_force_limit_newtons", _BASE_CART_FORCE_LIMIT_NEWTONS)
    )
    target_balance_angle_deg = float(target_physics_config.get("balance_angle_deg", _BASE_BALANCE_ANGLE_DEG))
    target_failure_angle_deg = float(target_physics_config.get("failure_angle_deg", _BASE_FAILURE_ANGLE_DEG))
    target_hold_steps = int(target_physics_config.get("balance_hold_steps_required", _BASE_BALANCE_HOLD_STEPS_REQUIRED))

    display_base_steps = int(base_physics_config.get("max_steps", _BASE_MAX_STEPS))

    # Episode length — sync stale text; "(originally …)" references source environment only.
    parsed_sc_steps = _parse_success_episode_steps(description)
    if parsed_sc_steps is not None and parsed_sc_steps != target_max_steps:
        sc_ep_pat = re.compile(
            r"3\. \*\*Episode length\*\*: At most (\d+) simulation steps(?: \(originally [^)]+\))?(\.)"
        )
        if sc_ep_pat.search(description):
            description = sc_ep_pat.sub(
                lambda m: (
                    f"3. **Episode length**: At most {target_max_steps} simulation steps{m.group(2)}"
                    if target_max_steps == _BASE_MAX_STEPS
                    else (
                        f"3. **Episode length**: At most {target_max_steps} simulation steps "
                        f"(originally {_BASE_MAX_STEPS} simulation steps in the source environment){m.group(2)}"
                    )
                ),
                description,
                count=1,
            )

    # Track limits — S-01-style inline (originally … in the source environment).
    parsed_tr = _parse_success_track(description)
    if parsed_tr is not None:
        pc, ps = parsed_tr
        if not math.isclose(pc, target_track_center, rel_tol=0.0, abs_tol=1e-6) or not math.isclose(
            ps, target_safe_range, rel_tol=0.0, abs_tol=1e-6
        ):
            track_any = re.compile(
                r"2\. \*\*Track Limits\*\*: Cart remains within the safe zone \((.+)\)\."
            )
            if track_any.search(description):
                description = track_any.sub(
                    f"{_success_track_limits_line(target_track_center, target_safe_range)}",
                    description,
                    count=1,
                )

    # Success Criteria grading band sync

    sc_bal_pat = re.compile(
        r"(\|angle\| <= )(\d+\.?\d*)(°\)) for at least (\d+)( consecutive simulation steps)"
        r"(?: \(originally [\d.]+° and \d+ steps in the source environment\))?"
    )
    if sc_bal_pat.search(description):
        if math.isclose(target_balance_angle_deg, _BASE_BALANCE_ANGLE_DEG) and target_hold_steps == _BASE_BALANCE_HOLD_STEPS_REQUIRED:
            description = sc_bal_pat.sub(rf"\g<1>{target_balance_angle_deg:g}\g<3> for at least {target_hold_steps}\g<5>", description, count=1)
        else:
            description = sc_bal_pat.sub(
                rf"\g<1>{target_balance_angle_deg:g}\g<3> for at least {target_hold_steps}\g<5> (originally {_BASE_BALANCE_ANGLE_DEG:g}° and {_BASE_BALANCE_HOLD_STEPS_REQUIRED} steps in the source environment)",
                description,
                count=1,
            )

    sc_fail_pat = re.compile(
        r"(\|angle\| > )(\d+\.?\d*)(°; \*\*final\*\* success requires \|angle\| <= )(\d+\.?\d*)(°)"
        r"(?: \(originally [\d.]+° and [\d.]+° in the source environment\))?"
    )
    if sc_fail_pat.search(description):
        if math.isclose(target_failure_angle_deg, _BASE_FAILURE_ANGLE_DEG) and math.isclose(target_balance_angle_deg, _BASE_BALANCE_ANGLE_DEG):
            description = sc_fail_pat.sub(rf"\g<1>{target_failure_angle_deg:g}\g<3>{target_balance_angle_deg:g}\g<5>", description, count=1)
        else:
            description = sc_fail_pat.sub(
                rf"\g<1>{target_failure_angle_deg:g}\g<3>{target_balance_angle_deg:g}\g<5> (originally {_BASE_FAILURE_ANGLE_DEG:g}° and {_BASE_BALANCE_ANGLE_DEG:g}° in the source environment)",
                description,
                count=1,
            )

    # Design Constraints — actuator
    sc_act = re.compile(
        r"(- \*\*Actuator\*\*: Cart force must not exceed ±)(\d+(?:\.\d+)?)\s*N\.?(?: \(originally [^)]+\))?"
    )

    am_sca = sc_act.search(description)
    if am_sca:
        cur_fl = float(am_sca.group(2))
        if not math.isclose(cur_fl, target_cart_force_limit, rel_tol=0.0, abs_tol=1e-6):
            fn = int(target_cart_force_limit) if float(target_cart_force_limit).is_integer() else target_cart_force_limit
            ob = int(_BASE_CART_FORCE_LIMIT_NEWTONS) if float(_BASE_CART_FORCE_LIMIT_NEWTONS).is_integer() else _BASE_CART_FORCE_LIMIT_NEWTONS
            if math.isclose(target_cart_force_limit, _BASE_CART_FORCE_LIMIT_NEWTONS):
                description = sc_act.sub(rf"\g<1>{fn}N.", description, count=1)
            else:
                description = sc_act.sub(
                    rf"\g<1>{fn}N. (originally {ob}N in the source environment)",
                    description,
                    count=1,
                )

    _verify_success_criteria_sync(
        description,
        target_max_steps,
        target_track_center,
        target_safe_range,
        target_cart_force_limit,
        target_balance_angle_deg,
        target_failure_angle_deg,
        target_hold_steps,
        target_sensor_delay_angle,
        target_sensor_delay_omega,
    )
    return description



# Union of all physical variables modified across Stage-1–4:
# Variables: sensor_delay_angle_steps, sensor_delay_omega_steps, gravity, pole_mass, cart_mass, track_center_x, max_steps
UNIFORM_SUFFIX = """
## Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables **MIGHT** have changed from the initial environment, **NOT ALL** of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
 - **Sensor delay**: Latency in measurement acquisition may affect how reported state tracks the true dynamics.
 - **Gravitational acceleration**: Vertical loads may be significantly different, affecting the system's dynamic response.
 - **Pole and cart mass**: The distribution of inertia within the assembly may be altered.
 - **Track center position**: The horizontal center of the safe balancing zone may have been relocated.
 - **Episode length**: The required duration of the stability task may be significantly different.

**Discovery via feedback**: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., cart position, pole angle trends, or loss of stability) to infer the hidden constraints and adapt your design.
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
            # Scalar gravity>0 means downward magnitude (0, -g); see environment.gravity_from_config
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
            "terrain_config": s.get("terrain_config", {}) or {},
            "task_description_suffix": s.get("task_description_suffix", "") or "",
        })
    return result
