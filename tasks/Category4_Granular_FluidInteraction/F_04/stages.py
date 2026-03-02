"""
F-04: The Filter task curriculum stages (mutations).

Mutated tasks vary invisible physical parameters: mix ratio (small/medium/large counts),
viscosity (linear/angular damping), particle friction, gravity, min_purity.
The solver is NOT told exact values; it must infer from environment feedback.
Stage-1/2: single parameter change each. Stage-3/4: multiple parameter changes.
Ordered by difficulty ascending.
"""
from __future__ import annotations

from typing import Any, Dict, List


def update_task_description_for_visible_changes(base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update task description for visible changes."""
    return base_description


def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update success criteria for visible changes."""
    return base_success_criteria


def get_f04_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns ordered stage configs for F-04 mutated tasks.
    Original reference solution (two-layer sieve, fixed gaps/nudge) should fail in all mutated stages.
    """
    return [
        {
            "stage_id": "Stage-1",
            "title": "Viscous atmosphere",
            "mutation_description": "Linear and angular damping increased; particles respond more slowly to nudge.",
            "task_description_suffix": """
## Environmental Warning
The atmosphere in the feed and separation region has become more viscous.
Particle motion and settling behavior may differ from nominal conditions.
Use simulation feedback to infer the new dynamics and adapt your design and control.
""",
            "terrain_config": {"min_purity": 0.42},
            "physics_config": {
                "linear_damping": 0.88,
                "angular_damping": 0.88,
            },
        },
        {
            "stage_id": "Stage-2",
            "title": "Skewed mix ratio",
            "mutation_description": "Mix ratio changed: more large and medium, fewer small. Load and contamination risk increase.",
            "task_description_suffix": """
## Environmental Warning
The composition of the particle mixture has changed.
The relative proportions of particle types may differ from what you expect.
Use feedback to ensure your separator still achieves the required purity.
""",
            "terrain_config": {
                "mix": {
                    "count_small": 10,
                    "count_medium": 20,
                    "count_large": 20,
                    "count_third_small": 10,
                    "count_third_medium": 20,
                    "count_third_large": 20,
                },
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-3",
            "title": "Viscous and skewed",
            "mutation_description": "Higher damping + skewed mix + raised purity target.",
            "task_description_suffix": """
## Environmental Warning
Multiple physical conditions have changed: fluid viscosity and mixture composition differ from nominal.
The required separation quality may also be stricter.
Infer the new environment from simulation feedback and adapt your design and control.
""",
            "terrain_config": {
                "mix": {
                    "count_small": 10,
                    "count_medium": 22,
                    "count_large": 22,
                    "count_third_small": 10,
                    "count_third_medium": 22,
                    "count_third_large": 22,
                },
                "min_purity": 0.42,
            },
            "physics_config": {
                "linear_damping": 0.28,
                "angular_damping": 0.28,
            },
        },
        {
            "stage_id": "Stage-4",
            "title": "Heavy, viscous, and skewed",
            "mutation_description": "Stronger gravity + high damping + skewed mix + higher purity + stickier particles.",
            "task_description_suffix": """
## Environmental Warning
Several physical conditions have changed: effective weight, viscosity, mixture composition, and particle-surface interaction may all differ from nominal.
Infer the new environment from feedback and adapt accordingly.
""",
            "terrain_config": {
                "mix": {
                    "count_small": 8,
                    "count_medium": 22,
                    "count_large": 24,
                    "count_third_small": 8,
                    "count_third_medium": 22,
                    "count_third_large": 24,
                    "friction": 0.52,
                    "restitution": 0.04,
                },
                "min_purity": 0.44,
            },
            "physics_config": {
                "gravity": (0, -14.0),
                "linear_damping": 0.32,
                "angular_damping": 0.32,
            },
        },
    ]
