"""
E-01: Inverted Gravity task curriculum stages (mutations).

Stages use a combination of visible (arena shrink) and invisible (gravity, damping, density)
physics changes. The reference structure has top at y~18; shrinking arena_y_max causes failure.

Stages ordered by difficulty: Stage-1 (easiest) to Stage-4 (hardest).
Each stage is designed so the original reference solution FAILS.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List


# --- Custom gravity functions ---

def gravity_base(t: float) -> tuple:
    """Base: period 5s, amplitude ±10."""
    g_y = 10.0 * math.sin(2.0 * math.pi * t / 5.0)
    return (0.0, g_y)


def gravity_fast_strong(t: float) -> tuple:
    """Faster (2.5s) + stronger (amplitude 16)."""
    g_y = 16.0 * math.sin(2.0 * math.pi * t / 2.5)
    return (0.0, g_y)


def gravity_extreme(t: float) -> tuple:
    """Very fast (1.2s) + strong (25) + horizontal component."""
    phase = 2.0 * math.pi * t / 1.2
    g_x = 6.0 * math.sin(phase)
    g_y = 25.0 * math.sin(phase)
    return (g_x, g_y)


TASK_DESCRIPTION_SUFFIX = """
Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables MIGHT have changed from the initial environment, NOT ALL of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
 - Arena and Build Zone Boundaries: The vertical limits of the navigable and buildable space.
 - Gravity: The magnitude, direction, or periodicity of the gravitational field.
 - Damping: Air resistance or internal friction affecting the decay of motion.
 - Material Density: The mass-to-volume ratio of the structural components.

Discovery via feedback: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., where a joint breaks or how a body moves) to infer the hidden constraints and adapt your design.
import re

def update_task_description_for_visible_changes(base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update task description when arena bounds change (visible)."""
    description = base_description

    # Update Arena y_max
    target_arena_y_max = target_terrain_config.get("arena_y_max", 20.0)
    base_arena_y_max = base_terrain_config.get("arena_y_max", 20.0)
    if target_arena_y_max != base_arena_y_max:
        arena_pattern = r"(- \*\*Arena\*\*: A bounded region with x in \[0, 40\] m and y in \[0, )(\d+\.?\d*)(\] m\.)"
        description = re.sub(
            arena_pattern,
            f"\\g<1>{target_arena_y_max:.1f}\\g<3> (originally y in [0, {base_arena_y_max:.1f}] m.)",
            description
        )

    # Update Build Zone y_max
    target_bz_y_max = target_terrain_config.get("build_zone_y_max", 18.0)
    base_bz_y_max = base_terrain_config.get("build_zone_y_max", 18.0)
    if target_bz_y_max != base_bz_y_max:
        bz_pattern = r"(- \*\*Build Zone\*\*: Structure must be built within x=\[12\.0, 28\.0\], y=\[6\.0, )(\d+\.?\d*)(\]\.)"
        description = re.sub(
            bz_pattern,
            f"\\g<1>{target_bz_y_max:.1f}\\g<3> (originally y=[6.0, {base_bz_y_max:.1f}].)",
            description
        )

    return description


def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update success criteria for visible changes."""
    return base_success_criteria


def get_e01_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns ordered stage configs. Reference structure top at y~18; arena_y_max < 18 causes failure.
    All stages shrink arena (visible) so reference fails; Stages 2-4 add invisible physics.
    """
    return [
        {
            "stage_id": "Stage-1",
            "title": "Slightly Reduced Arena",
            "mutation_description": "Arena y_max 16.8 (vs 20); build_zone y_max 16.5. Reference top center at y=17 exceeds bounds.",
            "task_description_suffix": TASK_DESCRIPTION_SUFFIX,
            "terrain_config": {
                "arena_y_max": 16.8,
                "build_zone_y_max": 16.5,
            },
            "physics_config": {"gravity": gravity_base},
        },
        {
            "stage_id": "Stage-2",
            "title": "Reduced Arena + Fast Gravity",
            "mutation_description": "Arena y_max 16.5; gravity period 2.5s, amplitude 16 (2 params).",
            "task_description_suffix": TASK_DESCRIPTION_SUFFIX,
            "terrain_config": {
                "arena_y_max": 16.5,
                "build_zone_y_max": 16.0,
            },
            "physics_config": {"gravity": gravity_fast_strong},
        },
        {
            "stage_id": "Stage-3",
            "title": "Reduced Arena + Negative Damping",
            "mutation_description": "Arena y_max 16.0; linear_damping -0.12, angular_damping -0.04 (3 params).",
            "task_description_suffix": TASK_DESCRIPTION_SUFFIX,
            "terrain_config": {
                "arena_y_max": 16.0,
                "build_zone_y_max": 15.5,
            },
            "physics_config": {
                "gravity": gravity_base,
                "linear_damping": -0.12,
                "angular_damping": -0.04,
            },
        },
        {
            "stage_id": "Stage-4",
            "title": "Maximum Reduction + Extreme Physics",
            "mutation_description": "Arena y_max 15.5, build_zone 15; gravity extreme (period 1.2s, gx+gy); damping -0.1; beam_density 0.5 (4+ params).",
            "task_description_suffix": TASK_DESCRIPTION_SUFFIX,
            "terrain_config": {
                "arena_y_max": 15.5,
                "build_zone_y_max": 15.0,
            },
            "physics_config": {
                "gravity": gravity_extreme,
                "linear_damping": -0.1,
                "angular_damping": -0.03,
                "beam_density_scale": 0.5,
            },
        },
    ]
