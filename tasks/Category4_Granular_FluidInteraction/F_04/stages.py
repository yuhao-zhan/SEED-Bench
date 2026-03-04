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
import re


def update_task_description_for_visible_changes(base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update task description for visible changes."""
    return base_description


def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update success criteria for visible changes."""
    criteria = base_success_criteria
    
    # min_purity
    target_purity = target_terrain_config.get("min_purity", 0.35)
    base_purity = base_terrain_config.get("min_purity", 0.35)
    
    if target_purity != base_purity:
        pattern = r"(1\. \*\*Classification Purity\*\*: Overall purity \(correctly categorized particles / total particles\) >= )(\d+\.?\d*%)"
        # The prompt has >= 35%. Let's use string replace for simplicity if pattern match is tricky
        criteria = criteria.replace(
            f">= {base_purity*100:.0f}%",
            f">= {target_purity*100:.0f}% (originally >= {base_purity*100:.0f}% in the source environment)"
        )
        
    return criteria


def get_f04_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns ordered stage configs for F-04 mutated tasks.
    Each stage: terrain_config + physics_config. Original solution (two-layer sieve, fixed gaps/nudge) should fail in all mutated stages.
    """
    task_description_suffix = """
Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables MIGHT have changed from the initial environment, NOT ALL of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
 - Separation Standards: The minimum required purity for classified material has been updated, demanding more precise filtration.
 - Ambient Viscosity: Variations in atmospheric damping affect how quickly particles respond to external forces and settle into bins.
 - Mixture Composition: The relative proportions of small, medium, and large particles in the feed material may have shifted.
 - Particle Surface Physics: Changes in friction and restitution coefficients alter how grains slide, bounce, and interact with the filter structure.
 - Gravity: The acceleration due to the local gravitational field, influencing the weight and flow rate of the granular material.

Discovery via feedback: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., where a joint breaks or how a body moves) to infer the hidden constraints and adapt your design.
"""
    return [
        {
            "stage_id": "Stage-1",
            "title": "Viscous atmosphere",
            "mutation_description": "Linear and angular damping increased; particles respond more slowly to nudge.",
            "task_description_suffix": task_description_suffix,
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
            "task_description_suffix": task_description_suffix,
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
            "task_description_suffix": task_description_suffix,
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
            "task_description_suffix": task_description_suffix,
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
