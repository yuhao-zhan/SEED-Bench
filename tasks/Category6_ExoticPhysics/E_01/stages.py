"""
E-01: Inverted Gravity task curriculum stages (mutations).

Stages use advanced physical anomalies to create non-linear challenges.
Each stage is designed so the original reference solution FAILS.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List


# --- Custom gravity functions ---

def gravity_resonant_violent(t: float) -> tuple:
    """Fast oscillation (0.5s period) with high amplitude to stress fragile joints."""
    g_y = 28.0 * math.sin(2.0 * math.pi * t / 0.5)
    return (0.0, g_y)


def gravity_biased_extreme(t: float) -> tuple:
    """Standard oscillation with constant lateral bias to trigger negative damping instability."""
    g_x = 8.0
    g_y = 15.0 * math.sin(2.0 * math.pi * t / 2.0)
    return (g_x, g_y)


def gravity_chaotic_max(t: float) -> tuple:
    """Violent chaotic 2D gravity with high-frequency components."""
    g_x = 18.0 * math.sin(2.0 * math.pi * t / 1.0)
    g_y = 35.0 * math.cos(2.0 * math.pi * t / 0.7)
    return (g_x, g_y)


def gravity_vortex_singularity(t: float) -> tuple:
    """Extreme vortex gravity forcing rapid multi-directional compensation."""
    phase = 2.0 * math.pi * t / 0.35
    g_x = 25.0 * math.sin(phase)
    g_y = 40.0 * math.cos(phase * 1.3)
    return (g_x, g_y)


TASK_DESCRIPTION_SUFFIX = """
## Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables **MIGHT** have changed from the initial environment, **NOT ALL** of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
- **Arena and Build Zone Boundaries**: Vertical limits of navigable and buildable space may be restricted, requiring more compact designs.
- **Gravity Field Dynamics**: The magnitude, direction, or oscillation frequency of the gravitational field may be altered, creating high acceleration or lateral loads.
- **Motion Damping**: Linear or angular damping may differ from standard values, affecting how vibrations evolve over time.
- **Structural Integrity Thresholds**: Joints may have a finite strength limit, potentially breaking under extreme inertial forces or resonant frequencies.
- **Surface Traction**: The friction coefficient of arena surfaces and obstacles may be altered, affecting designs that rely on surface grip.
- **Logistical Constraints**: The total mass budget or the number of available structural components (beams) may be strictly limited.

