"""
K-02: The Climber task curriculum stages (mutations).

All stage definitions live under tasks/Category2_Kinematics_Linkages/K_02.
The solver agent is NOT told the exact parameter changes; it must infer from feedback.
"""

from __future__ import annotations
from typing import Any, Dict, List

def update_task_description_for_visible_changes(base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update task description to reflect visible physical changes only."""
    return base_description

def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update success criteria for visible changes only."""
    return base_success_criteria

def get_k02_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns overhauled stage configs for K-02: The Climber task variants.
    Difficulty is escalated through fundamentally different environmental mechanics requiring structural redesigns.
    """

    UNIFORM_SUFFIX = """
## Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables **MIGHT** have changed from the initial environment, **NOT ALL** of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
 - **Geological Instability**: The ground platform or lower surfaces may spontaneously disintegrate or drop away.
 - **Kinematic Hazards**: Heavy debris or boulders may intermittently fall along the climbing vector.
 - **Seismic Resonance**: The vertical climbing surface may exhibit violent lateral oscillations.
 - **Structural Integrity Thresholds**: Joints between components may have severely altered breaking limits for tensile and shear forces.
 - **Atmospheric Shear Zones**: At specific high altitudes, localized atmospheric vortexes may exert extreme outward or upward aerodynamic forces.

**Discovery via feedback**: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., ground dropping, debris impact, or shattering joints) to infer the hidden constraints and adapt your design structure.
"""

    return [
        {
            "stage_id": "Stage-1",
            "title": "Abyssal Chasm",
            "mutation_description": "The ground vanishes at 1.0s. Any structure built from the ground will fall. Requires exclusive wall anchoring.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "destroy_ground_time": 1.0,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-2",
            "title": "Meteor Shower",
            "mutation_description": "Heavy boulders fall along the wall. The agent must build a robust slanted deflector roof.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "boulder_interval": 1.5,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-3",
            "title": "Tectonic Resonance",
            "mutation_description": "Wall vibrates intensely. Rigid joints will snap due to high reaction forces. Must use flexible joints.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "wall_oscillation_amp": 0.15,
                "wall_oscillation_freq": 10.0,
            },
            "physics_config": {
                "max_joint_force": 500.0,
            },
        },
        {
            "stage_id": "Stage-4",
            "title": "Ascension Vortex",
            "mutation_description": "Above y=15, a moderate wind pushes outward (-50N) and upward (+1N). Combined with brittle joints.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "vortex_y": 15.0,
                "vortex_force_x": -50.0,
                "vortex_force_y": 1.0,
            },
            "physics_config": {
                "max_joint_force": 300.0,
            },
        },
    ]
