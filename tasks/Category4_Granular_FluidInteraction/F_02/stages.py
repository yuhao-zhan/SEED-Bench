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
    task_description_suffix = """
## Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables **MIGHT** have changed from the initial environment, **NOT ALL** of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
- **Thrust Cooldown**: The minimum time required between propulsion strokes may have changed, affecting the frequency and consistency of forward thrust.
- **Opposing Current**: The magnitude of the water's flow against the direction of travel may be altered, resisting forward progress.
- **Liquid Density**: The mass per unit volume of the surrounding fluid may be adjusted, determining the buoyancy and flotation depth of the vehicle.
- **Fluid Drag**: The resistance encountered by bodies moving through the water may vary, impacting velocity and energy efficiency.
- **Wind Intensity**: The strength of atmospheric forces acting on the structure above the waterline may have changed.
- **Ambient Damping**: The rate at which the vehicle's linear and angular momentum are dissipated by the environment may be altered.
- **Gravity**: The acceleration due to the local gravitational field may differ from standard, influencing the effective weight and displacement of the vessel.

**Discovery via feedback**: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode (e.g., where a joint breaks or how a body moves) to infer the hidden constraints and adapt your design.
"""
    return [
        {
            "stage_id": "Stage-1",
            "title": "Slower Paddle Rhythm",
            "mutation_description": "Thrust cooldown increased; each body can thrust only every 6 steps. 9 bodies give ~1.5 thrust/step avg.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {
                "thrust_cooldown_steps": 6,  # Default 3 -> 9 bodies give ~1.5 thrust/step
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-2",
            "title": "Strong Opposing Current",
            "mutation_description": "Opposing current force per kg increased ~2.5x. Vehicle cannot make headway with nominal thrust.",
            "task_description_suffix": task_description_suffix,
            "terrain_config": {
                "current_per_kg": 14.0,  # Default 5.5 -> ~2.5x opposing force
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-3",
            "title": "Dense and Viscous",
            "mutation_description": "Low liquid density (weak buoyancy) + high water drag. Both buoyancy and propulsion severely affected.",
            "task_description_suffix": task_description_suffix,
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
            "task_description_suffix": task_description_suffix,
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