**Discovery via feedback**: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., where a joint breaks or how a body moves) to infer the hidden constraints and adapt your design.
"""

import re

def update_task_description_for_visible_changes(
    base_description: str,
    target_terrain_config: Dict[str, Any],
    base_terrain_config: Dict[str, Any],
    target_physics_config: Dict[str, Any] = None,
    base_physics_config: Dict[str, Any] = None,
) -> str:
    """Update task description with visible changes. Format: [new_value] (originally [old_value] in the source environment).
    Caller must pass base_terrain_config and base_physics_config as the SOURCE (unmutated) environment so "originally" is correct."""
    description = base_description
    target_terrain_config = target_terrain_config or {}
    base_terrain_config = base_terrain_config or {}
    target_physics_config = target_physics_config or {}
    base_physics_config = base_physics_config or {}

    # Update Arena y_max
    target_arena_y_max = target_terrain_config.get("arena_y_max", 20.0)
    base_arena_y_max = base_terrain_config.get("arena_y_max", 20.0)
    if target_arena_y_max != base_arena_y_max:
        arena_pattern = r"(- \*\*Arena\*\*: A bounded region with x in \[0, 40\] m and y in \[0, )(\d+\.?\d*)(\] m\.)"
        if re.search(arena_pattern, description):
            description = re.sub(
                arena_pattern,
                f"\\g<1>{target_arena_y_max:.1f}\\g<3> (originally y in [0, {base_arena_y_max:.1f}] m in the source environment).",
                description,
            )

    # Update Build Zone y_max (pattern matches both "]. " and "] (" so substitution is re-applicable for cumulative updates)
    target_bz_y_max = target_terrain_config.get("build_zone_y_max", 18.0)
    base_bz_y_max = base_terrain_config.get("build_zone_y_max", 18.0)
    if target_bz_y_max != base_bz_y_max:
        bz_pattern = r"(- \*\*Build Zone\*\*: Structure must be built within x=\[12\.0, 28\.0\], y=\[6\.0, )(\d+\.?\d*)(\]\.|\] \()"
        if re.search(bz_pattern, description):
            description = re.sub(
                bz_pattern,
                f"\\g<1>{target_bz_y_max:.1f}]. (originally y=[6.0, {base_bz_y_max:.1f}] in the source environment).",
                description,
            )

    # Update Joint strength (finite limit vs no limit)
    default_joint_limit = float("inf")
    target_joint_limit = target_physics_config.get("joint_force_limit", default_joint_limit)
    base_joint_limit = base_physics_config.get("joint_force_limit", default_joint_limit)
    if target_joint_limit != base_joint_limit and target_joint_limit < float("inf"):
        no_limit_phrase = r"(- \*\*Joint strength\*\*: )Joints have no force limit \(they do not break from overload\)\."
        originally_phrase = (
            f"(originally {base_joint_limit:.0f} N in the source environment)."
            if base_joint_limit < float("inf")
            else "(originally no force limit in the source environment)."
        )
        finite_replacement = (
            f"\\g<1>Joints break when reaction force exceeds {target_joint_limit:.0f} N "
            f"{originally_phrase}"
        )
        if re.search(no_limit_phrase, description):
            description = re.sub(no_limit_phrase, finite_replacement, description)
        else:
            # Already finite (e.g. Stage-4 from Stage-1): replace old value with new
            finite_pattern = r"(- \*\*Joint strength\*\*: Joints break when reaction force exceeds )(\d+\.?\d*)( N \(originally .+? in the source environment\)\.)"
            if re.search(finite_pattern, description):
                originally_finite = (
                    f"(originally {base_joint_limit:.0f} N in the source environment)."
                    if base_joint_limit < float("inf")
                    else "(originally no force limit in the source environment)."
                )
                description = re.sub(
                    finite_pattern,
                    f"\\g<1>{target_joint_limit:.0f} N {originally_finite}",
                    description,
                )

    return description


def update_success_criteria_for_visible_changes(
    base_success_criteria: str,
    target_terrain_config: Dict[str, Any],
    base_terrain_config: Dict[str, Any],
    target_physics_config: Dict[str, Any] = None,
    base_physics_config: Dict[str, Any] = None,
) -> str:
    """Update success criteria for visible changes. Format: [new_value] (originally [old_value] in the source environment).
    Caller must pass base_terrain_config and base_physics_config as the SOURCE (unmutated) environment."""
    criteria = base_success_criteria
    target_physics_config = target_physics_config or {}
    base_physics_config = base_physics_config or {}

    default_mass = 200.0
    target_mass = target_physics_config.get("max_structure_mass", default_mass)
    base_mass = base_physics_config.get("max_structure_mass", default_mass)
    if target_mass != base_mass:
        mass_pattern = r"(- \*\*Mass Budget\*\*: Total structure mass <= )(\d+\.?\d*)( kg\.)"
        if re.search(mass_pattern, criteria):
            criteria = re.sub(
                mass_pattern,
                f"\\g<1>{target_mass:.0f} kg (originally {base_mass:.0f} kg in the source environment).",
                criteria,
            )

    default_beams = 12
    target_beams = target_physics_config.get("max_beam_count", default_beams)
    base_beams = base_physics_config.get("max_beam_count", default_beams)
    if target_beams != base_beams:
        beam_pattern = r"(- \*\*Beam Limit\*\*: Maximum )(\d+)( beams\.)"
        if re.search(beam_pattern, criteria):
            criteria = re.sub(
                beam_pattern,
                f"\\g<1>{int(target_beams)} beams (originally {int(base_beams)} beams in the source environment).",
                criteria,
            )

    default_joint_limit = float("inf")
    target_joint_limit = target_physics_config.get("joint_force_limit", default_joint_limit)
    base_joint_limit = base_physics_config.get("joint_force_limit", default_joint_limit)
    if target_joint_limit != base_joint_limit and target_joint_limit < float("inf"):
        no_limit_phrase = r"(- \*\*Joint strength\*\*: )Joints have no force limit \(they do not break from overload\)\."
        originally_phrase = (
            f"(originally {base_joint_limit:.0f} N in the source environment)."
            if base_joint_limit < float("inf")
            else "(originally no force limit in the source environment)."
        )
        finite_replacement = (
            f"\\g<1>Joints break when reaction force exceeds {target_joint_limit:.0f} N "
            f"{originally_phrase}"
        )
        if re.search(no_limit_phrase, criteria):
            criteria = re.sub(no_limit_phrase, finite_replacement, criteria)
        else:
            finite_pattern = r"(- \*\*Joint strength\*\*: Joints break when reaction force exceeds )(\d+\.?\d*)( N \(originally .+? in the source environment\)\.)"
            if re.search(finite_pattern, criteria):
                originally_finite = (
                    f"(originally {base_joint_limit:.0f} N in the source environment)."
                    if base_joint_limit < float("inf")
                    else "(originally no force limit in the source environment)."
                )
                criteria = re.sub(
                    finite_pattern,
                    f"\\g<1>{target_joint_limit:.0f} N {originally_finite}",
                    criteria,
                )

    return criteria


def get_e01_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns ordered stage configs.
    Stages 1-2: Single variable non-linear challenges.
    Stages 3-4: Multi-variable complexity.
    """
    return [
        {
            "stage_id": "Stage-1",
            "title": "Fragile Structural Resonance",
            "mutation_description": "Extremely fragile joints (limit 600) under high-frequency gravity. Standard structures will disintegrate.",
            "task_description_suffix": TASK_DESCRIPTION_SUFFIX,
            "terrain_config": {
                "arena_y_max": 20.0,
                "build_zone_y_max": 18.0,
            },
            "physics_config": {
                "gravity": gravity_resonant_violent,
                "joint_force_limit": 600.0,
            },
        },
        {
            "stage_id": "Stage-2",
            "title": "Supercritical Instability",
            "mutation_description": "Extreme negative damping (-1.0) and reduced vertical clearance. Requires near-perfect equilibrium and rigid anchoring.",
            "task_description_suffix": TASK_DESCRIPTION_SUFFIX,
            "terrain_config": {
                "arena_y_max": 16.8,
                "build_zone_y_max": 16.5,
                "friction": 0.0,
            },
            "physics_config": {
                "gravity": gravity_biased_extreme,
                "linear_damping": -1.0,
            },
        },
        {
            "stage_id": "Stage-3",
            "title": "Mass-Constrained Turbulence",
            "mutation_description": "Strict mass budget (55kg) + chaotic 2D gravity. Forces lightweight, minimalist structural design.",
            "task_description_suffix": TASK_DESCRIPTION_SUFFIX,
            "terrain_config": {
                "arena_y_max": 18.0,
                "build_zone_y_max": 17.0,
            },
            "physics_config": {
                "gravity": gravity_chaotic_max,
                "max_structure_mass": 55.0,
            },
        },
        {
            "stage_id": "Stage-4",
            "title": "Singularity Point",
            "mutation_description": "Combined negative damping (-0.4), extreme vortex gravity, fragile joints (300), and zero friction.",
            "task_description_suffix": TASK_DESCRIPTION_SUFFIX,
            "terrain_config": {
                "arena_y_max": 16.0,
                "build_zone_y_max": 15.5,
                "friction": 0.0,
            },
            "physics_config": {
                "gravity": gravity_vortex_singularity,
                "linear_damping": -0.4,
                "joint_force_limit": 300.0,
                "max_beam_count": 6,
            },
        },
    ]
