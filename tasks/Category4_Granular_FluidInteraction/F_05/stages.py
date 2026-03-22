"""
F-05: The Boat task curriculum stages (mutations).

Mutations combine structural mechanisms (not simple linear scaling):
- Passive roll restoring torque from the environment (may differ from the baseline).
- Deck traction, joint fragility, hull flotation vs. submerged hazards, build-zone geometry,
  mass budget, gravity, hydrodynamic forcing (waves, wind, current, impulses),
  hull roll impulses, and granular cargo material (restitution, friction, damping).

Stage-1 & Stage-2: Each stage stresses primarily one physical axis with a sharp threshold.
Stage-3 & Stage-4: Coupled, conflicting constraints; difficulty increases monotonically.
Each runnable stage’s `terrain_config` / `physics_config` is produced by **shallow merge** over prior
stages in order: scalar keys in later stages **replace** earlier values (e.g. a later `restoring_coeff`
overwrites an earlier one); the nested `cargo` dict is merged field-by-field. This matches the
environment constructor, which reads a single merged dict—not a stack of every prior scalar value.
"""
from __future__ import annotations

from typing import Any, Dict, List
import math
import re


def _fmt_build_zone_axis(y: float) -> str:
    """Format build-zone bounds without `% 0.1` float residue (e.g. 2.0 vs 2.00)."""
    t = round(y * 100) / 100
    if math.isclose(t, round(t, 1), abs_tol=1e-9):
        return f"{round(t, 1):.1f}"
    s = f"{t:.2f}".rstrip("0").rstrip(".")
    return s


# Appended when repairing a truncated obstacle line (regex legacy path).
_ROCK_FIXTURES_SUFFIX = (
    " Each baseline rock fixture uses friction **0.6** and restitution **0.2** in the simulator; "
    "variants may change positions/radii and therefore the hazard field."
)


def _cargo_friction_restitution(terrain_config: Dict[str, Any]) -> tuple[float, float]:
    """Effective cargo friction and restitution (mirrors environment._create_cargo defaults)."""
    cargo = terrain_config.get("cargo") or {}
    fr = cargo.get("friction")
    if fr is None:
        fr = 0.28
    else:
        fr = float(fr)
    rest = cargo.get("restitution")
    if rest is None:
        cr = terrain_config.get("cargo_restitution")
        rest = 0.12 if cr is None else float(cr)
    else:
        rest = float(rest)
    return fr, rest


def _cargo_linear_angular_damping(terrain_config: Dict[str, Any]) -> tuple[float, float]:
    """Cargo linear/angular damping; falls back to global physics defaults 0.1 / 0.05."""
    default_ld, default_ad = 0.1, 0.05
    cargo = terrain_config.get("cargo") or {}
    ld = cargo.get("linear_damping", terrain_config.get("cargo_linear_damping"))
    ad = cargo.get("angular_damping", terrain_config.get("cargo_angular_damping"))
    return (
        float(ld) if ld is not None else default_ld,
        float(ad) if ad is not None else default_ad,
    )


def _hull_linear_angular_damping(physics_config: Dict[str, Any] | None) -> tuple[float, float]:
    """Hull/beam damping from physics_config (matches Sandbox defaults)."""
    default_ld, default_ad = 0.1, 0.05
    pc = physics_config or {}
    ld = pc.get("linear_damping", default_ld)
    ad = pc.get("angular_damping", default_ad)
    return float(ld), float(ad)


def _cargo_count_radius(terrain_config: Dict[str, Any]) -> tuple[int, float]:
    cargo = terrain_config.get("cargo") or {}
    return int(cargo.get("count", 10)), float(cargo.get("radius", 0.15))


def _format_rocks_summary(terrain_config: Dict[str, Any]) -> str:
    """Human-readable rock layout for prompts (must match default line in prompt.py)."""
    rocks = terrain_config.get("rocks")
    if not rocks:
        return (
            "four rocks: (13.50, 1.00, r=0.24); (14.50, 1.10, r=0.22); "
            "(15.50, 1.05, r=0.23); (16.50, 1.08, r=0.22)"
        )
    parts = []
    for r in rocks:
        rx = float(r.get("x", 15.0))
        ry = float(r.get("y", 1.0))
        rr = float(r.get("radius", r.get("r", 0.2)))
        parts.append(f"({rx:.2f}, {ry:.2f}, r={rr:.2f})")
    return f"{len(rocks)} rocks: " + "; ".join(parts)


