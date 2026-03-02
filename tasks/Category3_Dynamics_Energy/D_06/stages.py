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


def update_task_description_for_visible_changes(base_description: str, terrain_config: Dict[str, Any]) -> str:
    """D-06 mutations are all invisible; no visible changes to add to prompt."""
    return base_description


def update_success_criteria_for_visible_changes(base_success_criteria: str, terrain_config: Dict[str, Any]) -> str:
    """D-06 mutations are all invisible; no visible changes to add."""
    return base_success_criteria


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
            "task_description_suffix": """
## Environmental Warning
Structural stress limits have changed. Joints may fail under impact forces that were acceptable before.
Infer the new load limits from simulation feedback and adapt your design.
""",
            "terrain_config": {
                "max_joint_force": 180.0,      # Default 880 -> structure breaks under heavy ball impact
                "joint_fatigue_threshold": 140.0,  # Default 760
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-2",
            "title": "Faster Balls",
            "mutation_description": "All ball velocities +60% and launch times tightened. Sequential absorption much harder.",
            "task_description_suffix": """
## Environmental Warning
Projectile dynamics have changed. Balls arrive faster and closer together than nominal.
Sequential absorption may require different catcher placement or absorption strategy.
""",
            "terrain_config": {
                "ball_velocity_x": -38.0,   # Default -24
                "ball2_velocity_x": -42.0,  # Default -26
                "ball3_velocity_x": -38.0,  # Default -24
                "ball4_velocity_x": -44.0,  # Default -28
                "ball5_velocity_x": -40.0,  # Default -25
                "ball6_velocity_x": -42.0,  # Default -26
                "ball7_velocity_x": -40.0,  # Default -25
                "second_ball_launch_time": 0.28,  # Default 0.4 -> tighter spacing
                "third_ball_launch_time": 0.75,   # Default 1.0
                "fourth_ball_launch_time": 1.0,   # Default 1.3
                "fifth_ball_launch_time": 1.5,    # Default 1.8
                "sixth_ball_launch_time": 1.8,    # Default 2.2
                "seventh_ball_launch_time": 2.2,  # Default 2.7
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-3",
            "title": "Heavy Impact",
            "mutation_description": "Heavier balls + lower joint limits + higher ball velocities. Multiple physics changes.",
            "task_description_suffix": """
## Environmental Warning
Several physical properties have changed: projectile mass, impact limits, and arrival timing.
Infer the new dynamics from simulation feedback and adapt your design.
""",
            "terrain_config": {
                "ball_density": 145.0,         # Default 95 -> heavier balls
                "max_joint_force": 520.0,      # Default 880
                "joint_fatigue_threshold": 400.0,  # Default 760
                "ball_velocity_x": -30.0,
                "ball2_velocity_x": -32.0,
                "ball3_velocity_x": -30.0,
                "ball4_velocity_x": -34.0,
                "ball5_velocity_x": -31.0,
                "ball6_velocity_x": -32.0,
                "ball7_velocity_x": -31.0,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-4",
            "title": "Hostile Environment",
            "mutation_description": "Stronger gravity + heavier balls + lower joint limits + higher wind + faster balls. Full hostile.",
            "task_description_suffix": """
## Environmental Warning
Multiple environmental conditions have changed: gravity, projectile mass, structural limits, and lateral forces.
Infer all changes from simulation feedback and adapt your design accordingly.
""",
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
