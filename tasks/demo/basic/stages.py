"""
Basic task curriculum stages (mutations).

All stage definitions live under tasks/basic as requested.
The solver agent is NOT told the exact parameter changes; it must infer from feedback.
"""

from __future__ import annotations

from typing import Any, Dict, List


def get_basic_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns ordered stage configs.

    Each stage dict fields:
      - stage_id: str
      - title: str
      - mutation_description: str (for logs, not shown to solver)
      - task_description_suffix: str (generic warning, no exact numeric changes)
      - terrain_config: dict (passed to DaVinciSandbox)
      - physics_config: dict (passed to DaVinciSandbox)
    """
    return [
        {
            "stage_id": "Stage-1",
            "title": "The Ice World",
            "mutation_description": "Ground friction dropped significantly. High torque causes slipping.",
            "task_description_suffix": """
## Environmental Warning
The terrain has frozen over. The ground is extremely slippery (Ice).
Standard tires may lose traction easily.
""",
            "terrain_config": {
                "ground_friction": 0.1,
                "obstacle_friction": 0.1,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-3",
            "title": "The Mud Pit",
            "mutation_description": "Linear/Angular damping increased. Continuous power needed.",
            "task_description_suffix": """
## Environmental Warning
You are entering a swamp. The air and ground are thick and viscous.
Momentum is reduced. Coasting is difficult.
You need continuous, high-torque power to move effectively.
""",
            "terrain_config": {
                "obstacle_1": {"x": 15, "height": 1.5, "angle": 0.2},  # Reduced from 2.0 to 1.5
                "obstacle_2": {"x": 25, "height": 2.0, "angle": -0.3},  # Reduced from 3.0 to 2.0
            },
            "physics_config": {
                "linear_damping": 1.5,  # Reduced from 5.0 to 1.5 for better solvability
                "angular_damping": 1.5,  # Reduced from 5.0 to 1.5 for better solvability
            },
        },
        {
            "stage_id": "Stage-2",
            "title": "The Steep Canyon",
            "mutation_description": "Obstacle angles are extreme. Center of Mass is critical.",
            "task_description_suffix": """
## Environmental Warning
The terrain has become jagged and steep.
Obstacle geometry is far more extreme than before (including a sharp drop).
Vehicle stability and anti-flip geometry are critical.
""",
            "terrain_config": {
                "obstacle_1": {"x": 15, "height": 3.5, "angle": 0.7},
                "obstacle_2": {"x": 25, "height": 2.0, "angle": -0.8},
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-4",
            "title": "The Heavy Planet",
            "mutation_description": "Gravity increased significantly. Structures break, motors stall.",
            "task_description_suffix": """
## Environmental Warning
Gravity anomaly detected. Structural stress is increased.
Motors must lift much heavier effective weight; weak chassis may collapse.
""",
            "terrain_config": {},
            "physics_config": {"gravity": [0, -30.0]},
        },
        {
            "stage_id": "Stage-5",
            "title": "The Gap",
            "mutation_description": "Terrain has a gap. Falling implies failure; must bridge/jump.",
            "task_description_suffix": """
## Environmental Warning
Seismic activity has created a fracture in the terrain.
There is a wide gap ahead; falling into it implies failure.
You must bridge it or jump it.
""",
            "terrain_config": {"gap": {"x_start": 18, "x_end": 20, "depth": -10}},
            "physics_config": {},
        },
    ]