def update_task_description_for_visible_changes(
    base_description: str,
    target_terrain_config: Dict[str, Any],
    base_terrain_config: Dict[str, Any],
    target_physics_config: Dict[str, Any] | None = None,
    base_physics_config: Dict[str, Any] | None = None,
) -> str:
    """Update task description for visible terrain/config changes.

    ``base_terrain_config`` / ``base_physics_config`` must be the **Initial (source)**
    environment defaults (typically ``{}``), not a prior curriculum merge—otherwise
    ``(originally … in the source environment)`` legends become misleading.

    Sea-state numerics (waves, wind amplitudes, etc.) are not injected into prose.
    Deck friction and damping use the same numeric defaults as ``environment.Sandbox``; when they
    differ from the source environment, prose uses
    ``[new] (originally [old] in the source environment)`` (not sea-state forcings).
    """
    description = base_description
    target_physics_config = target_physics_config or {}
    base_physics_config = base_physics_config or {}
    target_x_min = target_terrain_config.get("build_zone_x_min", 12.0)
    target_x_max = target_terrain_config.get("build_zone_x_max", 18.0)
    target_y_min = target_terrain_config.get("build_zone_y_min", 2.0)
    target_y_max = target_terrain_config.get("build_zone_y_max", 4.5)

    base_x_min = base_terrain_config.get("build_zone_x_min", 12.0)
    base_x_max = base_terrain_config.get("build_zone_x_max", 18.0)
    base_y_min = base_terrain_config.get("build_zone_y_min", 2.0)
    base_y_max = base_terrain_config.get("build_zone_y_max", 4.5)

    if (
        target_x_min != base_x_min
        or target_x_max != base_x_max
        or target_y_min != base_y_min
        or target_y_max != base_y_max
    ):
        # Must match prompt.py build-zone sentence (en-dash in "beam–beam").
        # Optional "(originally ...)" supports idempotent re-application to already-updated text.
        bz_pat = (
            r"(- \*\*Build zone\*\*: Beam centers must lie in )"
            r"x=\[([\d.]+), ([\d.]+)\], y=\[([\d.]+), ([\d.]+)\]"
            r"(?: \(originally x=\[([\d.]+), ([\d.]+)\], y=\[([\d.]+), ([\d.]+)\] in the source environment\))?"
            r"(\. Every weld anchor for `add_joint` \(hull attachment or beam\u2013beam\) must lie in the same box "
            r"\(enforced at build time and in design checks\)\.)"
        )
        tx0 = f"{float(target_x_min):.1f}"
        tx1 = f"{float(target_x_max):.1f}"
        ty0 = _fmt_build_zone_axis(float(target_y_min))
        ty1 = _fmt_build_zone_axis(float(target_y_max))
        bx0 = f"{float(base_x_min):.1f}"
        bx1 = f"{float(base_x_max):.1f}"
        by0 = _fmt_build_zone_axis(float(base_y_min))
        by1 = _fmt_build_zone_axis(float(base_y_max))
        box = f"x=[{tx0}, {tx1}], y=[{ty0}, {ty1}] (originally x=[{bx0}, {bx1}], y=[{by0}, {by1}] in the source environment)"
        replacement = f"\\g<1>{box}\\g<10>"
        if re.search(bz_pat, description):
            description = re.sub(bz_pat, replacement, description, count=1)

    # Hull vertical offset (visible: nominal center y = 2.5 + offset)
    default_boat_off = 0.0
    target_off = float(target_terrain_config.get("boat_y_offset", default_boat_off))
    base_off = float(base_terrain_config.get("boat_y_offset", default_boat_off))
    if target_off != base_off:
        target_y = 2.5 + target_off
        base_y = 2.5 + base_off

        def _boat_repl(_m: re.Match[str]) -> str:
            return f"{_m.group(1)}{target_y:.1f} m (originally {base_y:.1f} m in the source environment)."

        boat_pat_mut = (
            r"(- \*\*Boat\*\*: Hull center at x≈15 m, y≈)([\d.]+) m "
            r"\(originally ([\d.]+) m in the source environment\)\."
        )
        boat_pat_plain = r"(- \*\*Boat\*\*: Hull center at x≈15 m, y≈)([\d.]+)( m\.)"
        if re.search(boat_pat_mut, description):
            description = re.sub(boat_pat_mut, _boat_repl, description, count=1)
        elif re.search(boat_pat_plain, description):
            description = re.sub(boat_pat_plain, _boat_repl, description, count=1)

    default_deck = 0.5
    target_deck = float(target_terrain_config.get("deck_friction", default_deck))
    base_deck = float(base_terrain_config.get("deck_friction", default_deck))
    if target_deck != base_deck:
        box2d_tail = (
            "In Box2D, contact friction combines **both** colliding fixtures: agent beams therefore interact "
            "with the floor and rocks using a **mixed** effective friction, not the rock/floor coefficients alone."
        )
        td, bd = float(target_deck), float(base_deck)
        new_deck_block = (
            "- **Hull & beam deck friction**: Deck-facing friction coefficient for the hull and agent beams is "
            f"**{td:.2f}** (originally **{bd:.2f}** in the source environment). "
            "Infer effective traction at contacts with cargo, floor, and rocks from interaction and feedback. "
            + box2d_tail
        )
        # Baseline prompt (numeric 0.5) and prior mutated forms.
        deck_pat_baseline = (
            r"(- \*\*Hull & beam deck friction\*\*: )"
            r"The hull and beams you build share a single deck-facing friction coefficient in the simulator; "
            r"the baseline value is \*\*0\.5\*\* \(variants may override\)\. "
            r"Infer effective traction at contacts with cargo, floor, and rocks from interaction and feedback\. "
            r"(In Box2D, contact friction combines \*\*both\*\* colliding fixtures: agent beams therefore interact "
            r"with the floor and rocks using a \*\*mixed\*\* effective friction, not the rock/floor coefficients alone\.)"
        )
        deck_pat_mut_numeric = (
            r"- \*\*Hull & beam deck friction\*\*: Deck-facing friction coefficient for the hull and agent beams is "
            r"\*\*[\d.]+\*\* \(originally \*\*[\d.]+\*\* in the source environment\)\. "
            r"Infer effective traction at contacts with cargo, floor, and rocks from interaction and feedback\. "
            r"In Box2D, contact friction combines \*\*both\*\* colliding fixtures: agent beams therefore interact "
            r"with the floor and rocks using a \*\*mixed\*\* effective friction, not the rock/floor coefficients alone\."
        )
        deck_pat_qual_legacy = (
            r"(- \*\*Hull & beam deck friction\*\*: )"
            r"The hull and beams you build share the environment[\u2019']s deck-facing friction setting with the hull; "
            r"exact coefficients are omitted.{1,3}infer traction from contacts and feedback\. "
            r"Variants may change deck traction\. "
            r"(In Box2D, contact friction combines \*\*both\*\* colliding fixtures: agent beams therefore interact "
            r"with the floor and rocks using a \*\*mixed\*\* effective friction, not the rock/floor coefficients alone\.)"
        )
        deck_pat_mut_qual_legacy = (
            r"- \*\*Hull & beam deck friction\*\*: The hull and beams you build share the environment[\u2019']s deck-facing "
            r"friction setting with the hull\. Deck traction in this variant may differ from the source environment "
            r"\(originally the source environment omitted explicit numeric deck coefficients in prose\)\. "
            r"Exact coefficients are omitted.{1,3}infer traction from contacts and feedback\. "
            r"Variants may change deck traction\. "
            r"In Box2D, contact friction combines \*\*both\*\* colliding fixtures: agent beams therefore interact "
            r"with the floor and rocks using a \*\*mixed\*\* effective friction, not the rock/floor coefficients alone\."
        )
        deck_pat_num_legacy = (
            r"- \*\*Hull & beam deck friction\*\*: Dynamic hull and agent beams use fixture friction \*\*[\d.]+\*\* "
            r"\(originally [\d.]+ in the source environment\)\. The source task omitted the explicit baseline "
            r"coefficient in prose\. Variants may change deck traction\. "
            r"In Box2D, contact friction combines \*\*both\*\* colliding fixtures: agent beams therefore interact "
            r"with the floor and rocks using a \*\*mixed\*\* effective friction, not the rock/floor coefficients alone\."
        )
        for pat in (
            deck_pat_mut_numeric,
            deck_pat_baseline,
            deck_pat_mut_qual_legacy,
            deck_pat_qual_legacy,
            deck_pat_num_legacy,
        ):
            if re.search(pat, description):
                description = re.sub(pat, new_deck_block, description, count=1)
                break

    target_rocks = _format_rocks_summary(target_terrain_config)
    base_rocks = _format_rocks_summary(base_terrain_config)
    if target_rocks != base_rocks:
        # Match prompt.py: rock list + "Each rock uses fixed contact parameters..." sentence.
        obs_pat_full = (
            r"(- \*\*Submerged obstacles\*\*: )"
            r"((?:four|\d+) rocks: .+?)"
            r"(?: \(originally .+? in the source environment\))?"
            r"(\. Each (?:rock uses environment-defined contact parameters \(magnitudes omitted\);|baseline rock fixture uses \*\*friction 0\.6\*\* and \*\*restitution 0\.2\*\* in the simulator; )"
            r"variants may change positions/radii and therefore the hazard field\.)"
        )
        if re.search(obs_pat_full, description):
            description = re.sub(
                obs_pat_full,
                f"\\g<1>{target_rocks} (originally {base_rocks} in the source environment)\\g<3>",
                description,
                count=1,
            )
        else:
            obs_pat_legacy = r"(- \*\*Submerged obstacles\*\*: )([^\n]+)"
            if re.search(obs_pat_legacy, description):
                description = re.sub(
                    obs_pat_legacy,
                    f"\\g<1>{target_rocks} (originally {base_rocks} in the source environment).{_ROCK_FIXTURES_SUFFIX}",
                    description,
                    count=1,
                )

    t_fr, t_rest = _cargo_friction_restitution(target_terrain_config)
    b_fr, b_rest = _cargo_friction_restitution(base_terrain_config)
    t_n, t_r = _cargo_count_radius(target_terrain_config)
    b_n, b_r = _cargo_count_radius(base_terrain_config)
    if t_fr != b_fr or t_rest != b_rest or t_n != b_n or not math.isclose(t_r, b_r, rel_tol=0.0, abs_tol=1e-9):
        cargo_pat = (
            r"(- \*\*Cargo\*\*: )(\d+) circular particles, radius ([\d.]+) m; baseline disk density 260, friction "
            r"([\d.]+(?: \(originally [\d.]+ in the source environment\))?)"
            r"(, restitution )"
            r"([\d.]+(?: \(originally [\d.]+ in the source environment\))?)"
            r"( \(variants may override contact parameters\)\.)"
        )
        fr_s = (
            f"{t_fr:.2f} (originally {b_fr:.2f} in the source environment)"
            if t_fr != b_fr
            else f"{t_fr:.2f}"
        )
        rest_s = (
            f"{t_rest:.2f} (originally {b_rest:.2f} in the source environment)"
            if t_rest != b_rest
            else f"{t_rest:.2f}"
        )

        def _cargo_full_repl(m: re.Match[str]) -> str:
            n_part = (
                f"{t_n} circular particles (originally {b_n} in the source environment)"
                if t_n != b_n
                else f"{t_n} circular particles"
            )
            r_fmt = f"{t_r:.2f}"
            if not math.isclose(t_r, b_r, rel_tol=0.0, abs_tol=1e-9):
                r_part = f"radius {r_fmt} m (originally {b_r:.2f} m in the source environment)"
            else:
                r_part = f"radius {r_fmt} m"
            return (
                f"{m.group(1)}{n_part}, {r_part}; baseline disk density 260, friction {fr_s}"
                f"{m.group(5)}{rest_s}{m.group(7)}"
            )

        if re.search(cargo_pat, description):
            description = re.sub(cargo_pat, _cargo_full_repl, description, count=1)

    th_ld, th_ad = _hull_linear_angular_damping(target_physics_config)
    bh_ld, bh_ad = _hull_linear_angular_damping(base_physics_config)
    tc_ld, tc_ad = _cargo_linear_angular_damping(target_terrain_config)
    bc_ld, bc_ad = _cargo_linear_angular_damping(base_terrain_config)
    if (th_ld, th_ad) != (bh_ld, bh_ad) or (tc_ld, tc_ad) != (bc_ld, bc_ad):
        damp_new = (
            "- **Damping (baseline)**: Hull and beams use linear damping **{hl:.2f}** and angular damping **{ha:.2f}**; "
            "cargo particles use linear damping **{cl:.2f}** and angular damping **{ca:.2f}** "
            "(originally hull/beam linear **{ohl:.2f}**, angular **{oha:.2f}** and cargo linear **{ocl:.2f}**, "
            "angular **{oca:.2f}** in the source environment). "
            "Variants may override these per body class."
        ).format(
            hl=th_ld,
            ha=th_ad,
            cl=tc_ld,
            ca=tc_ad,
            ohl=bh_ld,
            oha=bh_ad,
            ocl=bc_ld,
            oca=bc_ad,
        )
        damp_pat_mut = (
            r"- \*\*Damping \(baseline\)\*\*: Hull and beams use linear damping \*\*[\d.]+\*\* and angular damping \*\*[\d.]+\*\*; "
            r"cargo particles use linear damping \*\*[\d.]+\*\* and angular damping \*\*[\d.]+\*\* "
            r"\(originally hull/beam linear \*\*[\d.]+\*\*, angular \*\*[\d.]+\*\* and cargo linear \*\*[\d.]+\*\*, "
            r"angular \*\*[\d.]+\*\* in the source environment\)\. "
            r"Variants may override these per body class\."
        )
        damp_pat_qual_base = (
            r"- \*\*Damping \(baseline\)\*\*: Hull, beams, and cargo use linear damping \*\*0\.1\*\* and angular damping "
            r"\*\*0\.05\*\* by default \(simulator units; variants may override per body class\)\."
        )
        damp_pat_qual_base_legacy = (
            r"- \*\*Damping \(baseline\)\*\*: Hull, beams, and cargo use environment-configured linear and angular damping "
            r"unless a variant overrides them per body type; default magnitudes are omitted.{1,3}infer from motion decay\."
        )
        damp_pat_qual_mut_legacy = (
            r"- \*\*Damping \(baseline\)\*\*: Hull, beams, and cargo use environment-configured linear and angular damping "
            r"unless a variant overrides them per body type; default magnitudes are omitted.{1,3}infer from motion decay\. "
            r"Relative to the source environment, simulator damping for hull, beams, and/or cargo may differ "
            r"\(originally all body classes shared the same qualitative description without numeric values in prose\)\."
        )
        damp_pat_numeric_legacy = (
            r"- \*\*Damping \(baseline\)\*\*: hull and beams use .+?; cargo particles use .+? from the task physics configuration "
            r"unless a variant overrides them per body type\."
        )
        for pat in (
            damp_pat_mut,
            damp_pat_qual_mut_legacy,
            damp_pat_numeric_legacy,
            damp_pat_qual_base,
            damp_pat_qual_base_legacy,
        ):
            if re.search(pat, description):
                description = re.sub(pat, damp_new, description, count=1)
                break

    return description


