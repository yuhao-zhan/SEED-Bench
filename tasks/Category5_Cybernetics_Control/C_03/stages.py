"""
C-03: The Seeker task curriculum stages (mutations).

Five tasks in total: baseline (no mutation) + Stage-1 through Stage-4, difficulty ascending.
Mutated tasks change invisible physical parameters (target speed, ground friction, damping, impulse budget).
Do NOT reveal exact parameter values in task_description_suffix; agent must infer from feedback.
- Stage-1 / Stage-2: single parameter change each (hard enough that reference solution fails).
- Stage-3 / Stage-4: multiple parameter changes; difficulty increases.
"""

from __future__ import annotations

from typing import Any, Dict, List


def get_c03_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns ordered stage configs for C-03: The Seeker task variants.

    Each stage dict:
      - stage_id: str (e.g. "Stage-1")
      - title: str
      - mutation_description: str (for logs, not shown to solver)
      - task_description_suffix: str (generic warning; do NOT give exact parameter values for invisible physics)
      - terrain_config: dict (merged with defaults in Sandbox)
      - physics_config: dict (merged with defaults in Sandbox)
    """
    return [
        {
            "stage_id": "Stage-1",
            "title": "Faster target",
            "mutation_description": "Target base speed increased; velocity matching and slot timing harder.",
            "task_description_suffix": """
## Environmental note
Target motion may be more dynamic than in the nominal setting. Use step_count and evaluator feedback to adapt your approach and timing.
""",
            "terrain_config": {
                "target_speed": 2.2,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-2",
            "title": "Low traction",
            "mutation_description": "Ground friction reduced; seeker slips more under thrust, harder to hold position.",
            "task_description_suffix": """
## Environmental note
Surface traction may differ from the nominal setting. Observe how the seeker responds to thrust and use feedback to adapt.
""",
            "terrain_config": {
                "ground_friction": 0.04,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-3",
            "title": "Faster target + slip + damping",
            "mutation_description": "Target speed up, ground friction down, linear/angular damping up; multi-parameter change.",
            "task_description_suffix": """
## Environmental note
Multiple physical conditions differ from the nominal setting (e.g. target motion, traction, and how quickly the vehicle loses momentum). Use feedback to identify and adapt.
""",
            "terrain_config": {
                "target_speed": 2.0,
                "ground_friction": 0.18,
            },
            "physics_config": {
                "linear_damping": 0.85,
                "angular_damping": 0.85,
            },
        },
        {
            "stage_id": "Stage-4",
            "title": "High difficulty combo",
            "mutation_description": "Faster target, very low friction, tighter impulse budget, higher damping.",
            "task_description_suffix": """
## Environmental note
Physical environment is significantly different from the nominal setting (target motion, traction, thrust budget, and vehicle dynamics). Rely on evaluator feedback to discover and adapt.
""",
            "terrain_config": {
                "target_speed": 2.4,
                "ground_friction": 0.10,
                "impulse_budget": 14000.0,
            },
            "physics_config": {
                "linear_damping": 0.9,
                "angular_damping": 0.9,
            },
        },
    ]
