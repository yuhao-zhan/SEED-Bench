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


def update_task_description_for_visible_changes(base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update task description for visible changes."""
    return base_description


def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update success criteria for visible changes."""
    return base_success_criteria


def get_c04_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns ordered stage configs for C-04: The Escaper mutated tasks.
    Original solution uses UNLOCK_BACKWARD_STEPS=25; env default BACKWARD_STEPS_REQUIRED=20.
    """
    task_description_suffix = """
Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables MIGHT have changed from the initial environment, NOT ALL of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
 - whisker_delay_steps: Unexpected latency in proximity sensor (whisker) feedback.
 - backward_steps_required: Changes in the behavioral duration required to unlock progression.
 - backward_speed_max: Stricter speed limits for the backward movement phase.
 - slip_friction: Variations in surface traction, affecting movement precision.
 - momentum_drain_damping: Increased environmental resistance, causing faster loss of kinetic energy.
 - whisker_blind_front_x_lo/hi: Discovery of dead zones in sensor coverage in specific regions.
 - gravity: Alterations in the gravitational field affecting buoyancy and motion.
 - linear_damping: Increased resistance to movement through the environment.
 - current_force_back: Constant external forces opposing forward progress.
 - wind_base_down / wind_oscillation_amp: Static and oscillating environmental disturbances.

Discovery via feedback: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., where a joint breaks or how a body moves) to infer the hidden constraints and adapt your design.
"""
    return [
        {
            "stage_id": "Stage-1",
            "title": "Sensor Delay",
            "mutation_description": "Whisker sensors return readings with 8-step delay; obstacle avoidance and timing break.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {
                "whisker_delay_steps": 8,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-2",
            "title": "Stricter Unlock Condition",
            "mutation_description": "Behavioral unlock requires more consecutive backward-slow steps and lower max speed; agent's 25-step unlock fails.",
            "task_description_suffix": task_description_suffix,
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
            "task_description_suffix": task_description_suffix,
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
            "task_description_suffix": task_description_suffix,
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
