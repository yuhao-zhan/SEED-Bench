"""
C-03: The Seeker task curriculum stages (mutations).

Four mutated tasks in total: Stage-1 through Stage-4, difficulty ascending.

mutation_description is for logs/orchestration only — not shown to the agent.
"""

from __future__ import annotations
import importlib.util
import os
import re
from typing import Any, Dict, List

_stages_dir = os.path.dirname(os.path.abspath(__file__))
_spec_c03_st = importlib.util.spec_from_file_location(
    "c03_environment_stages", os.path.join(_stages_dir, "environment.py")
)
_c03_env_st = importlib.util.module_from_spec(_spec_c03_st)
_spec_c03_st.loader.exec_module(_c03_env_st)
DEFAULT_ACTIVATION_ZONE_X_MIN = _c03_env_st.ACTIVATION_ZONE_X_MIN
DEFAULT_ACTIVATION_ZONE_X_MAX = _c03_env_st.ACTIVATION_ZONE_X_MAX
DEFAULT_ACTIVATION_REQUIRED_STEPS = _c03_env_st.ACTIVATION_REQUIRED_STEPS
DEFAULT_HEADING_REF_MIN_TARGET_SPEED = _c03_env_st.HEADING_REFERENCE_MIN_TARGET_SPEED
RENDEZVOUS_DISTANCE_DEFAULT = _c03_env_st.RENDEZVOUS_DISTANCE_DEFAULT

# Defaults from environment.py (single source of truth)
DEFAULT_IMPULSE_BUDGET = _c03_env_st.IMPULSE_BUDGET
DEFAULT_TRACK_DISTANCE = _c03_env_st.TRACK_DISTANCE_DEFAULT
DEFAULT_RENDEZVOUS_REL_SPEED = _c03_env_st.RENDEZVOUS_REL_SPEED_DEFAULT
DEFAULT_TARGET_SPEED = 1.5
DEFAULT_GROUND_FRICTION = 0.4
DEFAULT_SPAWN_X = 11.0
DEFAULT_SPAWN_Y = 1.35
DEFAULT_SLOTS_PHASE1 = list(_c03_env_st.SLOTS_PHASE1)
DEFAULT_SLOTS_PHASE2 = list(_c03_env_st.SLOTS_PHASE2)
DEFAULT_LINEAR_DAMPING = 0.5
DEFAULT_ANGULAR_DAMPING = 0.5
DEFAULT_GRAVITY_XY = (0.0, -10.0)
DEFAULT_COOLDOWN_THRESHOLD = _c03_env_st.COOLDOWN_THRESHOLD
DEFAULT_COOLDOWN_MAX_THRUST = _c03_env_st.COOLDOWN_MAX_THRUST
DEFAULT_COOLDOWN_STEPS = _c03_env_st.COOLDOWN_STEPS
DEFAULT_MAX_THRUST_MAGNITUDE = _c03_env_st.MAX_THRUST_MAGNITUDE
DEFAULT_HEADING_TOLERANCE_DEG = _c03_env_st.RENDEZVOUS_HEADING_TOLERANCE_DEG_DEFAULT
DEFAULT_BLIND_ZONE_X_MIN = _c03_env_st.BLIND_ZONE_X_MIN
DEFAULT_BLIND_ZONE_X_MAX = _c03_env_st.BLIND_ZONE_X_MAX
DEFAULT_SPEED_BLIND_THRESHOLD = _c03_env_st.SPEED_BLIND_THRESHOLD
DEFAULT_RENDEZVOUS_DISTANCE = RENDEZVOUS_DISTANCE_DEFAULT
DEFAULT_RENDEZVOUS_ZONE_X_MIN = _c03_env_st.RENDEZVOUS_ZONE_X_MIN
DEFAULT_RENDEZVOUS_ZONE_X_MAX = _c03_env_st.RENDEZVOUS_ZONE_X_MAX
DEFAULT_GROUND_Y_TOP = _c03_env_st.DEFAULT_GROUND_Y_TOP
DEFAULT_SEEKER_MASS = 20.0
DEFAULT_SEEKER_RADIUS = 0.35
DEFAULT_TARGET_START_X = 12.0
DEFAULT_TARGET_START_Y = 2.0
DEFAULT_TARGET_CHANGE_INTERVAL = 1.2

# Static corridor boxes use these fixture material values in environment._create_obstacles (always).
STATIC_OBSTACLE_FIXTURE_SNIPPET = "fixture friction 0.5, restitution 0.1"


def _gravity_tuple(physics_cfg: Dict[str, Any]) -> tuple:
    physics_cfg = physics_cfg or {}
    g = physics_cfg.get("gravity", DEFAULT_GRAVITY_XY)
    if isinstance(g, (list, tuple)) and len(g) >= 2:
        return (float(g[0]), float(g[1]))
    return DEFAULT_GRAVITY_XY


# Default ice layout (from environment.py; must match prompt baseline)
DEFAULT_ICE_ZONES = [tuple(z) for z in _c03_env_st.ICE_ZONES]


def _ice_zones_key(zones) -> tuple:
    if not zones:
        return ()
    out = []
    for item in zones:
        (cx, cy, hw, hh), mu = item
        out.append(
            (
                round(float(cx), 6),
                round(float(cy), 6),
                round(float(hw), 6),
                round(float(hh), 6),
                round(float(mu), 6),
            )
        )
    return tuple(out)


def _fmt_ice_xy(x: float, y: float) -> str:
    """Match prompt.py ice layout: x to one decimal, y to two (e.g. 9.0, 1.25)."""
    return f"({float(x):.1f}, {float(y):.2f})"


def _fmt_ice_half(hw: float, hh: float) -> str:
    """Half-extents like 1.0×0.12 — width one decimal, height two when needed."""
    return f"{float(hw):.1f}×{float(hh):.2f}"


def _format_ice_sentence(zones) -> str:
    if not zones:
        return "none"
    zlist = list(zones)
    if len(zlist) == 2:
        (ax, ay, ahw, ahh), mu0 = zlist[0]
        (bx, by, bhw, bhh), mu1 = zlist[1]
        if (
            abs(float(mu0) - float(mu1)) < 1e-12
            and abs(float(ahw) - float(bhw)) < 1e-12
            and abs(float(ahh) - float(bhh)) < 1e-12
        ):
            return (
                f"Two low-friction patches centered at {_fmt_ice_xy(ax, ay)} and "
                f"{_fmt_ice_xy(bx, by)} m, half-size {_fmt_ice_half(ahw, ahh)} m, "
                f"with **friction coefficient {float(mu0)}** and **restitution 0** on the patch fixtures "
                f"(seeker–patch contact)"
            )
    parts = []
    for (cx, cy, hw, hh), mu in zlist:
        parts.append(
            f"center {_fmt_ice_xy(cx, cy)} m, half-extents {_fmt_ice_half(hw, hh)} m, "
            f"**friction coefficient {float(mu)}**, **restitution 0**"
        )
    return (
        "Low-friction ice patches: " + "; ".join(parts) + " on the patch fixtures (seeker–patch contact)"
    )


