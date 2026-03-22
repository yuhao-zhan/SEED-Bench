"""
C-03: The Seeker task curriculum stages (mutations).

Four mutated tasks in total: Stage-1 through Stage-4, difficulty ascending.

mutation_description is for logs/orchestration only — not shown to the agent.
"""

from __future__ import annotations
import re
from typing import Any, Dict, List

# Defaults from environment.py / evaluator defaults (source environment)
DEFAULT_IMPULSE_BUDGET = 18500.0
DEFAULT_TRACK_DISTANCE = 8.5
DEFAULT_RENDEZVOUS_REL_SPEED = 1.8
DEFAULT_TARGET_SPEED = 1.5
DEFAULT_GROUND_FRICTION = 0.4
DEFAULT_SPAWN_X = 11.0
DEFAULT_SPAWN_Y = 1.35
DEFAULT_SLOTS_PHASE1 = [(3700, 3800), (4200, 4300), (4700, 4800)]
DEFAULT_SLOTS_PHASE2 = [(6200, 6300), (6700, 6800), (7200, 7300)]
DEFAULT_LINEAR_DAMPING = 0.5
DEFAULT_ANGULAR_DAMPING = 0.5
DEFAULT_GRAVITY_XY = (0.0, -10.0)
DEFAULT_COOLDOWN_THRESHOLD = 120.0
DEFAULT_COOLDOWN_MAX_THRUST = 40.0
DEFAULT_COOLDOWN_STEPS = 80
DEFAULT_MAX_THRUST_MAGNITUDE = 200.0
DEFAULT_HEADING_TOLERANCE_DEG = 55.0
DEFAULT_BLIND_ZONE_X_MIN = 12.0
DEFAULT_BLIND_ZONE_X_MAX = 15.0
# Match environment.py RENDEZVOUS_ZONE_* / get_terrain_bounds defaults
DEFAULT_RENDEZVOUS_DISTANCE = 6.0
DEFAULT_RENDEZVOUS_ZONE_X_MIN = 10.0
DEFAULT_RENDEZVOUS_ZONE_X_MAX = 20.0

# Static corridor boxes use these fixture material values in environment._create_obstacles (always).
STATIC_OBSTACLE_FIXTURE_SNIPPET = "fixture friction 0.5, restitution 0.1"


def _gravity_tuple(physics_cfg: Dict[str, Any]) -> tuple:
    physics_cfg = physics_cfg or {}
    g = physics_cfg.get("gravity", DEFAULT_GRAVITY_XY)
    if isinstance(g, (list, tuple)) and len(g) >= 2:
        return (float(g[0]), float(g[1]))
    return DEFAULT_GRAVITY_XY


