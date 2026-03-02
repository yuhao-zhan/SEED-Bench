"""
F-02: The Amphibian task curriculum stages (mutations).

Mutated tasks vary invisible physical parameters: liquid density, water drag,
opposing current, headwind burst, gravity, damping. The solver is NOT told
exact values; it must infer from environment feedback.
Stage-1/2: single parameter change each (moderate difficulty).
Stage-3/4: multiple parameter changes (hard).
Ordered by difficulty ascending.
"""
from __future__ import annotations

from typing import Any, Dict, List


def update_task_description_for_visible_changes(base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update task description for visible changes."""
    return base_description


def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    """Update success criteria for visible changes."""
    return base_success_criteria


def get_f02_curriculum_stages() -> List[Dict[str, Any]]:
    """
    Returns ordered stage configs for F-02 mutated tasks.
    Each stage: terrain_config + physics_config (invisible params).
    Original solution (9-paddle raft, lift over pillars) should fail in all mutated stages.
    """
    return [
        {
            "stage_id": "Stage-1",
            "title": "Slower Paddle Rhythm",
            "mutation_description": "Thrust cooldown increased; each body can thrust only every 6 steps. 9 paddles give ~1.5 thrust/step avg.",
            "task_description_suffix": """
## Environmental Warning
Paddle stroke rhythm has changed. Each body can apply thrust less frequently than before.
You may need more paddles or a different propulsion strategy.
""",
            "terrain_config": {
                "thrust_cooldown_steps": 6,  # Default 3 -> 9 bodies give ~1.5 thrust/step
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-2",
            "title": "Strong Opposing Current",
            "mutation_description": "Opposing current force per kg increased ~2.5x. Vehicle cannot make headway with nominal thrust.",
            "task_description_suffix": """
## Environmental Warning
The water current has strengthened. The opposing force is higher than nominal.
Thrust strategies tuned for nominal conditions may no longer suffice.
""",
            "terrain_config": {
                "current_per_kg": 14.0,  # Default 5.5 -> ~2.5x opposing force
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-3",
            "title": "Dense and Viscous",
            "mutation_description": "Low liquid density (weak buoyancy) + high water drag. Both buoyancy and propulsion severely affected.",
            "task_description_suffix": """
## Environmental Warning
Multiple water properties have changed. Buoyancy and water resistance differ from nominal.
Infer the new dynamics from simulation feedback and adapt your design and control.
""",
            "terrain_config": {
                "liquid_density": 350.0,
                "water_drag_coef": 400.0,
                "current_per_kg": 11.0,
                "headwind_burst_per_kg": 1.7,  # Default 0.8
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-4",
            "title": "Hostile Crossing",
            "mutation_description": "Weak buoyancy + high drag + strong current + strong headwind + thrust cooldown increased. Full hostile environment.",
            "task_description_suffix": """
## Environmental Warning
Several physical conditions have changed: buoyancy, water resistance, opposing current, mid-water headwind, and propulsion rhythm.
The crossing is significantly harder than nominal. Infer changes from feedback and adapt accordingly.
""",
            "terrain_config": {
                "liquid_density": 400.0,
                "water_drag_coef": 280.0,
                "current_per_kg": 11.0,  # Default 5.5
                "headwind_burst_per_kg": 2.0,  # Default 0.8
                "thrust_cooldown_steps": 4,  # Default 3 -> 9 bodies give 2 thrust/step avg
            },
            "physics_config": {
                "linear_damping": 1.2,
                "angular_damping": 1.2,
                "gravity": (0, -14.0),  # Stronger gravity -> sink easier
            },
        },
    ]
