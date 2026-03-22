"""
F-01: The Dam task curriculum stages (mutations).

Mutations combine hidden levers (e.g. particle restitution, gravity, debris speed) with visible
terrain keys that appear in the task text. `update_task_description_for_visible_changes` syncs
weld force/steps, leak %, reservoir fill height, and wall A/P in the **task description** string.
`update_success_criteria_for_visible_changes` only syncs **leakage rate** lines in **success criteria**
(fill height and wall parameters are not repeated there).

Stage-1/2: exactly one terrain_config lever each (threshold vs granular–interface physics).
Stage-3/4: multiple interacting levers (Stage-4 extends Stage-3 with gravity + debris); difficulty strictly increases through Stage-4.

Information hiding: `mutation_description` is for logs/orchestration only and must NOT be shown to the agent.
"""
from __future__ import annotations

from typing import Any, Dict, List
import re

# Union of all physical variables touched across Stage-1 … Stage-4 (same string for every stage).
UNIFORM_SUFFIX = """
## Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables MIGHT have changed from the initial environment, NOT ALL of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
 - Beam-to-beam weld force threshold: The reaction-force limit above which a weld begins accumulating toward failure.
 - Weld failure persistence: The number of consecutive simulation steps used when deciding whether an overloaded weld is removed.
 - Reservoir particle normal restitution (bounciness of fluid granules): May differ from the nominal reservoir, affecting collision chains and slosh.
 - Downstream boundary oscillation: Lateral motion amplitude of the downstream wall (the leak boundary).
 - Gravitational acceleration: Global vertical gravity affecting loads and settling.
 - Debris impact velocity: Launch velocity of debris toward the dam.

Discovery via feedback: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., where a joint breaks, how a body moves, or how leakage spikes after a wall phase) to infer the hidden constraints and adapt your design.
"""


def _replace_weld_constraint_line(
    description: str,
    *,
    target_force: float,
    base_force: float,
    target_steps: int,
    base_steps: int,
) -> str:
    """Replace the single-line weld constraint; format (originally ...) only for mutated parts."""
    marker = "- **Constraint**: Beam-to-beam welds break when reaction force **reaches or exceeds** "
    start = description.find(marker)
    if start == -1:
        return description
    end = description.find("\n", start)
    if end == -1:
        end = len(description)
    force_part = f"{target_force:.0f} N"
    if target_force != base_force:
        force_part += f" (originally {base_force:.0f} N in the source environment)"
    steps_part = f"{target_steps} consecutive simulation steps"
    if target_steps != base_steps:
        steps_part += (
            f" (originally {base_steps} consecutive simulation steps in the source environment)"
        )
    new_line = f"{marker}{force_part} for {steps_part}."
    return description[:start] + new_line + description[end:]


def _fmt_float_short(x: float) -> str:
    s = f"{float(x):.6f}".rstrip("0").rstrip(".")
    return s if s else "0"


def _replace_moving_wall_amp_phase(
    description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]
) -> str:
    """Sync **A** and **P** in the moving-wall sentence; format (originally ...) when mutated."""
    default_amp = 0.4
    default_phase = 100.0
    ta = float(target_terrain_config.get("downstream_wall_amplitude", default_amp))
    ba = float(base_terrain_config.get("downstream_wall_amplitude", default_amp))
    tp = float(target_terrain_config.get("downstream_wall_phase_divisor", default_phase))
    bp = float(base_terrain_config.get("downstream_wall_phase_divisor", default_phase))
    if ta == ba and tp == bp:
        return description
    pat = re.compile(
        r"with \*\*A = \d+\.?\d*\*\* m(?: \(originally \d+\.?\d* m in the source environment\))? "
        r"and \*\*P = \d+\.?\d*\*\*(?: \(originally \d+(?:\.\d+)? in the source environment\))?, where"
    )
    if not pat.search(description):
        return description
    amp_seg = f"**A = {_fmt_float_short(ta)}** m"
    if ta != ba:
        amp_seg += f" (originally {_fmt_float_short(ba)} m in the source environment)"
    p_seg = f"**P = {_fmt_float_short(tp)}**"
    if tp != bp:
        p_seg += f" (originally {_fmt_float_short(bp)} in the source environment)"
    new_seg = f"with {amp_seg} and {p_seg}, where"
    return pat.sub(new_seg, description, count=1)


