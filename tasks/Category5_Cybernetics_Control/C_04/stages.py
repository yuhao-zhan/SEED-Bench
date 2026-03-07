"""
C-04: The Escaper task curriculum stages (mutations).

Mutation dimensions:
- Surface traction (ceiling_friction): critical threshold change breaking baseline unlock.
- Shear atmospheric disturbances (shear_wind_gradient): non-linear obstacle requiring momentum slingshot.
- Delay and other parameters for combined difficulty.
"""

from __future__ import annotations

from typing import Any, Dict, List


def update_task_description_for_visible_changes(base_description: str, target_physics_config: Dict[str, Any], base_physics_config: Dict[str, Any]) -> str:
    return base_description

def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    return base_success_criteria

def get_c04_curriculum_stages() -> List[Dict[str, Any]]:
    # DYNAMIC GENERATION OF SUFFIX
    # We must extract the UNION of all physical variables mutated across Stages 1-4.
    # Stage 1: ceiling_friction
    # Stage 2: shear_wind_gradient
    # Stage 3: ceiling_friction, shear_wind_gradient, whisker_delay_steps
    # Stage 4: ceiling_friction, shear_wind_gradient, whisker_delay_steps, gravity, current_force_back, momentum_drain_damping
    
    # Let's map these to descriptive bullet points
    anomalies = {
        "ceiling_friction": "- **Surface traction loss**: Upper boundary surfaces may exhibit near-zero friction, rendering them useless for physical bracing.",
        "shear_wind_gradient": "- **Shear atmospheric flow**: Intense lateral winds that vary dramatically by altitude may create impenetrable aerodynamic barriers at certain heights.",
        "whisker_delay_steps": "- **Proximity sensing latency**: Obstacle detection (whisker) sensor feedback may suffer significant signal delay.",
        "gravity": "- **Gravitational acceleration**: The vertical force field may be amplified, affecting buoyancy and vertical maneuvering.",
        "current_force_back": "- **Environmental flow**: Unidirectional currents opposing forward progress may be drastically stronger.",
        "momentum_drain_damping": "- **Energy dissipation**: Damping zones may exhibit extreme kinetic energy drain, altering speed-control dynamics."
    }
    
    # We dynamically create the bullet list from the union
    union_vars = ["ceiling_friction", "shear_wind_gradient", "whisker_delay_steps", "gravity", "current_force_back", "momentum_drain_damping"]
    bullet_points = "\n".join([anomalies[v] for v in union_vars])
    
    task_description_suffix = f"""
## Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables **MIGHT** have changed from the initial environment, **NOT ALL** of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
{bullet_points}

**Discovery via feedback**: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., where a joint breaks or how a body moves) to infer the hidden constraints and adapt your design.
"""

    return [
        {
            "stage_id": "Stage-1",
            "title": "Frictionless Ceiling",
            "mutation_description": "Ceiling friction reduced to 0. Baseline fails because it cannot generate friction to unlock.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {
                "ceiling_friction": 0.0,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-2",
            "title": "Shear Wind Barrier",
            "mutation_description": "Strong shear wind makes the lower path impossible to traverse directly. Requires momentum slingshot via the upper path.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {
                "ceiling_friction": 0.0,
            },
            "physics_config": {
                "shear_wind_gradient": 120.0,
            },
        },
        {
            "stage_id": "Stage-3",
            "title": "Frictionless Ceiling + Shear Wind + Sensor Delay",
            "mutation_description": "Combines Stage 1 and 2, and adds a 10-step sensor delay, making navigation blind and requiring precise internal state estimation.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {
                "ceiling_friction": 0.0,
                "whisker_delay_steps": 10,
            },
            "physics_config": {
                "shear_wind_gradient": 120.0,
            },
        },
        {
            "stage_id": "Stage-4",
            "title": "Extreme Conflicting Constraints",
            "mutation_description": "Heavy gravity pulls agent down (harder to slingshot), strong backward current, heavy momentum drain, frictionless ceiling, and shear wind.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {
                "ceiling_friction": 0.0,
                "whisker_delay_steps": 12,
            },
            "physics_config": {
                "shear_wind_gradient": 120.0,
                "gravity": (0, -15),
                "current_force_back": 30.0,
                "momentum_drain_damping": 20.0,
            },
        },
    ]
