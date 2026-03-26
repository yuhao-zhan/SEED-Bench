"""
F-01: The Dam task curriculum stages (mutations).

Mutations combine hidden levers (e.g. particle restitution, gravity, debris speed) with visible
terrain keys that appear in the task text. `update_task_description_for_visible_changes` syncs
weld force/steps, leak %, reservoir fill height in the **task description** string.
`update_success_criteria_for_visible_changes` only syncs **leakage rate** lines in **success criteria**
(fill height and weld parameters are not repeated there).

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
    
    # Capture the parenthetical explanation if it exists
    line_content = description[start:end]
    suffix = ""
    paren_start = line_content.find(" (")
    if paren_start != -1:
        suffix = line_content[paren_start:]

    force_part = f"{target_force:.0f} N"
    if target_force != base_force:
        force_part += f" (originally {base_force:.0f} N in the source environment)"
    steps_part = f"{target_steps} consecutive simulation steps"
    if target_steps != base_steps:
        steps_part += (
            f" (originally {base_steps} consecutive simulation steps in the source environment)"
        )
    
    # Reconstruct line with prefix, force, steps, and original suffix
    new_line = f"{marker}{force_part} for {steps_part}{suffix}"
    return description[:start] + new_line + description[end:]


def update_task_description_for_visible_changes(
    base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]
) -> str:
    """
    Update task description for visible changes using format:
    [new_value] (originally [old_value] in the source environment).
    """
    description = base_description
    
    # Map of parameter keys to their labels and regex patterns in task_description
    visible_params = [
        ("max_leakage_rate", r"(the leakage rate does not exceed )(\d+\.?\d*%)(\.)", lambda v: f"{v*100:.2f}%"),
        ("fluid_height", r"(\*\*Reservoir fill height\*\*: )(\d+\.?\d* m)(\.)", lambda v: f"{v:.1f} m"),
        ("max_structure_mass", r"(- \*\*Mass Budget\*\*: Total structure mass <= )(\d+\.?\d* kg)()", lambda v: f"{v:.0f} kg"),
        ("max_beam_count", r"(\(minimum \d+, maximum )(\d+)(\))", lambda v: f"{v}"),
        ("min_beam_count", r"(\(minimum )(\d+)(, maximum \d+\))", lambda v: f"{v}"),
        ("max_joint_count", r"(- \*\*Joint Limit\*\*: Maximum )(\d+)( beam-to-beam joints)", lambda v: f"{v}"),
        ("max_beams_middle_strip", r"(at most )(\d+)( beam \(forces bridge topology\))", lambda v: f"{v}"),
        ("max_beams_right_strip", r"(Right strip \[13.4, 13.6\] may contain at most )(\d+)( beams)", lambda v: f"{v}"),
        ("min_beams_per_band", r"(At least )(\d+)( beam centers must lie in each vertical band)", lambda v: f"{v}"),
        ("min_beam_bottom_y", r"(no beams allowed below y=)(\d+\.?\d*m)()", lambda v: f"{v:.1f}m"),
        ("max_beam_width", r"(Maximum beam width is )(\d+\.?\d* m)(;)", lambda v: f"{v:.1f} m"),
        ("max_beam_height", r"(maximum beam height is )(\d+\.?\d* m)(\.)", lambda v: f"{v:.1f} m"),
    ]

    defaults = {
        "max_leakage_rate": 0.001,
        "fluid_height": 7.0,
        "max_structure_mass": 380.0,
        "max_beam_count": 18,
        "min_beam_count": 10,
        "max_joint_count": 15,
        "max_beams_middle_strip": 1,
        "max_beams_right_strip": 2,
        "min_beams_per_band": 3,
        "min_beam_bottom_y": 0.5,
        "max_beam_width": 0.6,
        "max_beam_height": 1.5,
    }

    for key, pattern, formatter in visible_params:
        target_val = target_terrain_config.get(key, defaults.get(key))
        base_val = base_terrain_config.get(key, defaults.get(key))
        if target_val is not None and base_val is not None and target_val != base_val:
            if re.search(pattern, description):
                description = re.sub(
                    pattern,
                    f"\\g<1>{formatter(target_val)} (originally {formatter(base_val)} in the source environment)\\g<3>",
                    description,
                )

    # Joint break force + consecutive steps (special handling for combined line)
    default_break = 50000.0
    default_steps = 3
    target_break = float(target_terrain_config.get("joint_break_force", default_break))
    base_break = float(base_terrain_config.get("joint_break_force", default_break))
    target_steps = int(target_terrain_config.get("joint_break_consecutive_steps", default_steps))
    base_steps = int(base_terrain_config.get("joint_break_consecutive_steps", default_steps))
    if target_break != base_break or target_steps != base_steps:
        description = _replace_weld_constraint_line(
            description,
            target_force=target_break,
            base_force=base_break,
            target_steps=target_steps,
            base_steps=base_steps,
        )

    return description


def update_success_criteria_for_visible_changes(
    base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]
) -> str:
    """
    Update success criteria for visible changes using format:
    [new_value] (originally [old_value] in the source environment).
    """
    criteria = base_success_criteria
    
    visible_params = [
        ("max_leakage_rate", r"(1\. \*\*Leakage Rate\*\*: Total leakage <= )(\d+\.?\d*%)(\.)", lambda v: f"{v*100:.2f}%"),
        ("max_structure_mass", r"(- \*\*Mass Budget\*\*: Total structure mass <= )(\d+\.?\d* kg)()", lambda v: f"{v:.0f} kg"),
        ("max_beam_count", r"(- \*\*Beam Limit\*\*: Between \d+ and )(\d+)( beams)", lambda v: f"{v}"),
        ("min_beam_count", r"(- \*\*Beam Limit\*\*: Between )(\d+)( and \d+ beams)", lambda v: f"{v}"),
        ("max_joint_count", r"(- \*\*Joint Limit\*\*: Maximum )(\d+)( beam-to-beam joints)", lambda v: f"{v}"),
    ]

    defaults = {
        "max_leakage_rate": 0.001,
        "max_structure_mass": 380.0,
        "max_beam_count": 18,
        "min_beam_count": 10,
        "max_joint_count": 15,
    }

    for key, pattern, formatter in visible_params:
        target_val = target_terrain_config.get(key, defaults.get(key))
        base_val = base_terrain_config.get(key, defaults.get(key))
        if target_val is not None and base_val is not None and target_val != base_val:
            if re.search(pattern, criteria):
                criteria = re.sub(
                    pattern,
                    f"\\g<1>{formatter(target_val)} (originally {formatter(base_val)} in the source environment)\\g<3>",
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
