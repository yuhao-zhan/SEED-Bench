"""
C-04 curriculum stages. mutation_description is for logs/orchestration only — not shown to the agent.
Visible prompt deltas use: [new_value] (originally [old_value] in the source environment).
Viscous drag, turbulence, control reversal, magnetic floor, time-varying horizontal forcing, and similar
channels stay non-numeric in the base prompt; contact/damping coefficients are qualitative in prompt.py.
Mutated runs append **Environmental Anomalies Detected** via `_build_environmental_anomalies_suffix_curriculum_union()`
(S-01-style union over Stage-1…Stage-4 channels; no numeric leaks in the suffix).
"""
from typing import Any, Dict, List, Optional, Tuple
import re
import warnings

from tasks.Category5_Cybernetics_Control.C_04 import environment as c04_env

# Must match environment.py MAZE_WALLS
_DEFAULT_WALLS: Dict[int, Tuple[float, float, float, float]] = {
    0: (0.0, 0.0, 20.0, 0.5),
    1: (0.0, 2.5, 20.0, 0.5),
    2: (0.0, 0.0, 0.5, 3.0),
    3: (20.0, 0.0, 0.5, 3.0),
    4: (5.0, 0.0, 0.2, 1.0),
    5: (9.0, 1.8, 0.2, 1.2),
    6: (14.0, 1.8, 0.2, 1.2),
}

_DEFAULT_PHYSICS = {
    "control_lag_steps": 0,
    "structural_impulse_scale_k": float(c04_env.STRUCTURAL_IMPULSE_SCALE_K),
    "fluid_drag_x_min": -999.0,
    "fluid_drag_x_max": -999.0,
    "fluid_drag_coeff": 0.0,
    "turbulence_intensity": 0.0,
    "control_reversal_x_min": -999.0,
    "control_reversal_x_max": -999.0,
    "magnetic_floor_y_max": -999.0,
    "magnetic_floor_force": 0.0,
    "current_force_back": 0.0,
    "shear_wind_gradient": 0.0,
    "shear_wind_reference_y": float(c04_env.SHEAR_WIND_REFERENCE_Y),
    "oneway_force_right": float(c04_env.ONEWAY_FORCE_RIGHT),
    "lock_gate_fx": float(c04_env.LOCK_GATE_FX),
    "wind_oscillation_amp": float(c04_env.WIND_OSCILLATION_AMP),
    "wind_oscillation_omega": float(c04_env.WIND_OSCILLATION_OMEGA),
    "slip_friction": float(c04_env.SLIP_FRICTION),
    "max_steps": int(c04_env.MAX_STEPS),
    "lock_gate_x_min": float(c04_env.LOCK_GATE_X_MIN),
    "lock_gate_x_max": float(c04_env.LOCK_GATE_X_MAX),
    "activation_x_min": float(c04_env.ACTIVATION_X_MIN),
    "activation_x_max": float(c04_env.ACTIVATION_X_MAX),
    "backward_fx_threshold": float(c04_env.BACKWARD_FX_THRESHOLD),
    "backward_speed_max": float(c04_env.BACKWARD_SPEED_MAX),
    "backward_steps_required": int(c04_env.BACKWARD_STEPS_REQUIRED),
}

_DEFAULT_TERRAIN_DELAY = {
    "whisker_delay_steps": 0,
    "position_delay_steps": 0,
    "oneway_x": float(c04_env.ONEWAY_X),
}

# Labels aligned with environment.MAZE_WALLS comments (indices 4–6)
_MAZE_INNER_WALL_LABELS = ["internal wall 1", "internal wall 2", "internal wall 3"]


def _labeled_inner_walls_subset(terrain: Dict[str, Any] | None, indices: List[int]) -> str:
    raw = _effective_walls_subset(terrain, indices)
    parts = raw.split("; ")
    labels = _MAZE_INNER_WALL_LABELS
    return "; ".join(f"{labels[i]} {parts[i]}" for i in range(len(parts)))


def _gravity_y(pc: Optional[Dict[str, Any]]) -> float:
    if not pc:
        return -9.8
    g = pc.get("gravity", -9.8)
    if isinstance(g, (list, tuple)):
        return float(g[1])
    return float(g)


