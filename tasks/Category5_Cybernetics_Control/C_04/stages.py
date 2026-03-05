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
## Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables **MIGHT** have changed from the initial environment, **NOT ALL** of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
- **Proximity sensing latency**: Latency in obstacle detection (whisker) sensor feedback may be present.
- **Behavioral duration requirements**: Changes in the time or steps needed to satisfy progression conditions may occur.
- **Operational speed limits**: Limits on velocity during specific movement phases may be adjusted.
- **Surface traction**: Variations in friction affecting movement precision and stability may occur.
- **Energy dissipation**: Environmental resistance causing loss of kinetic energy may vary.
- **Sensor blind zones**: Regions where sensor coverage is unavailable or unreliable may exist.
- **Gravitational acceleration**: Alterations in the vertical force field affecting motion and buoyancy may be present.
- **Translational resistance**: Resistance to movement through the medium (linear damping) may have changed.
- **Environmental flow**: Constant external forces (e.g., currents) opposing progress in specific directions may vary.
- **Atmospheric disturbances**: Static and oscillating external forces (e.g., wind) affecting stability may be present.

**Discovery via feedback**: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., where the agent gets stuck or drifts) to infer the hidden constraints and adapt your design.
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
                "backward_steps_required": 40,
                "backward_speed_max": 0.6,
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
