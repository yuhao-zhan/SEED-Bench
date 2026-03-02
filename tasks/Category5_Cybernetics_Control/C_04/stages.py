"""
C-04: The Escaper task curriculum stages (mutations).

Mutation dimensions: maze complexity (slip friction), sensor blind zones, sensor delay,
momentum drain, gravity, damping, unlock conditions (backward steps, speed threshold).
All mutations use non-visible physical parameters; agent must infer from feedback.

Stage order: Initial (baseline) < Stage-1 < Stage-2 < Stage-3 < Stage-4 (difficulty ascending).
Stage-1/2: single parameter change each. Stage-3/4: multiple parameters.
"""

from __future__ import annotations

from typing import Any, Dict, List


def get_c04_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns ordered stage configs for C-04: The Escaper mutated tasks.
    Original solution uses UNLOCK_BACKWARD_STEPS=25; env default BACKWARD_STEPS_REQUIRED=20.
    """
    return [
        {
            "stage_id": "Stage-1",
            "title": "Sensor Delay",
            "mutation_description": "Whisker sensors return readings with 8-step delay; obstacle avoidance and timing break.",
            "task_description_suffix": """
## Environmental Warning
Sensing may be subject to latency. Observed distances may not reflect the current physical state.
Use feedback to infer and compensate for any lag or misalignment.
""",
            "terrain_config": {
                "whisker_delay_steps": 8,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-2",
            "title": "Stricter Unlock Condition",
            "mutation_description": "Behavioral unlock requires more consecutive backward-slow steps and lower max speed; agent's 25-step unlock fails.",
            "task_description_suffix": """
## Environmental Warning
Conditions for progressing may differ from nominal. Some behavioral requirements may be stricter.
Infer from feedback what is needed before the exit can be reached.
""",
            "terrain_config": {},
            "physics_config": {
                "backward_steps_required": 35,
                "backward_speed_max": 2.0,
            },
        },
        {
            "stage_id": "Stage-3",
            "title": "Sensor Delay + Stronger Momentum Drain + Slip Zone",
            "mutation_description": "Sensor delay (6 steps), stronger momentum drain, and higher slip friction; navigation and passage through zones harder.",
            "task_description_suffix": """
## Environmental Warning
Multiple environmental factors have shifted. Sensing, zone resistances, and terrain friction may all differ from nominal.
Infer from feedback and adapt your strategy accordingly.
""",
            "terrain_config": {
                "whisker_delay_steps": 6,
                "slip_friction": 0.18,
            },
            "physics_config": {
                "momentum_drain_damping": 20.0,
            },
        },
        {
            "stage_id": "Stage-4",
            "title": "Combined Perturbations",
            "mutation_description": "Gravity, damping, stricter unlock, stronger momentum drain, current, and front sensor blind zone in obstacle region.",
            "task_description_suffix": """
## Environmental Warning
Multiple environmental factors have shifted. Sensing, actuation, dynamics, and behavioral requirements may all differ from nominal.
Infer from feedback and adapt your strategy accordingly.
""",
            "terrain_config": {
                "whisker_delay_steps": 5,
                "whisker_blind_front_x_lo": 4.5,
                "whisker_blind_front_x_hi": 6.5,
            },
            "physics_config": {
                "gravity": (0, -13),
                "linear_damping": 0.7,
                "backward_steps_required": 38,
                "backward_speed_max": 2.2,
                "momentum_drain_damping": 22.0,
                "current_force_back": 32.0,
                "wind_base_down": 12.0,
                "wind_oscillation_amp": 14.0,
            },
        },
    ]