def update_success_criteria_for_visible_changes(
    base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]
) -> str:
    """Update success criteria for visible changes.

    ``base_terrain_config`` must be the **Initial** task defaults (typically ``{}``), not a
    prior merged stage, so ``(originally … in the source environment)`` refers to the true source.
    """
    criteria = base_success_criteria
    inf = float("inf")
    target_joint = target_terrain_config.get("joint_max_force", inf)
    base_joint = base_terrain_config.get("joint_max_force", inf)
    pattern_generic = (
        r"(- \*\*Joint structural limits\*\*: )"
        r"When no per-weld load cap is configured, welds do not break under reaction loads\. "
        r"When a force cap \*\*F_max\*\* \(N\) is configured, the simulator also enforces a coupled torque cap "
        r"\*\*0\.4 × F_max\*\* \(N\u00b7m\); a weld breaks if simulated reaction force exceeds \*\*F_max\*\* or reaction torque exceeds that torque cap\. "
        r"Numeric \*\*F_max\*\* and the derived torque cap appear in Success Criteria when configured; use episode feedback when limits are not printed\."
    )
    pattern_configured = (
        r"(- \*\*Joint structural limits\*\*: )"
        r"Maximum joint reaction force [\d.]+ N \(originally [^\)]+\); "
        r"reaction torque limit [\d.]+ N\u00b7m \(originally [^\)]+\)\. "
        r"A weld fails when simulated reaction force exceeds the force limit or "
        r"simulated reaction torque exceeds the torque limit\."
    )
    TORQUE_SCALE = 0.4
    if target_joint != inf:
        target_val = float(target_joint)
        torque_limit = target_val * TORQUE_SCALE
        if base_joint == inf or base_joint is None:
            orig_f = "∞ in the source environment"
            orig_t = "∞ in the source environment"
        else:
            base_val = float(base_joint)
            base_torque = base_val * TORQUE_SCALE
            orig_f = f"{base_val:.0f} N in the source environment"
            orig_t = f"{base_torque:.0f} N\u00b7m in the source environment"

        def _joint_repl(m: re.Match[str]) -> str:
            return (
                f"{m.group(1)}Maximum joint reaction force {target_val:.0f} N "
                f"(originally {orig_f}); "
                f"reaction torque limit {torque_limit:.0f} N\u00b7m "
                f"(originally {orig_t}). "
                "A weld fails when simulated reaction force exceeds the force limit or "
                "simulated reaction torque exceeds the torque limit."
            )

        if re.search(pattern_generic, criteria):
            criteria = re.sub(pattern_generic, _joint_repl, criteria, count=1)
        elif re.search(pattern_configured, criteria):
            criteria = re.sub(pattern_configured, _joint_repl, criteria, count=1)

    default_mass = 60.0
    target_mass = float(target_terrain_config.get("max_structure_mass", default_mass))
    base_mass = float(base_terrain_config.get("max_structure_mass", default_mass))
    if target_mass != base_mass:
        mass_pat_plain = r"(- \*\*Mass Budget\*\*: Total structure mass <= )([\d.]+)( kg\.)"
        mass_pat_mut = (
            r"(- \*\*Mass Budget\*\*: Total structure mass <= )[\d.]+ kg "
            r"\(originally [\d.]+ kg in the source environment\)\."
        )
        mass_repl = f"\\g<1>{target_mass:.0f} kg (originally {base_mass:.0f} kg in the source environment)."
        if re.search(mass_pat_mut, criteria):
            criteria = re.sub(mass_pat_mut, mass_repl, criteria, count=1)
        elif re.search(mass_pat_plain, criteria):
            criteria = re.sub(mass_pat_plain, mass_repl, criteria, count=1)

    default_cap = 18.0
    target_cap = float(target_terrain_config.get("max_capsize_angle_deg", default_cap))
    base_cap = float(base_terrain_config.get("max_capsize_angle_deg", default_cap))
    if target_cap != base_cap:
        # Prefer the already-mutated form first so we do not match "14.5 degrees." inside
        # "14.5 degrees (originally 18.0 degrees in the source environment)."
        cap_pat = (
            r"(\*\*Stability\*\*: Peak absolute hull roll angle after that same settling window must stay at or below )"
            r"(?:([\d.]+) degrees \(originally ([\d.]+) degrees in the source environment\)\.|([\d.]+)\s*degrees\.)"
        )
        if re.search(cap_pat, criteria):
            criteria = re.sub(
                cap_pat,
                f"\\g<1>{target_cap:.1f} degrees (originally {base_cap:.1f} degrees in the source environment).",
                criteria,
                count=1,
            )

    default_cwy = 1.98
    default_grace = 120
    target_cwy = float(target_terrain_config.get("cargo_water_y", default_cwy))
    base_cwy = float(base_terrain_config.get("cargo_water_y", default_cwy))
    target_grace = int(target_terrain_config.get("cargo_loss_grace_steps", default_grace))
    base_grace = int(base_terrain_config.get("cargo_loss_grace_steps", default_grace))

    if target_cwy != base_cwy or target_grace != base_grace:
        # Tight y + grace captures (avoid `.+?` spanning "after the first").
        retention_pat = (
            r"(1\. \*\*Cargo Retention\*\*: A particle fails if its center \*\*ever\*\* falls below y = )"
            r"([\d.]+ m(?: \(originally [\d.]+ m in the source environment\))?)"
            r"( after the first )"
            r"(\d+)(?: \(originally \d+ in the source environment\))?"
            r"( physics steps \(brief spawn/settling is ignored\)\.)"
        )

        def _retention_repl(m: re.Match[str]) -> str:
            y_part = (
                f"{target_cwy:.2f} m (originally {base_cwy:.2f} m in the source environment)"
                if not math.isclose(target_cwy, base_cwy, rel_tol=0.0, abs_tol=1e-9)
                else f"{target_cwy:.2f} m"
            )
            grace_part = (
                f"{target_grace} (originally {base_grace} in the source environment)"
                if target_grace != base_grace
                else str(target_grace)
            )
            return f"{m.group(1)}{y_part}{m.group(3)}{grace_part}{m.group(5)}"

        if re.search(retention_pat, criteria):
            criteria = re.sub(retention_pat, _retention_repl, criteria, count=1)
    return criteria


