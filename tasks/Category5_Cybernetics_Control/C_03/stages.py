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


def update_task_description_for_visible_changes(base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update task description for visible changes."""
    return base_description


def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update success criteria for visible changes."""
    return base_success_criteria


def get_c03_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns ordered stage configs for C-03: The Seeker task variants.
    """
    task_description_suffix = """
Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables MIGHT have changed from the initial environment, NOT ALL of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
 - target_speed: Variations in the base speed of the target object, affecting interception timing.
 - rendezvous_distance: Stricter proximity requirements for a successful rendezvous.
 - rendezvous_rel_speed: Lower tolerance for relative velocity during the final approach.
 - impulse_budget: Reductions in the total propellant or energy available for maneuvers.
 - linear_damping: Increased environmental resistance to the vehicle's translational motion.
 - angular_damping: Increased resistance to changes in the vehicle's orientation.
 - ground_friction: Alterations in surface traction, affecting acceleration and braking efficiency.

Discovery via feedback: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., where a joint breaks or how a body moves) to infer the hidden constraints and adapt your design.
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