def _replace_ice_task_line(description: str, body: str) -> str:
    """Replace the single `- **Ice patches**: ...` line; body includes trailing period."""
    return re.sub(r"(- \*\*Ice patches\*\*: )[^\n]*", rf"\g<1>{body}", description, count=1)

STATIC_BOXES_PROMPT_SNIPPET = (
    "centers (7.5, 1.5), (14.0, 1.5), (20.5, 1.5) m, half-extents 0.3×0.5 m, "
    "fixture friction 0.5, restitution 0.1"
)


def _slot_window_bounds(slots_phase1: List, slots_phase2: List) -> tuple:
    """Return (lo1, hi1, lo2, hi2) for phase1 and phase2 windows."""
    def bounds(slots):
        if not slots:
            return 3700, 4800
        try:
            return min(s[0] for s in slots), max(s[1] for s in slots)
        except (TypeError, IndexError):
            return 3700, 4800
    p1_lo, p1_hi = bounds(slots_phase1)
    p2_lo, p2_hi = bounds(slots_phase2)
    return p1_lo, p1_hi, p2_lo, p2_hi


def _format_slot_bands(slots: List) -> str:
    """Format slot list as '[lo, hi], [lo, hi], ...' for prompt."""
    if not slots:
        return ""
    return ", ".join(f"[{int(s[0])}, {int(s[1])}]" for s in slots)


def _require_pristine_prompt_text(text: str, *, label: str) -> None:
    if "(originally " in text and " in the source environment)" in text:
        raise ValueError(
            f"{label} must be pristine: it already contains "
            "'(originally … in the source environment)'. "
            "Pass the unmodified base strings from prompt.py, not a prior mutation output."
        )


