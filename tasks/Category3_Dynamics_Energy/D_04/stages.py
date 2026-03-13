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
    """
    
    # We dynamically generate the uniform suffix from the union of all mutated variables
    # across the 4 stages to ensure information hiding and embodied discovery.
    # The variables used in our stages are:
    # 1. dead_zone
    # 2. quadratic_damping
    # 3. actuator_fault
    # 4. wind_strength & wind_period (constant extreme wind)
    
    union_variables = {
        "Actuator Dead Zone": "The swing's primary force thrusters may fail to engage within certain spatial regions, requiring momentum to carry the seat through.",
        "Quadratic Damping Anomaly": "The environment may exhibit extreme energy drain that scales exponentially with the swing's velocity, heavily penalizing excessive speed.",
        "Directional Actuator Fault": "The force actuators may be jammed, allowing thrust to be applied in only one horizontal direction.",
        "Extreme Atmospheric Conditions": "Atmospheric or wind conditions may differ from the initial environment in ways that affect the swing's equilibrium and trajectory; use feedback to infer the actual behavior."
    }
    
    bullet_points = "\\n".join([f" - **{k}**: {v}" for k, v in union_variables.items()])
    
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
            "title": "The Dead Zone",
            "mutation_description": "Actuator fails between x=9.5 and x=10.5. Wind pushes it out eventually.",
            "task_description_suffix": _D04_SUFFIX,
            "terrain_config": {
                "dead_zone": [9.5, 10.5],
                "wind_strength": 60.0, # Strong wind to push it out of dead zone
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
            "mutation_description": "Actuator only pushes left, but there is a massive constant wind pushing right.",
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
            "mutation_description": "Right-only actuator, dead zone in the middle, quadratic damping, and constant leftward gale.",
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
