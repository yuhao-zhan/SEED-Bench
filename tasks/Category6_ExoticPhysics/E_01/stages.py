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


def update_task_description_for_visible_changes(base_description: str, terrain_config: Dict[str, Any]) -> str:
    """Update task description when arena bounds change (visible)."""
    if "arena_y_max" in terrain_config:
        y_max = terrain_config["arena_y_max"]
        suffix = f"\n\n## Arena Change (visible)\nThe arena ceiling has been lowered: valid y range is now [0, {y_max}]. The structure must fit within this reduced height. Build zone y_max may also be reduced accordingly."
        return base_description + suffix
    return base_description


def update_success_criteria_for_visible_changes(base_success_criteria: str, terrain_config: Dict[str, Any]) -> str:
    """Update success criteria for visible changes."""
    if "arena_y_max" in terrain_config:
        y_max = terrain_config["arena_y_max"]
        suffix = f"\n- **Arena bounds**: x in [0, 40], y in [0, {y_max}] (reduced ceiling)."
        return base_success_criteria + suffix
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
            "task_description_suffix": "\n\n## Arena Change (visible)\nThe arena ceiling has been slightly lowered: valid y range is now [0, 16.8]. Build zone y_max is 16.5.",
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
            "task_description_suffix": "\n\n## Arena Change (visible)\nThe arena ceiling has been lowered: valid y range is now [0, 16.5]. Build zone y_max is 16.",
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
            "task_description_suffix": "\n\n## Arena Change (visible)\nThe arena ceiling has been lowered: valid y range is now [0, 16]. Build zone y_max is 15.5.",
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
            "task_description_suffix": "\n\n## Arena Change (visible)\nThe arena ceiling has been significantly lowered: valid y range is now [0, 15.5]. Build zone y_max is 15.",
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