def _f05_baseline_rocks_signature() -> str:
    return _format_rocks_summary({})


def _physics_gravity_tuple(pc: Dict[str, Any] | None) -> tuple[float, float]:
    pc = pc or {}
    g = pc.get("gravity", (0, -10))
    if isinstance(g, (list, tuple)) and len(g) >= 2:
        return float(g[0]), float(g[1])
    return 0.0, -10.0


def build_f05_uniform_suffix(
    merged_terrain_config: Dict[str, Any], merged_physics_config: Dict[str, Any] | None = None
) -> str:
    """Build suffix from families that differ from canonical F-05 baseline (environment defaults)."""
    labels: List[str] = []

    def add(s: str) -> None:
        if s not in labels:
            labels.append(s)

    inf = float("inf")
    tc = merged_terrain_config
    pc = merged_physics_config or {}

    if not math.isclose(float(tc.get("restoring_coeff", 1600.0)), 1600.0, rel_tol=0.0, abs_tol=1e-3):
        add("Environmental roll-restoring couple")
    if not math.isclose(float(tc.get("deck_friction", 0.5)), 0.5, rel_tol=0.0, abs_tol=1e-9):
        add("Deck surface traction")
    if float(tc.get("joint_max_force", inf)) < inf:
        add("Joint load tolerance")
    if not math.isclose(float(tc.get("boat_y_offset", 0.0)), 0.0, rel_tol=0.0, abs_tol=1e-9):
        add("Hull vertical placement relative to obstacles")
    if _format_rocks_summary(tc) != _f05_baseline_rocks_signature():
        add("Submerged obstacle layout")
    if (
        float(tc.get("build_zone_x_min", 12.0)) != 12.0
        or float(tc.get("build_zone_x_max", 18.0)) != 18.0
        or float(tc.get("build_zone_y_min", 2.0)) != 2.0
        or float(tc.get("build_zone_y_max", 4.5)) != 4.5
    ):
        add("Integration zone (build zone)")
    if not math.isclose(float(tc.get("max_structure_mass", 60.0)), 60.0, rel_tol=0.0, abs_tol=1e-6):
        add("Structure mass budget")
    gx, gy = _physics_gravity_tuple(pc)
    if not (
        math.isclose(gx, 0.0, abs_tol=1e-9)
        and math.isclose(gy, -10.0, rel_tol=0.0, abs_tol=1e-6)
    ):
        add("Gravitational acceleration")
    h_ld, h_ad = _hull_linear_angular_damping(pc)
    if (h_ld, h_ad) != (0.1, 0.05):
        add("Hull and beam motion damping")
    if not math.isclose(float(tc.get("current_strength", 0.35)), 0.35, rel_tol=0.0, abs_tol=1e-6):
        add("Water-current bias")
    if not math.isclose(float(tc.get("wind_amplitude", 5.0)), 5.0, rel_tol=0.0, abs_tol=1e-6):
        add("Lateral wind forcing")
    if not math.isclose(float(tc.get("lateral_impulse_amplitude", 68.0)), 68.0, rel_tol=0.0, abs_tol=1e-6):
        add("Periodic lateral impulse kicks")
    if not math.isclose(float(tc.get("cargo_water_y", 1.98)), 1.98, rel_tol=0.0, abs_tol=1e-6):
        add("Cargo loss-plane height")
    h_amp = float(tc.get("hull_roll_impulse_amplitude", 0.0))
    h_int = int(tc.get("hull_roll_impulse_interval_steps", 90))
    if h_amp > 0.0 or h_int != 90:
        add("Hull roll impulses")

    t_fr, t_rest = _cargo_friction_restitution(tc)
    b_fr, b_rest = _cargo_friction_restitution({})
    tc_ld, tc_ad = _cargo_linear_angular_damping(tc)
    bc_ld, bc_ad = _cargo_linear_angular_damping({})
    if t_rest != b_rest:
        add("Cargo restitution")
    if t_fr != b_fr or (tc_ld, tc_ad) != (bc_ld, bc_ad):
        add("Cargo friction and damping")
    if not math.isclose(float(tc.get("max_capsize_angle_deg", 18.0)), 18.0, rel_tol=0.0, abs_tol=1e-6):
        add("Safe hull roll-angle limit")

    bullet_block = "\n".join(f" - **{lab}**" for lab in labels)
    return f"""
## Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables MIGHT have changed from the initial environment, NOT ALL of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
{bullet_block}

**Discovery via feedback**: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze failure modes from simulation feedback and adapt your design.
"""


