"""
C-02: The Lander task curriculum stages (mutations).

All mutations use invisible physics parameters (gravity mutation, fuel limits,
damping, thrust delay, wind). No task_description_suffix — agent must infer
from environment feedback.

Stages ordered by difficulty: Stage-1 (single param) -> Stage-4 (multiple params).
"""

from __future__ import annotations

from typing import Any, Dict, List


def get_c02_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns ordered stage configs for C-02: The Lander task variants.
    Each stage: stage_id, title, mutation_description, terrain_config, physics_config.
    """
    return [
        # Stage-1: Gravity mutation mid-flight — ref uses fixed GRAVITY=10, will miscalculate descent
        {
            "stage_id": "Stage-1",
            "title": "Gravity spike",
            "mutation_description": "Gravity suddenly increases from 10 to 16 m/s² at step 180.",
            "terrain_config": {},
            "physics_config": {
                "gravity_mutation": {
                    "at_step": 180,
                    "gravity_after": (0, -16.0),
                },
            },
        },
        # Stage-2: Limited fuel — ref burns too much during climb/cross
        {
            "stage_id": "Stage-2",
            "title": "Fuel scarcity",
            "mutation_description": "Total fuel reduced, min fuel remaining at landing increased.",
            "terrain_config": {},
            "physics_config": {
                "total_fuel_impulse": 3800.0,
                "min_fuel_remaining_at_landing": 420.0,
            },
        },
        # Stage-3: Gravity mutation + limited fuel
        {
            "stage_id": "Stage-3",
            "title": "Gravity spike and fuel scarcity",
            "mutation_description": "Gravity mutation at step 200 plus reduced fuel budget.",
            "terrain_config": {},
            "physics_config": {
                "gravity_mutation": {"at_step": 200, "gravity_after": (0, -15.5)},
                "total_fuel_impulse": 4000.0,
                "min_fuel_remaining_at_landing": 400.0,
            },
        },
        # Stage-4: Multiple harsh params — gravity mutation + fuel + delay + wind
        {
            "stage_id": "Stage-4",
            "title": "Hostile environment",
            "mutation_description": "Gravity mutation, limited fuel, longer thrust delay, stronger wind.",
            "terrain_config": {},
            "physics_config": {
                "gravity_mutation": {"at_step": 150, "gravity_after": (0, -17.0)},
                "total_fuel_impulse": 3600.0,
                "min_fuel_remaining_at_landing": 450.0,
                "thrust_delay_steps": 6,
                "wind_amplitude": 48.0,
                "gust_amplitude": 75.0,
                "gust_prob": 0.08,
            },
        },
    ]
