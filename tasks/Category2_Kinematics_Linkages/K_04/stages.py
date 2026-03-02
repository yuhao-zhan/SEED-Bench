"""
K-04: The Pusher task curriculum stages (mutations).

All stage definitions live under tasks/Category2_Kinematics_Linkages/K_04 as requested.
The solver agent is NOT told the exact parameter changes; it must infer from feedback.
Physical changes are invisible (ground friction, gravity, damping, object CoM) - no prompt updates.
"""

from __future__ import annotations

from typing import Any, Dict, List


def update_task_description_for_visible_changes(base_description: str, terrain_config: Dict[str, Any]) -> str:
    """
    Update task description to reflect visible physical changes.
    
    For invisible physical parameters (gravity, damping, friction, CoM), changes are NOT reflected.
    
    Args:
        base_description: Original task description
        terrain_config: Terrain configuration with changes
        
    Returns:
        Updated task description with visible changes explicitly marked
    """
    # K-04 mutations use only invisible params; no visible changes to describe
    return base_description


def update_success_criteria_for_visible_changes(base_success_criteria: str, terrain_config: Dict[str, Any]) -> str:
    """
    Update success criteria to reflect visible physical changes.
    
    Args:
        base_success_criteria: Original success criteria
        terrain_config: Terrain configuration with changes
        
    Returns:
        Updated success criteria with visible changes explicitly marked
    """
    return base_success_criteria


def get_k04_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns ordered stage configs for K-04: The Pusher task variants.
    Order: Stage-1, Stage-2 (one param each), Stage-3, Stage-4 (multiple params), difficulty increasing.
    Baseline = no env_overrides (default environment).
    
    Each stage dict fields:
      - stage_id: str
      - title: str
      - mutation_description: str (for logs, not shown to solver)
      - task_description_suffix: str (generic warning, no exact numeric changes)
      - terrain_config: dict (passed to Sandbox)
      - physics_config: dict (passed to Sandbox)
    """
    return [
        # --- Stage-1: one invisible param — low ground friction (wheel slip) ---
        {
            "stage_id": "Stage-1",
            "title": "Low Ground Friction",
            "mutation_description": "Ground friction reduced from 1.2 to 0.18. Wheels slip; original pusher loses traction.",
            "task_description_suffix": """
## Environmental Warning
Surface contact properties in this region have changed.
The ground may provide different traction than in standard conditions.
Your pusher must maintain effective contact and overcome resistance under these conditions.
""",
            "terrain_config": {
                "ground_friction": 0.18,
            },
            "physics_config": {"do_sleep": False},
        },
        # --- Stage-2: one invisible param — object center of mass offset ---
        {
            "stage_id": "Stage-2",
            "title": "Object Center of Mass Offset",
            "mutation_description": "Object center of mass offset (0.25, 0.15) in local coords. Object tends to rotate when pushed; harder to push straight.",
            "task_description_suffix": """
## Environmental Warning
The object's load distribution may differ from standard conditions.
Pushing behavior and stability of the object may be affected.
Your pusher must adapt to ensure controlled, straight-line pushing.
""",
            "terrain_config": {
                "object": {"center_of_mass_offset": (0.25, 0.15)},
            },
            "physics_config": {"do_sleep": False},
        },
        # --- Stage-3: multiple invisible params — low ground friction + increased gravity ---
        {
            "stage_id": "Stage-3",
            "title": "Low Friction + Heavy World",
            "mutation_description": "Ground friction 0.22, gravity -14 m/s². Poor traction + heavier effective load.",
            "task_description_suffix": """
## Environmental Warning
Multiple physical conditions have changed: surface traction and gravitational load.
Your pusher must adapt to reduced ground grip and increased effective weight.
""",
            "terrain_config": {
                "ground_friction": 0.22,
            },
            "physics_config": {
                "gravity": (0, -14.0),
                "do_sleep": False,
            },
        },
        # --- Stage-4: multiple params — low friction + gravity + object damping + CoM offset ---
        {
            "stage_id": "Stage-4",
            "title": "Extreme Challenge",
            "mutation_description": "Ground friction 0.16, gravity -15, object damping 0.4, object CoM offset (0.2, 0.12). Maximum difficulty.",
            "task_description_suffix": """
## Environmental Warning
Multiple environmental anomalies detected: surface traction, gravitational load,
object dynamics, and load distribution have all changed significantly.
This is an extreme challenge requiring optimal pusher design and control.
""",
            "terrain_config": {
                "ground_friction": 0.16,
                "object": {
                    "linear_damping": 0.4,
                    "angular_damping": 0.4,
                    "center_of_mass_offset": (0.2, 0.12),
                },
            },
            "physics_config": {
                "gravity": (0, -15.0),
                "do_sleep": False,
            },
        },
    ]