def _merge_f05_terrain(prev: Dict[str, Any], delta: Dict[str, Any]) -> Dict[str, Any]:
    """Shallow merge with nested `cargo` dict merge; scalar/list keys in delta replace prev."""
    out = dict(prev)
    for k, v in delta.items():
        if k == "cargo" and isinstance(v, dict):
            base_c = out.get("cargo")
            out["cargo"] = {**(base_c if isinstance(base_c, dict) else {}), **v}
        else:
            out[k] = v
    return out


def _merge_f05_physics(prev: Dict[str, Any], delta: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(prev)
    out.update(delta)
    return out


def get_f05_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns overhauled stage configs for F-05: The Boat.
    Stages focus on structural innovation and complex physical reasoning.

    mutation_description is for logs/orchestration only and must NOT be shown to the agent.
    """

    _reef_barrier_rocks = [
        {"x": 13.15, "y": 2.02, "r": 0.44},
        {"x": 15.0, "y": 1.97, "r": 0.5},
        {"x": 16.85, "y": 2.02, "r": 0.44},
    ]

    _stage3_reef_field = [
        {"x": 13.05, "y": 2.06, "r": 0.46},
        {"x": 15.0, "y": 2.02, "r": 0.52},
        {"x": 16.95, "y": 2.06, "r": 0.46},
        {"x": 15.0, "y": 1.48, "r": 0.33},
    ]

    _raw_stages: List[Dict[str, Any]] = [
        {
            "stage_id": "Stage-1",
            "title": "Metacentric Deficit",
            "mutation_description": "Single-axis challenge: passive environmental roll-restoring torque may differ from the baseline. Capsize risk may increase unless the design provides explicit restoring moment and roll inertia.",
            "task_description_suffix": None,
            "terrain_config": {
                "restoring_coeff": 240.0,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-2",
            "title": "Raised Loss Plane",
            "mutation_description": "Single-axis challenge: the cargo-loss height threshold may differ from the baseline, tightening retention relative to the source task under wave-driven motion.",
            "task_description_suffix": None,
            "terrain_config": {
                "cargo_water_y": 2.28,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-3",
            "title": "Shoal Lock-In",
            "mutation_description": "Multi-axis coupling: altered reef layout, hull vertical placement, build-zone floor height, joint limits, lateral drift bias, impulsive hull roll kicks, and cargo contact parameters. Containment must supply roll inertia, avoid obstacle envelopes, and seal the hold within stated beam-width limits.",
            "task_description_suffix": None,
            "terrain_config": {
                "boat_y_offset": -0.10,
                "rocks": list(_stage3_reef_field),
                "build_zone_y_min": 2.58,
                "joint_max_force": 1750.0,
                "current_strength": 0.64,
                "cargo_restitution": 0.36,
                "cargo": {"friction": 0.62, "linear_damping": 0.24},
                "hull_roll_impulse_amplitude": 20.5,
                "hull_roll_impulse_interval_steps": 73,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-4",
            "title": "Perfect Storm Assembly Budget",
            "mutation_description": "Hardest coupling: altered reef layout, deck traction, gravity, mass budget, roll-restoring torque, lateral wind, impulses, and drift—overlapping with prior stage stressors. Designs must stay within the build zone, respect mass limits, and fully retain cargo.",
            "task_description_suffix": None,
            "terrain_config": {
                "boat_y_offset": -0.10,
                "rocks": list(_reef_barrier_rocks),
                "build_zone_y_min": 2.58,
                "current_strength": 0.62,
                "deck_friction": 0.0,
                "max_structure_mass": 46.0,
                "restoring_coeff": 340.0,
                "wind_amplitude": 8.8,
                "lateral_impulse_amplitude": 76.0,
                # Higher cap than Stage-3 so reference designs survive the full 10k-step evaluation horizon under +gravity / zero deck friction.
                "joint_max_force": 3100.0,
            },
            "physics_config": {
                "gravity": (0, -17.5),
            },
        },
    ]

    merged_tc: Dict[str, Any] = {}
    merged_pc: Dict[str, Any] = {}
    out_stages: List[Dict[str, Any]] = []
    for s in _raw_stages:
        s = dict(s)
        merged_tc = _merge_f05_terrain(merged_tc, s.get("terrain_config") or {})
        merged_pc = _merge_f05_physics(merged_pc, s.get("physics_config") or {})
        s["terrain_config"] = dict(merged_tc)
        s["physics_config"] = dict(merged_pc)
        s["task_description_suffix"] = build_f05_uniform_suffix(merged_tc, merged_pc)
        out_stages.append(s)
    return out_stages
