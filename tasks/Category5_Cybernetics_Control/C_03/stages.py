"""
C-03: The Seeker task curriculum stages (mutations).

Five tasks in total: baseline (no mutation) + Stage-1 through Stage-4, difficulty ascending.
Mutated tasks change invisible physical parameters (target speed, ground friction, damping, impulse budget).
Do NOT reveal exact parameter values in task_description_suffix; agent must infer from feedback.
- Stage-1 / Stage-2: single parameter change each (hard enough that reference solution fails).
- Stage-3 / Stage-4: multiple parameter changes; difficulty increases.
"""

from __future__ import annotations

from typing import Any, Dict, List
import re

def update_task_description_for_visible_changes(base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update task description for visible changes."""
    description = base_description
    target_dist = target_terrain_config.get("rendezvous_distance")
    target_v = target_terrain_config.get("rendezvous_rel_speed")
    
    if target_dist is not None and target_dist != 6.0:
        pattern = r"(getting close \(<)(\d+\.?\d*)(m\))"
        description = re.sub(pattern, f"\\g<1>{target_dist:.1f}m (originally < 6.0m))", description)
    if target_v is not None and target_v != 1.8:
        pattern = r"(matching velocity \(rel speed < )(\d+\.?\d*)( m/s\))"
        description = re.sub(pattern, f"\\g<1>{target_v:.1f} m/s (originally < 1.8 m/s))", description)
        
    return description


def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update success criteria for visible changes."""
    criteria = base_success_criteria
    target_dist = target_terrain_config.get("rendezvous_distance")
    
    if target_dist is not None and target_dist != 6.0:
        # success_criteria has "Maintain distance <= 8.5 m" which relates to rendezvous_dist + 2.5
        new_track_dist = target_dist + 2.5
        pattern = r"(Maintain distance <= )(\d+\.?\d*)( m from target)"
        criteria = re.sub(pattern, f"\\g<1>{new_track_dist:.1f} m from target (originally <= 8.5 m)", criteria)
        
    return criteria


def get_c03_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns ordered stage configs for C-03: The Seeker task variants.
    """
    task_description_suffix = """
## Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables **MIGHT** have changed from the initial environment, **NOT ALL** of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
- **External object dynamics**: Variations in the movement speed of the target object may occur, affecting interception timing.
- **Proximity requirements**: Distance constraints for a successful rendezvous or docking may be adjusted.
- **Relative velocity limits**: The tolerance for relative speed during the final approach phase may be altered.
- **Resource availability**: The total energy or propellant available for maneuvers may differ from standard.
- **Translational resistance**: Environmental resistance (linear damping) to the vehicle's motion may vary.
- **Rotational resistance**: Resistance to changes in the vehicle's orientation (angular damping) may have changed.
- **Surface traction**: Alterations in friction may occur, significantly affecting acceleration and braking efficiency.

**Discovery via feedback**: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., how the vehicle overshoots or stalls) to infer the hidden constraints and adapt your design.
"""
    return [
        {
            "stage_id": "Stage-1",
            "title": "Faster target",
            "mutation_description": "Target base speed increased; velocity matching and slot timing harder.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {
                "target_speed": 2.2,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-2",
            "title": "Strict Rendezvous and Budget",
            "mutation_description": "Stricter rendezvous conditions and tight impulse budget.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {
                "rendezvous_distance": 2.5,
                "track_distance": 5.0,
                "rendezvous_rel_speed": 0.8,
                "impulse_budget": 8500.0,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-3",
            "title": "Strict Rendezvous and Damping",
            "mutation_description": "Stricter distance and speed requirements for rendezvous with higher damping.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {
                "rendezvous_distance": 3.0,
                "track_distance": 5.5,
                "rendezvous_rel_speed": 1.0,
            },
            "physics_config": {
                "linear_damping": 0.85,
                "angular_damping": 0.85,
            },
        },
        {
            "stage_id": "Stage-4",
            "title": "Hostile Seeker Environment",
            "mutation_description": "Extreme target speed, negligible friction, very tight budget.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {
                "target_speed": 2.8,
                "track_distance": 5.0,
                "ground_friction": 0.01,
                "impulse_budget": 9000.0,
                "rendezvous_distance": 2.5,
                "rendezvous_rel_speed": 0.8,
            },
            "physics_config": {
                "linear_damping": 0.9,
                "angular_damping": 0.9,
            },
        },
    ]