# Default ice layout (must match prompt.py baseline)
DEFAULT_ICE_ZONES = [
    ((9.0, 1.25, 1.0, 0.12), 0.08),
    ((16.5, 1.25, 1.0, 0.12), 0.08),
]

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
        # Matches baseline or a prior per-coefficient mutation (S_01-style "originally" per value).
        damp_pat = (
            r"Default \*\*linear damping (\d+(?:\.\d+)?)\*\*"
            r"(?: \(originally \*\*(?:\d+(?:\.\d+)?)\*\* in the source environment\))?"
            r" and \*\*angular damping (\d+(?:\.\d+)?)\*\*"
            r"(?: \(originally \*\*(?:\d+(?:\.\d+)?)\*\* in the source environment\))?"
            r" on the seeker body \(Box2D\); curriculum `physics_config` may override these coefficients\."
        )
        if re.search(damp_pat, description):
            replacement = (
                f"Default **linear damping {target_ld:.1f}** (originally **{base_ld:.1f}** in the source environment) "
                f"and **angular damping {target_ad:.1f}** (originally **{base_ad:.1f}** in the source environment) "
                f"on the seeker body (Box2D); curriculum `physics_config` may override these coefficients."
            )
            description = re.sub(damp_pat, replacement, description, count=1)

    # Gravity: when mutated vs source, do not disclose any numeric g vector (hidden physics).
    tg, bg = _gravity_tuple(tp), _gravity_tuple(bp)
    if tg != bg:
        grav_infer_pat = (
            r"\- \*\*Gravity\*\*: Infer the effective gravitational field from motion and dynamics; "
            r"the specific acceleration vector is not disclosed for this environment\.(?:\n|$)"
        )
        replacement_grav = (
            "- **Gravity**: Infer the effective gravitational field from motion and dynamics; "
            "the specific acceleration vector is not disclosed for this environment.\n"
        )
        if re.search(grav_infer_pat, description):
            description = re.sub(
                grav_infer_pat,
                replacement_grav,
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
                rf"\1none (originally {STATIC_BOXES_PROMPT_SNIPPET} in the source environment)\2 "
                r"No static boxes are present in this environment.",
                description,
                count=1,
            )

    # Ice patches removal
    target_ice = target_terrain_config.get("ice_zones")
    if target_ice is not None and len(target_ice) == 0:
        ice_snippet = (
            r"Two low-friction patches centered at \(9\.0, 1\.25\) and \(16\.5, 1\.25\) m, "
            r"half-size 1\.0×0\.12 m, with unstated friction coefficient"
        )
        pattern = rf"(\*\*Ice patches\*\*: ){ice_snippet}(\.)"
        if re.search(pattern, description):
            _ice_orig = (
                "Two low-friction patches centered at (9.0, 1.25) and (16.5, 1.25) m, "
                "half-size 1.0×0.12 m, with unstated friction coefficient"
            )
            description = re.sub(
                pattern,
                rf"\1none (originally {_ice_orig} in the source environment)\2 "
                r"No low-friction ice zones are present in this environment.",
                description,
                count=1,
            )

    # Spawn position (x, y)
    target_sx = float(target_terrain_config.get("spawn_x", DEFAULT_SPAWN_X))
    target_sy = float(target_terrain_config.get("spawn_y", DEFAULT_SPAWN_Y))
    base_sx = float(base_terrain_config.get("spawn_x", DEFAULT_SPAWN_X))
    base_sy = float(base_terrain_config.get("spawn_y", DEFAULT_SPAWN_Y))
    if (target_sx, target_sy) != (base_sx, base_sy):
        spawn_re = re.compile(
            r"The seeker spawns at \(\d+(?:\.\d+)?, \d+(?:\.\d+)?\) m \(x, y\)"
            r"(?: \(originally \([\d., ]+\) m \(x, y\) in the source environment\))?(\.)"
        )
        if spawn_re.search(description):
            description = spawn_re.sub(
                f"The seeker spawns at ({target_sx:.1f}, {target_sy:.2f}) m (x, y) "
                f"(originally ({base_sx:.1f}, {base_sy:.2f}) m (x, y) in the source environment).",
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
            r"(3\. \*\*Tracking\*\*: Maintain distance <= )\d+(?:\.\d+)? m( from the target after the second rendezvous\.)"
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
            r"(\(relative speed < )\d+(?:\.\d+)? m/s(\))"
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
        # Group 2 is ", matching velocity" only — value already ends with " m" before the comma.
        rd_pat = (
            r"(distance to target ≤ )\d+(?:\.\d+)?"
            r"(?: \(originally \d+(?:\.\d+)? m in the source environment\))?"
            r"(, matching velocity)"
        )
        if re.search(rd_pat, description):
            description = re.sub(
                rd_pat,
                f"\\g<1>{target_rd:.1f} m (originally {base_rd:.1f} m in the source environment)\\g<2>",
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

    # Blind zone
    base_bzmin = float(base_terrain_config.get("blind_zone_x_min", DEFAULT_BLIND_ZONE_X_MIN))
    base_bzmax = float(base_terrain_config.get("blind_zone_x_max", DEFAULT_BLIND_ZONE_X_MAX))
    target_bzmin = float(target_terrain_config.get("blind_zone_x_min", base_bzmin))
    target_bzmax = float(target_terrain_config.get("blind_zone_x_max", base_bzmax))
    if abs(target_bzmin - base_bzmin) > 1e-9 or abs(target_bzmax - base_bzmax) > 1e-9:
        bz_pat = (
            r"(seeker x is in )\[(\d+(?:\.\d+)?), (\d+(?:\.\d+)?)\] m( \(blind band\))"
            r"(?: \(originally \[[^\]]+\] m in the source environment\))?"
            r"( OR seeker speed exceeds 2\.0 m/s)"
        )
        if re.search(bz_pat, description):
            description = re.sub(
                bz_pat,
                f"\\g<1>[{target_bzmin:.1f}, {target_bzmax:.1f}] m\\g<4> "
                f"(originally [{base_bzmin:.1f}, {base_bzmax:.1f}] m in the source environment)\\g<5>",
                description,
                count=1,
            )

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
    criteria = base_success_criteria
    target_terrain_config = target_terrain_config or {}
    base_terrain_config = base_terrain_config or {}

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
        # Group 2 is "; relative speed < " only — avoid duplicating " m" before the semicolon.
        rd_crit_pat = (
            r"(distance to \*\*true\*\* target ≤ )\d+(?:\.\d+)?"
            r"(?: \(originally \d+(?:\.\d+)? m in the source environment\))?"
            r"(; relative speed < )"
        )
        if re.search(rd_crit_pat, criteria):
            criteria = re.sub(
                rd_crit_pat,
                f"\\g<1>{target_rd:.1f} m (originally {base_rd:.1f} m in the source environment)\\g<2>",
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
 - **Gravitational acceleration**: The strength and direction of gravity.
 - **Rendezvous relative speed**: The maximum relative speed allowed for a rendezvous to count.
 - **Time-slot windows**: The coarse step ranges (phase 1 and phase 2) by which rendezvous deadlines are enforced.
 - **Rendezvous slot bands**: The exact step sub-intervals within those windows that count as valid rendezvous opportunities.
 - **Linear damping**: The linear velocity damping of the seeker body (resistance proportional to speed).
 - **Angular damping**: The resistance to rotational motion of the seeker body.
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