def _replace_debris_velocity_line(
    description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]
) -> str:
    """Sync debris launch velocity in task description, including (originally ...) for mutated parts."""
    default_vx = 2.2
    default_vy = 0.0
    tvx = float(target_terrain_config.get("debris_linear_velocity_x", default_vx))
    bvx = float(base_terrain_config.get("debris_linear_velocity_x", default_vx))
    tvy = float(target_terrain_config.get("debris_linear_velocity_y", default_vy))
    bvy = float(base_terrain_config.get("debris_linear_velocity_y", default_vy))
    if tvx == bvx and tvy == bvy:
        return description

    pat = re.compile(
        r"default initial velocity \*\*\(([+-]?\d+\.?\d*),\s*([+-]?\d+\.?\d*)\)\*\* m/s unless the configuration overrides the debris velocity\."
    )
    m = pat.search(description)
    if not m:
        return description

    vx_seg = _fmt_float_short(tvx)
    vy_seg = _fmt_float_short(tvy)
    if tvx != bvx:
        vx_seg += f" (originally {_fmt_float_short(bvx)} in the source environment)"
    if tvy != bvy:
        vy_seg += f" (originally {_fmt_float_short(bvy)} in the source environment)"
    new_text = (
        f"default initial velocity **({vx_seg}, {vy_seg})** m/s unless the configuration overrides the debris velocity."
    )
    return pat.sub(new_text, description, count=1)


def update_task_description_for_visible_changes(
    base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]
) -> str:
    """
    Update task description for visible changes using format:
    [new_value] (originally [old_value] in the source environment).

    IMPORTANT: base_terrain_config must be the pristine/source environment (empty or default).
    If base_terrain_config is another stage's config (e.g. in cross-mutated evaluation),
    the phrase "originally ... in the source environment" will be misleading.
    """
    description = base_description
    default_leakage = 0.001
    default_joint_break_force = 50000.0
    default_joint_break_consecutive_steps = 3
    default_fluid_height = 7.0

    # Leakage rate
    target_leakage = target_terrain_config.get("max_leakage_rate", default_leakage)
    base_leakage = base_terrain_config.get("max_leakage_rate", default_leakage)
    if target_leakage != base_leakage:
        # Task objective line
        pattern_obj = r"(the leakage rate does not exceed )(\d+\.?\d*%)"
        if re.search(pattern_obj, description):
            description = re.sub(
                pattern_obj,
                f"\\g<1>{target_leakage*100:.2f}% (originally {base_leakage*100:.2f}% in the source environment)",
                description,
            )
        # Legacy wording (if present)
        pattern_legacy = r"(leakage rate remains below )(\d+\.?\d*%)"
        if re.search(pattern_legacy, description):
            description = re.sub(
                pattern_legacy,
                f"\\g<1>{target_leakage*100:.2f}% (originally {base_leakage*100:.2f}% in the source environment)",
                description,
            )

    # Joint break force + consecutive steps (visible structural limits)
    target_break = float(target_terrain_config.get("joint_break_force", default_joint_break_force))
    base_break = float(base_terrain_config.get("joint_break_force", default_joint_break_force))
    target_steps = int(target_terrain_config.get("joint_break_consecutive_steps", default_joint_break_consecutive_steps))
    base_steps = int(base_terrain_config.get("joint_break_consecutive_steps", default_joint_break_consecutive_steps))
    if target_break != base_break or target_steps != base_steps:
        description = _replace_weld_constraint_line(
            description,
            target_force=target_break,
            base_force=base_break,
            target_steps=target_steps,
            base_steps=base_steps,
        )

    # Reservoir fill height (visible structural limit)
    target_height = target_terrain_config.get("fluid_height", default_fluid_height)
    base_height = base_terrain_config.get("fluid_height", default_fluid_height)
    if target_height != base_height:
        pattern = r"(\*\*Reservoir fill height\*\*: )(\d+\.?\d*)( m\.)"
        if re.search(pattern, description):
            description = re.sub(
                pattern,
                f"\\g<1>{target_height:.1f} m (originally {base_height:.1f} m in the source environment).",
                description,
            )

    # Moving wall oscillation (visible: A and P appear in task_description)
    description = _replace_moving_wall_amp_phase(description, target_terrain_config, base_terrain_config)
    # Debris launch velocity (visible in task_description if present)
    description = _replace_debris_velocity_line(description, target_terrain_config, base_terrain_config)

    return description


