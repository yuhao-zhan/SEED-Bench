"""
D-03: Phase-Locked Gate curriculum stages (mutations).

Stage order: Stage-1 < Stage-2 < Stage-3 < Stage-4 (difficulty ascending).
All mutations use non-visible physical parameters (impulse strength, damping, gravity);
do NOT expose exact values in the task prompt — the agent must infer from feedback.
"""

from __future__ import annotations

from typing import Any, Dict, List


def update_task_description_for_visible_changes(
    base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]
) -> str:
    """Update task description only for visible changes."""
    return base_description


def update_success_criteria_for_visible_changes(
    base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]
) -> str:
    """Update success criteria only for visible changes."""
    return base_success_criteria


_D03_SUFFIX = """
## Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables **MIGHT** have changed from the initial environment, **NOT ALL** of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
- **External Track Forces**: The magnitude of impulses applied along the track may vary, affecting the cart's acceleration and peak velocity.
- **Ambient Resistance**: Linear or angular damping across the environment may be altered, causing the cart to shed speed differently.
- **Deceleration Zone Damping**: The resistance within specific slowing zones may have been adjusted, altering how effectively the cart is braked.
- **Gravity**: Changes in the gravitational field may affect the effective weight and friction of the cart as it moves.

**Discovery via feedback**: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., where a joint breaks or how a body moves) to infer the hidden constraints and adapt your design.
"""


def get_d03_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Return ordered stage configs for D-03 mutated tasks.
    Stage-1/2: single physical parameter change (harder so original solution fails).
    Stage-3/4: multiple parameter changes (progressively harder).
    """
    return [
        {
            "stage_id": "Stage-1",
            "title": "Stronger first impulse",
            "mutation_description": "Impulse magnitude in zone [8,9] increased; need more mass to survive speed trap v(9)≥2.8.",
            "task_description_suffix": _D03_SUFFIX,
            "terrain_config": {
                "impulse_magnitude": 2.5,  # default 1.5 — stronger backward kick, original solution may fail v(9)≥2.8
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-2",
            "title": "Higher ambient damping",
            "mutation_description": "Linear and angular damping increased; cart sheds more speed everywhere, v(11) band and gate timing harder.",
            "task_description_suffix": _D03_SUFFIX,
            "terrain_config": {},
            "physics_config": {
                "linear_damping": 0.55,
                "angular_damping": 0.55,
            },
        },
        {
            "stage_id": "Stage-3",
            "title": "Stronger impulses and decel zone",
            "mutation_description": "First impulse, second impulse, and decel zone damping all increased; v(9) and v(11) both harder to meet.",
            "task_description_suffix": _D03_SUFFIX,
            "terrain_config": {
                "impulse_magnitude": 2.5,
                "impulse2_magnitude": 0.95,
                "decel_damping": 4.8,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-4",
            "title": "Heavy world and strong impulses",
            "mutation_description": "Gravity increased, both impulses and decel damping stronger, plus ambient damping; full profile and phase must be re-tuned.",
            "task_description_suffix": _D03_SUFFIX,
            "terrain_config": {
                "impulse_magnitude": 2.6,
                "impulse2_magnitude": 0.95,
                "decel_damping": 4.5,
            },
            "physics_config": {
                "gravity": (0, -12),
                "linear_damping": 0.4,
                "angular_damping": 0.4,
            },
        },
    ]
