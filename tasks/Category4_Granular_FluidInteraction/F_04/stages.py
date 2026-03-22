"""
F-04: The Filter — curriculum stages (mutations).

Mutations use regime shifts (e.g. net-upward gravity), resonant kinematic forcing (sweeper speed scale),
intrusive obstacle geometry (lowered baffles), multi-field shear (wind + sparsity), and full-stack
coupling (mass/beam caps, ice-like beam friction, heavy/bouncy/slippery particles, elevated damping).

Stage-1 / Stage-2: exactly one terrain or physics family changes per stage (baseline elsewhere).
Stage-3 / Stage-4: combined constraints with strictly increasing difficulty.

Information hiding: `mutation_description` is for logs/orchestration only and must NOT be shown to the agent.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple


def _f04_fmt_m(x: float) -> str:
    """Format a length in metres for prompts (no spurious trailing zeros)."""
    s = f"{float(x):.4f}".rstrip("0").rstrip(".")
    return s if s else "0"


def _f04_particle_counts_core(terrain_config: Dict[str, Any]) -> str:
    mix = terrain_config.get("mix") or {}
    n_first = int(mix.get("count_first_wave", 15))
    ns = int(mix.get("count_small", n_first))
    nm = int(mix.get("count_medium", n_first))
    nl = int(mix.get("count_large", n_first))
    n_third = int(mix.get("count_third_wave", 15))
    nt_s = int(mix.get("count_third_small", n_third))
    nt_m = int(mix.get("count_third_medium", n_third))
    nt_l = int(mix.get("count_third_large", n_third))
    s2 = int(terrain_config.get("second_wave_step", 1800))
    s3 = int(terrain_config.get("third_wave_step", 3600))
    ts = ns * 2 + nt_s
    tm = nm * 2 + nt_m
    tl = nl * 2 + nt_l
    total = ts + tm + tl
    if nt_s == nt_m == nt_l:
        third_seg = f"and {nt_s} of each size again at step {s3}"
    else:
        third_seg = f"and {nt_s} small, {nt_m} medium, and {nt_l} large at step {s3}"
    return (
        f"{ns} small, {nm} medium, and {nl} large in the first wave; the same counts again at step {s2}; "
        f"{third_seg} — **{total} particles total** ({ts} small, {tm} medium, {tl} large) after all waves have spawned"
    )


def _f04_particle_counts_visible(terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    t = _f04_particle_counts_core(terrain_config)
    b = _f04_particle_counts_core(base_terrain_config)
    if t != b:
        return f"{t} (originally {b} in the source environment)"
    return t


def _f04_feed_schedule_paragraph(terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    s2 = int(terrain_config.get("second_wave_step", 1800))
    s3 = int(terrain_config.get("third_wave_step", 3600))
    b2 = int(base_terrain_config.get("second_wave_step", 1800))
    b3 = int(base_terrain_config.get("third_wave_step", 3600))
    mid = f"(second batch at step {s2}, third at step {s3} by default)"
    if (s2, s3) != (b2, b3):
        mid += (
            f" (originally second batch at step {b2}, third at step {b3} in the source environment)"
        )
    return (
        "- **Feed schedule**: Additional batches of particles are released at fixed simulation steps "
        f"{mid}. **Simulation budget**: allow **at least 5000** steps so every batch can spawn and the system "
        f"can settle after the third wave (which starts at step {s3}). **Step cap**: The sandbox exposes "
        "`MAX_STEPS` (default 10000); runners typically stop at that many steps unless configured "
        "otherwise—plan so the task is solvable within both the minimum above and this cap."
    )


def _f04_sync_particle_counts_bullet(
    description: str,
    target_terrain_config: Dict[str, Any],
    base_terrain_config: Dict[str, Any],
) -> str:
    middle = _f04_particle_counts_visible(target_terrain_config, base_terrain_config)
    pat = r"- \*\*Particle counts \(default\)\*\*:.*?(?=\. \*\*Classification purity\*\*)"
    if not re.search(pat, description):
        return description
    return re.sub(
        pat,
        f"- **Particle counts (default)**: {middle}",
        description,
        count=1,
    )


def _f04_sync_feed_schedule_bullet(
    description: str,
    target_terrain_config: Dict[str, Any],
    base_terrain_config: Dict[str, Any],
) -> str:
    new_para = _f04_feed_schedule_paragraph(target_terrain_config, base_terrain_config)
    pat = (
        r"- \*\*Feed schedule\*\*: Additional batches of particles are released at fixed simulation steps "
        r".*?this cap\."
    )
    if not re.search(pat, description):
        return description
    return re.sub(pat, new_para, description, count=1)


def _f04_feed_bounds(terrain_config: Dict[str, Any]) -> Tuple[float, float, float, float]:
    return (
        float(terrain_config.get("feed_x_min", 5.2)),
        float(terrain_config.get("feed_x_max", 6.9)),
        float(terrain_config.get("feed_y_min", 3.0)),
        float(terrain_config.get("feed_y_max", 5.0)),
    )


def _f04_sweeper_effective_speeds(terrain_config: Dict[str, Any]) -> Tuple[float, float]:
    sw = terrain_config.get("sweeper") or {}
    scale = float(sw.get("speed_scale", 1.0))
    v1 = float(sw.get("v_sweep1", 0.09)) * scale
    v2 = float(sw.get("v_sweep2", 0.05)) * scale
    return v1, v2


def _f04_sync_feed_y_cross_zone_line(
    text: str,
    base_feed: Tuple[float, float, float, float],
    target_feed: Tuple[float, float, float, float],
) -> str:
    """When feed_y_min changes, update contamination threshold lines to the required (originally …) format."""
    if target_feed[2] == base_feed[2]:
        return text
    new_y, old_y = _f04_fmt_m(target_feed[2]), _f04_fmt_m(base_feed[2])
    repl = f"when **y < {new_y} m** (originally **{old_y} m** in the source environment)"
    pristine = (
        r"when \*\*y < \d+(?:\.\d+)? m\*\* \(Feed Zone lower y in the source environment\)"
    )
    if re.search(pristine, text):
        return re.sub(pristine, repl, text)
    already = (
        r"when \*\*y < \d+(?:\.\d+)? m\*\* \(originally \*\*\d+(?:\.\d+)? m\*\* in the source environment\)"
        r"(?: \(Feed Zone lower y boundary\))?"
    )
    if re.search(already, text):
        return re.sub(already, repl, text)
    return text


def update_task_description_for_visible_changes(
    base_description: str,
    target_terrain_config: Dict[str, Any],
    base_terrain_config: Dict[str, Any],
    **kwargs: Any,
) -> str:
    """Update task description for visible changes using format: [new_value] (originally [old_value] in the source environment).

    ``base_terrain_config`` must be the pristine / Initial source (typically ``{}``). Passing another stage's
    config will produce incorrect ``(originally …)`` values.

    Accepts ``**kwargs`` (e.g. ``stage=`` from evaluate_mutated) so callers need not special-case signatures.
    """
    description = base_description
    base_mass = base_terrain_config.get("max_structure_mass", 75.0)
    target_mass = target_terrain_config.get("max_structure_mass", 75.0)
    if target_mass != base_mass:
        mass_pattern = (
            r"(Total structure mass <= )(\d+\.?\d*)( kg)"
            r"(?: \(originally \d+\.?\d* kg in the source environment\))?;"
        )
        if re.search(mass_pattern, description):
            description = re.sub(
                mass_pattern,
                lambda m: (
                    f"{m.group(1)}{target_mass:.0f}{m.group(3)} "
                    f"(originally {base_mass:.0f}{m.group(3)} in the source environment);"
                ),
                description,
                count=1,
            )
        else:
            needle_mass = f"<= {base_mass:.0f} kg"
            if needle_mass in description:
                description = description.replace(
                    needle_mass,
                    f"<= {target_mass:.0f} kg (originally {base_mass:.0f} kg in the source environment)",
                    1,
                )
    base_beams = base_terrain_config.get("max_beams", 6)
    target_beams = target_terrain_config.get("max_beams", 6)
    if target_beams != base_beams:
        beams_pattern = (
            r"(Maximum )(\d+)( beams)(?: \(originally \d+ beams in the source environment\))?(\.)"
        )
        if re.search(beams_pattern, description):
            description = re.sub(
                beams_pattern,
                lambda m: (
                    f"{m.group(1)}{target_beams}{m.group(3)} "
                    f"(originally {base_beams}{m.group(3)} in the source environment){m.group(4)}"
                ),
                description,
                count=1,
            )
        else:
            needle_beams = f"Maximum {base_beams} beams"
            if needle_beams in description:
                description = description.replace(
                    needle_beams,
                    f"Maximum {target_beams} beams (originally {base_beams} beams in the source environment)",
                    1,
                )

    base_feed = _f04_feed_bounds(base_terrain_config)
    target_feed = _f04_feed_bounds(target_terrain_config)
    if target_feed != base_feed:
        feed_pat = (
            r"- \*\*Feed Zone\*\*: Particles are introduced in "
            r"x=\[\d+\.?\d*, \d+\.?\d*\] m, y=\[\d+\.?\d*, \d+\.?\d*\] m"
            r"(?: \(originally x=\[\d+\.?\d*, \d+\.?\d*\] m, y=\[\d+\.?\d*, \d+\.?\d*\] m in the source environment\))?"
            r" \(bounds may be overridden via environment configuration\)\."
        )
        feed_repl = (
            f"- **Feed Zone**: Particles are introduced in x=[{target_feed[0]:.1f}, {target_feed[1]:.1f}] m, "
            f"y=[{target_feed[2]:.1f}, {target_feed[3]:.1f}] m "
            f"(originally x=[{base_feed[0]:.1f}, {base_feed[1]:.1f}] m, y=[{base_feed[2]:.1f}, {base_feed[3]:.1f}] m "
            f"in the source environment) (bounds may be overridden via environment configuration)."
        )
        if re.search(feed_pat, description):
            description = re.sub(feed_pat, feed_repl, description, count=1)
        else:
            old_snip = (
                f"x=[{base_feed[0]:.1f}, {base_feed[1]:.1f}] m, "
                f"y=[{base_feed[2]:.1f}, {base_feed[3]:.1f}] m"
            )
            new_snip = (
                f"x=[{target_feed[0]:.1f}, {target_feed[1]:.1f}] m, "
                f"y=[{target_feed[2]:.1f}, {target_feed[3]:.1f}] m "
                f"(originally x=[{base_feed[0]:.1f}, {base_feed[1]:.1f}] m, y=[{base_feed[2]:.1f}, {base_feed[3]:.1f}] m "
                f"in the source environment)"
            )
            if old_snip in description:
                description = description.replace(old_snip, new_snip, 1)

    base_purity = base_terrain_config.get("min_purity", 0.35)
    target_purity = target_terrain_config.get("min_purity", 0.35)
    if target_purity != base_purity:
        # Keep objective text synchronized with success criteria when purity mutates.
        desc_purity_pat = (
            r"(Achieves \*\*classification purity ≥ )(\d+\.?\d*)(%\*\*)"
            r"(?: \(originally \d+\.?\d*% in the source environment\))?"
        )
        if re.search(desc_purity_pat, description):
            description = re.sub(
                desc_purity_pat,
                lambda m: (
                    f"{m.group(1)}{target_purity*100:.0f}{m.group(3)} "
                    f"(originally {base_purity*100:.0f}% in the source environment)"
                ),
                description,
                count=1,
            )

    v1_b, v2_b = _f04_sweeper_effective_speeds(base_terrain_config)
    v1_t, v2_t = _f04_sweeper_effective_speeds(target_terrain_config)
    if v1_t != v1_b:
        lower_pat = (
            r"(nominal speed ~)(\d+\.?\d*)( m/s)"
            r"(?: \(originally ~\d+\.?\d* m/s in the source environment\))?"
        )
        if re.search(lower_pat, description):
            description = re.sub(
                lower_pat,
                lambda m: (
                    f"{m.group(1)}{v1_t:.2f}{m.group(3)} "
                    f"(originally ~{v1_b:.2f} m/s in the source environment)"
                ),
                description,
                count=1,
            )
        else:
            needle_lo = f"nominal speed ~{v1_b:.2f} m/s"
            repl_lo = (
                f"nominal speed ~{v1_t:.2f} m/s "
                f"(originally ~{v1_b:.2f} m/s in the source environment)"
            )
            if needle_lo in description:
                description = description.replace(needle_lo, repl_lo, 1)
    if v2_t != v2_b:
        upper_pat = (
            r"(at ~)(\d+\.?\d*)( m/s in the opposite direction)"
            r"(?: \(originally ~\d+\.?\d* m/s in the source environment\))?"
        )
        if re.search(upper_pat, description):
            description = re.sub(
                upper_pat,
                lambda m: (
                    f"{m.group(1)}{v2_t:.2f}{m.group(3)} "
                    f"(originally ~{v2_b:.2f} m/s in the source environment)"
                ),
                description,
                count=1,
            )
        else:
            needle_hi = f"at ~{v2_b:.2f} m/s in the opposite direction"
            repl_hi = (
                f"at ~{v2_t:.2f} m/s in the opposite direction "
                f"(originally ~{v2_b:.2f} m/s in the source environment)"
            )
            if needle_hi in description:
                description = description.replace(needle_hi, repl_hi, 1)

    base_baffles = base_terrain_config.get("baffles") or {}
    target_baffles = target_terrain_config.get("baffles") or {}
    base_baffle_y = float(base_baffles.get("y_bottom", 2.4))
    target_baffle_y = float(target_baffles.get("y_bottom", base_baffle_y))
    if target_baffle_y != base_baffle_y:
        # Idempotent: matches pristine "y=2.4 m;" or already-updated "y=1.80 m (originally 2.40 m in the source environment);"
        baffle_y_pattern = (
            r"(lower edge at y=)(\d+\.?\d*) m(?: \(originally \d+\.?\d* m in the source environment\))?;"
        )
        if re.search(baffle_y_pattern, description):
            description = re.sub(
                baffle_y_pattern,
                lambda m: (
                    f"{m.group(1)}{target_baffle_y:.2f} m (originally {base_baffle_y:.2f} m in the source environment);"
                ),
                description,
                count=1,
            )

    description = _f04_sync_particle_counts_bullet(description, target_terrain_config, base_terrain_config)
    description = _f04_sync_feed_schedule_bullet(description, target_terrain_config, base_terrain_config)

    bf = _f04_feed_bounds(base_terrain_config)
    tf = _f04_feed_bounds(target_terrain_config)
    description = _f04_sync_feed_y_cross_zone_line(description, bf, tf)
    return description


def update_success_criteria_for_visible_changes(
    base_success_criteria: str,
    target_terrain_config: Dict[str, Any],
    base_terrain_config: Dict[str, Any],
    **kwargs: Any,
) -> str:
    """Update success criteria for visible changes using format: [new_value] (originally [old_value] in the source environment).

    ``base_terrain_config`` must be the pristine / Initial source (typically ``{}``).

    Accepts ``**kwargs`` for compatibility with callers that pass extra arguments.
    """
    criteria = base_success_criteria

    target_purity = target_terrain_config.get("min_purity", 0.35)
    base_purity = base_terrain_config.get("min_purity", 0.35)
    if target_purity != base_purity:
        purity_pat = (
            r"(Overall purity \(correctly categorized particles / total particles"
            r"(?: \*\*currently in the simulation\*\*)?\) >= )(\d+\.?\d*)(%)"
            r"(?: \(originally \d+\.?\d*% in the source environment\))?"
        )
        if re.search(purity_pat, criteria):
            criteria = re.sub(
                purity_pat,
                lambda m: (
                    f"{m.group(1)}{target_purity*100:.0f}{m.group(3)} "
                    f"(originally {base_purity*100:.0f}{m.group(3)} in the source environment)"
                ),
                criteria,
                count=1,
            )
        else:
            criteria = criteria.replace(
                f">= {base_purity*100:.0f}%",
                f">= {target_purity*100:.0f}% (originally {base_purity*100:.0f}% in the source environment)",
                1,
            )

    target_mass = target_terrain_config.get("max_structure_mass", 75.0)
    base_mass = base_terrain_config.get("max_structure_mass", 75.0)
    if target_mass != base_mass:
        mass_pattern = (
            r"(Total structure mass <= )(\d+\.?\d*)( kg)"
            r"(?: \(originally \d+\.?\d* kg in the source environment\))?(\.)"
        )
        if re.search(mass_pattern, criteria):
            criteria = re.sub(
                mass_pattern,
                lambda m: (
                    f"{m.group(1)}{target_mass:.0f} kg "
                    f"(originally {base_mass:.0f} kg in the source environment){m.group(4)}"
                ),
                criteria,
                count=1,
            )
        else:
            mass_needles = []
            for fmt in ("{:.0f}", "{:.1f}"):
                s = fmt.format(base_mass)
                mass_needles.extend([f"<= {s} kg.", f"<= {s} kg"])
            seen = set()
            for needle in mass_needles:
                if needle in seen:
                    continue
                seen.add(needle)
                if needle in criteria:
                    criteria = criteria.replace(
                        needle,
                        f"<= {target_mass:.0f} kg (originally {base_mass:.0f} kg in the source environment).",
                        1,
                    )
                    break

    target_beams = target_terrain_config.get("max_beams", 6)
    base_beams = base_terrain_config.get("max_beams", 6)
    if target_beams != base_beams:
        beams_pattern = (
            r"(Maximum )(\d+)( beams)(?: \(originally \d+ beams in the source environment\))?(\.)"
        )
        if re.search(beams_pattern, criteria):
            criteria = re.sub(
                beams_pattern,
                lambda m: (
                    f"{m.group(1)}{target_beams} beams "
                    f"(originally {base_beams} beams in the source environment){m.group(4)}"
                ),
                criteria,
                count=1,
            )
        else:
            for needle in (f"Maximum {base_beams} beams.", f"Maximum {base_beams} beams"):
                if needle in criteria:
                    criteria = criteria.replace(
                        needle,
                        f"Maximum {target_beams} beams (originally {base_beams} beams in the source environment).",
                        1,
                    )
                    break

    bf = _f04_feed_bounds(base_terrain_config)
    tf = _f04_feed_bounds(target_terrain_config)
    criteria = _f04_sync_feed_y_cross_zone_line(criteria, bf, tf)
    return criteria


def get_f04_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Ordered stage configs. Uniform suffix = union of every physical knob touched in Stage-1…Stage-4
    (worded generally — no per-stage numeric spoilers).
    """
    # Union of mutated variables across all stages (see terrain_config / physics_config below):
    # - baffles.y_bottom (vertical extent of feed obstructions into the classifier band)
    # - sweeper.speed_scale (kinematic aggressiveness of horizontal sweepers)
    # - max_beams, max_structure_mass
    # - wind_amplitude, gust_amplitude, wind_period_steps
    # - gravity (physics_config)
    # - linear_damping, angular_damping
    # - mix.density, mix.restitution, mix.friction
    # - beam_friction (agent structure vs particles)
    UNIFORM_SUFFIX = """

## Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables **MIGHT** have changed from the initial environment, **NOT ALL** of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
- **Feed obstruction (`baffles` geometry)**: Vertical baffle placement or vertical extent may differ from the source layout, altering unobstructed paths through the classifier band.
- **Sweeper kinematics (`sweeper.speed_scale`, sweep velocities)**: Horizontal sweeper motion parameters may differ from the source environment.
- **Structural budgets (`max_beams`, `max_structure_mass`)**: Limits on beam count and total structural mass may differ from the source environment.
- **Lateral wind & gusts (`wind_amplitude`, `gust_amplitude`, `wind_period_steps`)**: Lateral forcing on particles may differ from the source environment.
- **Gravitational field (`gravity`)**: Net gravitational acceleration may differ from the source environment.
- **Ambient damping (`linear_damping`, `angular_damping`)**: Linear and angular damping applied to bodies may differ from the source environment.
- **Particle bulk properties (`mix.density`, `mix.restitution`, `mix.friction`)**: Particle inertia and contact behavior may differ from the source mixture.
- **Structure–particle contact (`beam_friction`)**: Tangential interaction between your beams and particles may differ from the source environment.

**Discovery via feedback**: Identify the effective physical rules of this environment through trial and reasoning. When a design fails, use observed motion, contacts, and metrics to revise the structure and control strategy.
"""
    return [
        {
            "stage_id": "Stage-1",
            "title": "Buoyant Regime — Net Upward Gravity",
            "mutation_description": "Single change: gravity (0,+0.55) — net upward acceleration; passive settling assumptions fail (threshold crossing, not mild g-tweak).",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "min_purity": 0.35,
            },
            "physics_config": {
                "gravity": (0.0, 0.55),
            },
        },
        {
            "stage_id": "Stage-2",
            "title": "Resonant Sweeper Forcing",
            "mutation_description": "Single change: sweeper.speed_scale=5.0 — deterministic disruption of the baseline rhythm (validated vs reference).",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "min_purity": 0.35,
                "sweeper": {"speed_scale": 5.0},
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-3",
            "title": "Shear + Sparsity + Intrusion",
            "mutation_description": "Beam cap (5), lowered baffles into sieve band, strong oscillatory wind — baseline six-beam layout invalid; harder than Stage-2, weaker than Stage-4 stack.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "min_purity": 0.35,
                "max_beams": 5,
                "baffles": {"y_bottom": 1.80},
                "wind_amplitude": 410.0,
                "wind_period_steps": 260,
                "gust_amplitude": 105.0,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-4",
            "title": "Heavy Ice Storm Sieve",
            "mutation_description": "Full stack: deep baffles, faster sweepers, tight mass/beam caps, wind, elevated damping+gravity, dense/bouncy/slippery mix, zero beam friction.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "min_purity": 0.35,
                "max_beams": 5,
                "max_structure_mass": 30.0,
                "baffles": {"y_bottom": 1.64},
                "sweeper": {"speed_scale": 2.85},
                "wind_amplitude": 600.0,
                "wind_period_steps": 190,
                "gust_amplitude": 150.0,
                "beam_friction": 0.0,
                "mix": {
                    "density": 2950.0,
                    "restitution": 0.74,
                    "friction": 0.13,
                },
            },
            "physics_config": {
                "gravity": (0.0, -12.4),
                "linear_damping": 0.64,
                "angular_damping": 0.64,
            },
        },
    ]
