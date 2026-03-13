"""
D-06: The Catch curriculum stages (mutations).

Mutated tasks vary invisible physical parameters: ball velocity/mass (density),
max joint force, joint fatigue threshold, gravity, wind, damping.
The solver is NOT told exact values; it must infer from environment feedback.
Stage-1/2: single parameter change each (moderate difficulty).
Stage-3/4: multiple parameter changes (hard).
Ordered by difficulty ascending.
"""
from __future__ import annotations

from typing import Any, Dict, List


import re

def update_task_description_for_visible_changes(base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    description = base_description
    
    # Update Mass Budget if changed
    default_mass = 10.0
    target_mass = target_terrain_config.get("max_structure_mass", default_mass)
    base_mass = base_terrain_config.get("max_structure_mass", default_mass)
    if target_mass != base_mass:
        pattern = r"(- \*\*Mass Budget\*\*: Total structure mass < )(\d+\.?\d*)( kg\.)"
        if re.search(pattern, description):
            description = re.sub(
                pattern,
                f"\\g<1>{target_mass:.1f} kg (originally < {base_mass:.1f} kg in the source environment).",
                description
            )

    # Update Beam Limit if changed
    default_beams = 9
    target_beams = target_terrain_config.get("max_beam_count", default_beams)
    base_beams = base_terrain_config.get("max_beam_count", default_beams)
    if target_beams != base_beams:
        pattern = r"(- \*\*Beam Limit\*\*: Maximum )(\d+)( beams\.)"
        if re.search(pattern, description):
            description = re.sub(
                pattern,
                f"\\g<1>{target_beams} beams (originally {base_beams} in the source environment).",
                description
            )

    # Update Joint force limit if changed (VISIBLE: required to solve the task)
    default_joint_force = 880.0
    target_joint = target_terrain_config.get("max_joint_force", default_joint_force)
    base_joint = base_terrain_config.get("max_joint_force", default_joint_force)
    if target_joint != base_joint:
        pattern = r"(- \*\*Joint force limit\*\*: Joints fail if the reaction force exceeds )(\d+\.?\d*)( N in a single step\.)"
        if re.search(pattern, description):
            description = re.sub(
                pattern,
                f"\\g<1>{target_joint:.0f} N (originally {base_joint:.0f} N in the source environment) in a single step.",
                description
            )

    return description


def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    criteria = base_success_criteria

    # Update Mass Budget if changed
    default_mass = 10.0
    target_mass = target_terrain_config.get("max_structure_mass", default_mass)
    base_mass = base_terrain_config.get("max_structure_mass", default_mass)
    if target_mass != base_mass:
        pattern = r"(- \*\*Mass Budget\*\*: Total structure mass < )(\d+\.?\d*)( kg\.)"
        if re.search(pattern, criteria):
            criteria = re.sub(
                pattern,
                f"\\g<1>{target_mass:.1f} kg (originally < {base_mass:.1f} kg in the source environment).",
                criteria
            )

    # Update Joint force limit if changed (VISIBLE)
    default_joint_force = 880.0
    target_joint = target_terrain_config.get("max_joint_force", default_joint_force)
    base_joint = base_terrain_config.get("max_joint_force", default_joint_force)
    if target_joint != base_joint:
        pattern = r"(- \*\*Joint force limit\*\*: Joints fail if the reaction force exceeds )(\d+\.?\d*)( N in a single step\.)"
        if re.search(pattern, criteria):
            criteria = re.sub(
                pattern,
                f"\\g<1>{target_joint:.0f} N (originally {base_joint:.0f} N in the source environment) in a single step.",
                criteria
            )

    return criteria


_D06_SUFFIX = """
## Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables **MIGHT** have changed from the initial environment, **NOT ALL** of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
- **Structural Stress Limits**: The maximum force and fatigue thresholds of joints may have changed, affecting the catcher's proneness to breaking under impact.
- **Projectile Dynamics**: The velocity and launch timing of arriving balls may have changed, altering their arrival frequency and impact energy.
- **Projectile Mass**: The density and mass of the balls may have changed, affecting the momentum that must be absorbed.
- **Gravity**: Variations in the gravitational field may alter the balls' trajectories and the effective weight of the catcher structure.
- **Lateral Forces**: Changes in wind amplitude or other lateral forces may add unexpected horizontal loads to the structure.

**Discovery via feedback**: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., where a joint breaks or how a body moves) to infer the hidden constraints and adapt your design.
"""


def get_d06_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns ordered stage configs for D-06 mutated tasks.
    Each stage: terrain_config + physics_config (invisible params).
    Original solution (6 beams, left + right coverage, low restitution) should fail in all mutated stages.
    """
    return [
        {
            "stage_id": "Stage-1",
            "title": "Weakened Joints",
            "mutation_description": "Max joint force and fatigue threshold significantly lowered. Structure breaks under impact.",
            "task_description_suffix": _D06_SUFFIX,
            "terrain_config": {
                "max_joint_force": 180.0,      # Default 880 -> structure breaks under heavy ball impact
                "joint_fatigue_threshold": 140.0,  # Default 760
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-2",
            "title": "Faster Balls",
            "mutation_description": "All ball velocities +100% and launch times significantly tightened. Sequential absorption extremely difficult.",
            "task_description_suffix": _D06_SUFFIX,
            "terrain_config": {
                "ball_velocity_x": -48.0,   # Default -24
                "ball2_velocity_x": -52.0,  # Default -26
                "ball3_velocity_x": -48.0,  # Default -24
                "ball4_velocity_x": -56.0,  # Default -28
                "ball5_velocity_x": -50.0,  # Default -25
                "ball6_velocity_x": -52.0,  # Default -26
                "ball7_velocity_x": -50.0,  # Default -25
                "second_ball_launch_time": 0.20,  # Default 0.4
                "third_ball_launch_time": 0.50,   # Default 1.0
                "fourth_ball_launch_time": 0.80,   # Default 1.3
                "fifth_ball_launch_time": 1.10,    # Default 1.8
                "sixth_ball_launch_time": 1.40,    # Default 2.2
                "seventh_ball_launch_time": 1.70,  # Default 2.7
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-3",
            "title": "Heavy Impact",
            "mutation_description": "Much heavier balls + significantly lower joint limits + high ball velocities. Extreme impact momentum.",
            "task_description_suffix": _D06_SUFFIX,
            "terrain_config": {
                "ball_density": 250.0,         # Default 95 -> much heavier balls
                "max_joint_force": 420.0,      # Default 880
                "joint_fatigue_threshold": 300.0,  # Default 760
                "ball_velocity_x": -40.0,
                "ball2_velocity_x": -42.0,
                "ball3_velocity_x": -40.0,
                "ball4_velocity_x": -44.0,
                "ball5_velocity_x": -41.0,
                "ball6_velocity_x": -42.0,
                "ball7_velocity_x": -41.0,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-4",
            "title": "Hostile Environment",
            "mutation_description": "Stronger gravity + heavier balls + lower joint limits + higher wind + faster balls. Full hostile.",
            "task_description_suffix": _D06_SUFFIX,
            "terrain_config": {
                "ball_density": 150.0,         # Default 95
                "max_joint_force": 480.0,      # Default 880
                "joint_fatigue_threshold": 380.0,  # Default 760
                "ball_velocity_x": -32.0,
                "ball2_velocity_x": -35.0,
                "ball3_velocity_x": -32.0,
                "ball4_velocity_x": -36.0,
                "ball5_velocity_x": -33.0,
                "ball6_velocity_x": -34.0,
                "ball7_velocity_x": -33.0,
                "wind_amplitude": 8.0,         # Default 5.0 -> stronger lateral wind
            },
            "physics_config": {
                "gravity": (0, -14.0),         # Default -10 -> stronger gravity
            },
        },
    ]