def update_task_description_for_visible_changes(
    base_description: str,
    target_terrain_config: Dict[str, Any],
    base_terrain_config: Dict[str, Any],
    target_physics_config: Dict[str, Any] = None,
    base_physics_config: Dict[str, Any] = None,
) -> str:
    """
    Update task description with visible changes using format:
    [new_value] (originally [old_value] in the source environment).
    """
    _require_pristine_prompt_text(base_description, label="base_description (task_description)")
    description = base_description
    target_terrain_config = target_terrain_config or {}
    base_terrain_config = base_terrain_config or {}
    tp = dict(target_physics_config or {})
    bp = dict(base_physics_config or {})

    # Linear / angular damping (visible defaults in prompt; physics_config may override)
    base_ld = float(bp.get("linear_damping", DEFAULT_LINEAR_DAMPING))
    base_ad = float(bp.get("angular_damping", DEFAULT_ANGULAR_DAMPING))
    target_ld = float(tp.get("linear_damping", base_ld))
    target_ad = float(tp.get("angular_damping", base_ad))
    if abs(target_ld - base_ld) > 1e-9 or abs(target_ad - base_ad) > 1e-9:
        # Baseline or remutation: optional "(originally …)" may use plain or legacy **bold** numerics.
        _orig_plain = r"(?: \(originally (?:\*\*)?\d+(?:\.\d+)?(?:\*\*)? in the source environment\))?"
        damp_pat = (
            r"Default \*\*linear damping (\d+(?:\.\d+)?)\*\*"
            + _orig_plain
            + r" and \*\*angular damping (\d+(?:\.\d+)?)\*\*"
            + _orig_plain
            + r" on the seeker body \(Box2D\)\. Follow the numerics printed for your specific run\."
        )
        if re.search(damp_pat, description):
            replacement = (
                f"Default **linear damping {target_ld:.1f}** (originally {base_ld:.1f} in the source environment) "
                f"and **angular damping {target_ad:.1f}** (originally {base_ad:.1f} in the source environment) "
                f"on the seeker body (Box2D). Follow the numerics printed for your specific run."
            )
            description = re.sub(damp_pat, replacement, description, count=1)

    # Gravity: when mutated vs source, do not disclose any numeric g vector (hidden physics).
    tg, bg = _gravity_tuple(tp), _gravity_tuple(bp)
    if tg != bg:
        grav_infer_pat = (
            r"\- \*\*Effective acceleration field\*\*: Infer from observed motion; "
            r"no numeric acceleration vector is disclosed here\.(?:\n|$)"
        )
        replacement_grav = (
            "- **Effective acceleration field**: Infer from observed motion; "
            "no numeric acceleration vector is disclosed here.\n"
        )
        if re.search(grav_infer_pat, description):
            description = re.sub(
                grav_infer_pat,
                replacement_grav,
                description,
                count=1,
            )

    # Activation gate (x-band and consecutive-step dwell)
    base_az0 = float(
        base_terrain_config.get("activation_zone_x_min", DEFAULT_ACTIVATION_ZONE_X_MIN)
    )
    base_az1 = float(
        base_terrain_config.get("activation_zone_x_max", DEFAULT_ACTIVATION_ZONE_X_MAX)
    )
    base_ast = int(
        base_terrain_config.get("activation_required_steps", DEFAULT_ACTIVATION_REQUIRED_STEPS)
    )
    target_az0 = float(target_terrain_config.get("activation_zone_x_min", base_az0))
    target_az1 = float(target_terrain_config.get("activation_zone_x_max", base_az1))
    target_ast = int(target_terrain_config.get("activation_required_steps", base_ast))
    if (target_az0, target_az1, target_ast) != (base_az0, base_az1, base_ast):
        act_gate_pat = (
            r"(- \*\*Activation Gate\*\*: Rendezvous only counts after the seeker \"activates\" by staying in x in )"
            r"\[(\d+(?:\.\d+)?), (\d+(?:\.\d+)?)\] m"
            r"(?: \(originally \[[\d., ]+\] m in the source environment\))?"
            r" for at least (\d+) consecutive steps"
            r"(?: \(originally \d+ in the source environment\))?"
            r"(\.)"
        )
        if re.search(act_gate_pat, description):
            x_disp = f"[{target_az0:.1f}, {target_az1:.1f}] m"
            if abs(target_az0 - base_az0) > 1e-9 or abs(target_az1 - base_az1) > 1e-9:
                x_disp += (
                    f" (originally [{base_az0:.1f}, {base_az1:.1f}] m in the source environment)"
                )
            step_disp = f"for at least {target_ast} consecutive steps"
            if target_ast != base_ast:
                step_disp += f" (originally {base_ast} in the source environment)"
            description = re.sub(
                act_gate_pat,
                f"\\g<1>{x_disp} {step_disp}\\g<5>",
                description,
                count=1,
            )

    # Heading reference min target speed (evaluator / prompt)
    base_href = float(
        base_terrain_config.get(
            "heading_reference_min_target_speed", DEFAULT_HEADING_REF_MIN_TARGET_SPEED
        )
    )
    target_href = float(
        target_terrain_config.get("heading_reference_min_target_speed", base_href)
    )
    if abs(target_href - base_href) > 1e-12:
        href_obj_pat = (
            r"(when target speed ≥ )(\d+(?:\.\d+)?)( m/s)"
            r"(?: \(originally \d+(?:\.\d+)? m/s in the source environment\))?"
            r"(, otherwise seeker-to-target direction\.)"
        )
        if re.search(href_obj_pat, description):
            description = re.sub(
                href_obj_pat,
                f"\\g<1>{target_href:g}\\g<3> (originally {base_href:g} m/s in the source environment)\\g<4>",
                description,
                count=1,
            )

    # Target nominal speed (1.5 m/s)
    target_speed = float(target_terrain_config.get("target_speed", DEFAULT_TARGET_SPEED))
    base_speed = float(base_terrain_config.get("target_speed", DEFAULT_TARGET_SPEED))
    if target_speed != base_speed:
        pattern = (
            r"(Target nominal speed up to )\d+(?:\.\d+)?( m/s)"
            r"(?: \(originally \d+(?:\.\d+)? m/s in the source environment\))?(\.)"
        )
        if re.search(pattern, description):
            description = re.sub(
                pattern,
                f"\\g<1>{target_speed:.1f}\\g<2> (originally {base_speed:.1f} m/s in the source environment)\\g<3>",
                description,
                count=1,
            )

    # Static boxes -> none when target has []
    target_obstacles = target_terrain_config.get("obstacles")
    if target_obstacles is not None and len(target_obstacles) == 0:
        esc = re.escape(STATIC_BOXES_PROMPT_SNIPPET)
        # Static line ends with "." only; collision rule is a separate sentence in prompt.py.
        pattern = rf"(\*\*Static boxes\*\*: ){esc}(\.)"
        if re.search(pattern, description):
            description = re.sub(
                pattern,
                rf"\1none (originally {STATIC_BOXES_PROMPT_SNIPPET} in the source environment)\2",
                description,
                count=1,
            )

    # Ice patches: removal, or non-empty layout/friction change vs base
    base_ice = base_terrain_config.get("ice_zones", None)
    if base_ice is None:
        base_ice = list(DEFAULT_ICE_ZONES)
    if "ice_zones" in target_terrain_config:
        target_ice = target_terrain_config["ice_zones"]
        if len(target_ice) == 0:
            body = f"none (originally {_format_ice_sentence(base_ice)} in the source environment)."
            if re.search(r"- \*\*Ice patches\*\*:", description):
                description = _replace_ice_task_line(description, body)
        elif _ice_zones_key(target_ice) != _ice_zones_key(base_ice):
            body = (
                f"{_format_ice_sentence(target_ice)} "
                f"(originally {_format_ice_sentence(base_ice)} in the source environment)."
            )
            if re.search(r"- \*\*Ice patches\*\*:", description):
                description = _replace_ice_task_line(description, body)

    # Spawn position (x, y)
    target_sx = float(target_terrain_config.get("spawn_x", DEFAULT_SPAWN_X))
    target_sy = float(target_terrain_config.get("spawn_y", DEFAULT_SPAWN_Y))
    base_sx = float(base_terrain_config.get("spawn_x", DEFAULT_SPAWN_X))
    base_sy = float(base_terrain_config.get("spawn_y", DEFAULT_SPAWN_Y))
    if (target_sx, target_sy) != (base_sx, base_sy):
        spawn_re = re.compile(
            r"The seeker spawns at \(\d+(?:\.\d+)?, \d+(?:\.\d+)?\) m \(x, y\)"
            r"(?: \(originally \([\d., ]+\)(?: m \(x, y\))? in the source environment\))?(\.)"
        )
        if spawn_re.search(description):
            description = spawn_re.sub(
                f"The seeker spawns at ({target_sx:.1f}, {target_sy:.2f}) m (x, y) "
                f"(originally ({base_sx:.1f}, {base_sy:.2f}) m (x, y) in the source environment).",
                description,
                count=1,
            )

    # Seeker mass and radius
    base_sm = float(base_terrain_config.get("seeker_mass", DEFAULT_SEEKER_MASS))
    base_sr = float(base_terrain_config.get("seeker_radius", DEFAULT_SEEKER_RADIUS))
    target_sm = float(target_terrain_config.get("seeker_mass", base_sm))
    target_sr = float(target_terrain_config.get("seeker_radius", base_sr))
    if abs(target_sm - base_sm) > 1e-9 or abs(target_sr - base_sr) > 1e-9:
        seeker_mr_pat = (
            r"(Mass )(\d+(?:\.\d+)?)( kg, radius )(\d+(?:\.\d+)?)( m\.)"
            r"(?: \(originally \d+(?:\.\d+)? kg, \d+(?:\.\d+)? m in the source environment\))?"
        )
        if re.search(seeker_mr_pat, description):
            description = re.sub(
                seeker_mr_pat,
                f"Mass {target_sm:.1f} kg, radius {target_sr:.2f} m "
                f"(originally {base_sm:.1f} kg, {base_sr:.2f} m in the source environment).",
                description,
                count=1,
            )

    # Target default start position
    base_tx = float(base_terrain_config.get("target_start_x", DEFAULT_TARGET_START_X))
    base_ty = float(base_terrain_config.get("target_start_y", DEFAULT_TARGET_START_Y))
    target_tx = float(target_terrain_config.get("target_start_x", base_tx))
    target_ty = float(target_terrain_config.get("target_start_y", base_ty))
    if abs(target_tx - base_tx) > 1e-9 or abs(target_ty - base_ty) > 1e-9:
        tgt_start_pat = (
            r"(The target starts at )\*\*\((\d+(?:\.\d+)?), (\d+(?:\.\d+)?)\) m\*\* \(defaults\)"
            r"(?: \(originally \*\*\([\d., ]+\) m\*\* in the source environment\))?(\.)"
        )
        if re.search(tgt_start_pat, description):
            description = re.sub(
                tgt_start_pat,
                f"\\g<1>**({target_tx:.1f}, {target_ty:.1f}) m** (defaults) "
                f"(originally **({base_tx:.1f}, {base_ty:.1f}) m** in the source environment)\\g<4>",
                description,
                count=1,
            )

    # Target nominal direction change interval (~seconds)
    base_tci = float(base_terrain_config.get("target_change_interval", DEFAULT_TARGET_CHANGE_INTERVAL))
    target_tci = float(target_terrain_config.get("target_change_interval", base_tci))
    if abs(target_tci - base_tci) > 1e-9:
        tci_pat = (
            r"(Nominal direction changes every ~)\d+(?:\.\d+)?( s\.)"
            r"(?: \(originally \d+(?:\.\d+)? in the source environment\))?"
        )
        if re.search(tci_pat, description):
            description = re.sub(
                tci_pat,
                f"\\g<1>{target_tci:.1f}\\g<2> (originally {base_tci:.1f} in the source environment)",
                description,
                count=1,
            )

    # Impulse budget (Task Environment)
    target_impulse = float(target_terrain_config.get("impulse_budget", DEFAULT_IMPULSE_BUDGET))
    base_impulse = float(base_terrain_config.get("impulse_budget", DEFAULT_IMPULSE_BUDGET))
    if target_impulse != base_impulse:
        impulse_pat = (
            r"(Total thrust impulse is limited to )\d+(?:\.\d+)? N·s"
            r"(?: \(originally \d+(?:\.\d+)? N·s in the source environment\))?"
            r"(; \*\*reaching or exceeding\*\* that budget fails the run\.)"
        )
        if re.search(impulse_pat, description):
            description = re.sub(
                impulse_pat,
                f"\\g<1>{target_impulse:.0f} N·s (originally {base_impulse:.0f} N·s in the source environment)\\g<2>",
                description,
                count=1,
            )

    # Track distance (Task Objective)
    target_track = float(target_terrain_config.get("track_distance", DEFAULT_TRACK_DISTANCE))
    base_track = float(base_terrain_config.get("track_distance", DEFAULT_TRACK_DISTANCE))
    if target_track != base_track:
        track_pat = (
            r"(3\. \*\*Tracking\*\*: Maintain distance <= )\d+(?:\.\d+)? m"
            r"(?: \(originally \d+(?:\.\d+)? m in the source environment\))?"
            r"( from the target after the second rendezvous\.)"
        )
        if re.search(track_pat, description):
            description = re.sub(
                track_pat,
                f"\\g<1>{target_track:.1f} m (originally {base_track:.1f} m in the source environment)\\g<2>",
                description,
                count=1,
            )

    # Rendezvous relative speed (Task Objective)
    target_rel = float(target_terrain_config.get("rendezvous_rel_speed", DEFAULT_RENDEZVOUS_REL_SPEED))
    base_rel = float(base_terrain_config.get("rendezvous_rel_speed", DEFAULT_RENDEZVOUS_REL_SPEED))
    if abs(target_rel - base_rel) > 1e-9:
        rel_pat = (
            r"(\(relative speed < )\d+(?:\.\d+)? m/s"
            r"(?: \(originally \d+(?:\.\d+)? m/s in the source environment\))?(\))"
        )
        if re.search(rel_pat, description):
            description = re.sub(
                rel_pat,
                f"\\g<1>{target_rel:.2f} m/s (originally {base_rel:.2f} m/s in the source environment)\\g<2>",
                description,
                count=1,
            )

    # Rendezvous capture range (Task Objective)
    base_rd = float(base_terrain_config.get("rendezvous_distance", DEFAULT_RENDEZVOUS_DISTANCE))
    target_rd = float(target_terrain_config.get("rendezvous_distance", base_rd))
    if abs(target_rd - base_rd) > 1e-9:
        # "(originally …)" sits after " m" (baseline has no clause; remutations may already have one).
        rd_pat = (
            r"(distance to target ≤ )\d+(?:\.\d+)?"
            r"( m)"
            r"(?: \(originally \d+(?:\.\d+)? m in the source environment\))?"
            r"(, matching velocity)"
        )
        if re.search(rd_pat, description):
            description = re.sub(
                rd_pat,
                f"\\g<1>{target_rd:.1f}\\g<2> (originally {base_rd:.1f} m in the source environment)\\g<3>",
                description,
                count=1,
            )

    # Rendezvous x-band (Task Objective)
    base_rzx0 = float(base_terrain_config.get("rendezvous_zone_x_min", DEFAULT_RENDEZVOUS_ZONE_X_MIN))
    base_rzx1 = float(base_terrain_config.get("rendezvous_zone_x_max", DEFAULT_RENDEZVOUS_ZONE_X_MAX))
    target_rzx0 = float(target_terrain_config.get("rendezvous_zone_x_min", base_rzx0))
    target_rzx1 = float(target_terrain_config.get("rendezvous_zone_x_max", base_rzx1))
    if abs(target_rzx0 - base_rzx0) > 1e-9 or abs(target_rzx1 - base_rzx1) > 1e-9:
        rzx_pat = (
            r"(Rendezvous only counts with seeker x in )\[(\d+(?:\.\d+)?), (\d+(?:\.\d+)?)\] m"
            r"(?: \(originally \[\d+(?:\.\d+)?, \d+(?:\.\d+)?\] m in the source environment\))?"
            r"(\.)"
        )
        if re.search(rzx_pat, description):
            description = re.sub(
                rzx_pat,
                f"\\g<1>[{target_rzx0:.1f}, {target_rzx1:.1f}] m "
                f"(originally [{base_rzx0:.1f}, {base_rzx1:.1f}] m in the source environment)\\g<4>",
                description,
                count=1,
            )

    # Heading tolerance
    base_ht = float(
        base_terrain_config.get("rendezvous_heading_tolerance_deg", DEFAULT_HEADING_TOLERANCE_DEG)
    )
    target_ht = float(
        target_terrain_config.get("rendezvous_heading_tolerance_deg", base_ht)
    )
    if abs(target_ht - base_ht) > 1e-9:
        ht_pat = (
            r"(heading within )(\d+(?:\.\d+)?)°( of the reference direction)"
            r"(?: \(originally \d+(?:\.\d+)?° in the source environment\))?"
        )
        if re.search(ht_pat, description):
            description = re.sub(
                ht_pat,
                f"\\g<1>{target_ht:.1f}°\\g<3> (originally {base_ht:.1f}° in the source environment)",
                description,
                count=1,
            )

    # Max thrust magnitude
    base_mtm = float(base_terrain_config.get("max_thrust_magnitude", DEFAULT_MAX_THRUST_MAGNITUDE))
    target_mtm = float(target_terrain_config.get("max_thrust_magnitude", base_mtm))
    if abs(target_mtm - base_mtm) > 1e-9:
        mtm_pat = (
            r"(magnitude capped at )(\d+(?:\.\d+)?) N( per command)"
            r"(?: \(originally \d+(?:\.\d+)? N in the source environment\))?"
        )
        if re.search(mtm_pat, description):
            description = re.sub(
                mtm_pat,
                f"\\g<1>{target_mtm:.1f} N\\g<3> (originally {base_mtm:.1f} N in the source environment)",
                description,
                count=1,
            )

    # Cooldown: threshold, max thrust during cooldown, and duration (steps)
    base_cth = float(base_terrain_config.get("cooldown_threshold", DEFAULT_COOLDOWN_THRESHOLD))
    base_cmt = float(base_terrain_config.get("cooldown_max_thrust", DEFAULT_COOLDOWN_MAX_THRUST))
    base_csteps = int(base_terrain_config.get("cooldown_steps", DEFAULT_COOLDOWN_STEPS))
    target_cth = float(target_terrain_config.get("cooldown_threshold", base_cth))
    target_cmt = float(target_terrain_config.get("cooldown_max_thrust", base_cmt))
    target_csteps = int(target_terrain_config.get("cooldown_steps", base_csteps))
    if (target_cth, target_cmt, target_csteps) != (base_cth, base_cmt, base_csteps):
        # Baseline or prior mutation: "(originally … N in the source environment)" appears after each "… N" value.
        cool_pat = (
            r"After any step where applied thrust exceeds (\d+(?:\.\d+)?) N"
            r"(?: \(originally \d+(?:\.\d+)? N in the source environment\))?"
            r", max commanded thrust is reduced to (\d+(?:\.\d+)?) N"
            r"(?: \(originally \d+(?:\.\d+)? N in the source environment\))?"
            r" for the next (\d+) steps"
            r"(?: \(originally \d+ steps in the source environment\))?"
            r" \(cooldown\)"
            r"(?: \(originally [^\)]+ in the source environment\))?(\.)"
        )
        if re.search(cool_pat, description):
            thr_exceeds = f"{target_cth:.1f} N"
            if abs(target_cth - base_cth) > 1e-9:
                thr_exceeds += f" (originally {base_cth:.1f} N in the source environment)"
            thr_reduced = f"{target_cmt:.1f} N"
            if abs(target_cmt - base_cmt) > 1e-9:
                thr_reduced += f" (originally {base_cmt:.1f} N in the source environment)"
            if target_csteps != base_csteps:
                steps_part = (
                    f"{target_csteps} steps (originally {base_csteps} steps in the source environment)"
                )
            else:
                steps_part = f"{target_csteps} steps"
            replacement = (
                f"After any step where applied thrust exceeds {thr_exceeds}, "
                f"max commanded thrust is reduced to {thr_reduced} for the next {steps_part} (cooldown)"
            )
            description = re.sub(cool_pat, lambda m: replacement + m.group(4), description, count=1)

    # Blind x-band and speed-blind threshold (full sensing sentence)
    base_bzmin = float(base_terrain_config.get("blind_zone_x_min", DEFAULT_BLIND_ZONE_X_MIN))
    base_bzmax = float(base_terrain_config.get("blind_zone_x_max", DEFAULT_BLIND_ZONE_X_MAX))
    target_bzmin = float(target_terrain_config.get("blind_zone_x_min", base_bzmin))
    target_bzmax = float(target_terrain_config.get("blind_zone_x_max", base_bzmax))
    base_sb = float(base_terrain_config.get("speed_blind_threshold_mps", DEFAULT_SPEED_BLIND_THRESHOLD))
    target_sb = float(target_terrain_config.get("speed_blind_threshold_mps", base_sb))
    if (
        abs(target_bzmin - base_bzmin) > 1e-9
        or abs(target_bzmax - base_bzmax) > 1e-9
        or abs(target_sb - base_sb) > 1e-9
    ):
        blind_pat = re.compile(
            r"If seeker x is in .+?the reading does not update \(stale\)\.",
            re.DOTALL,
        )
        x_clause = f"[{target_bzmin:.1f}, {target_bzmax:.1f}] m (blind band)"
        if abs(target_bzmin - base_bzmin) > 1e-9 or abs(target_bzmax - base_bzmax) > 1e-9:
            x_clause += (
                f" (originally [{base_bzmin:.1f}, {base_bzmax:.1f}] m in the source environment)"
            )
        sb_clause = f"{target_sb:.1f} m/s"
        if abs(target_sb - base_sb) > 1e-9:
            sb_clause += f" (originally {base_sb:.1f} m/s in the source environment)"
        new_blind = (
            f"If seeker x is in {x_clause} OR seeker speed exceeds {sb_clause}, "
            f"the reading does not update (stale)."
        )
        if blind_pat.search(description):
            description = blind_pat.sub(new_blind, description, count=1)

    # Ground friction (seeker–ground contact; must stay synced with prompt baseline 0.4)
    target_gfr = float(target_terrain_config.get("ground_friction", DEFAULT_GROUND_FRICTION))
    base_gfr = float(base_terrain_config.get("ground_friction", DEFAULT_GROUND_FRICTION))
    if abs(target_gfr - base_gfr) > 1e-9:
        gfr_pat = (
            r"(Ground friction coefficient \(seeker vs\. ground contact\) is )\d+(?:\.\d+)?"
            r"(?: \(originally \d+(?:\.\d+)? in the source environment\))?(\.)"
        )
        if re.search(gfr_pat, description):
            description = re.sub(
                gfr_pat,
                f"\\g<1>{target_gfr:.2f} (originally {base_gfr:.2f} in the source environment)\\g<2>",
                description,
                count=1,
            )

    # Ground top surface y (target vertical clamp follows ground_y_top + 0.5 / + 2.0)
    base_gy_top = float(base_terrain_config.get("ground_y_top", DEFAULT_GROUND_Y_TOP))
    target_gy_top = float(target_terrain_config.get("ground_y_top", base_gy_top))
    if abs(target_gy_top - base_gy_top) > 1e-9:
        gy_top_pat = (
            r"\(top surface at y = (\d+(?:\.\d+)?) m by default"
            r"(?: \(originally \d+(?:\.\d+)? m by default in the source environment\))?"
            r"; `terrain_config\[\"ground_y_top\"\]` overrides\)\."
        )
        if re.search(gy_top_pat, description):
            description = re.sub(
                gy_top_pat,
                f"(top surface at y = {target_gy_top:.1f} m by default "
                f"(originally {base_gy_top:.1f} m by default in the source environment); "
                f"`terrain_config[\"ground_y_top\"]` overrides).",
                description,
                count=1,
            )
        ymin_t, ymax_t = target_gy_top + 0.5, target_gy_top + 2.0
        ymin_b, ymax_b = base_gy_top + 0.5, base_gy_top + 2.0
        tgt_y_pat = (
            r"(Position clamped to x ∈ \[6, 26\] m and y ∈ )\[(\d+(?:\.\d+)?), (\d+(?:\.\d+)?)\] m"
            r"(?: \(originally \[\d+(?:\.\d+)?, \d+(?:\.\d+)?\] m in the source environment\))?"
            r" \(i\.e\. ground top y \+ 0\.5 m through ground top y \+ 2\.0 m; default ground top y = "
            r"(\d+(?:\.\d+)?)( m\)\.)"
        )
        if re.search(tgt_y_pat, description):
            description = re.sub(
                tgt_y_pat,
                f"\\g<1>[{ymin_t:.1f}, {ymax_t:.1f}] m (originally [{ymin_b:.1f}, {ymax_b:.1f}] m in the source environment) "
                f"(i.e. ground top y + 0.5 m through ground top y + 2.0 m; default ground top y = {target_gy_top:.1f} m "
                f"(originally {base_gy_top:.1f} m in the source environment)).",
                description,
                count=1,
            )

    # Static obstacles modification (Stage-3)
    if target_obstacles is not None and len(target_obstacles) > 0 and target_obstacles != [(7.5, 1.5, 0.3, 0.5), (14.0, 1.5, 0.3, 0.5), (20.5, 1.5, 0.3, 0.5)]:
        esc = re.escape(STATIC_BOXES_PROMPT_SNIPPET)
        pattern = rf"(\*\*Static boxes\*\*: ){esc}(\.)"
        if re.search(pattern, description):
            new_obs_str = "; ".join(
                f"center ({cx:.1f}, {cy:.1f}) m, half-extents {hw:.1f}×{hh:.1f} m"
                for cx, cy, hw, hh in target_obstacles
            )
            new_obs_str = f"{new_obs_str}, {STATIC_OBSTACLE_FIXTURE_SNIPPET}"
            description = re.sub(
                pattern,
                rf"\1{new_obs_str} (originally {STATIC_BOXES_PROMPT_SNIPPET} in the source environment)\2",
                description,
                count=1,
            )

    # Rendezvous Slots (Task Objective)
    t_s1 = target_terrain_config.get("slots_phase1", DEFAULT_SLOTS_PHASE1)
    t_s2 = target_terrain_config.get("slots_phase2", DEFAULT_SLOTS_PHASE2)
    b_s1 = base_terrain_config.get("slots_phase1", DEFAULT_SLOTS_PHASE1)
    b_s2 = base_terrain_config.get("slots_phase2", DEFAULT_SLOTS_PHASE2)

    if t_s1 != b_s1 or t_s2 != b_s2:
        # Coarse windows update
        t_lo1, t_hi1, t_lo2, t_hi2 = _slot_window_bounds(t_s1, t_s2)
        b_lo1, b_hi1, b_lo2, b_hi2 = _slot_window_bounds(b_s1, b_s2)
        
        window_pat = (
            r"(\(coarse windows )\[\d+, \d+\] and \[\d+, \d+\] steps"
            r"(?: \(originally \[\d+, \d+\] and \[\d+, \d+\] steps in the source environment\))?(\))"
        )
        if re.search(window_pat, description):
            description = re.sub(
                window_pat,
                f"\\g<1>[{t_lo1}, {t_hi1}] and [{t_lo2}, {t_hi2}] steps (originally [{b_lo1}, {b_hi1}] and [{b_lo2}, {b_hi2}] steps in the source environment)\\g<2>",
                description,
                count=1,
            )

        # Strip prior slot (originally …) clause so re-mutation stays anchored to slot lists only
        slots_strip_pat = (
            r"(Rendezvous counts only when the step is inside: phase 1 [\d, \s\[\]]+; phase 2 [\d, \s\[\]]+)"
            r" \(originally phase 1 [\d, \s\[\]]+; phase 2 [\d, \s\[\]]+ in the source environment\)(\.)"
        )
        description = re.sub(slots_strip_pat, r"\1\2", description, count=1)

        # Exact slots update (wording must match prompt.py: "Rendezvous counts only when …")
        slots_pat = (
            r"(Rendezvous counts only when the step is inside: phase 1 )[\d, \s\[\]]+(; phase 2 )[\d, \s\[\]]+(\.)"
        )
        if re.search(slots_pat, description):
            t_f1 = _format_slot_bands(t_s1)
            t_f2 = _format_slot_bands(t_s2)
            b_f1 = _format_slot_bands(b_s1)
            b_f2 = _format_slot_bands(b_s2)
            description = re.sub(
                slots_pat,
                f"\\g<1>{t_f1}\\g<2>{t_f2} (originally phase 1 {b_f1}; phase 2 {b_f2} in the source environment)\\g<3>",
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
    """Update success criteria with visible changes (same format)."""
    _require_pristine_prompt_text(base_success_criteria, label="base_success_criteria")
    criteria = base_success_criteria
    target_terrain_config = target_terrain_config or {}
    base_terrain_config = base_terrain_config or {}

    base_az0 = float(
        base_terrain_config.get("activation_zone_x_min", DEFAULT_ACTIVATION_ZONE_X_MIN)
    )
    base_az1 = float(
        base_terrain_config.get("activation_zone_x_max", DEFAULT_ACTIVATION_ZONE_X_MAX)
    )
    base_ast = int(
        base_terrain_config.get("activation_required_steps", DEFAULT_ACTIVATION_REQUIRED_STEPS)
    )
    target_az0 = float(target_terrain_config.get("activation_zone_x_min", base_az0))
    target_az1 = float(target_terrain_config.get("activation_zone_x_max", base_az1))
    target_ast = int(target_terrain_config.get("activation_required_steps", base_ast))
    if (target_az0, target_az1, target_ast) != (base_az0, base_az1, base_ast):
        act_succ_pat = (
            r"(activation already achieved \(≥)(\d+)( consecutive steps with seeker x ∈ )\[(\d+(?:\.\d+)?), (\d+(?:\.\d+)?)\] m\)"
            r"(?:; \(originally ≥\d+ consecutive steps with seeker x ∈ \[\d+(?:\.\d+)?, \d+(?:\.\d+)?\] m in the source environment\))?"
            r"(; seeker x ∈ )"
        )
        if re.search(act_succ_pat, criteria):
            orig_act = (
                f"; (originally ≥{base_ast} consecutive steps with seeker x ∈ "
                f"[{base_az0:.1f}, {base_az1:.1f}] m in the source environment)"
            )
            criteria = re.sub(
                act_succ_pat,
                f"\\g<1>{target_ast}\\g<3>[{target_az0:.1f}, {target_az1:.1f}] m){orig_act}\\g<6>",
                criteria,
                count=1,
            )

    base_href = float(
        base_terrain_config.get(
            "heading_reference_min_target_speed", DEFAULT_HEADING_REF_MIN_TARGET_SPEED
        )
    )
    target_href = float(
        target_terrain_config.get("heading_reference_min_target_speed", base_href)
    )
    if abs(target_href - base_href) > 1e-12:
        href_sc_pat = (
            r"(if target speed ≥ )(\d+(?:\.\d+)?)( m/s)"
            r"(?: \(originally \d+(?:\.\d+)? m/s in the source environment\))?"
            r"(, else seeker-to-target direction\.)"
        )
        if re.search(href_sc_pat, criteria):
            criteria = re.sub(
                href_sc_pat,
                f"\\g<1>{target_href:g}\\g<3> (originally {base_href:g} m/s in the source environment)\\g<4>",
                criteria,
                count=1,
            )

    # Track distance
    target_track = float(target_terrain_config.get("track_distance", DEFAULT_TRACK_DISTANCE))
    base_track = float(base_terrain_config.get("track_distance", DEFAULT_TRACK_DISTANCE))
    if target_track != base_track:
        pattern = (
            r"(Maintain distance <= )\d+(?:\.\d+)?( m)(?: \(originally \d+(?:\.\d+)? m in the source environment\))?"
            r"( from target after the second rendezvous until the end\.)"
        )
        if re.search(pattern, criteria):
            criteria = re.sub(
                pattern,
                f"\\g<1>{target_track:.1f}\\g<2> (originally {base_track:.1f} m in the source environment)\\g<3>",
                criteria,
                count=1,
            )

    # Impulse budget in success criteria
    target_impulse = float(target_terrain_config.get("impulse_budget", DEFAULT_IMPULSE_BUDGET))
    base_impulse = float(base_terrain_config.get("impulse_budget", DEFAULT_IMPULSE_BUDGET))
    if target_impulse != base_impulse:
        pattern = (
            r"(Total thrust impulse must not exceed )\*\*\d+ N·s\*\*"
            r"(?: \(originally \*\*\d+ N·s\*\* in the source environment\))?"
            r"(; reaching or exceeding the budget fails the run\.)"
        )
        if re.search(pattern, criteria):
            criteria = re.sub(
                pattern,
                f"\\g<1>**{target_impulse:.0f} N·s** (originally **{base_impulse:.0f} N·s** in the source environment)\\g<2>",
                criteria,
                count=1,
            )

    target_rel = float(target_terrain_config.get("rendezvous_rel_speed", DEFAULT_RENDEZVOUS_REL_SPEED))
    base_rel = float(base_terrain_config.get("rendezvous_rel_speed", DEFAULT_RENDEZVOUS_REL_SPEED))
    if abs(target_rel - base_rel) > 1e-9:
        rel_pat = (
            r"(relative speed < )\d+(?:\.\d+)?( m/s)"
            r"(?: \(originally \d+(?:\.\d+)? m/s in the source environment\))?"
            r"(; heading within)"
        )
        if re.search(rel_pat, criteria):
            criteria = re.sub(
                rel_pat,
                f"\\g<1>{target_rel:.2f}\\g<2> (originally {base_rel:.2f} m/s in the source environment)\\g<3>",
                criteria,
                count=1,
            )

    # Rendezvous capture distance (success criteria)
    base_rd = float(base_terrain_config.get("rendezvous_distance", DEFAULT_RENDEZVOUS_DISTANCE))
    target_rd = float(target_terrain_config.get("rendezvous_distance", base_rd))
    if abs(target_rd - base_rd) > 1e-9:
        rd_crit_pat = (
            r"(distance to \*\*true\*\* target ≤ )\d+(?:\.\d+)?"
            r"( m)"
            r"(?: \(originally \d+(?:\.\d+)? m in the source environment\))?"
            r"(; relative speed < )"
        )
        if re.search(rd_crit_pat, criteria):
            criteria = re.sub(
                rd_crit_pat,
                f"\\g<1>{target_rd:.1f}\\g<2> (originally {base_rd:.1f} m in the source environment)\\g<3>",
                criteria,
                count=1,
            )

    # Rendezvous x-band (success criteria)
    base_rzx0 = float(base_terrain_config.get("rendezvous_zone_x_min", DEFAULT_RENDEZVOUS_ZONE_X_MIN))
    base_rzx1 = float(base_terrain_config.get("rendezvous_zone_x_max", DEFAULT_RENDEZVOUS_ZONE_X_MAX))
    target_rzx0 = float(target_terrain_config.get("rendezvous_zone_x_min", base_rzx0))
    target_rzx1 = float(target_terrain_config.get("rendezvous_zone_x_max", base_rzx1))
    if abs(target_rzx0 - base_rzx0) > 1e-9 or abs(target_rzx1 - base_rzx1) > 1e-9:
        rzx_crit_pat = (
            r"(seeker x ∈ )\[(\d+(?:\.\d+)?), (\d+(?:\.\d+)?)\] m"
            r"(?: \(originally \[\d+(?:\.\d+)?, \d+(?:\.\d+)?\] m in the source environment\))?"
            r"(; distance to \*\*true\*\* target ≤ )"
        )
        if re.search(rzx_crit_pat, criteria):
            criteria = re.sub(
                rzx_crit_pat,
                f"\\g<1>[{target_rzx0:.1f}, {target_rzx1:.1f}] m "
                f"(originally [{base_rzx0:.1f}, {base_rzx1:.1f}] m in the source environment)\\g<4>",
                criteria,
                count=1,
            )

    # Heading tolerance in success criteria
    base_ht = float(
        base_terrain_config.get("rendezvous_heading_tolerance_deg", DEFAULT_HEADING_TOLERANCE_DEG)
    )
    target_ht = float(
        target_terrain_config.get("rendezvous_heading_tolerance_deg", base_ht)
    )
    if abs(target_ht - base_ht) > 1e-9:
        # prompt.py uses Markdown: "target **velocity** direction"
        ht_pat = (
            r"(heading within )(\d+(?:\.\d+)?)°"
            r"(?: \(originally \d+(?:\.\d+)?° in the source environment\))?"
            r"( of target \*\*velocity\*\* direction)"
        )
        if re.search(ht_pat, criteria):
            criteria = re.sub(
                ht_pat,
                f"\\g<1>{target_ht:.1f}° (originally {base_ht:.1f}° in the source environment)\\g<3>",
                criteria,
                count=1,
            )

    # Rendezvous Slot Windows (Success Criteria)
    t_s1 = target_terrain_config.get("slots_phase1", DEFAULT_SLOTS_PHASE1)
    t_s2 = target_terrain_config.get("slots_phase2", DEFAULT_SLOTS_PHASE2)
    b_s1 = base_terrain_config.get("slots_phase1", DEFAULT_SLOTS_PHASE1)
    b_s2 = base_terrain_config.get("slots_phase2", DEFAULT_SLOTS_PHASE2)

    if t_s1 != b_s1 or t_s2 != b_s2:
        t_lo1, t_hi1, t_lo2, t_hi2 = _slot_window_bounds(t_s1, t_s2)
        b_lo1, b_hi1, b_lo2, b_hi2 = _slot_window_bounds(b_s1, b_s2)
        
        window_pat = (
            r"(phase-1 and phase-2 \*\*designated\*\* time slots \(coarse windows )\[\d+, \d+\] and \[\d+, \d+\] steps"
            r"(?: \(originally \[\d+, \d+\] and \[\d+, \d+\] steps in the source environment\))?(\))"
        )
        if re.search(window_pat, criteria):
            criteria = re.sub(
                window_pat,
                f"\\g<1>[{t_lo1}, {t_hi1}] and [{t_lo2}, {t_hi2}] steps (originally [{b_lo1}, {b_hi1}] and [{b_lo2}, {b_hi2}] steps in the source environment)\\g<2>",
                criteria,
                count=1,
            )

    return criteria


# Union of all physical variables modified in Stage-1 through Stage-4 (warn what might have changed, never how).
UNIFORM_SUFFIX = """
## Environmental Anomalies Detected
Sensors indicate that this region may exhibit non-standard physical properties.
While the following variables **MIGHT** have changed from the initial environment, **NOT ALL** of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
 - **Target speed**: The nominal speed of the dynamic target.
 - **Impulse budget**: The total allowed thrust impulse (N·s) for the run.
 - **Track distance**: The maximum allowed distance from the target after the second rendezvous.
 - **Static obstacles**: The presence, number, or layout of fixed obstacles in the corridor.
 - **Ground friction**: The friction coefficient between the seeker and the ground.
 - **Spawn position**: The initial (x, y) position of the seeker.
 - **Gravitational acceleration**: May differ from what you assume from prior runs.
 - **Rendezvous relative speed**: The maximum relative speed allowed for a rendezvous to count.
 - **Time-slot windows**: The coarse step ranges (phase 1 and phase 2) by which rendezvous deadlines are enforced.
 - **Rendezvous slot bands**: The exact step sub-intervals within those windows that count as valid rendezvous opportunities.
 - **Linear damping**: The linear velocity damping coefficient on the seeker body.
 - **Angular damping**: The angular velocity damping coefficient on the seeker body.
 - **Ice / low-friction patches**: The presence, layout, or friction of ice-like surface regions.
 - **Max thrust magnitude**: The maximum instantaneous force the thrusters can generate.
 - **Thrust cooldown threshold**: The force level above which thrusters enter a weakened cooldown state.
 - **Cooldown max thrust**: The reduced maximum thrust available during the cooldown period.
 - **Blind zone boundaries**: The x-range where target sensor data is unavailable.
 - **Rendezvous heading tolerance**: The maximum allowed angle between seeker heading and target direction.

**Discovery via feedback**: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode to infer hidden constraints and adapt your design.
"""


def get_c03_curriculum_stages() -> List[Dict[str, Any]]:
    return [
        {
            "stage_id": "Stage-1",
            "title": "Sonic Storm",
            "mutation_description": "Curriculum variant: target motion, fuel budget, post-capture tracking, and static obstacle layout differ from the source task.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "target_speed": 1.8,
                "impulse_budget": 25000.0,
                "track_distance": 15.0,
                "obstacles": [],
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-2",
            "title": "Hurricane Void",
            "mutation_description": "Curriculum variant: surface interaction, spawn location, obstacle/ice layout, and bulk body forces differ from the source task.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "ground_friction": 0.0,
                "impulse_budget": 100000.0,
                "spawn_x": 15.0,
                "obstacles": [],
                "ice_zones": [],
            },
            "physics_config": {
                "gravity": (-5.0, 0.0),  # Lateral gravity only
            },
        },
        {
            "stage_id": "Stage-3",
            "title": "Submerged Abyss",
            "mutation_description": "Curriculum variant: damping, bulk body forces, friction, rendezvous tolerances, thrust limits, sensor blind band, obstacles, and slot timing differ from the source task.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "ground_friction": 0.05,
                "impulse_budget": 75000.0,
                "rendezvous_rel_speed": 0.95,
                "rendezvous_heading_tolerance_deg": 85.0,
                "target_speed": 1.5,
                "max_thrust_magnitude": 600.0,
                "cooldown_threshold": 500.0,
                "cooldown_max_thrust": 300.0,
                "blind_zone_x_min": 12.5,
                "blind_zone_x_max": 14.5,
                "obstacles": [(7.5, 1.2, 0.3, 0.2), (14.0, 1.2, 0.3, 0.2), (20.5, 1.2, 0.3, 0.2)],
                "slots_phase1": [[3700, 4950], [4200, 4300], [4700, 4800]],
                "slots_phase2": [[6200, 7400], [6700, 6800], [7200, 7300]],
            },
            "physics_config": {
                "linear_damping": 1.8,
                "angular_damping": 1.2,
                "gravity": (1.2, -11.0),
            },
        },
        {
            "stage_id": "Stage-4",
            "title": "Critical Resource Scarcity",
            "mutation_description": "Curriculum variant: fuel budget and static obstacle layout differ from the source task.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "impulse_budget": 8000.0,
                "obstacles": [],
            },
            "physics_config": {},
        },
    ]
