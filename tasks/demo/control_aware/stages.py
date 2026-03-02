"""
Control-Aware task curriculum stages (mutations).
"""

from __future__ import annotations

from typing import Any, Dict, List


def get_control_aware_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns ordered stage configs.
    """
    return [
        {
            "stage_id": "Stage-1",
            "title": "The Slippery Track",
            "mutation_description": "Track friction increased. Slider needs more control.",
            "task_description_suffix": """
## Environmental Warning
The track has become slippery. Friction has increased.
Speed control becomes more challenging as slider may slide unexpectedly.
""",
            "terrain_config": {
                "track_friction": 0.3,  # Increased friction
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-2",
            "title": "The High Damping Zone",
            "mutation_description": "Linear damping increased. Slider slows down faster.",
            "task_description_suffix": """
## Environmental Warning
You are entering a high-resistance zone. The air is thick and viscous.
Momentum is reduced. Slider slows down faster.
You need continuous control input to maintain desired speeds.
""",
            "terrain_config": {},
            "physics_config": {
                "linear_damping": 1.5,
            },
        },
    ]