def _merge_physics(pc: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    out = dict(_DEFAULT_PHYSICS)
    if pc:
        pc = dict(pc)
        pc.pop("task_description", None)
        if "structural_impulse_scale_k" not in pc and "collision_velocity_limit" in pc:
            pc["structural_impulse_scale_k"] = float(pc["collision_velocity_limit"])
        pc.pop("collision_velocity_limit", None)
        out.update(pc)
    return out


def _terrain_delays(tc: Optional[Dict[str, Any]]) -> Tuple[int, int]:
    t = tc or {}
    wd = int(t.get("whisker_delay_steps", _DEFAULT_TERRAIN_DELAY["whisker_delay_steps"]))
    pd = int(t.get("position_delay_steps", _DEFAULT_TERRAIN_DELAY["position_delay_steps"]))
    return wd, pd


def _effective_walls_subset(terrain: Dict[str, Any] | None, indices: List[int]) -> str:
    w = dict(_DEFAULT_WALLS)
    overrides = (terrain or {}).get("wall_overrides") or {}
    for k, v in overrides.items():
        w[int(k)] = tuple(float(x) for x in v)
    parts = [w[i] for i in indices]
    return "; ".join(f"({t[0]:.1f}, {t[1]:.1f}, {t[2]:.1f}, {t[3]:.1f})" for t in parts)


def _blind_active(lo: float, hi: float) -> bool:
    return lo > -500.0 and hi > -500.0 and lo < hi


def _fmt_impulse_ns(v: float) -> str:
    """Match baseline prompt style: whole N·s omit trailing “.0” (e.g. 125 N·s)."""
    iv = int(round(v))
    if abs(v - iv) < 1e-6:
        return f"{iv} N·s"
    return f"{v:.1f} N·s"


# Appended after any whisker-blind value so mutation regex does not strip this disclosure.
_WHISKER_BLIND_NOTE = (
    " (When active, suppression uses **physical** body x—whisker raycasts use true pose—not reported position.)"
)


def _position_delay_reported_tail(delay_steps: int) -> str:
    if delay_steps <= 0:
        # Must stay aligned with baseline bullet in prompt.py (delay == 0).
        return (
            "**Reported vs physical pose**: When delay is 0, reported position matches physical position for exit, "
            "unlock, lock gate, and one-way bias. Other environmental effects may use **reported** pose, **physical** "
            "linear velocity, or **physical** height for participation rules depending on the active simulator "
            "configuration; those rules are **not** fully enumerated here (see **Environmental Anomalies Detected** "
            "when present on mutated runs). When delay is N>0, x-band memberships that rely on **reported** pose lag "
            "physical state by N simulation steps."
        )
    return (
        f"**Reported vs physical pose**: When delay is {delay_steps}, exit/unlock, lock gate, and one-way bias use "
        f"reported position lagging physical state by {delay_steps} simulation steps. Other environmental effects may "
        f"still combine reported pose with physical velocity or height per simulator rules; infer from interaction "
        f"(see **Environmental Anomalies Detected** when present)."
    )


def _configs_differ_from_base(
    tt: Optional[Dict[str, Any]],
    tp_raw: Optional[Dict[str, Any]],
    bt: Dict[str, Any],
    bp_merged: Dict[str, Any],
    bp_raw: Optional[Dict[str, Any]] = None,
) -> bool:
    """True if target stage differs from base (mutated curriculum vs source)."""
    tt = tt or {}
    tp_m = _merge_physics(tp_raw)
    bp_r = bp_raw or {}
    if _gravity_y(tp_raw) != _gravity_y(bp_r):
        return True
    if _effective_walls_subset(tt, list(range(7))) != _effective_walls_subset(bt, list(range(7))):
        return True
    blo, bhi = float(bt.get("whisker_blind_front_x_lo", -999.0)), float(bt.get("whisker_blind_front_x_hi", -999.0))
    tlo, thi = float(tt.get("whisker_blind_front_x_lo", -999.0)), float(tt.get("whisker_blind_front_x_hi", -999.0))
    base_blind = "none" if not _blind_active(blo, bhi) else f"x in [{blo:.1f}, {bhi:.1f}] m"
    tgt_blind = "none" if not _blind_active(tlo, thi) else f"x in [{tlo:.1f}, {thi:.1f}] m"
    if tgt_blind != base_blind:
        return True
    wdb, pdb = _terrain_delays(bt)
    wdt, pdt = _terrain_delays(tt)
    if wdb != wdt or pdb != pdt:
        return True
    if float(tt.get("oneway_x", _DEFAULT_TERRAIN_DELAY["oneway_x"])) != float(
        bt.get("oneway_x", _DEFAULT_TERRAIN_DELAY["oneway_x"])
    ):
        return True
    if int(tp_m["control_lag_steps"]) != int(bp_merged["control_lag_steps"]):
        return True
    if float(tp_m["structural_impulse_scale_k"]) != float(bp_merged["structural_impulse_scale_k"]):
        return True
    if int(tp_m.get("max_steps", _DEFAULT_PHYSICS["max_steps"])) != int(
        bp_merged.get("max_steps", _DEFAULT_PHYSICS["max_steps"])
    ):
        return True
    if int(tp_m.get("backward_steps_required", _DEFAULT_PHYSICS["backward_steps_required"])) != int(
        bp_merged.get("backward_steps_required", _DEFAULT_PHYSICS["backward_steps_required"])
    ):
        return True
    if float(tp_m.get("backward_fx_threshold", _DEFAULT_PHYSICS["backward_fx_threshold"])) != float(
        bp_merged.get("backward_fx_threshold", _DEFAULT_PHYSICS["backward_fx_threshold"])
    ):
        return True
    if float(tp_m.get("backward_speed_max", _DEFAULT_PHYSICS["backward_speed_max"])) != float(
        bp_merged.get("backward_speed_max", _DEFAULT_PHYSICS["backward_speed_max"])
    ):
        return True
    for key in (
        "fluid_drag_x_min",
        "fluid_drag_x_max",
        "fluid_drag_coeff",
        "turbulence_intensity",
        "control_reversal_x_min",
        "control_reversal_x_max",
        "magnetic_floor_y_max",
        "magnetic_floor_force",
        "current_force_back",
        "shear_wind_gradient",
        "shear_wind_reference_y",
        "oneway_force_right",
        "lock_gate_fx",
        "lock_gate_x_min",
        "lock_gate_x_max",
        "activation_x_min",
        "activation_x_max",
        "wind_oscillation_amp",
        "wind_oscillation_omega",
        "slip_friction",
    ):
        if float(tp_m.get(key, _DEFAULT_PHYSICS[key])) != float(bp_merged.get(key, _DEFAULT_PHYSICS[key])):
            return True
    return False


_UNIFORM_SUFFIX_GRAVITY_BULLET = (
    " - **Gravitational acceleration**: Vertical loads may differ from the nominal environment.\n"
)
_UNIFORM_SUFFIX_BULLETS_REST = """ - **Viscous Fluid Drag**: May have changed from the nominal environment.
 - **Stochastic forcing / turbulence**: Random lateral disturbances may differ from the nominal environment.
 - **Control Reversal Zone**: May have changed from the nominal environment.
 - **Magnetic Floor Anomaly**: May have changed from the nominal environment (low-altitude zone).

**Discovery via feedback**: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode to infer hidden constraints and adapt your design.
"""


def _uniform_suffix(include_gravity_mutation: bool) -> str:
    """Full curriculum superset appended to mutated task prompts (agent-facing)."""
    header = """## Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables **MIGHT** have changed from the initial environment, **NOT ALL** of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
"""
    g = _UNIFORM_SUFFIX_GRAVITY_BULLET if include_gravity_mutation else ""
    return header + g + _UNIFORM_SUFFIX_BULLETS_REST


def _build_environmental_anomalies_suffix_curriculum_union() -> str:
    """Union of qualitative warnings for every channel touched by Stage-1…Stage-4 (no per-stage diff, no numerics)."""
    return _uniform_suffix(include_gravity_mutation=False).strip()


# Same text appended to mutated task descriptions (single source; gravity omitted—no stage mutates gravity).
UNIFORM_SUFFIX = _build_environmental_anomalies_suffix_curriculum_union()

# Shown under success criteria for mutated stages (dynamic anomaly list is appended to task_description).
MUTATED_SUCCESS_CRITERIA_POINTER = """
---
**Mutated environment:** The **Environmental Anomalies Detected** section at the end of the Task Environment above lists physical channels that may differ from the source environment; apply that notice when solving this stage.
"""


def update_task_description_for_visible_changes(
    base_description: str,
    target_terrain_config: Dict[str, Any],
    base_terrain_config: Dict[str, Any],
    target_physics_config: Dict[str, Any] = None,
    base_physics_config: Dict[str, Any] = None,
) -> str:
    """Sync visible baseline strings when terrain/physics differ from source environment."""
    description = base_description
    bt = base_terrain_config or {}
    tt = target_terrain_config or {}
    bp_raw = base_physics_config or {}
    tp_raw = target_physics_config or {}
    bp = _merge_physics(base_physics_config)
    tp = _merge_physics(target_physics_config)

    mutated = _configs_differ_from_base(tt, tp_raw, bt, bp, bp_raw)
    # Gravity: do not inject numeric values into the prompt (hidden physics). Agents use world.gravity.y.

    # --- Maze outer shell (indices 0-3) ---
    ws_base_03 = _effective_walls_subset(bt, [0, 1, 2, 3])
    ws_tgt_03 = _effective_walls_subset(tt, [0, 1, 2, 3])
    if ws_tgt_03 != ws_base_03:
        pat = r"(- \*\*Maze outer shell \(indices 0–3; lower-left x, y, width, height in m\)\*\*: )(.*?)(\.\n|$)"
        # Note: In a real implementation we would preserve labels, but here we fulfill the prompt format requirement.
        # labels: floor, ceiling, left wall, right wall
        labels = ["floor", "ceiling", "left wall", "right wall"]
        base_parts = ws_base_03.split("; ")
        tgt_parts = ws_tgt_03.split("; ")
        base_labeled = "; ".join(f"{l} {p}" for l, p in zip(labels, base_parts))
        tgt_labeled = "; ".join(f"{l} {p}" for l, p in zip(labels, tgt_parts))
        if re.search(pat, description):
            description = re.sub(
                pat,
                lambda m: f"{m.group(1)}{tgt_labeled} (originally {base_labeled} in the source environment){m.group(3)}",
                description,
                count=1,
            )
        else:
            warnings.warn(
                "C_04 stages: maze outer shell mutation but outer-shell regex did not match.",
                RuntimeWarning,
                stacklevel=2,
            )

    # --- Maze walls (indices 4-6) ---
    ws_base_46 = _effective_walls_subset(bt, [4, 5, 6])
    ws_tgt_46 = _effective_walls_subset(tt, [4, 5, 6])
    if ws_tgt_46 != ws_base_46:
        pat = r"(- \*\*Maze walls \(indices 4-6; lower-left x, y, width, height in m\)\*\*: )(.*?)(\.\n|$)"
        tgt_labeled_46 = _labeled_inner_walls_subset(tt, [4, 5, 6])
        base_labeled_46 = _labeled_inner_walls_subset(bt, [4, 5, 6])
        if re.search(pat, description):
            description = re.sub(
                pat,
                lambda m: (
                    f"{m.group(1)}{tgt_labeled_46} (originally {base_labeled_46} in the source environment)"
                    f"{m.group(3)}"
                ),
                description,
                count=1,
            )
        else:
            warnings.warn(
                "C_04 stages: maze wall mutation but wall line regex did not match.", RuntimeWarning, stacklevel=2
            )

    # --- Whisker blind band ---
    blo, bhi = float(bt.get("whisker_blind_front_x_lo", -999.0)), float(bt.get("whisker_blind_front_x_hi", -999.0))
    tlo, thi = float(tt.get("whisker_blind_front_x_lo", -999.0)), float(tt.get("whisker_blind_front_x_hi", -999.0))
    base_blind = "none" if not _blind_active(blo, bhi) else f"x in [{blo:.1f}, {bhi:.1f}] m"
    tgt_blind = "none" if not _blind_active(tlo, thi) else f"x in [{tlo:.1f}, {thi:.1f}] m"
    if tgt_blind != base_blind or (tgt_blind != "none" and base_blind == "none"):
        if _blind_active(tlo, thi) and not _blind_active(blo, bhi):
            new_val = f"x in [{tlo:.1f}, {thi:.1f}] m (originally none in the source environment)"
        elif not _blind_active(tlo, thi) and _blind_active(blo, bhi):
            new_val = f"none (originally x in [{blo:.1f}, {bhi:.1f}] m in the source environment)"
        elif _blind_active(tlo, thi) and _blind_active(blo, bhi) and (tlo != blo or thi != bhi):
            new_val = f"x in [{tlo:.1f}, {thi:.1f}] m (originally x in [{blo:.1f}, {bhi:.1f}] m in the source environment)"
        else:
            new_val = None
        if new_val:
            pat = r"(- \*\*Whisker blind band along x \(m\)\*\*: )(.*?)(?=\s\()"
            if re.search(pat, description):
                description = re.sub(pat, lambda m: f"{m.group(1)}{new_val}", description, count=1)
            else:
                warnings.warn(
                    "C_04 stages: whisker blind mutation but blind-band regex did not match.", RuntimeWarning, stacklevel=2
                )

    # --- Control lag (idempotent) ---
    if int(tp["control_lag_steps"]) != int(bp["control_lag_steps"]):
        pat = r"(- \*\*Control lag \(simulation steps before commanded force takes effect\)\*\*: )(.*?)(\.\n|$)"
        if re.search(pat, description):
            description = re.sub(
                pat,
                lambda m: (
                    f"{m.group(1)}{int(tp['control_lag_steps'])} "
                    f"(originally {int(bp['control_lag_steps'])} simulation steps in the source environment){m.group(3)}"
                ),
                description,
                count=1,
            )
        else:
            warnings.warn(
                "C_04 stages: control_lag mutation but control lag regex did not match.", RuntimeWarning, stacklevel=2
            )

    # --- One-way threshold (terrain) + rightward assist force (physics) ---
    oxb = float(bt.get("oneway_x", _DEFAULT_TERRAIN_DELAY["oneway_x"]))
    oxt = float(tt.get("oneway_x", _DEFAULT_TERRAIN_DELAY["oneway_x"]))
    ofb = float(bp.get("oneway_force_right", _DEFAULT_PHYSICS["oneway_force_right"]))
    oft = float(tp.get("oneway_force_right", _DEFAULT_PHYSICS["oneway_force_right"]))
    if oxt != oxb or oft != ofb:
        pat = r"(- \*\*One-way rightward assist\*\*: )(.*?)(\.\n|$)"
        if re.search(pat, description):
            new_one = (
                f"While **reported** x **>** **{oxt:.1f}** m, an additional constant **+{oft:.1f}** N horizontal force "
                f"acts on the agent in +x (in addition to any other environmental horizontal forcing) "
                f"(originally {oxb:.1f} m threshold and +{ofb:.1f} N in the source environment)"
            )
            description = re.sub(pat, lambda m: f"{m.group(1)}{new_one}{m.group(3)}", description, count=1)
        else:
            warnings.warn(
                "C_04 stages: one-way assist mutation but one-way regex did not match.", RuntimeWarning, stacklevel=2
            )

    # --- Lock corridor repelling force (physics lock_gate_fx); unicode minus before x in baseline prompt ---
    lkb = abs(float(bp["lock_gate_fx"]))
    lkt = abs(float(tp["lock_gate_fx"]))
    if lkt != lkb:
        # Baseline: `**…** N in −x applies`; after mutation: `**…** N (originally **…** N in …) in −x applies`.
        pat = (
            r"(repelling horizontal force of )\*\*[^*]+\*\* N"
            r"(?: \(originally \*\*[^*]+\*\* N in the source environment\))? in −x applies"
        )
        if re.search(pat, description):
            description = re.sub(
                pat,
                lambda m: (
                    f"{m.group(1)}**{lkt:g}** N (originally **{lkb:g}** N in the source environment) in −x applies"
                ),
                description,
                count=1,
            )
        else:
            warnings.warn(
                "C_04 stages: lock_gate_fx mutation but lock-force regex did not match.",
                RuntimeWarning,
                stacklevel=2,
            )

    # --- Lock gate x-band (inside unlock bullet) ---
    lkb_lo, lkb_hi = float(bp["lock_gate_x_min"]), float(bp["lock_gate_x_max"])
    lkt_lo, lkt_hi = float(tp["lock_gate_x_min"]), float(tp["lock_gate_x_max"])
    if (lkt_lo, lkt_hi) != (lkb_lo, lkb_hi):
        pat = (
            r"(while \*\*reported\*\* x is in \[)"
            r"[\d.]+,\s*[\d.]+\]\s+m"
            r"(?: \(originally \[[\d.]+,\s*[\d.]+\]\s+m in the source environment\))?"
            r" \(\s*an additional repelling horizontal force"
        )
        if re.search(pat, description):
            description = re.sub(
                pat,
                lambda m: (
                    f"{m.group(1)}{lkt_lo:.1f}, {lkt_hi:.1f}] m (originally [{lkb_lo:.1f}, {lkb_hi:.1f}] m in the "
                    f"source environment) (an additional repelling horizontal force"
                ),
                description,
                count=1,
            )
        else:
            warnings.warn(
                "C_04 stages: lock_gate_x mutation but lock-band regex did not match.",
                RuntimeWarning,
                stacklevel=2,
            )

    # --- Activation x-band (unlock bullet) ---
    axb_lo, axb_hi = float(bp["activation_x_min"]), float(bp["activation_x_max"])
    axt_lo, axt_hi = float(tp["activation_x_min"]), float(tp["activation_x_max"])
    if (axt_lo, axt_hi) != (axb_lo, axb_hi):
        pat = (
            r"(To unlock: \*\*reported\*\* position x in \[)"
            r"[\d.]+,\s*[\d.]+\]\s+m"
            r"(?: \(originally \[[\d.]+,\s*[\d.]+\]\s+m in the source environment\))?"
            r" with"
        )
        if re.search(pat, description):
            description = re.sub(
                pat,
                lambda m: (
                    f"{m.group(1)}{axt_lo:.1f}, {axt_hi:.1f}] m (originally [{axb_lo:.1f}, {axb_hi:.1f}] m in the "
                    f"source environment) with"
                ),
                description,
                count=1,
            )
        else:
            warnings.warn(
                "C_04 stages: activation_x mutation but activation-band regex did not match.",
                RuntimeWarning,
                stacklevel=2,
            )

    # --- Behavioral unlock thresholds (commanded Fx, speed cap, consecutive steps) ---
    fxt, fxb = float(tp["backward_fx_threshold"]), float(bp["backward_fx_threshold"])
    st, sb = float(tp["backward_speed_max"]), float(bp["backward_speed_max"])
    nt, nb = int(tp["backward_steps_required"]), int(bp["backward_steps_required"])
    if fxt != fxb:
        fx_pat = (
            r"\*\*strictly less than \-?\d+(?:\.\d+)? N\*\*"
            r"(?: \(originally \*\*strictly less than \-?\d+(?:\.\d+)? N\*\* in the source environment\))?"
            r" \(e\.g\. \-?\d+(?:\.\d+)? N qualifies; \-?\d+(?:\.\d+)? N does not\)"
        )
        qual = int(round(fxt - 1.0))
        rep = (
            f"**strictly less than {fxt:.1f} N** (originally **strictly less than {fxb:.1f} N** in the source environment) "
            f"(e.g. {qual} N qualifies; {fxt:.1f} N does not)"
        )
        if re.search(fx_pat, description):
            description = re.sub(fx_pat, rep, description, count=1)
        else:
            warnings.warn(
                "C_04 stages: backward_fx_threshold mutation but unlock Fx regex did not match.",
                RuntimeWarning,
                stacklevel=2,
            )
    if st != sb:
        sp_pat = (
            r"(\*\*< )(\d+(?:\.\d+)?)( m/s\*\*)"
            r"(?: \(originally \*\*< \d+(?:\.\d+)? m/s\*\* in the source environment\))?"
        )
        if re.search(sp_pat, description):
            description = re.sub(
                sp_pat,
                f"**< {st:.1f} m/s** (originally **< {sb:.1f} m/s** in the source environment)",
                description,
                count=1,
            )
        else:
            warnings.warn(
                "C_04 stages: backward_speed_max mutation but unlock speed regex did not match.",
                RuntimeWarning,
                stacklevel=2,
            )
    if nt != nb:
        hold_rx = re.compile(
            rf"for at least \*\*{re.escape(str(nb))}\*\* consecutive steps(?!\s+\(originally)",
        )
        new_steps = (
            f"for at least **{nt}** consecutive steps "
            f"(originally **{nb}** consecutive steps in the source environment)"
        )
        description, n_hold = hold_rx.subn(new_steps, description, count=3)
        if n_hold < 3:
            warnings.warn(
                "C_04 stages: backward_steps_required mutation but fewer than 3 consecutive-steps phrases matched.",
                RuntimeWarning,
                stacklevel=2,
            )

    # --- Contact friction (qualitative baseline; mutation appends visibility note + originally clause) ---
    sfb, sft = float(bp["slip_friction"]), float(tp["slip_friction"])
    if sft != sfb:
        pat_contact = (
            r"(- \*\*Contact dynamics\*\*: Wall–agent friction and restitution are set on \*\*Box2D\*\* fixtures; )"
            r"(numeric coefficients are \*\*not stated in this document\*\*—infer from motion and impacts )"
            r"(\(see \*\*Environmental Anomalies Detected\*\* when present on mutated runs\)\.)"
        )
        if re.search(pat_contact, description):
            description = re.sub(
                pat_contact,
                lambda m: (
                    f"{m.group(1)}numeric coefficients are **not stated in this document**—infer from motion and impacts; "
                    f"**wall–agent friction may differ from the nominal environment** "
                    f"(originally the same qualitative contact model as in the source environment) "
                    f"{m.group(3)}"
                ),
                description,
                count=1,
            )
        else:
            warnings.warn(
                "C_04 stages: slip_friction mutation but contact-dynamics regex did not match.",
                RuntimeWarning,
                stacklevel=2,
            )

    # --- Structural k (impulse-per-mass scale); format: new (originally old in the source environment) ---
    tk, bk = float(tp["structural_impulse_scale_k"]), float(bp["structural_impulse_scale_k"])
    if tk != bk:
        am = float(c04_env.AGENT_MASS)
        imp_t, imp_b = tk * am, bk * am
        pat = (
            r"(- \*\*Structural k \(failure if collision normal impulse exceeds k \* agent mass [\d.]+ kg\)\*\*: )([^\n]+)"
        )
        old_val = f"k={bk:.1f}, impulse threshold {_fmt_impulse_ns(imp_b)}"
        new_val = f"k={tk:.1f}, impulse threshold {_fmt_impulse_ns(imp_t)}"
        new_line = (
            f"{new_val} (originally {old_val} in the source environment). "
            f"Here the failure condition is **normal impulse > (k × {am:g}) N·s** "
            f"(k acts as an impulse-per-mass scale in N·s per kg)."
        )
        if re.search(pat, description):
            description = re.sub(
                pat,
                lambda m: f"{m.group(1)}{new_line}\n",
                description,
                count=1,
            )
        else:
            warnings.warn(
                "C_04 stages: structural k mutation but structural k regex did not match.", RuntimeWarning, stacklevel=2
            )

    # --- Whisker stream delay / position report delay ---
    wdb, pdb = _terrain_delays(bt)
    wdt, pdt = _terrain_delays(tt)
    if wdb != wdt:
        pat = r"(- \*\*Whisker stream delay \(simulation steps\)\*\*: )(.*?)(\.\n|$)"
        if re.search(pat, description):
            description = re.sub(
                pat,
                lambda m: (
                    f"{m.group(1)}{wdt} "
                    f"(originally {wdb} simulation steps in the source environment){m.group(3)}"
                ),
                description,
                count=1,
            )
        else:
            warnings.warn(
                "C_04 stages: whisker delay mutation but regex did not match.", RuntimeWarning, stacklevel=2
            )

    # --- Position report delay (tail text must stay consistent with delay value) ---
    if pdb != pdt:
        pat = r"(- \*\*Position report delay \(simulation steps\)\*\*: )(.*?)(\.\n|$)"
        if re.search(pat, description):
            new_tail = _position_delay_reported_tail(pdt)
            description = re.sub(
                pat,
                lambda m: f"{m.group(1)}{pdt} (originally {pdb} simulation steps in the source environment). {new_tail}\n",
                description,
                count=1,
            )
        else:
            warnings.warn(
                "C_04 stages: position_delay_steps mutation but position delay regex did not match.",
                RuntimeWarning,
                stacklevel=2,
            )

    # --- Time limit (MAX_STEPS) ---
    if int(tp["max_steps"]) != int(bp["max_steps"]):
        pat = r"(- \*\*Time limit\*\*: At most )([\d,]+)( simulation steps)(\.)"
        if re.search(pat, description):
            description = re.sub(
                pat,
                lambda m: (
                    f"{m.group(1)}{int(tp['max_steps']):,}{m.group(3)} "
                    f"(originally {int(bp['max_steps']):,}{m.group(3)} in the source environment)"
                    f"{m.group(4)}"
                ),
                description,
                count=1,
            )
        else:
            warnings.warn(
                "C_04 stages: max_steps mutation but time limit regex did not match.",
                RuntimeWarning,
                stacklevel=2,
            )

    out = description.strip()
    if mutated:
        out = out + "\n\n" + _build_environmental_anomalies_suffix_curriculum_union()
    return out


def update_success_criteria_for_visible_changes(
    base_success_criteria: str,
    target_terrain_config: Dict[str, Any],
    base_terrain_config: Dict[str, Any],
    target_physics_config: Dict[str, Any] = None,
    base_physics_config: Dict[str, Any] = None,
) -> str:
    bt = base_terrain_config or {}
    tt = target_terrain_config or {}
    bp = _merge_physics(base_physics_config)
    tp = _merge_physics(target_physics_config)
    bp_raw = base_physics_config or {}
    tp_raw = target_physics_config or {}
    criteria = base_success_criteria
    am = float(c04_env.AGENT_MASS)
    tk, bk = float(tp["structural_impulse_scale_k"]), float(bp["structural_impulse_scale_k"])
    if tk != bk:
        imp_t, imp_b = tk * am, bk * am
        pat = r"(3\. \*\*Survival\*\*: )([^\n]+)"
        if re.search(pat, criteria):
            new_survival = (
                f"Stay below the structural impulse limit: **{_fmt_impulse_ns(imp_t)}** at k={tk:.1f} "
                f"(originally **{_fmt_impulse_ns(imp_b)}** at k={bk:.1f} in the source environment); "
                f"failure if normal impulse exceeds **k × ({am:g} kg)** in N·s."
            )
            criteria = re.sub(pat, lambda m: f"{m.group(1)}{new_survival}", criteria, count=1)
        else:
            warnings.warn(
                "C_04 stages: structural k mutation but success criteria Survival regex did not match.",
                RuntimeWarning,
                stacklevel=2,
            )
    nb_hold, nt_hold = int(bp["backward_steps_required"]), int(tp["backward_steps_required"])
    if nt_hold != nb_hold:
        hold_crit_rx = re.compile(
            rf"at least \*\*{re.escape(str(nb_hold))}\*\* consecutive steps(?!\s+\(originally)",
        )
        new_hold = (
            f"at least **{nt_hold}** consecutive steps "
            f"(originally **{nb_hold}** consecutive steps in the source environment)"
        )
        criteria, nhc = hold_crit_rx.subn(new_hold, criteria, count=1)
        if nhc < 1:
            warnings.warn(
                "C_04 stages: backward_steps_required mutation but success criteria Hold line not updated.",
                RuntimeWarning,
                stacklevel=2,
            )
    if _configs_differ_from_base(tt, tp_raw, bt, bp, bp_raw):
        criteria = criteria.rstrip() + "\n" + MUTATED_SUCCESS_CRITERIA_POINTER.strip()
    return criteria


def get_source_base_physics_config() -> Dict[str, Any]:
    """Merged defaults aligned with `environment.Sandbox` when `physics_config` is empty."""
    return dict(_merge_physics(None))


def get_source_base_terrain_config() -> Dict[str, Any]:
    """Canonical source terrain for staging comparisons (empty dict = default maze / delays in `environment.Sandbox`)."""
    return {}


def get_c04_curriculum_stages() -> List[Dict[str, Any]]:
    return [
        {
            "stage_id": "Stage-1",
            "title": "Inertial Fragility",
            "mutation_description": "Longer actuation latency and a much lower collision impulse tolerance than nominal.",
            "terrain_config": {},
            "physics_config": {
                "control_lag_steps": 25,
                "structural_impulse_scale_k": 5.0,
            },
        },
        {
            "stage_id": "Stage-2",
            "title": "Blind Altitude Shift",
            "mutation_description": "Whisker dropout over a forward x-band; interior walls lowered to the floor, removing crawl gaps.",
            "terrain_config": {
                "whisker_blind_front_x_lo": 5.0,
                "whisker_blind_front_x_hi": 13.0,
                "wall_overrides": {
                    "5": (9.0, 0.0, 0.2, 2.0),
                    "6": (14.0, 0.0, 0.2, 2.0),
                },
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-3",
            "title": "Turbulent Narrowway",
            "mutation_description": "Taller internal wall segment near x=5 m, adjusted obstacle geometry near x=9 m, viscous drag and random forcing in a mid-maze band, higher collision impulse ceiling.",
            "terrain_config": {
                "wall_overrides": {
                    "4": (5.0, 0.0, 0.2, 1.6),
                    "5": (9.0, 1.0, 0.2, 2.0),
                }
            },
            "physics_config": {
                "fluid_drag_x_min": 6.0,
                "fluid_drag_x_max": 14.0,
                "fluid_drag_coeff": 4.0,
                "turbulence_intensity": 50.0,
                "structural_impulse_scale_k": 50.0,
            },
        },
        {
            "stage_id": "Stage-4",
            "title": "The Magnetic Reversal Storm",
            "mutation_description": "Horizontal control inversion throughout the maze, strong downward bias near the floor, high turbulence; control lag matches the source environment (0 steps).",
            "terrain_config": {},
            "physics_config": {
                "control_reversal_x_min": 0.0,
                "control_reversal_x_max": 20.0,
                "magnetic_floor_y_max": 1.5,
                "magnetic_floor_force": -80.0,
                "turbulence_intensity": 150.0,
                "control_lag_steps": 0,
                "structural_impulse_scale_k": 50.0,
            },
        },
    ]
