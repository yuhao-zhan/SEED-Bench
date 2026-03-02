"""
S-06: The Overhang task curriculum stages (mutations).

All stage definitions live under tasks/Category1_Statics_Equilibrium/S-06.
The solver agent is NOT told the exact parameter changes; it must infer from feedback.
"""

from __future__ import annotations

from typing import Any, Dict, List


def update_task_description_for_visible_changes(base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update task description for visible changes."""
    return base_description


def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update success criteria for visible changes."""
    return base_success_criteria


def get_s06_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns ordered stage configs for S-06: The Overhang task variants.
    
    Each stage dict fields:
      - stage_id: str
      - title: str
      - mutation_description: str (for logs, not shown to solver)
      - task_description_suffix: str (generic warning, no exact numeric changes)
      - terrain_config: dict (passed to Sandbox)
      - physics_config: dict (passed to Sandbox)
    """
    return [
        {
            "stage_id": "Stage-1",
            "title": "Increased Gravity",
            "mutation_description": "Gravity increased from -10 to -14 m/s². Structures experience significantly higher loads.",
            "task_description_suffix": """
## Environmental Warning
Physical conditions in this region have changed.
All structures experience significantly increased loads.
Your overhang structure must be designed to withstand higher structural stresses.
""",
            "terrain_config": {},
            "physics_config": {
                "gravity": (0, -14.0),  # Increased from default -10.0
            },
        },
        {
            "stage_id": "Stage-2",
            "title": "Reduced Friction",
            "mutation_description": "Block friction reduced from 0.5 to 0.08, table friction reduced from 0.5 to 0.08. Blocks slide extremely easily.",
            "task_description_suffix": """
## Environmental Warning
Surface contact properties have changed.
Blocks may slide more easily than in standard conditions.
Your structure must account for these changes to prevent sliding and maintain stability.
""",
            "terrain_config": {
                "block_friction": 0.08,  # Reduced from default 0.5
                "table_friction": 0.08,  # Reduced from default 0.5
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-3",
            "title": "Increased Gravity + Reduced Friction",
            "mutation_description": "Gravity increased from -10 to -13 m/s², friction reduced from 0.5 to 0.18. High load with reduced grip.",
            "task_description_suffix": """
## Environmental Warning
Physical conditions and surface contact properties have changed simultaneously.
All structures experience significantly increased loads, and blocks slide more easily.
Your overhang structure must be designed to withstand higher stresses while preventing sliding.
""",
            "terrain_config": {
                "block_friction": 0.18,  # Reduced from default 0.5
                "table_friction": 0.18,  # Reduced from default 0.5
            },
            "physics_config": {
                "gravity": (0, -13.0),  # Increased from default -10.0
            },
        },
        {
            "stage_id": "Stage-4",
            "title": "Extreme Challenge",
            "mutation_description": "Combined: Low density (0.35) + Very low friction (0.08) + High gravity (-17) + No damping. Maximum difficulty.",
            "task_description_suffix": """
## Environmental Warning
Multiple environmental anomalies detected simultaneously.
Material properties, contact behavior, and structural loads have all changed significantly.
This is an extreme engineering challenge requiring optimal structural design.
Your structure must adapt to all these changes simultaneously to maintain stability.
""",
            "terrain_config": {
                "block_density": 0.35,  # Reduced from default 1.0
                "block_friction": 0.08,  # Reduced from default 0.5
                "table_friction": 0.08,  # Reduced from default 0.5
            },
            "physics_config": {
                "gravity": (0, -17.0),  # Increased from default -10.0
                "linear_damping": 0.0,  # No damping
                "angular_damping": 0.0,  # No damping
            },
        },
    ]
