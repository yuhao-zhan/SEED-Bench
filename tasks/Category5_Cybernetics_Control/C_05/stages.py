"""
C-05: The Logic Lock task curriculum stages (mutations).

Mutation dimensions: dwell (activation duration), zone dynamics (speed cap, in-zone force limit, repulsion), temporal windows, C altitude lookback, barrier delay, and terrain friction.
Visible parameters are updated in the prompt with format: [new_value] (originally [old_value] in the source environment).
Terrain keys in ``terrain_config`` for ground / ramp / platform friction and optional ``agent_fixture_friction`` / ``barrier_fixture_friction`` are synced into the prompt when they differ from the source environment; effective values resolve target overrides then base overrides then module defaults (matching ``Sandbox`` in ``environment.py``).

mutation_description is for logs and orchestration only and must NOT be shown to the agent.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

from tasks.Category5_Cybernetics_Control.C_05 import environment as _env

# Baseline values from environment.py (single source of truth)
_BASE_TRIGGER_STAY = _env.TRIGGER_STAY_STEPS
_BASE_SPEED_CAP = _env.SPEED_CAP_INSIDE
_BASE_COOLDOWN = _env.COOLDOWN_STEPS
_BASE_BARRIER_DELAY = _env.BARRIER_DELAY_STEPS
_BASE_C_REQUIRED_MAX_Y = _env.C_REQUIRED_MAX_Y
_BASE_C_HIGH_HISTORY = _env.C_HIGH_HISTORY
_BASE_RECENT_A_FOR_B = _env.RECENT_A_FOR_B
_BASE_RECENT_B_FOR_C = _env.RECENT_B_FOR_C
_BASE_FORCE_LIMIT = _env.FORCE_LIMIT_INSIDE
_BASE_REPULSION_MAG = _env.REPULSION_MAG
_BASE_REPULSION_TANGENTIAL_MAG = _env.REPULSION_TANGENTIAL_MAG
_BASE_BARRIER_X = _env.BARRIER_X
_BASE_SPAWN_X = _env.SPAWN_X
_BASE_SPAWN_Y = _env.SPAWN_Y
_BASE_AGENT_RADIUS = _env.AGENT_RADIUS
_BASE_AGENT_MASS = _env.AGENT_MASS
_BASE_MAX_AGENT_FORCE_PER_AXIS = _env.MAX_AGENT_FORCE_PER_AXIS
_BASE_REPULSION_RANGE = _env.REPULSION_RANGE
_BASE_GROUND_FRICTION = _env.GROUND_FRICTION_DEFAULT
_BASE_RAMP_FRICTION = _env.RAMP_FRICTION_DEFAULT
_BASE_PLATFORM_FRICTION = _env.PLATFORM_FRICTION_DEFAULT
_BASE_AGENT_BODY_FRICTION = _env.AGENT_FIXTURE_FRICTION
_BARRIER_BODY_FRICTION = _env.BARRIER_FIXTURE_FRICTION


def _fmt_scalar_prompt(x: float) -> str:
    """Stable decimal string for prompt sync (avoids spurious float noise)."""
    xf = float(x)
    if abs(xf - round(xf)) < 1e-9:
        return str(int(round(xf)))
    return format(xf, ".15g").rstrip("0").rstrip(".") or "0"


def _fmt_repulsion_peak(x: float) -> str:
    """One-decimal Newton magnitudes for repulsion lines (matches baseline e.g. 22.0 N)."""
    return f"{float(x):.1f}"


def _friction_component(tv: float, bv: float) -> str:
    ts = _fmt_scalar_prompt(tv)
    if abs(float(tv) - float(bv)) < 1e-12:
        return ts
    return f"{ts} (originally {_fmt_scalar_prompt(bv)} in the source environment)"


def _effective_terrain(
    target_tc: Dict[str, Any], base_tc: Dict[str, Any], key: str, default: float
) -> float:
    if target_tc and key in target_tc:
        return float(target_tc[key])
    if base_tc and key in base_tc:
        return float(base_tc[key])
    return float(default)


def _base_terrain(base_tc: Dict[str, Any], key: str, default: float) -> float:
    if base_tc and key in base_tc:
        return float(base_tc[key])
    return float(default)


def _task_friction_line(target_tc: Dict[str, Any], base_tc: Dict[str, Any]) -> str:
    tg = _effective_terrain(target_tc, base_tc, "ground_friction", _BASE_GROUND_FRICTION)
    bg = _base_terrain(base_tc, "ground_friction", _BASE_GROUND_FRICTION)
    tr = _effective_terrain(target_tc, base_tc, "ramp_friction", _BASE_RAMP_FRICTION)
    br = _base_terrain(base_tc, "ramp_friction", _BASE_RAMP_FRICTION)
    tp = _effective_terrain(target_tc, base_tc, "platform_friction", _BASE_PLATFORM_FRICTION)
    bp = _base_terrain(base_tc, "platform_friction", _BASE_PLATFORM_FRICTION)
    ta = _effective_terrain(target_tc, base_tc, "agent_fixture_friction", _BASE_AGENT_BODY_FRICTION)
    ba = _base_terrain(base_tc, "agent_fixture_friction", _BASE_AGENT_BODY_FRICTION)
    tb = _effective_terrain(target_tc, base_tc, "barrier_fixture_friction", _BARRIER_BODY_FRICTION)
    bb = _base_terrain(base_tc, "barrier_fixture_friction", _BARRIER_BODY_FRICTION)
    return (
        "- **Terrain & contact friction (Box2D coefficients)**: "
        f"Ground {_friction_component(tg, bg)}; "
        f"ramps {_friction_component(tr, br)}; "
        f"platform {_friction_component(tp, bp)}; "
        f"agent body {_friction_component(ta, ba)}; "
        f"barrier {_friction_component(tb, bb)}."
    )


def _criteria_friction_line(target_tc: Dict[str, Any], base_tc: Dict[str, Any]) -> str:
    tg = _effective_terrain(target_tc, base_tc, "ground_friction", _BASE_GROUND_FRICTION)
    bg = _base_terrain(base_tc, "ground_friction", _BASE_GROUND_FRICTION)
    tr = _effective_terrain(target_tc, base_tc, "ramp_friction", _BASE_RAMP_FRICTION)
    br = _base_terrain(base_tc, "ramp_friction", _BASE_RAMP_FRICTION)
    tp = _effective_terrain(target_tc, base_tc, "platform_friction", _BASE_PLATFORM_FRICTION)
    bp = _base_terrain(base_tc, "platform_friction", _BASE_PLATFORM_FRICTION)
    ta = _effective_terrain(target_tc, base_tc, "agent_fixture_friction", _BASE_AGENT_BODY_FRICTION)
    ba = _base_terrain(base_tc, "agent_fixture_friction", _BASE_AGENT_BODY_FRICTION)
    tb = _effective_terrain(target_tc, base_tc, "barrier_fixture_friction", _BARRIER_BODY_FRICTION)
    bb = _base_terrain(base_tc, "barrier_fixture_friction", _BARRIER_BODY_FRICTION)
    return (
        "- **Friction**: "
        f"Ground {_friction_component(tg, bg)}; "
        f"ramps {_friction_component(tr, br)}; "
        f"platform {_friction_component(tp, bp)}; "
        f"agent {_friction_component(ta, ba)}; "
        f"barrier {_friction_component(tb, bb)} "
        "(Box2D coefficients)."
    )


def _get_physics(base_physics: Dict[str, Any], key: str, default: Any) -> Any:
    if base_physics is None:
        return default
    return base_physics.get(key, default)


def update_task_description_for_visible_changes(
    base_description: str,
    target_terrain_config: Dict[str, Any],
    base_terrain_config: Dict[str, Any],
    target_physics_config: Dict[str, Any] = None,
    base_physics_config: Dict[str, Any] = None,
) -> str:
    """Update task description with visible changes using format: [new_value] (originally [old_value] in the source environment).

    Callers must pass base_terrain_config and base_physics_config from the **source** (unmutated)
    environment so ``(originally …)`` matches the true baseline.
    """
    description = base_description
    target_terrain_config = target_terrain_config or {}
    base_terrain_config = base_terrain_config or {}
    target_physics_config = target_physics_config or {}
    base_physics_config = base_physics_config or {}

    def target_phys(key: str, default: Any) -> Any:
        return target_physics_config.get(key, default)

    def base_phys(key: str, default: Any) -> Any:
        return _get_physics(base_physics_config, key, default)

    # Activation duration
    t_trigger = int(target_phys("trigger_stay_steps", _BASE_TRIGGER_STAY))
    b_trigger = int(base_phys("trigger_stay_steps", _BASE_TRIGGER_STAY))
    if t_trigger != b_trigger:
        pattern = (
            r"(- \*\*Activation duration\*\*: The agent must stay inside a zone for )"
            r"(\d+) consecutive steps(?: \(originally \d+ consecutive steps in the source environment\))? "
            r"(\(with speed and force constraints below\) to trigger it\.)"
        )
        if re.search(pattern, description):
            description = re.sub(
                pattern,
                f"\\g<1>{t_trigger} consecutive steps (originally {b_trigger} consecutive steps in the source environment) "
                f"\\g<3>",
                description,
            )

    # Speed cap inside zones (avoid "; (originally" — put originally immediately after value)
    t_speed = float(target_phys("speed_cap_inside", _BASE_SPEED_CAP))
    b_speed = float(base_phys("speed_cap_inside", _BASE_SPEED_CAP))
    if t_speed != b_speed:
        pattern = (
            r"(- \*\*Speed cap inside zones\*\*: Maximum velocity allowed inside a trigger zone for progress to count is )"
            r"([\d.]+) m/s(?: \(originally [\d.]+ m/s in the source environment\))?; exceeding this resets"
        )
        if re.search(pattern, description):
            description = re.sub(
                pattern,
                f"\\g<1>{t_speed} m/s (originally {b_speed} m/s in the source environment); exceeding this resets",
                description,
            )

    # Cooldown — full sentence substitution
    t_cool = int(target_phys("cooldown_steps", _BASE_COOLDOWN))
    b_cool = int(base_phys("cooldown_steps", _BASE_COOLDOWN))
    if t_cool != b_cool:
        # Idempotent: matches baseline or already-mutated "(originally …) before …"
        pattern = (
            r"(- \*\*Cooldown between triggers\*\*: After triggering a zone, the agent must wait )"
            r"\d+ steps(?: \(originally \d+ steps in the source environment\))? "
            r"before the next zone will accept progress\."
        )
        if re.search(pattern, description):
            description = re.sub(
                pattern,
                f"\\g<1>{t_cool} steps (originally {b_cool} steps in the source environment) "
                f"before the next zone will accept progress.",
                description,
            )

    # Barrier delay bullet
    t_barrier = int(target_phys("barrier_delay_steps", _BASE_BARRIER_DELAY))
    b_barrier = int(base_phys("barrier_delay_steps", _BASE_BARRIER_DELAY))
    if t_barrier != b_barrier:
        pattern = (
            r"(- \*\*Barrier delay after A\*\*: The gate opens )\d+ steps"
            r"(?: \(originally \d+ steps in the source environment\))? "
            r"after zone A is triggered, not immediately\."
        )
        if re.search(pattern, description):
            description = re.sub(
                pattern,
                f"\\g<1>{t_barrier} steps (originally {b_barrier} steps in the source environment) "
                f"after zone A is triggered, not immediately.",
                description,
            )
    # Temporal window A to B (single source in task bullets; objective references this heading)
    t_ab = int(target_phys("recent_a_for_b", _BASE_RECENT_A_FOR_B))
    b_ab = int(base_phys("recent_a_for_b", _BASE_RECENT_A_FOR_B))
    if t_ab != b_ab:
        pattern = (
            r"(- \*\*Temporal window A to B\*\*: Zone B only counts stay-steps if the agent was in zone A within the last )"
            r"\d+ steps(?: \(originally \d+ steps in the source environment\))?(\.)"
        )
        if re.search(pattern, description):
            description = re.sub(
                pattern,
                f"\\g<1>{t_ab} steps (originally {b_ab} steps in the source environment)\\g<2>",
                description,
            )

    # Temporal window B to C
    t_bc = int(target_phys("recent_b_for_c", _BASE_RECENT_B_FOR_C))
    b_bc = int(base_phys("recent_b_for_c", _BASE_RECENT_B_FOR_C))
    if t_bc != b_bc:
        pattern = (
            r"(- \*\*Temporal window B to C\*\*: Zone C only counts stay-steps if the agent was in zone B within the last )"
            r"\d+ steps(?: \(originally \d+ steps in the source environment\))?(\.)"
        )
        if re.search(pattern, description):
            description = re.sub(
                pattern,
                f"\\g<1>{t_bc} steps (originally {b_bc} steps in the source environment)\\g<2>",
                description,
            )

    # C altitude requirement bullet + objective line
    t_cy = float(target_phys("c_required_max_y", _BASE_C_REQUIRED_MAX_Y))
    b_cy = float(base_phys("c_required_max_y", _BASE_C_REQUIRED_MAX_Y))
    t_ch = int(target_phys("c_high_history", _BASE_C_HIGH_HISTORY))
    b_ch = int(base_phys("c_high_history", _BASE_C_HIGH_HISTORY))
    if t_cy != b_cy or t_ch != b_ch:
        c_alt_pat = (
            r"(?m)^- \*\*C altitude requirement\*\*: Zone C only counts stay-steps if the agent's maximum y over the retained y-history window "
            r"\(length up to \d+ simulation steps(?: \(originally \d+ simulation steps in the source environment\))?; "
            r"shorter early in the episode\) is at least [\d.]+ m"
            r"(?: \(originally [\d.]+ m in the source environment\))? \(approach from elevated path\)\.\s*$"
        )
        if re.search(c_alt_pat, description):
            cy_note = (
                f" (originally {b_cy} m in the source environment)"
                if t_cy != b_cy
                else ""
            )
            ch_note = (
                f" (originally {b_ch} simulation steps in the source environment)"
                if t_ch != b_ch
                else ""
            )
            new_line = (
                f"- **C altitude requirement**: Zone C only counts stay-steps if the agent's maximum y over the retained y-history window "
                f"(length up to {t_ch} simulation steps{ch_note}; shorter early in the episode) is at least {t_cy} m{cy_note} "
                f"(approach from elevated path)."
            )
            description = re.sub(c_alt_pat, new_line, description, count=1)

    # Force limit inside zone
    t_force = float(target_phys("force_limit_inside", _BASE_FORCE_LIMIT))
    b_force = float(base_phys("force_limit_inside", _BASE_FORCE_LIMIT))
    if t_force != b_force:
        pattern = (
            r"(- \*\*Force limit inside zone\*\*: Applying \*\*controller\*\* force with magnitude above )"
            r"[\d.]+ N \(Newtons\)"
            r"(?: \(originally [\d.]+ N \(Newtons\) in the source environment\))?"
            r" while inside a zone resets"
        )
        if re.search(pattern, description):
            description = re.sub(
                pattern,
                f"\\g<1>{_fmt_scalar_prompt(t_force)} N (Newtons) (originally {_fmt_scalar_prompt(b_force)} N (Newtons) in the source environment) "
                f"while inside a zone resets",
                description,
            )

    # Task Objective item 4: keep numeric speed/force in sync when either physics value differs from base.
    if t_speed != b_speed or t_force != b_force:
        speed_txt = (
            f"{t_speed} m/s (originally {b_speed} m/s in the source environment)"
            if t_speed != b_speed
            else f"{t_speed} m/s"
        )
        force_txt = (
            f"{_fmt_scalar_prompt(t_force)} N (originally {_fmt_scalar_prompt(b_force)} N in the source environment)"
            if t_force != b_force
            else f"{_fmt_scalar_prompt(t_force)} N"
        )
        pattern_obj_speed = (
            r"(speed cap \()([\d.]+ m/s(?: \(originally [\d.]+ m/s in the source environment\))?)(\))"
            r"(?= and force limit)"
        )
        if re.search(pattern_obj_speed, description):
            description = re.sub(
                pattern_obj_speed,
                lambda m, st=speed_txt: f"{m.group(1)}{st}{m.group(3)}",
                description,
            )
        pattern_obj_force = (
            r"force limit [\d.]+\s+N(?:\s+\(originally [\d.]+\s+N in the source environment\))? inside zones"
        )
        if re.search(pattern_obj_force, description):
            description = re.sub(
                pattern_obj_force,
                f"force limit {force_txt} inside zones",
                description,
            )

    # Peak repulsion scale (visible; synced with prompt.py and environment REPULSION_MAG)
    t_rep = float(target_phys("repulsion_mag", _BASE_REPULSION_MAG))
    b_rep = float(base_phys("repulsion_mag", _BASE_REPULSION_MAG))
    if t_rep != b_rep:
        pattern = (
            r"(The \*\*peak repulsion scale\*\* at each zone center is )"
            r"[\d.]+ N \(Newtons\)"
            r"(?: \(originally [\d.]+ N(?: \(Newtons\))? in the source environment\))?; strength decreases linearly"
        )
        if re.search(pattern, description):
            description = re.sub(
                pattern,
                f"\\g<1>{_fmt_repulsion_peak(t_rep)} N (Newtons) (originally {_fmt_repulsion_peak(b_rep)} N in the source environment); strength decreases linearly",
                description,
            )

    # Peak tangential repulsion scale (physics_config repulsion_tangential_mag)
    t_tan = float(target_phys("repulsion_tangential_mag", _BASE_REPULSION_TANGENTIAL_MAG))
    b_tan = float(base_phys("repulsion_tangential_mag", _BASE_REPULSION_TANGENTIAL_MAG))
    if t_tan != b_tan:
        tan_pat = (
            r"(The \*\*peak tangential \(swirling\) scale\*\* at each zone center is )"
            r"[\d.]+ N \(Newtons\)"
            r"(?: \(originally [\d.]+ N(?: \(Newtons\))? in the source environment\))?, with the same linear falloff to zero at the field edge\. "
            r"(The agent must navigate these fields)"
        )
        if re.search(tan_pat, description):
            description = re.sub(
                tan_pat,
                f"\\g<1>{_fmt_repulsion_peak(t_tan)} N (Newtons) (originally {_fmt_repulsion_peak(b_tan)} N in the source environment), "
                f"with the same linear falloff to zero at the field edge. \\g<2>",
                description,
            )

    # Repulsion field radius (physics_config)
    t_rr = float(target_phys("repulsion_range", _BASE_REPULSION_RANGE))
    b_rr = float(base_phys("repulsion_range", _BASE_REPULSION_RANGE))
    if t_rr != b_rr:
        rr_pat = (
            r"(The field extends to a radius of )([\d.]+) m"
            r"(?: \(originally [\d.]+ m in the source environment\))?(\.)"
        )
        if re.search(rr_pat, description):
            description = re.sub(
                rr_pat,
                f"\\g<1>{_fmt_scalar_prompt(t_rr)} m (originally {_fmt_scalar_prompt(b_rr)} m in the source environment)\\g<3>",
                description,
            )

    # Barrier x position (terrain_config) — visible in task description
    t_bx = _effective_terrain(target_terrain_config, base_terrain_config, "barrier_x", _BASE_BARRIER_X)
    b_bx = _base_terrain(base_terrain_config, "barrier_x", _BASE_BARRIER_X)
    if t_bx != b_bx:
        bpat = (
            r"(- \*\*Barrier\*\*: A narrow vertical gate \(half-width ≈ 0\.08 m\) at x = )"
            r"[\d.]+ m(?: \(originally [\d.]+ m in the source environment\))?, spanning y from 0 to 4 m, "
            r"blocks passage until it opens according to \*\*Barrier delay after A\*\* below\."
        )
        if re.search(bpat, description):
            description = re.sub(
                bpat,
                f"\\g<1>{t_bx} m (originally {b_bx} m in the source environment), spanning y from 0 to 4 m, "
                r"blocks passage until it opens according to **Barrier delay after A** below.",
                description,
            )
        auth_bpat = (
            r"(The vertical barrier is a separate static box at x = )"
            r"[\d.]+ m(?: \(originally [\d.]+ m in the source environment\))? \(same centerline x as the \*\*Barrier\*\* bullet below\)\."
        )
        if re.search(auth_bpat, description):
            description = re.sub(
                auth_bpat,
                f"\\g<1>{t_bx} m (originally {b_bx} m in the source environment) "
                f"(same centerline x as the **Barrier** bullet below).",
                description,
            )

    # Spawn and agent body (terrain_config) — visible in task description
    t_sx = _effective_terrain(target_terrain_config, base_terrain_config, "spawn_x", _BASE_SPAWN_X)
    b_sx = _base_terrain(base_terrain_config, "spawn_x", _BASE_SPAWN_X)
    t_sy = _effective_terrain(target_terrain_config, base_terrain_config, "spawn_y", _BASE_SPAWN_Y)
    b_sy = _base_terrain(base_terrain_config, "spawn_y", _BASE_SPAWN_Y)
    t_ar = _effective_terrain(target_terrain_config, base_terrain_config, "agent_radius", _BASE_AGENT_RADIUS)
    b_ar = _base_terrain(base_terrain_config, "agent_radius", _BASE_AGENT_RADIUS)
    t_am = _effective_terrain(target_terrain_config, base_terrain_config, "agent_mass", _BASE_AGENT_MASS)
    b_am = _base_terrain(base_terrain_config, "agent_mass", _BASE_AGENT_MASS)
    if (t_sx, t_sy, t_ar, t_am) != (b_sx, b_sy, b_ar, b_am):
        apat = (
            r"(?m)^- \*\*Agent\*\*: Spawn at \([^)]+\) m(?: \(originally \([^)]+\) m in the source environment\))?; "
            r"radius [\d.]+ m(?: \(originally [\d.]+ m in the source environment\))?; "
            r"mass [\d.]+ kg(?: \(originally [\d.]+ kg in the source environment\))?\. "
            r"(Linear damping \*\*[\d.]+\*\* and angular damping \*\*[\d.]+\*\* on the agent body \(Box2D\)\. "
            r"Other simulator-side motion details not listed here may still require inference from observations\.)$"
        )

        def _agent_repl(m: re.Match) -> str:
            passive = m.group(1)
            spawn_txt = f"Spawn at ({t_sx}, {t_sy}) m"
            if (t_sx, t_sy) != (b_sx, b_sy):
                spawn_txt += (
                    f" (originally ({b_sx}, {b_sy}) m in the source environment)"
                )
            rad_txt = f"radius {t_ar} m"
            if t_ar != b_ar:
                rad_txt = f"radius {t_ar} m (originally {b_ar} m in the source environment)"
            mass_txt = f"mass {t_am} kg"
            if t_am != b_am:
                mass_txt = f"mass {t_am} kg (originally {b_am} kg in the source environment)"
            return f"- **Agent**: {spawn_txt}; {rad_txt}; {mass_txt}. {passive}"

        if re.search(apat, description):
            description = re.sub(apat, _agent_repl, description, count=1)

    # Max controller force per axis (physics_config max_agent_force_per_axis)
    t_maf = float(target_phys("max_agent_force_per_axis", _BASE_MAX_AGENT_FORCE_PER_AXIS))
    b_maf = float(base_phys("max_agent_force_per_axis", _BASE_MAX_AGENT_FORCE_PER_AXIS))
    if t_maf != b_maf:
        maf_pat = (
            r"(- \*\*Agent max applied force\*\*: The controller can apply at most )"
            r"[\d.]+ N \(Newtons\) per axis per step"
            r"(?: \(originally [\d.]+ N \(Newtons\) per axis per step in the source environment\))?"
            r" \(same convention as \*\*apply_agent_force\*\* in the API below\)\."
        )
        if re.search(maf_pat, description):
            description = re.sub(
                maf_pat,
                f"\\g<1>{_fmt_scalar_prompt(t_maf)} N (Newtons) per axis per step "
                f"(originally {_fmt_scalar_prompt(b_maf)} N (Newtons) per axis per step in the source environment) "
                f"(same convention as **apply_agent_force** in the API below).",
                description,
            )

    friction_task_pat = r"(?m)^- \*\*Terrain & contact friction \(Box2D coefficients\)\*\*:.*$"
    if re.search(friction_task_pat, description):
        description = re.sub(
            friction_task_pat,
            _task_friction_line(target_terrain_config, base_terrain_config),
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
) -> str:
    """Update success criteria with visible changes using format: [new_value] (originally [old_value] in the source environment).

    Callers must pass base configs from the **source** (unmutated) environment.
    """
    criteria = base_success_criteria
    target_terrain_config = target_terrain_config or {}
    base_terrain_config = base_terrain_config or {}
    target_physics_config = target_physics_config or {}
    base_physics_config = base_physics_config or {}

    def target_phys(key: str, default: Any) -> Any:
        return target_physics_config.get(key, default)

    def base_phys(key: str, default: Any) -> Any:
        return _get_physics(base_physics_config, key, default)

    t_trigger = int(target_phys("trigger_stay_steps", _BASE_TRIGGER_STAY))
    b_trigger = int(base_phys("trigger_stay_steps", _BASE_TRIGGER_STAY))
    if t_trigger != b_trigger:
        pattern_act = (
            r"(- \*\*Activation duration\*\*: )(\d+) consecutive steps(?: \(originally \d+ consecutive steps in the source environment\))? "
            r"per zone \(with speed <= (.+?) and force <= (.+?)( inside zone\)\.)"
        )
        if re.search(pattern_act, criteria):
            criteria = re.sub(
                pattern_act,
                lambda m: (
                    f"{m.group(1)}{t_trigger} consecutive steps (originally {b_trigger} consecutive steps in the source environment) "
                    f"per zone (with speed <= {m.group(3)} and force <= {m.group(4)}{m.group(5)}"
                ),
                criteria,
            )

    t_speed = float(target_phys("speed_cap_inside", _BASE_SPEED_CAP))
    b_speed = float(base_phys("speed_cap_inside", _BASE_SPEED_CAP))
    t_force = float(target_phys("force_limit_inside", _BASE_FORCE_LIMIT))
    b_force = float(base_phys("force_limit_inside", _BASE_FORCE_LIMIT))
    if t_speed != b_speed:
        pattern = (
            r"(speed <= )([\d.]+) m/s(?: \(originally [\d.]+ m/s in the source environment\))?"
            r"( and force)"
        )
        if re.search(pattern, criteria):
            criteria = re.sub(
                pattern,
                f"\\g<1>{t_speed} m/s (originally {b_speed} m/s in the source environment)\\g<3>",
                criteria,
                count=1,
            )
    if t_force != b_force:
        pattern = (
            r"(force <= )([\d.]+)\s+N(?:\s+\(originally [\d.]+\s+N in the source environment\))?( inside zone\)\.)"
        )
        if re.search(pattern, criteria):
            criteria = re.sub(
                pattern,
                f"\\g<1>{_fmt_scalar_prompt(t_force)} N (originally {_fmt_scalar_prompt(b_force)} N in the source environment)\\g<3>",
                criteria,
                count=1,
            )

    t_cool = int(target_phys("cooldown_steps", _BASE_COOLDOWN))
    b_cool = int(base_phys("cooldown_steps", _BASE_COOLDOWN))
    if t_cool != b_cool:
        pattern = (
            r"(- \*\*Cooldown\*\*: )\d+ steps(?: \(originally \d+ steps in the source environment\))? "
            r"between triggers\."
        )
        if re.search(pattern, criteria):
            criteria = re.sub(
                pattern,
                f"\\g<1>{t_cool} steps (originally {b_cool} steps in the source environment) between triggers.",
                criteria,
            )

    t_barrier = int(target_phys("barrier_delay_steps", _BASE_BARRIER_DELAY))
    b_barrier = int(base_phys("barrier_delay_steps", _BASE_BARRIER_DELAY))
    if t_barrier != b_barrier:
        pattern = (
            r"(- \*\*Barrier delay\*\*: )\d+ steps(?: \(originally \d+ steps in the source environment\))? "
            r"after A before gate opens\."
        )
        if re.search(pattern, criteria):
            criteria = re.sub(
                pattern,
                f"\\g<1>{t_barrier} steps (originally {b_barrier} steps in the source environment) after A before gate opens.",
                criteria,
            )

    t_bx_c = _effective_terrain(target_terrain_config, base_terrain_config, "barrier_x", _BASE_BARRIER_X)
    b_bx_c = _base_terrain(base_terrain_config, "barrier_x", _BASE_BARRIER_X)
    if t_bx_c != b_bx_c:
        crit_geom_pat = (
            r"(- \*\*Barrier geometry\*\*: Vertical gate at x = )"
            r"[\d.]+ m(?: \(originally [\d.]+ m in the source environment\))? \(centerline\), half-width ≈ 0\.08 m, spanning y from 0 to 4 m; "
            r"blocks passage until opened per \*\*Barrier delay\*\* below\."
        )
        if re.search(crit_geom_pat, criteria):
            criteria = re.sub(
                crit_geom_pat,
                f"\\g<1>{t_bx_c} m (originally {b_bx_c} m in the source environment) (centerline), half-width ≈ 0.08 m, spanning y from 0 to 4 m; "
                r"blocks passage until opened per **Barrier delay** below.",
                criteria,
            )

    t_mafc = float(target_phys("max_agent_force_per_axis", _BASE_MAX_AGENT_FORCE_PER_AXIS))
    b_mafc = float(base_phys("max_agent_force_per_axis", _BASE_MAX_AGENT_FORCE_PER_AXIS))
    if t_mafc != b_mafc:
        maf_crit_pat = (
            r"(- \*\*Agent max applied force\*\*: At most )"
            r"[\d.]+ N per axis per simulation step"
            r"(?: \(originally [\d.]+ N per axis per simulation step in the source environment\))?"
            r" \(\*\*apply_agent_force\*\*\), matching the task API\."
        )
        if re.search(maf_crit_pat, criteria):
            criteria = re.sub(
                maf_crit_pat,
                f"\\g<1>{_fmt_scalar_prompt(t_mafc)} N per axis per simulation step "
                f"(originally {_fmt_scalar_prompt(b_mafc)} N per axis per simulation step in the source environment) "
                f"(**apply_agent_force**), matching the task API.",
                criteria,
            )

    t_ab = int(target_phys("recent_a_for_b", _BASE_RECENT_A_FOR_B))
    b_ab = int(base_phys("recent_a_for_b", _BASE_RECENT_A_FOR_B))
    t_bc = int(target_phys("recent_b_for_c", _BASE_RECENT_B_FOR_C))
    b_bc = int(base_phys("recent_b_for_c", _BASE_RECENT_B_FOR_C))
    if t_ab != b_ab or t_bc != b_bc:
        tw_pattern = (
            r"(- \*\*Temporal windows\*\*: A to B within )\d+ steps"
            r"(?: \(originally \d+ steps in the source environment\))?; B to C within \d+ steps"
            r"(?: \(originally \d+ steps in the source environment\))?(\.)"
        )

        def _tw_repl(m: re.Match) -> str:
            cur = m.group(0)
            ab_m = re.search(r"A to B within (\d+) steps", cur)
            bc_m = re.search(r"B to C within (\d+) steps", cur)
            cur_ab = int(ab_m.group(1)) if ab_m else b_ab
            cur_bc = int(bc_m.group(1)) if bc_m else b_bc
            ab_new = t_ab if t_ab != b_ab else cur_ab
            bc_new = t_bc if t_bc != b_bc else cur_bc
            ab_tag = f" (originally {b_ab} steps in the source environment)" if t_ab != b_ab else ""
            bc_tag = f" (originally {b_bc} steps in the source environment)" if t_bc != b_bc else ""
            return (
                f"- **Temporal windows**: A to B within {ab_new} steps{ab_tag}; "
                f"B to C within {bc_new} steps{bc_tag}{m.group(2)}"
            )

        if re.search(tw_pattern, criteria):
            criteria = re.sub(tw_pattern, _tw_repl, criteria)

    t_cy = float(target_phys("c_required_max_y", _BASE_C_REQUIRED_MAX_Y))
    b_cy = float(base_phys("c_required_max_y", _BASE_C_REQUIRED_MAX_Y))
    t_ch = int(target_phys("c_high_history", _BASE_C_HIGH_HISTORY))
    b_ch = int(base_phys("c_high_history", _BASE_C_HIGH_HISTORY))
    if t_cy != b_cy or t_ch != b_ch:
        pattern = (
            r"(?m)^- \*\*C altitude\*\*: Recent max y >= [\d.]+(?: \(originally [\d.]+ m in the source environment\))? "
            r"m over a rolling window of up to \d+ simulation steps"
            r"(?: \(originally \d+ simulation steps in the source environment\))? "
            r"\(all elapsed steps count until the buffer is full\)\.\s*$"
        )
        if re.search(pattern, criteria):
            ypart = f"{t_cy} m"
            if t_cy != b_cy:
                ypart += f" (originally {b_cy} m in the source environment)"
            spart = f"{t_ch} simulation steps"
            if t_ch != b_ch:
                spart = (
                    f"{t_ch} simulation steps (originally {b_ch} simulation steps in the source environment)"
                )
            new_line = (
                f"- **C altitude**: Recent max y >= {ypart} over a rolling window of up to {spart} "
                f"(all elapsed steps count until the buffer is full)."
            )
            criteria = re.sub(pattern, new_line, criteria, count=1)

    t_rr = float(target_phys("repulsion_range", _BASE_REPULSION_RANGE))
    b_rr = float(base_phys("repulsion_range", _BASE_REPULSION_RANGE))
    if t_rr != b_rr:
        rr_crit_pat = (
            r"(field radius )([\d.]+) m"
            r"(?: \(originally [\d.]+ m in the source environment\))? "
            r"(\(linear falloff\)\.)"
        )
        if re.search(rr_crit_pat, criteria):
            criteria = re.sub(
                rr_crit_pat,
                f"\\g<1>{_fmt_scalar_prompt(t_rr)} m (originally {_fmt_scalar_prompt(b_rr)} m in the source environment) \\g<3>",
                criteria,
            )

    t_rep = float(target_phys("repulsion_mag", _BASE_REPULSION_MAG))
    b_rep = float(base_phys("repulsion_mag", _BASE_REPULSION_MAG))
    if t_rep != b_rep:
        pat_rep = (
            r"(Peak scale \(radial component\) )"
            r"[\d.]+(?: N)?(?: \(originally [\d.]+(?: N)? in the source environment\))?"
            r"( at zone centers;)"
        )
        if re.search(pat_rep, criteria):
            criteria = re.sub(
                pat_rep,
                f"\\g<1>{_fmt_repulsion_peak(t_rep)} N (originally {_fmt_repulsion_peak(b_rep)} N in the source environment)\\g<2>",
                criteria,
            )

    t_tan = float(target_phys("repulsion_tangential_mag", _BASE_REPULSION_TANGENTIAL_MAG))
    b_tan = float(base_phys("repulsion_tangential_mag", _BASE_REPULSION_TANGENTIAL_MAG))
    if t_tan != b_tan:
        pat_tan = (
            r"(peak tangential \(swirling\) scale )"
            r"[\d.]+(?: N)?(?: \(originally [\d.]+(?: N)? in the source environment\))? "
            r"(; field radius )"
        )
        if re.search(pat_tan, criteria):
            criteria = re.sub(
                pat_tan,
                f"\\g<1>{_fmt_repulsion_peak(t_tan)} N (originally {_fmt_repulsion_peak(b_tan)} N in the source environment)\\g<2>",
                criteria,
            )

    friction_crit_pat = r"(?m)^- \*\*Friction\*\*:.*$"
    if re.search(friction_crit_pat, criteria):
        criteria = re.sub(
            friction_crit_pat,
            _criteria_friction_line(target_terrain_config, base_terrain_config),
            criteria,
            count=1,
        )

    return criteria


def get_c05_curriculum_stages() -> List[Dict[str, Any]]:
    """Returns ordered stage configs for C-05: The Logic Lock task variants."""
    UNIFORM_SUFFIX = """
## Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables **MIGHT** have changed from the initial environment, **NOT ALL** of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
- **Regional speed limits**: Constraints on the maximum velocity allowed within trigger zones to count progress.
- **Repulsive field strength**: Alterations in the intensity of forces pushing the agent away from targets.
- **Repulsive field geometry**: The spatial pattern of repulsive forces near targets may differ from the baseline.
- **Input sensitivity thresholds**: High in-zone forces may interact with the trigger mechanism in non-obvious ways; rely on observed dwell behavior rather than assumptions.
- **Surface friction anomalies**: Significant changes in surface grip on flat ground, ramps, or platforms.
- **Environmental response timing**: Delays in barrier activation or system feedback after a trigger may vary.
- **Activation duration**: The required continuous time to stay within a zone to successfully trigger it.
- **Temporal sequencing windows**: Changes in the allowed time between sequential interactions (e.g., A to B or B to C).
- **State persistence requirements**: Changes in how long prior motion history (e.g., elevated trajectory) is remembered for downstream triggers.
- **Ambient wind / lateral forcing**: Time-varying lateral disturbances may or may not be present; magnitudes are not disclosed.

**Discovery via feedback**: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; use run feedback to infer effective constraints and adapt your strategy.
"""
    return [
        {
            "stage_id": "Stage-1",
            "title": "Strict zone speed, long temporal windows",
            "mutation_description": "Very low zone speed cap; A→B, B→C, and C history windows widened for solvability.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {},
            "physics_config": {
                "speed_cap_inside": 0.05,
                "recent_a_for_b": 5000,
                "recent_b_for_c": 5000,
                "c_high_history": 5000,
            },
        },
        {
            "stage_id": "Stage-2",
            "title": "Long dwell, strong repulsion, strict zone speed",
            "mutation_description": "Longer dwell requirement, stronger repulsion, low zone speed; temporal windows still widened.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {},
            "physics_config": {
                "trigger_stay_steps": 300,
                "speed_cap_inside": 0.05,
                "repulsion_mag": 40.0,
                "recent_a_for_b": 5000,
                "recent_b_for_c": 5000,
                "c_high_history": 5000,
            },
        },
        {
            "stage_id": "Stage-3",
            "title": "Vortex & Sensitive Trigger",
            "mutation_description": "Stage variant with tangential repulsion, force cap in zones, and ramp friction change.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "ramp_friction": 0.05,
            },
            "physics_config": {
                "speed_cap_inside": 0.15,
                "repulsion_mag": 45.0,
                "repulsion_tangential_mag": 30.0,
                "force_limit_inside": 45.0,
                "trigger_stay_steps": 60,
                "recent_a_for_b": 5000,
                "recent_b_for_c": 5000,
                "c_high_history": 5000,
            },
        },
        {
            "stage_id": "Stage-4",
            "title": "Compound friction, barrier delay, repulsion",
            "mutation_description": "Lower ground and ramp friction, longer barrier delay after A, long dwell, stronger repulsion including tangential component.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "ramp_friction": 0.02,
                "ground_friction": 0.2,
            },
            "physics_config": {
                "speed_cap_inside": 0.08,
                "repulsion_mag": 45.0,
                "repulsion_tangential_mag": 40.0,
                "force_limit_inside": 60.0,
                "trigger_stay_steps": 120,
                "barrier_delay_steps": 350,
                "recent_a_for_b": 5000,
                "recent_b_for_c": 5000,
                "c_high_history": 5000,
            },
        },
    ]
