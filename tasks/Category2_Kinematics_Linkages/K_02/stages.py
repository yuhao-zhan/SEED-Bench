"""
K-02: The Climber task curriculum stages (mutations).

All stage definitions live under tasks/Category2_Kinematics_Linkages/K_02.
The solver agent is NOT told the exact parameter changes; it must infer from feedback.
"""

from __future__ import annotations

from typing import Any, Dict, List


def update_task_description_for_visible_changes(base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """
    Update task description to reflect visible physical changes only.
    """
    return base_description


def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update success criteria for visible changes only."""
    return base_success_criteria


def get_k02_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns ordered stage configs for K-02: The Climber task variants.
    """
    task_description_suffix = """
## Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables **MIGHT** have changed from the initial environment, **NOT ALL** of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
- **Wall Friction**: The traction and slipperiness of the vertical climbing surface may be altered.
- **Gravity**: The magnitude and direction of the gravitational force may differ from standard.
- **Suction Force Scale**: The scaling factor for the adhesive force of suction pads may be adjusted.
- **Maximum Suction Force**: The peak force limit for individual suction pad attachments may have changed.

**Discovery via feedback**: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., where a joint breaks or how a body moves) to infer the hidden constraints and adapt your design.
"""
    return [
        {
            "stage_id": "Stage-1",
            "title": "Low Wall Friction",
            "mutation_description": "Wall friction reduced from 1.0 to 0.12. Legs and pads slip very easily; original grip is insufficient.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {"wall_friction": 0.12},
            "physics_config": {},
        },
        {
            "stage_id": "Stage-2",
            "title": "Increased Gravity",
            "mutation_description": "Gravity increased from -8 to -20 m/s\u00b2. Climber experiences much higher effective weight; pads and motors insufficient.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {},
            "physics_config": {"gravity": (0, -20.0)},
        },
        {
            "stage_id": "Stage-3",
            "title": "Reduced Friction + Increased Gravity",
            "mutation_description": "Wall friction 0.20, gravity -16 m/s\u00b2. Combined: harder to grip and heavier; original design slips or cannot lift.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {"wall_friction": 0.20},
            "physics_config": {"gravity": (0, -16.0)},
        },
        {
            "stage_id": "Stage-4",
            "title": "Extreme: Low Friction + High Gravity + Weaker Suction",
            "mutation_description": "Wall friction 0.14, gravity -20 m/s\u00b2, pad force scale 35 and max 22 N. Maximum difficulty: slip, weight, and reduced adhesion.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {"wall_friction": 0.14},
            "physics_config": {
                "gravity": (0, -20.0),
                "pad_force_scale": 35.0,
                "max_pad_force": 22.0,
            },
        },
    ]
