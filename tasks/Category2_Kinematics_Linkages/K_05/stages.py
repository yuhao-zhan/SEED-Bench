"""
K-05: The Lifter task curriculum stages (mutations).

All stage definitions live under tasks/Category2_Kinematics_Linkages/K_05.
The solver agent is NOT told exact invisible parameter changes; it must infer from feedback.
"""

from __future__ import annotations

from typing import Any, Dict, List
import re


def update_task_description_for_visible_changes(base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """
    Update task description to reflect visible physical changes.
    """
    description = base_description
    target_y = target_terrain_config.get("target_object_y", 9.0)
    base_y = base_terrain_config.get("target_object_y", 9.0)
    
    if target_y != base_y:
        # Update "at least y=9.0m"
        pattern = r"(at least y=)(\d+\.?\d*)m"
        description = re.sub(pattern, f"\\g<1>{target_y:.1f}m (originally y={base_y:.1f}m in the source environment)", description)
        
        # Update "at or above y=9.0m"
        pattern2 = r"(at or above y=)(\d+\.?\d*)m"
        description = re.sub(pattern2, f"\\g<1>{target_y:.1f}m (originally y={base_y:.1f}m in the source environment)", description)
        
    return description


def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update success criteria to reflect visible physical changes."""
    criteria = base_success_criteria
    target_y = target_terrain_config.get("target_object_y", 9.0)
    base_y = base_terrain_config.get("target_object_y", 9.0)
    
    if target_y != base_y:
        # Update "Reaches y >= 9.0m"
        pattern = r"(Reaches y >= )(\d+\.?\d*)m"
        criteria = re.sub(pattern, f"\\g<1>{target_y:.1f}m (originally y >= {base_y:.1f}m in the source environment)", criteria)
        
        # Update "holds the object at or above y=9.0m"
        pattern2 = r"(at or above y=)(\d+\.?\d*)m"
        criteria = re.sub(pattern2, f"\\g<1>{target_y:.1f}m (originally y={base_y:.1f}m in the source environment)", criteria)
        
    return criteria


def get_k05_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns ordered stage configs for K-05: The Lifter task variants.
    """
    task_description_suffix = """
## Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables **MIGHT** have changed from the initial environment, **NOT ALL** of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
- **Atmospheric Wind**: Constant lateral wind forces may act on all objects.
- **Narrow Clearance Obstacles**: The environment may feature ceilings with narrow gaps that restrict the lifter platform's maximum width.
- **Object Center of Mass**: The internal weight distribution of the target object may be non-uniform, causing it to tilt or slide unpredictably.
- **Joint Fragility**: Mechanical joints may have a maximum tolerance and break under excessive stress or reaction forces.
- **Surface Friction**: The object and platform surfaces may have significantly reduced friction, making it harder to secure the payload.
- **Target Height & Object Mass**: The final lifting height and the mass of the target object might be drastically increased.

**Discovery via feedback**: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., where a joint breaks or how a body moves) to infer the hidden constraints and adapt your design.
"""
    return [
        {
            "stage_id": "Stage-1",
            "title": "Severe Hurricane Wind",
            "mutation_description": "Powerful lateral wind (400N) blows everything away.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {},
            "physics_config": {"wind_force": (400.0, 0.0)},
        },
        {
            "stage_id": "Stage-2",
            "title": "The Needle's Eye",
            "mutation_description": "Extremely narrow ceiling gap (1.2m) prevents wide platforms or walls.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {
                "ceiling_gap": {"x_min": 3.4, "x_max": 4.6, "y": 5.0}
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-3",
            "title": "The Unbalanced Heavyweight",
            "mutation_description": "Heavy object (60kg) with an offset center of mass (0.3m right).",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {
                "target_object_y": 10.5,
                "object": {"mass": 60.0, "com_offset": (0.3, 0.0)}
            },
            "physics_config": {
                "wind_force": (50.0, 0.0) 
            },
        },
        {
            "stage_id": "Stage-4",
            "title": "The Master's Gauntlet",
            "mutation_description": "Combined wind, narrow gap, heavy load, and fragile joints.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {
                "ceiling_gap": {"x_min": 3.2, "x_max": 4.8, "y": 6.0}, # 1.6m gap
                "target_object_y": 10.0,
                "object": {"mass": 40.0, "friction": 0.2}
            },
            "physics_config": {
                "wind_force": (150.0, 0.0),
                "max_joint_force": 1500.0
            },
        },
    ]
