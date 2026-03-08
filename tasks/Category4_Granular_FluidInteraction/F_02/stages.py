"""
F-02: The Amphibian task curriculum stages (mutations).
Extreme difficulty to ensure naive solutions fail.
"""
from __future__ import annotations
from typing import Any, Dict, List
import re

def update_task_description_for_visible_changes(base_description: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    description = base_description
    
    # Update thrust cooldown if it's considered a visible change
    default_cooldown = 3
    target_cooldown = int(target_terrain_config.get("thrust_cooldown_steps", default_cooldown))
    base_cooldown = int(base_terrain_config.get("thrust_cooldown_steps", default_cooldown))
    
    if target_cooldown != base_cooldown:
        cooldown_pattern = r"(- \*\*Propulsion\*\*: Use `apply_force\(\)` for paddling\. \*\*Cooldown\*\*: Each component has a )(\d+)(-step cooldown between thrusts\.)"
        if re.search(cooldown_pattern, description):
            description = re.sub(
                cooldown_pattern,
                f"\\g<1>{target_cooldown}\\g<3> (originally {base_cooldown}-step in the source environment)",
                description
            )
            
    return description

def update_success_criteria_for_visible_changes(base_success_criteria: str, target_terrain_config: Dict[str, Any], base_terrain_config: Dict[str, Any]) -> str:
    criteria = base_success_criteria
    
    # Update mass budget if it's considered a visible change
    default_mass = 600.0
    target_mass = float(target_terrain_config.get("max_structure_mass", default_mass))
    base_mass = float(base_terrain_config.get("max_structure_mass", default_mass))
    
    if target_mass != base_mass:
        mass_pattern = r"(- \*\*Mass Budget\*\*: Total structure mass <= )(\d+)( kg\.)"
        if re.search(mass_pattern, criteria):
            criteria = re.sub(
                mass_pattern,
                f"\\g<1>{target_mass:.0f}\\g<3> (originally <= {base_mass:.0f} kg in the source environment)",
                criteria
            )
            
    return criteria

def get_f02_curriculum_stages() -> List[Dict[str, Any]]:
    UNIFORM_SUFFIX = """
## Environmental Anomalies Detected
Sensors indicate that this region exhibits non-standard physical properties.
While the following variables **MIGHT** have changed from the initial environment, **NOT ALL** of them will necessarily be mutated in any given task. You must use active interaction and environmental feedback to deduce which specific conditions apply:
- **Joint Strength**: The maximum force a structural connection can withstand before failing may be limited.
- **Opposing Current**: The magnitude of the water's flow against the direction of travel may be altered.
- **Deep Channel Buoyancy**: The buoyancy provided by the fluid in the central channel may be significantly reduced.
- **Liquid Density**: The mass per unit volume of the fluid may be adjusted.
- **Gravity**: The acceleration due to the local gravitational field may differ.
- **Headwind Burst**: A localized, intense air resistance in the middle of the crossing.
- **Thrust Cooldown**: The minimum time required between propulsion strokes.

**Discovery via feedback**: Your objective is to identify the underlying physical rules of this specific environment through trial and reasoning. Initial standard solutions may fail; analyze the failure mode to infer the hidden constraints and adapt your design.
"""
    return [
        {
            "stage_id": "Stage-1",
            "title": "Fragile Infrastructure",
            "mutation_description": "Extremely fragile joints and sudden headwind.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "max_joint_force": 350.0, 
                "headwind_burst_per_kg": 25.0,
            },
            "physics_config": {},
        },
        {
            "stage_id": "Stage-2",
            "title": "Tsunami Current",
            "mutation_description": "Unstoppable current and high gravity.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "current_per_kg": 600.0, 
            },
            "physics_config": {
                "gravity": (0, -200.0),
            },
        },
        {
            "stage_id": "Stage-3",
            "title": "The Void",
            "mutation_description": "Zero buoyancy + high gravity + opposing current.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "max_joint_force": 800.0,
                "current_per_kg": 150.0, 
                "deep_channel_buoyancy_scale": 0.0,
            },
            "physics_config": {
                "gravity": (0, -180.0),
            },
        },
        {
            "stage_id": "Stage-4",
            "title": "Abyssal Storm",
            "mutation_description": "Total hostile environment.",
            "task_description_suffix": UNIFORM_SUFFIX,
            "terrain_config": {
                "max_joint_force": 300.0,
                "current_per_kg": 800.0, 
                "liquid_density": 500.0,
                "headwind_burst_per_kg": 80.0,
                "thrust_cooldown_steps": 10, 
                "deep_channel_buoyancy_scale": 0.0,
            },
            "physics_config": {
                "gravity": (0, -300.0),
            },
        },
    ]
