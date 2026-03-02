"""
C-06: The Governor task curriculum stages (mutations).

Mutation dimensions used here: measurement delay, torque deadzone, low-speed torque limit,
step-load timing/magnitude, disturbance amplitude/period, cogging/stiction strength.

Each stage contains hidden `physics_config` overrides so the environment behavior changes
without revealing precise numeric values to the agent prompt (agents must infer from feedback).
"""

from __future__ import annotations

from typing import Any, Dict, List


def update_task_description_for_visible_changes(base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update task description for visible changes."""
    return base_description


def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update success criteria for visible changes."""
    return base_success_criteria


def get_c06_curriculum_stages() -> List[Dict[str, Any]]:
    """Returns ordered stage configs for C-06: The Governor task variants.

    Order: Stage-0 baseline (reference), Stage-1..Stage-4 increasing difficulty.
    """
    return [
        {
            "stage_id": "Stage-0",
            "title": "C-06 Reference",
            "mutation_description": "Reference environment (baseline).",
            "task_description_suffix": "",
            "terrain_config": {},
            "physics_config": {},
        },
        {
            "stage_id": "Stage-1",
            "title": "Increased Measurement Delay",
            "mutation_description": "Measurement delay increased (agent sees older velocity).",
            "task_description_suffix": "\n## Environmental Warning\nSensor latency increased; readings may be more sluggish than before.\n",
            "terrain_config": {},
            "physics_config": {
                # Hidden: increase measurement delay so naive delay-compensation must adjust
                "measure_delay_steps": 9,
            },
        },
        {
            "stage_id": "Stage-2",
            "title": "Larger Motor Deadzone",
            "mutation_description": "Motor applies a larger torque deadzone (small commands ignored).",
            "task_description_suffix": "\n## Environmental Warning\nActuators exhibit a larger deadzone — small control commands may have no effect.\n",
            "terrain_config": {},
            "physics_config": {
                # Hidden: reduce low-speed torque availability so escaping stall is harder
                "torque_limit_at_zero": 1.0,
            },
        },
        {
            "stage_id": "Stage-3",
            "title": "Early Heavy Step + Weaker Low-Speed Torque",
            "mutation_description": "Introduce an earlier/heavier step load and reduce low-speed torque availability.",
            "task_description_suffix": "\n## Environmental Warning\nOccasional heavy transient loads occur earlier in the run; low-speed actuation may be weaker.\n",
            "terrain_config": {},
            "physics_config": {
                # Hidden: earlier/larger step load and stronger periodic disturbance
                "step_load_at_step": 1500,
                "step_load_extra": 8.0,
                "disturb_period": 200,
                "disturb_torque": -8.0,
                # Reduce torque available at zero speed (makes stall easier)
                "torque_limit_at_zero": 1.5,
            },
        },
        {
            "stage_id": "Stage-4",
            "title": "Compound: High Delay, Strong Cogging & Stiction",
            "mutation_description": "Combine multiple adversarial hidden changes: very large delay, increased cogging and stiction, higher drag and reduced torque reserve.",
            "task_description_suffix": "\n## Environmental Warning\nMultiple hidden dynamics changed simultaneously — sensing latency, nonlinear loads and stiction are stronger. Precise, robust control is required.\n",
            "terrain_config": {},
            "physics_config": {
                # Combine several harder mutations (hidden to agent)
                "measure_delay_steps": 12,
                "torque_deadzone": 5.5,
                "torque_limit_at_zero": 2.0,
                "k_drag": 1.5,
                "cogging_amplitude": 3.0,
                "stiction_speed_band": 0.8,
                "stiction_factor": 2.2,
            },
        },
    ]