def update_success_criteria_for_visible_changes(
    base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]
) -> str:
    """
    Update success criteria for visible changes using format:
    [new_value] (originally [old_value] in the source environment).

    base_terrain_config must be the pristine/source environment; otherwise
    "originally ... in the source environment" is misleading.
    """
    criteria = base_success_criteria
    default_leakage = 0.001

    # Leakage rate
    target_leakage = target_terrain_config.get("max_leakage_rate", default_leakage)
    base_leakage = base_terrain_config.get("max_leakage_rate", default_leakage)
    if target_leakage != base_leakage:
        pattern_le = r"(1\. \*\*Leakage Rate\*\*: Total leakage <= )(\d+\.?\d*%)"
        if re.search(pattern_le, criteria):
            criteria = re.sub(
                pattern_le,
                f"\\g<1>{target_leakage*100:.2f}% (originally {base_leakage*100:.2f}% in the source environment)",
                criteria,
            )
        else:
            pattern_lt = r"(1\. \*\*Leakage Rate\*\*: Total leakage < )(\d+\.?\d*%)"
            if re.search(pattern_lt, criteria):
                criteria = re.sub(
                    pattern_lt,
                    f"\\g<1>{target_leakage*100:.2f}% (originally {base_leakage*100:.2f}% in the source environment)",
                    criteria,
                )

    return criteria


def get_f01_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns ordered stage configs for F-01: The Dam (difficulty ascending).
    Each stage assigns the same UNIFORM_SUFFIX; hidden mechanics differ.
    """
    return [
        {
            "stage_id": "Stage-1",
            "title": "Low weld ceiling (threshold physics)",
            "mutation_description": "Single lever: reduced weld force ceiling (just below what the stock design survives).",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "joint_break_force": 41000.0,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-2",
            "title": "Elastic reservoir granules",
            "mutation_description": "Single lever: raised restitution on every fluid particle so impacts rebound through the pile—multi-bounce chain reactions and impulsive lateral loading instead of the damped slosh the stock dam assumes.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "fluid_particle_restitution": 0.78,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-3",
            "title": "Fragile welds + moving squeeze + fast snap",
            "mutation_description": "Combined: reduced weld ceiling, 2-step failure persistence, and wider downstream wall oscillation (no extra friction—keeps the task solvable while baseline still fails).",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "joint_break_force": 40000.0,
                "joint_break_consecutive_steps": 2,
                "downstream_wall_amplitude": 0.55,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-4",
            "title": "Heavier world + harder debris on top of Stage-3",
            "mutation_description": "All Stage-3 couplings plus elevated gravity and faster debris launches—competing overload from dead load, squeeze, and impacts.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "joint_break_force": 40000.0,
                "joint_break_consecutive_steps": 2,
                "downstream_wall_amplitude": 0.55,
                "debris_linear_velocity_x": 2.45,
            },
            "physics_config": {
                "gravity": (0, -10.6),
            },
        },
    ]
