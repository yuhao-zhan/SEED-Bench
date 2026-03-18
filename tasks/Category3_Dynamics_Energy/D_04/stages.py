"""
D-04: The Swing curriculum stages (mutations).
"""

from __future__ import annotations

from typing import Any, Dict, List

def get_d04_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Return ordered stage configs for D-04 mutated tasks.
    Order: Stage-1 (one param) -> Stage-2 (one param) -> Stage-3 (multi) -> Stage-4 (multi).
    Difficulty increases so that the reference solution fails in each mutated environment.
    mutation_description is for logs/orchestration only and must NOT be shown to the agent;
    only task_description_suffix is appended to the prompt. Descriptions must not leak
    INVISIBLE values or directions (e.g. actuator left/right, wind direction).
    """
    
    # We dynamically generate the uniform suffix from the union of all mutated variables
    # across the 4 stages to ensure information hiding and embodied discovery.
    # The variables used in our stages are:
    # 1. dead_zone (+ optional dead_zone_min_speed: velocity-gated actuation in zone)
    # 2. quadratic_damping
    # 3. actuator_fault
    # 4. wind_strength & wind_period (constant extreme wind)
    
    union_variables = {
        "Actuator Dead Zone": "The swing's primary force thrusters may exhibit spatial or engagement anomalies; use feedback to infer where and when thrust is available.",
        "Quadratic Damping Anomaly": "The environment may exhibit anomalous energy dissipation; use feedback to infer the actual behavior.",
        "Directional Actuator Fault": "The force actuators may exhibit directional or engagement anomalies; use feedback to infer how thrust is available.",
        "Extreme Atmospheric Conditions": "Atmospheric or wind conditions may differ from the initial environment in ways that affect the swing's equilibrium and trajectory; use feedback to infer the actual behavior."
    }
    
    bullet_points = "\n".join([f" - **{k}**: {v}" for k, v in union_variables.items()])
    
    _D04_SUFFIX = f"""
## Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables **MIGHT** have changed from the initial environment, **NOT ALL** of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
{bullet_points}

**Discovery via feedback**: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., where a joint breaks or how a body moves) to infer the hidden constraints and adapt your design.
"""

    return [
        {
            "stage_id": "Stage-1",
            "title": "The Velocity-Gated Dead Zone",
            "mutation_description": "Actuator fails in an asymmetric central region unless horizontal speed exceeds a critical threshold; thrust is only available in narrow side bands or when crossing the zone at high speed—discovery of the velocity-gate and side-band strategy is required.",
            "task_description_suffix": _D04_SUFFIX,
            "terrain_config": {
                "dead_zone": [9.5, 11.0],
                "dead_zone_min_speed": 14.0,  # High enough so initial solution rarely has |vx|>=14 when crossing → fails
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-2",
            "title": "Quadratic Energy Drain",
            "mutation_description": "High quadratic damping penalizes fast swings. Baseline reaches a terminal amplitude below target.",
            "task_description_suffix": _D04_SUFFIX,
            "terrain_config": {
                "quadratic_damping": 0.25,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-3",
            "title": "One-Way Actuator & Gale",
            "mutation_description": "Directional actuator fault combined with strong constant wind; thrust is available in only one horizontal direction and wind acts in a fixed direction. The agent must discover which directions apply via feedback.",
            "task_description_suffix": _D04_SUFFIX,
            "terrain_config": {
                "actuator_fault": "left_only",
                "wind_strength": 30.0,
                "wind_period": 0.0, # Effectively constant
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-4",
            "title": "The Ultimate Crucible",
            "mutation_description": "Combined directional actuator fault, central dead zone, quadratic damping, and strong constant wind; all directions and magnitudes must be inferred from feedback.",
            "task_description_suffix": _D04_SUFFIX,
            "terrain_config": {
                "actuator_fault": "right_only",
                "dead_zone": [9.8, 10.2],
                "quadratic_damping": 0.10,
                "wind_strength": -25.0,
                "wind_period": 0.0,
            },
            "physics_config": {},
        },
    ]

def update_task_description_for_visible_changes(base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update task description for visible changes."""
    return base_description

def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update success criteria for visible changes."""
    return base_success_criteria
