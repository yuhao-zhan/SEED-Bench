"""
F-03: The Excavator — curriculum stages (mutations).

Mutated tasks vary physical parameters: particle friction, gravity, damping,
pit drift, target count, scoop capacity. Invisible changes are not revealed in
the prompt; the solver must infer from feedback. Visible changes (e.g. stricter
target count) are stated in task_description_suffix.
Stage-1/2: single parameter change each. Stage-3/4: multiple parameter changes.
Ordered by difficulty ascending.
"""
from __future__ import annotations

from typing import Any, Dict, List


def update_task_description_for_visible_changes(
    base_description: str, terrain_config: Dict[str, Any]
) -> str:
    """Update task description when stage has visible changes (e.g. min_particles_in_hopper)."""
    return base_description


def update_success_criteria_for_visible_changes(
    base_success_criteria: str, terrain_config: Dict[str, Any]
) -> str:
    """Update success criteria when stage has visible changes."""
    return base_success_criteria


def get_f03_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns ordered stage configs for F-03: The Excavator (difficulty ascending).
    Each stage: stage_id, title, mutation_description, task_description_suffix,
    terrain_config, physics_config. Original reference solution should fail in all mutated stages.
    """
    return [
        {
            "stage_id": "Stage-1",
            "title": "Slippery sand",
            "mutation_description": "Particle friction reduced; sand slides off scoop more easily, fewer grains retained per trip.",
            "task_description_suffix": """
## Environmental Warning
The granular material in the pit behaves differently than nominal conditions. It may be more prone to sliding or spilling.
Use simulation feedback to adapt your scooping and dumping strategy.
""",
            "terrain_config": {
                "particles": {"friction": 0.22, "count": 200, "radius": 0.06, "density": 1500.0, "seed": 42},
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-2",
            "title": "Heavier world",
            "mutation_description": "Gravity increased; arm and scoop feel heavier, timing and clearance may be affected.",
            "task_description_suffix": """
## Environmental Warning
Local gravity differs from nominal. Structural loads and motion dynamics may change.
Infer the new behavior from simulation feedback and adapt your control timing.
""",
            "terrain_config": {},
            "physics_config": {"gravity": (0, -14.0)},
        },
        {
            "stage_id": "Stage-3",
            "title": "Dense atmosphere and slippery grains",
            "mutation_description": "Higher linear/angular damping and lower particle friction; grains slide off more and mechanism coasts less.",
            "task_description_suffix": """
## Environmental Warning
Multiple physical conditions differ from nominal: material behavior and motion resistance.
Use feedback to infer the new environment and adapt your design or control.
""",
            "terrain_config": {
                "particles": {"friction": 0.32, "count": 200, "radius": 0.06, "density": 1500.0, "seed": 42},
            },
            "physics_config": {
                "linear_damping": 0.06,
                "angular_damping": 0.06,
            },
        },
        {
            "stage_id": "Stage-4",
            "title": "Hostile excavation",
            "mutation_description": "Lower particle friction, stronger gravity, pit drift, higher target count, and limited scoop capacity per trip.",
            "task_description_suffix": """
## Environmental Warning
Several physical and task conditions have changed. The pit material may slide more easily; gravity and drift may differ; the required number of particles to deposit is **at least 70** (stricter than nominal). Scoop carry capacity per trip may also be more limited.
Infer the new environment from simulation feedback and adapt to meet the stricter requirement.
""",
            "terrain_config": {
                "particles": {"friction": 0.26, "count": 200, "radius": 0.06, "density": 1500.0, "seed": 42},
                "min_particles_in_hopper": 70,
                "pit_drift_force": 1.8,
                "scoop_capacity": 28,
            },
            "physics_config": {
                "gravity": (0, -15.0),
            },
        },
    ]
