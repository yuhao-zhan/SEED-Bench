"""
E-03: Slippery World task curriculum stages (mutations).

All mutations change INVISIBLE physics parameters (global friction, gravity,
linear/angular damping, momentum drain, thrust-scale zone, speed penalty).
The solver agent is NOT told the exact parameter changes; it must infer from feedback.

Stages ordered by difficulty: Stage-1 (easiest, one param) -> Stage-4 (hardest, multiple params).
Each stage is designed so the original reference solution FAILS (environment adaptability).
"""
from __future__ import annotations

from typing import Any, Dict, List


def update_task_description_for_visible_changes(base_description: str, terrain_config: Dict[str, Any]) -> str:
    """Update task description for visible changes. E-03 stages use only invisible params; no change."""
    return base_description


def update_success_criteria_for_visible_changes(base_success_criteria: str, terrain_config: Dict[str, Any]) -> str:
    """Update success criteria for visible changes. E-03 stages use only invisible params; no change."""
    return base_success_criteria


def get_e03_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns ordered stage configs for E-03 variants.
    Each stage: terrain_config, physics_config. No task_description_suffix (invisible params).
    Stage-1/2: one physical parameter change each (hard enough so ref fails).
    Stage-3/4: multiple parameter changes (increasing difficulty).
    """
    return [
        {
            "stage_id": "Stage-1",
            "title": "Higher global friction",
            "mutation_description": "Ground and sled friction increased (0.02 -> 0.14). Momentum is lost faster; ref's fixed gains may not overcome drain zone in time.",
            "task_description_suffix": "",
            "terrain_config": {
                "ground_friction": 0.14,
                "sled_friction": 0.14,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-2",
            "title": "Stronger gravity",
            "mutation_description": "Gravity increased (0, -10) -> (0, -15). Vertical control harder; ref's gravity compensation and climb to checkpoint A may be insufficient.",
            "task_description_suffix": "",
            "terrain_config": {},
            "physics_config": {
                "gravity": (0, -15),
            },
        },
        {
            "stage_id": "Stage-3",
            "title": "Stronger drain + damping",
            "mutation_description": "Momentum drain factor 0.85 -> 0.70; linear_damping 0.5. Velocity decays faster; ref may not reach B or final target in time.",
            "task_description_suffix": "",
            "terrain_config": {},
            "physics_config": {
                "momentum_drain_factor": 0.70,
                "linear_damping": 0.5,
            },
        },
        {
            "stage_id": "Stage-4",
            "title": "Multi-parameter shift",
            "mutation_description": "Gravity (0,-18), friction 0.10, linear_damping 0.6, momentum_drain 0.68, thrust_scale_factor 0.38. Ref's fixed gains and 2x thrust compensation fail.",
            "task_description_suffix": "",
            "terrain_config": {
                "ground_friction": 0.10,
                "sled_friction": 0.10,
            },
            "physics_config": {
                "gravity": (0, -18),
                "linear_damping": 0.6,
                "momentum_drain_factor": 0.68,
                "thrust_scale_factor": 0.38,
            },
        },
    ]
